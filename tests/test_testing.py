import pytest

from rxon.models import (
    Resources,
    TaskPayload,
    TaskResult,
    WorkerCapabilities,
    WorkerRegistration,
)
from rxon.testing import MockTransport


@pytest.mark.asyncio
async def test_mock_transport_flow():
    transport = MockTransport(worker_id="mock-1")
    await transport.connect()

    # 1. Register
    reg = WorkerRegistration(
        worker_id="mock-1",
        worker_type="cpu",
        supported_tasks=[],
        resources=Resources(1, 1),
        installed_software={},
        installed_models=[],
        capabilities=WorkerCapabilities("h", "i", {}),
    )
    success = await transport.register(reg)
    assert success is True
    assert len(transport.registered) == 1
    assert transport.registered[0].worker_id == "mock-1"

    # 2. Poll (Empty)
    task = await transport.poll_task(timeout=0.1)
    assert task is None

    # 3. Poll (With Task)
    mock_task = TaskPayload("job1", "task1", "echo", {}, {})
    transport.push_task(mock_task)

    task = await transport.poll_task(timeout=1.0)
    assert task is not None
    assert task.job_id == "job1"

    # 4. Result
    res = TaskResult("job1", "task1", "mock-1", "success")
    success = await transport.send_result(res)
    assert success is True
    assert len(transport.results) == 1

    await transport.close()
