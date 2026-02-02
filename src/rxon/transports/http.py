from asyncio import sleep
from logging import getLogger
from ssl import SSLContext
from typing import Any, AsyncIterator, Dict, Optional, cast

from aiohttp import ClientError, ClientSession, ClientTimeout, TCPConnector, WSMsgType

from ..constants import (
    AUTH_HEADER_WORKER,
    ENDPOINT_TASK_NEXT,
    ENDPOINT_TASK_RESULT,
    ENDPOINT_WORKER_HEARTBEAT,
    ENDPOINT_WORKER_REGISTER,
    PROTOCOL_VERSION,
    PROTOCOL_VERSION_HEADER,
    STS_TOKEN_ENDPOINT,
    WS_ENDPOINT,
)
from ..exceptions import (
    RxonAuthError,
    RxonError,
    RxonNetworkError,
    RxonProtocolError,
)
from ..models import (
    Heartbeat,
    ProgressUpdatePayload,
    TaskPayload,
    TaskResult,
    TokenResponse,
    WorkerCommand,
    WorkerRegistration,
)
from ..utils import json_dumps, to_dict
from .base import Transport

logger = getLogger(__name__)


class HttpTransport(Transport):
    """
    HTTP implementation of the RXON Transport using aiohttp.
    Supports Long-Polling for tasks and WebSocket for commands.
    """

    def __init__(
        self,
        base_url: str,
        worker_id: str,
        token: str,
        ssl_context: Optional[SSLContext] = None,
        session: Optional[ClientSession] = None,
        verify_ssl: bool = True,
        result_retries: int = 3,
        result_retry_delay: float = 0.1,
    ):
        self.base_url = base_url.rstrip("/")
        self.worker_id = worker_id
        self.token = token
        self.ssl_context = ssl_context
        self._session = session
        self._own_session = False
        self._headers = {
            AUTH_HEADER_WORKER: self.token,
            PROTOCOL_VERSION_HEADER: PROTOCOL_VERSION,
        }
        self.verify_ssl = verify_ssl
        self.result_retries = result_retries
        self.result_retry_delay = result_retry_delay
        self._ws_connection = None

    async def connect(self) -> None:
        if not self._session:
            connector = TCPConnector(ssl=self.ssl_context) if self.ssl_context else None
            self._session = ClientSession(connector=connector, json_serialize=json_dumps)
            self._own_session = True

    async def close(self) -> None:
        if self._ws_connection and not self._ws_connection.closed:
            await self._ws_connection.close()
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        timeout: Optional[ClientTimeout] = None,
    ) -> Any:
        """
        Internal helper to execute HTTP requests with automatic 401 retry and error handling.
        """
        if not self._session:
            raise RxonNetworkError("Transport not connected. Call connect() first.")

        url = f"{self.base_url}{endpoint}"
        headers = self._headers.copy()
        attempts = 2
        for attempt in range(attempts):
            try:
                async with self._session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=timeout,
                ) as resp:
                    if resp.status == 204:
                        return None

                    if resp.status == 401:
                        if attempt == 0:
                            logger.warning(f"Unauthorized (401) from {endpoint}. Refreshing token.")
                            if await self.refresh_token():
                                headers = self._headers.copy()  # Update headers with new token
                                continue
                            else:
                                raise RxonAuthError(f"Token refresh failed after 401 from {endpoint}")
                        else:
                            raise RxonAuthError(f"Unauthorized (401) from {endpoint} after retry")

                    if resp.status >= 400:
                        text = await resp.text()
                        raise RxonProtocolError(
                            f"HTTP {resp.status}: {text}", details={"status": resp.status, "body": text}
                        )

                    return await resp.json()

            except (ClientError, TimeoutError) as e:
                # If it's a network/timeout error, we wrap it
                raise RxonNetworkError(f"Network error during {method} {endpoint}: {str(e)}") from e
            except RxonError:
                # Re-raise known errors
                raise
            except Exception as e:
                # Catch-all for unexpected errors
                logger.exception("Unexpected error in transport")
                raise RxonError(f"Unexpected transport error: {e}") from e
        return None

    async def refresh_token(self) -> Optional[TokenResponse]:
        if not self._session:
            logger.error("Cannot refresh token: Session not initialized")
            return None

        url = f"{self.base_url}{STS_TOKEN_ENDPOINT}"
        try:
            async with self._session.post(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    valid_fields = {k: v for k, v in data.items() if k in TokenResponse._fields}
                    token_response = TokenResponse(**valid_fields)
                    self.token = token_response.access_token
                    self._headers[AUTH_HEADER_WORKER] = self.token
                    logger.info(f"Token refreshed successfully. Expires in {token_response.expires_in}s")
                    return token_response
                else:
                    logger.error(f"Failed to refresh token: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
        return None

    async def register(self, registration: WorkerRegistration) -> bool:
        """
        Register the holon shell with the orchestrator.
        Raises RxonError on failure.
        """
        payload = to_dict(registration)
        await self._request("POST", ENDPOINT_WORKER_REGISTER, json=payload)
        return True

    async def poll_task(self, timeout: float = 30.0) -> Optional[TaskPayload]:
        """
        Long-poll for the next available task.
        Raises RxonError on network/protocol failures.
        """
        endpoint = ENDPOINT_TASK_NEXT.format(worker_id=self.worker_id)
        client_timeout = ClientTimeout(total=timeout + 5)

        data = await self._request("GET", endpoint, timeout=client_timeout)

        if data:
            valid_fields = {k: v for k, v in data.items() if k in TaskPayload._fields}
            return TaskPayload(**valid_fields)
        return None

    async def send_result(
        self, result: TaskResult, max_retries: int | None = None, initial_delay: float | None = None
    ) -> bool:
        """
        Send task execution result back to orchestrator.
        Retries on RxonNetworkError.
        Raises RxonError if all retries fail.
        """
        payload = to_dict(result)
        retries = max_retries if max_retries is not None else self.result_retries
        delay = initial_delay if initial_delay is not None else self.result_retry_delay

        last_error = None
        for i in range(retries):
            try:
                await self._request("POST", ENDPOINT_TASK_RESULT, json=payload)
                return True
            except RxonNetworkError as e:
                logger.warning(f"Network error sending result (attempt {i + 1}/{retries}): {e}")
                last_error = e
            except RxonError as e:
                logger.error(f"Protocol/Auth error sending result: {e}")
                raise e
            if i < retries - 1:
                await sleep(delay * (2**i))
        if last_error:
            raise last_error
        return False

    async def send_heartbeat(self, heartbeat: Heartbeat) -> bool:
        endpoint = ENDPOINT_WORKER_HEARTBEAT.format(worker_id=self.worker_id)
        payload = to_dict(heartbeat)
        try:
            await self._request("PATCH", endpoint, json=payload)
            return True
        except RxonError as e:
            logger.warning(f"Heartbeat failed: {e}")
            raise e

    async def send_progress(self, progress: ProgressUpdatePayload) -> bool:
        if self._ws_connection and not self._ws_connection.closed:
            try:
                await self._ws_connection.send_json(to_dict(progress))
                return True
            except Exception as e:
                logger.warning(f"Failed to send progress via WebSocket: {e}")
                return False
        return False

    async def listen_for_commands(self) -> AsyncIterator[WorkerCommand]:
        if not self._session:
            return

        ws_url = self.base_url.replace("http", "ws", 1) + WS_ENDPOINT
        try:
            async with self._session.ws_connect(ws_url, headers=self._headers) as ws:
                self._ws_connection = cast(Any, ws)
                logger.info(f"Connected to WebSocket: {ws_url}")

                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        try:
                            data = msg.json()
                            valid_fields = {k: v for k, v in data.items() if k in WorkerCommand._fields}
                            yield WorkerCommand(**valid_fields)
                        except Exception as e:
                            logger.warning(f"Invalid command received: {e}")
                    elif msg.type == WSMsgType.ERROR:
                        logger.error(f"WebSocket connection closed with error: {ws.exception()}")
                        break
        except (ClientError, TimeoutError) as e:
            logger.error(f"WebSocket connection error: {e}")
            raise RxonNetworkError(f"WebSocket connection failed: {e}") from e
        except Exception as e:
            logger.error(f"WebSocket unexpected error: {e}")
            raise RxonError(f"WebSocket error: {e}") from e
        finally:
            self._ws_connection = None
