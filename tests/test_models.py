# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from rxon.models import (
    HardwareDevice,
    Heartbeat,
    Resources,
    SecurityContext,
    SkillInfo,
    TaskPayload,
    TaskResult,
    WorkerEventPayload,
    WorkerRegistration,
)
from rxon.utils import from_dict, to_dict


def test_skill_info_matches_edge_cases() -> None:
    skill = SkillInfo(name="echo", type="service", version="1.0.0")

    assert skill.matches(SkillInfo(name="echo"))
    assert skill.matches(SkillInfo(name="echo", type=None, version=None))

    assert not skill.matches(SkillInfo(name=""))
    assert not skill.matches(SkillInfo(name="echo", type=""))

    skill_incomplete = SkillInfo(name="echo")
    assert not skill_incomplete.matches(SkillInfo(name="echo", version="1.0.0"))


def test_task_payload_validation_advanced() -> None:
    skill = SkillInfo(
        name="process",
        input_schema={
            "type": "object",
            "properties": {"count": {"type": "integer"}, "tags": {"type": "array", "items": {"type": "string"}}},
            "required": ["count"],
        },
    )

    assert TaskPayload("j", "t", "p", {"count": 1}).validate_params(skill)[0] is True

    is_valid, err = TaskPayload("j", "t", "p", {"count": 1.5}).validate_params(skill)
    assert is_valid is False
    assert err is not None and "Expected integer" in err

    is_valid, err = TaskPayload("j", "t", "p", {"count": 5, "tags": [1, "2"]}).validate_params(skill)
    assert is_valid is False
    assert err is not None and "Expected string" in err

    skill_optional = SkillInfo(name="opt", input_schema={"type": "object"})
    assert TaskPayload("j", "t", "p", None).validate_params(skill_optional)[0] is False
    assert TaskPayload("j", "t", "p", {}).validate_params(skill_optional)[0] is True


def test_task_payload_validation_no_params() -> None:
    skill = SkillInfo(name="echo", input_schema={"type": "object", "required": ["msg"]})
    task = TaskPayload(job_id="j1", task_id="t1", type="echo", params=None)

    is_valid, err = task.validate_params(skill)
    assert is_valid is False
    assert err is not None and "Expected object, got null" in err


def test_worker_event_traceability() -> None:
    event = WorkerEventPayload(
        event_id="e1",
        worker_id="w1",
        origin_worker_id="w0",
        origin_task_id="t0",
        event_type="progress",
        payload={"done": 50},
    )
    assert event.origin_task_id == "t0"
    d = to_dict(event)
    assert d["origin_task_id"] == "t0"


def test_task_payload_deadline_int() -> None:
    task = TaskPayload(job_id="j1", task_id="t1", type="echo", deadline=1713456789)
    assert isinstance(task.deadline, int)
    d = to_dict(task)
    assert d["deadline"] == 1713456789


def test_worker_registration_serialization() -> None:
    reg = WorkerRegistration(
        worker_id="test-1",
        supported_skills=[],
        resources=Resources(properties={"cpu_cores": 4, "ram_gb": 16.0}),
        security=SecurityContext(signature="sig123", signer_id="boss"),
    )
    d = to_dict(reg)
    assert d["worker_id"] == "test-1"
    assert d["resources"]["properties"]["cpu_cores"] == 4
    assert d["security"]["signature"] == "sig123"


def test_task_payload_defaults() -> None:
    task = TaskPayload(job_id="j1", task_id="t1", type="echo")
    assert task.priority == 0.0
    assert task.params is None
    assert task.deadline is None


def test_hardware_device_to_dict() -> None:
    dev = HardwareDevice(type="gpu", model="A100", properties={"vram": 40})
    d = to_dict(dev)
    assert d["type"] == "gpu"
    assert d["properties"]["vram"] == 40


def test_security_context_empty() -> None:
    sc = SecurityContext()
    assert sc.signature is None
    assert sc.signer_id is None


def test_task_result_minimal() -> None:
    res = TaskResult(job_id="j1", task_id="t1", worker_id="w1", status="success")
    assert res.status == "success"
    assert res.data is None


def test_task_result_origin_id_and_timestamp() -> None:
    res = TaskResult(
        job_id="j1",
        task_id="t1",
        worker_id="proxy-1",
        origin_worker_id="real-worker-01",
        timestamp=12345678,
    )
    d = to_dict(res)
    assert d["origin_worker_id"] == "real-worker-01"
    assert d["timestamp"] == 12345678

    restored = from_dict(TaskResult, d)
    assert restored.origin_worker_id == "real-worker-01"
    assert restored.timestamp == 12345678


def test_task_payload_with_timestamp() -> None:
    payload = TaskPayload(job_id="j1", task_id="t1", type="test", timestamp=999)
    assert payload.timestamp == 999
    d = to_dict(payload)
    assert d["timestamp"] == 999


def test_models_empty_collections_serialization() -> None:
    hb = Heartbeat(
        worker_id="w1",
        status="idle",
        current_tasks=[],
        metadata={},
    )
    d = to_dict(hb)
    assert d["current_tasks"] == []
    assert d["metadata"] == {}

    hb2 = Heartbeat(worker_id="w2", status="idle")
    d2 = to_dict(hb2)
    assert "current_tasks" not in d2
    assert "metadata" not in d2


def test_heartbeat_minimal() -> None:
    hb = Heartbeat(worker_id="w1", status="busy")
    assert hb.worker_id == "w1"
    assert hb.status == "busy"
    assert hb.usage is None
