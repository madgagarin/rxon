from asyncio import Queue, wait_for
from asyncio import TimeoutError as AsyncTimeoutError
from typing import AsyncIterator, List, Optional

from .models import (
    Heartbeat,
    ProgressUpdatePayload,
    TaskPayload,
    TaskResult,
    TokenResponse,
    WorkerCommand,
    WorkerRegistration,
)
from .transports.base import Transport


class MockTransport(Transport):
    """
    In-memory mock transport for testing Workers without a real Orchestrator.
    """

    def __init__(self, worker_id: str = "mock-worker", token: str = "mock-token"):
        self.worker_id = worker_id
        self.token = token
        self.connected = False
        self.registered: List[WorkerRegistration] = []
        self.heartbeats: List[Heartbeat] = []
        self.results: List[TaskResult] = []
        self.progress_updates: List[ProgressUpdatePayload] = []
        self.task_queue: Queue[TaskPayload] = Queue()
        self.command_queue: Queue[WorkerCommand] = Queue()

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.connected = False

    async def register(self, registration: WorkerRegistration) -> bool:
        self.registered.append(registration)
        return True

    async def poll_task(self, timeout: float = 30.0) -> Optional[TaskPayload]:
        try:
            return await wait_for(self.task_queue.get(), timeout=timeout)
        except AsyncTimeoutError:
            return None

    async def send_result(self, result: TaskResult, max_retries: int = 3, initial_delay: float = 0.1) -> bool:
        self.results.append(result)
        return True

    async def send_heartbeat(self, heartbeat: Heartbeat) -> bool:
        self.heartbeats.append(heartbeat)
        return True

    async def send_progress(self, progress: ProgressUpdatePayload) -> bool:
        self.progress_updates.append(progress)
        return True

    async def listen_for_commands(self) -> AsyncIterator[WorkerCommand]:
        while self.connected:
            cmd = await self.command_queue.get()
            yield cmd

    async def refresh_token(self) -> Optional[TokenResponse]:
        return TokenResponse(access_token=f"refreshed-{self.token}", expires_in=3600, worker_id=self.worker_id)

    def push_task(self, task: TaskPayload):
        """Inject a task into the queue for the worker to pick up."""
        self.task_queue.put_nowait(task)

    def push_command(self, command: WorkerCommand):
        """Inject a command into the queue."""
        self.command_queue.put_nowait(command)
