from asyncio import sleep
from logging import getLogger
from ssl import SSLContext
from typing import AsyncIterator, Optional

from aiohttp import ClientSession, ClientTimeout, TCPConnector, WSMsgType

from ..constants import (
    AUTH_HEADER_WORKER,
    ENDPOINT_TASK_NEXT,
    ENDPOINT_TASK_RESULT,
    ENDPOINT_WORKER_HEARTBEAT,
    ENDPOINT_WORKER_REGISTER,
    STS_TOKEN_ENDPOINT,
    WS_ENDPOINT,
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
from ..utils import to_dict
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
        self._headers = {AUTH_HEADER_WORKER: self.token}
        self.verify_ssl = verify_ssl
        self.result_retries = result_retries
        self.result_retry_delay = result_retry_delay
        self._ws_connection = None

    async def connect(self) -> None:
        if not self._session:
            connector = TCPConnector(ssl=self.ssl_context) if self.ssl_context else None
            self._session = ClientSession(connector=connector)
            self._own_session = True

    async def close(self) -> None:
        if self._ws_connection and not self._ws_connection.closed:
            await self._ws_connection.close()
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def _handle_401(self, func, *args, **kwargs):
        """Helper to retry a request once after refreshing the token on 401."""
        if not self._session:
            raise RuntimeError("Transport not connected. Call connect() first.")

        call_headers = kwargs.get("headers", {})
        kwargs["headers"] = {**self._headers, **call_headers}
        resp = await func(*args, **kwargs)

        if resp.status == 401:
            logger.warning(f"Unauthorized (401) from {self.base_url}. Attempting token refresh.")
            resp.close()
            if await self.refresh_token():
                kwargs["headers"] = {**self._headers, **call_headers}
                return await func(*args, **kwargs)
        return resp

    async def refresh_token(self) -> Optional[TokenResponse]:
        if not self._session:
            logger.error("Cannot refresh token: Session not initialized")
            return None

        url = f"{self.base_url}{STS_TOKEN_ENDPOINT}"
        try:
            async with self._session.post(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Safe parsing
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
        if not self._session:
            logger.error("Transport not connected")
            return False

        url = f"{self.base_url}{ENDPOINT_WORKER_REGISTER}"
        payload = to_dict(registration)
        try:
            resp = await self._handle_401(self._session.post, url, json=payload)
            async with resp:
                if resp.status >= 400:
                    logger.error(f"Error registering with {self.base_url}: {resp.status}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Error registering with {self.base_url}: {e}")
            return False

    async def poll_task(self, timeout: float = 30.0) -> Optional[TaskPayload]:
        if not self._session:
            logger.error("Transport not connected")
            return None

        url = f"{self.base_url}{ENDPOINT_TASK_NEXT.format(worker_id=self.worker_id)}"
        client_timeout = ClientTimeout(total=timeout + 5)
        try:
            resp = await self._handle_401(self._session.get, url, timeout=client_timeout)
            async with resp:
                if resp.status == 200:
                    data = await resp.json()
                    valid_fields = {k: v for k, v in data.items() if k in TaskPayload._fields}
                    return TaskPayload(**valid_fields)
                elif resp.status != 204:
                    logger.warning(f"Unexpected status from {self.base_url} during poll: {resp.status}")
        except Exception as e:
            logger.error(f"Error polling tasks from {self.base_url}: {e}")
        return None

    async def send_result(
        self, result: TaskResult, max_retries: int | None = None, initial_delay: float | None = None
    ) -> bool:
        if not self._session:
            logger.error("Transport not connected")
            return False

        url = f"{self.base_url}{ENDPOINT_TASK_RESULT}"
        payload = to_dict(result)

        retries = max_retries if max_retries is not None else self.result_retries
        delay = initial_delay if initial_delay is not None else self.result_retry_delay

        for i in range(retries):
            try:
                resp = await self._handle_401(self._session.post, url, json=payload)
                async with resp:
                    if resp.status == 200:
                        return True
                    logger.error(f"Error sending result (attempt {i + 1}): {resp.status}")
            except Exception as e:
                logger.error(f"Network error sending result: {e}")

            if i < retries - 1:
                await sleep(delay * (2**i))
        return False

    async def send_heartbeat(self, heartbeat: Heartbeat) -> bool:
        if not self._session:
            return False

        url = f"{self.base_url}{ENDPOINT_WORKER_HEARTBEAT.format(worker_id=self.worker_id)}"
        payload = to_dict(heartbeat)
        try:
            resp = await self._handle_401(self._session.patch, url, json=payload)
            async with resp:
                if resp.status >= 400:
                    logger.warning(f"Heartbeat failed: {resp.status}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False

    async def send_progress(self, progress: ProgressUpdatePayload) -> bool:
        if self._ws_connection and not self._ws_connection.closed:
            try:
                await self._ws_connection.send_json(to_dict(progress))
                return True
            except Exception as e:
                logger.warning(f"Failed to send progress via WebSocket: {e}")
        return False

    async def listen_for_commands(self) -> AsyncIterator[WorkerCommand]:
        if not self._session:
            return

        ws_url = self.base_url.replace("http", "ws", 1) + WS_ENDPOINT
        try:
            async with self._session.ws_connect(ws_url, headers=self._headers) as ws:
                self._ws_connection = ws  # type: ignore
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
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            self._ws_connection = None
