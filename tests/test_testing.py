# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pytest import mark

from rxon.models import Heartbeat, Resources, TaskPayload, TaskResult, WorkerCommand, WorkerRegistration
from rxon.testing import MockTransport


@mark.asyncio
async def test_mock_transport_full_flow() -> None:
    transport = MockTransport(worker_id="test-worker")
    await transport.connect()
    assert transport.connected

    reg = WorkerRegistration(worker_id="test-worker", resources=Resources(properties={"cpu_cores": 2}))
    resp = await transport.register(reg)
    assert resp["status"] == "registered"
    assert len(transport.registered) == 1

    hb = Heartbeat(worker_id="test-worker", status="idle")
    await transport.send_heartbeat(hb)
    assert len(transport.heartbeats) == 1

    # pushing a dict, expecting a model
    transport.push_task({"job_id": "j1", "task_id": "t1", "type": "compute", "params": {"n": 10}})
    task = await transport.poll_task(timeout=0.1)
    assert isinstance(task, TaskPayload)
    assert task.job_id == "j1"
    assert task.params is not None
    assert task.params["n"] == 10

    # Test skills filtering in poll_task (just verification of signature/call)
    transport.push_task(TaskPayload("j2", "t2", "test"))
    task2 = await transport.poll_task(timeout=0.1, available_skills=["s1"], hot_skills=["s2"])
    assert task2 is not None
    assert task2.job_id == "j2"

    res = TaskResult(job_id="j1", task_id="t1", worker_id="test-worker", status="success")
    await transport.send_result(res)
    assert len(transport.results) == 1

    # pushing a dict, expecting a model
    transport.push_command({"command": "stop", "task_id": "t1"})

    # We need to manually iterate since it's an async generator
    cmd_iter = transport.listen_for_commands()
    cmd = await anext(cmd_iter)
    assert isinstance(cmd, WorkerCommand)
    assert cmd.command == "stop"

    await transport.close()
    assert not transport.connected
