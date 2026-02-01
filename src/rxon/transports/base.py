from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

from ..models import (
    Heartbeat,
    ProgressUpdatePayload,
    TaskPayload,
    TaskResult,
    TokenResponse,
    WorkerCommand,
    WorkerRegistration,
)


class Transport(ABC):
    """
    Abstract Base Class for RXON Transports (Worker Side).
    Implementations of this class handle the physical communication
    between a Holon Shell (Worker) and its Ghost (Orchestrator).
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection or initialize transport.
        Configuration (endpoint, token, etc.) should be passed to the constructor.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close transport resources.
        """
        pass

    @abstractmethod
    async def register(self, registration: WorkerRegistration) -> bool:
        """
        Register the holon shell with the orchestrator.
        Returns True if successful.
        """
        pass

    @abstractmethod
    async def poll_task(self, timeout: float = 30.0) -> Optional[TaskPayload]:
        """
        Long-poll for the next available task.
        """
        pass

    @abstractmethod
    async def send_result(self, result: TaskResult, max_retries: int = 3, initial_delay: float = 0.1) -> bool:
        """
        Send task execution result back to orchestrator.
        Returns True if successful.
        """
        pass

    @abstractmethod
    async def send_heartbeat(self, heartbeat: Heartbeat) -> bool:
        """
        Update holon status and availability.
        Returns True if successful.
        """
        pass

    @abstractmethod
    async def send_progress(self, progress: ProgressUpdatePayload) -> bool:
        """
        Send real-time progress updates for a running task.
        """
        pass

    @abstractmethod
    def listen_for_commands(self) -> AsyncIterator[WorkerCommand]:
        """
        Listen for incoming commands from the orchestrator (e.g., via WebSocket).
        """
        pass

    @abstractmethod
    async def refresh_token(self) -> Optional[TokenResponse]:
        """
        Refresh the authentication token (e.g. using STS).
        """
        pass


class Listener(ABC):
    """
    Abstract Base Class for RXON Listeners (Orchestrator Side).
    Implementations of this class listen for incoming worker connections
    and route them to the Orchestrator Engine.
    """

    @abstractmethod
    async def start(
        self,
        handler: Callable[[str, Any, dict[str, Any]], Awaitable[Any]],
    ) -> None:
        """
        Start the listener.
        The handler callback accepts (message_type, payload, context) and returns a response.
        Context usually contains authentication info (e.g., 'token', 'worker_id').
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the listener and release ports/resources.
        """
        pass
