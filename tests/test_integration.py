import asyncio

import pytest
from aiohttp import web

from rxon import HttpListener, create_transport
from rxon.models import (
    Heartbeat,
    ProgressUpdatePayload,
    Resources,
    TaskPayload,
    TaskResult,
    WorkerCapabilities,
    WorkerCommand,
    WorkerRegistration,
)
from rxon.utils import to_dict

# --- Fixtures ---


@pytest.fixture
def unused_tcp_port_factory():
    """Factory to find an unused port."""

    def factory():
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    return factory


@pytest.fixture
async def server(unused_tcp_port_factory):
    """
    Starts a real aiohttp server with HttpListener.
    Returns the base_url and the listener instance.
    """
    port = unused_tcp_port_factory()
    app = web.Application()
    listener = HttpListener(app)

    # Simple In-Memory Orchestrator Logic
    state = {"registered": [], "heartbeats": [], "results": [], "tasks_queue": []}

    async def mock_handler(msg_type, payload, context):
        if msg_type == "register":
            state["registered"].append(payload)
            return True
        elif msg_type == "heartbeat":
            state["heartbeats"].append(payload)
            return {"status": "ok"}
        elif msg_type == "poll":
            # Return a task if available
            if state["tasks_queue"]:
                return state["tasks_queue"].pop(0)
            return None  # 204 No Content
        elif msg_type == "result":
            state["results"].append(payload)
            return True
        elif msg_type == "sts_token":
            from rxon.models import TokenResponse

            return TokenResponse(access_token="new_refreshed_token", expires_in=3600, worker_id="test")

    await listener.start(handler=mock_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    base_url = f"http://127.0.0.1:{port}"

    yield base_url, state, listener

    await runner.cleanup()


# --- Tests ---


@pytest.mark.asyncio
async def test_full_cycle(server):
    base_url, state, listener = server
    worker_id = "worker-test-01"
    token = "initial-token"

    # 1. Create Transport
    transport = create_transport(base_url, worker_id, token)
    await transport.connect()

    try:
        # 2. Register
        reg = WorkerRegistration(
            worker_id=worker_id,
            worker_type="cpu",
            supported_tasks=["test"],
            resources=Resources(1, 4),
            installed_software={},
            installed_models=[],
            capabilities=WorkerCapabilities("host", "127.0.0.1", {}),
        )
        success = await transport.register(reg)
        assert success is True
        assert len(state["registered"]) == 1
        assert state["registered"][0]["worker_id"] == worker_id

        # 3. Heartbeat
        hb = Heartbeat(worker_id, "idle", 0.1, [], [], [], None)
        success = await transport.send_heartbeat(hb)
        assert success is True
        assert len(state["heartbeats"]) == 1

        # 4. Poll (Empty)
        task = await transport.poll_task(timeout=1.0)
        assert task is None

        # 5. Poll (With Task)
        # Inject task into server state
        mock_task = TaskPayload(
            job_id="job-1", task_id="task-1", type="echo", params={"msg": "hello"}, tracing_context={}
        )
        state["tasks_queue"].append(mock_task)

        task = await transport.poll_task(timeout=1.0)
        assert task is not None
        assert task.job_id == "job-1"
        assert task.params["msg"] == "hello"

        # 6. Send Result
        res = TaskResult("job-1", "task-1", worker_id, "success", data={"reply": "hello world"})
        success = await transport.send_result(res)
        assert success is True
        assert len(state["results"]) == 1
        assert state["results"][0]["data"]["reply"] == "hello world"

    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_auth_refresh(server):
    """Test that transport handles 401 by refreshing token and retrying."""
    base_url, state, listener = server

    # Override handler to force 401 once
    auth_attempts = 0

    async def auth_fail_handler(msg_type, payload, context):
        nonlocal auth_attempts
        # Simulate 401 on first heartbeat attempt
        if msg_type == "heartbeat":
            token = context.get("token")
            if token == "expired-token":
                raise web.HTTPUnauthorized(text="Token expired")
            return {"status": "ok"}

        if msg_type == "sts_token":
            return {"access_token": "valid-token", "expires_in": 300, "worker_id": "test"}

        return True

    listener.handler = auth_fail_handler

    transport = create_transport(base_url, "worker-auth", "expired-token")
    await transport.connect()

    try:
        hb = Heartbeat("worker-auth", "idle", 0.0, [], [], [], None)

        # This call should:
        # 1. Send heartbeat (fail 401)
        # 2. Call refresh_token (success)
        # 3. Retry heartbeat (success with new token)
        success = await transport.send_heartbeat(hb)

        assert success is True
        assert transport.token == "valid-token"

    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_websocket_flow(server):
    """Test WebSocket connection: receiving commands and sending progress."""
    base_url, state, listener = server
    worker_id = "ws-worker"

    # Event to signal that server received progress
    progress_received = asyncio.Event()

    async def ws_handler(msg_type, payload, context):
        if msg_type == "websocket":
            ws = payload
            # 1. Send a command to the worker
            cmd = WorkerCommand(command="stop_task", task_id="task-99")
            await ws.send_json(to_dict(cmd))

            # 2. Listen for progress updates from worker
            from aiohttp import WSMsgType

            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = msg.json()
                    if data.get("event") == "progress":
                        state["results"].append(data)  # Store in results for verification
                        progress_received.set()
                        # Close connection after receiving progress to finish the test
                        await ws.close()
                elif msg.type == WSMsgType.ERROR:
                    print("ws connection closed with exception %s", ws.exception())

    listener.handler = ws_handler

    transport = create_transport(base_url, worker_id, "token")
    await transport.connect()

    try:
        # Start listening for commands
        # Since listen_for_commands is an async iterator, we iterate over it.
        # It will yield the command sent by server.

        command_iterator = transport.listen_for_commands()

        # We expect the server to send the command immediately upon connection
        command = await anext(command_iterator)

        assert command.command == "stop_task"
        assert command.task_id == "task-99"

        # Now send progress back to server
        # Note: In a real app, listen_for_commands usually runs in a background task.
        # Here we are in the same flow, but send_progress requires self._ws_connection to be set.
        # listen_for_commands sets self._ws_connection BEFORE yielding?
        # Let's check implementation: yes, it sets self._ws_connection = ws then iterates.
        # So while we are inside the loop (or paused at yield), _ws_connection is active.

        prog = ProgressUpdatePayload(
            event="progress", task_id="task-99", job_id="job-1", progress=0.5, message="Halfway"
        )
        sent = await transport.send_progress(prog)
        assert sent is True

        # Wait for server to receive it
        await asyncio.wait_for(progress_received.wait(), timeout=2.0)

        # Verify server state
        assert len(state["results"]) == 1
        assert state["results"][0]["progress"] == 0.5

    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_server_error_handling(server):
    """Test that listener gracefully handles exceptions in user handler."""
    base_url, state, listener = server
    transport = create_transport(base_url, "worker-err", "token")
    await transport.connect()

    # Case 1: Handler raises generic exception
    async def buggy_handler(msg_type, payload, context):
        raise RuntimeError("Something went boom")

    listener.handler = buggy_handler

    # Should return 500 but not crash the server
    # Transport logs error and returns False/None
    success = await transport.register(
        WorkerRegistration("w", "t", [], Resources(1, 1), {}, [], WorkerCapabilities("h", "i", {}))
    )
    assert success is False

    # Case 2: Handler raises HTTP Exception (e.g. 400 Bad Request)
    async def validation_handler(msg_type, payload, context):
        raise web.HTTPBadRequest(text="Invalid data")

    listener.handler = validation_handler
    success = await transport.send_heartbeat(Heartbeat("w", "s", 0, [], [], [], None))
    assert success is False  # Client receives 400, logs warning, returns False

    await transport.close()


@pytest.mark.asyncio
async def test_no_handler_configured(unused_tcp_port_factory):
    """Test listener behavior when no handler is set."""
    port = unused_tcp_port_factory()
    app = web.Application()
    listener = HttpListener(app)
    # Don't call start() with handler, just setup routes manually or start without handler if possible
    # But start() requires handler. So we manually setup routes to simulate "handler missing" or start then set to None

    await listener.start(lambda m, p, c: True)  # Valid start
    listener.handler = None  # Break it

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    transport = create_transport(f"http://127.0.0.1:{port}", "w", "t")
    await transport.connect()

    # Register should fail with 500
    success = await transport.register(
        WorkerRegistration("w", "t", [], Resources(1, 1), {}, [], WorkerCapabilities("h", "i", {}))
    )
    assert success is False

    await transport.close()
    await runner.cleanup()


@pytest.mark.asyncio
async def test_network_errors(unused_tcp_port_factory):
    """Test transport resilience when server is unreachable."""
    # Use a port where no server is listening
    port = unused_tcp_port_factory()
    base_url = f"http://127.0.0.1:{port}"

    transport = create_transport(base_url, "worker-net", "token")
    await transport.connect()

    # 1. Register should fail gracefully (catch ClientConnectorError)
    success = await transport.register(
        WorkerRegistration("w", "t", [], Resources(1, 1), {}, [], WorkerCapabilities("h", "i", {}))
    )
    assert success is False

    # 2. Poll should return None gracefully
    task = await transport.poll_task(timeout=0.1)
    assert task is None

    # 3. Heartbeat should fail gracefully
    success = await transport.send_heartbeat(Heartbeat("w", "s", 0, [], [], [], None))
    assert success is False

    # 4. Result sending should fail gracefully (and retry internally)
    # We set retries=0 to speed up test
    transport.result_retries = 0
    success = await transport.send_result(TaskResult("j", "t", "w", "success"))
    assert success is False

    await transport.close()
