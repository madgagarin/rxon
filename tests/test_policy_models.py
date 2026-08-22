# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest.mock import MagicMock, patch

from msgspec import Struct
from pytest import raises

from rxon.models import TaskPayload, TaskResult
from rxon.utils import from_dict, to_dict


def test_task_payload_policy_headers_happy_path() -> None:
    payload = TaskPayload(
        job_id="job-123",
        task_id="task-456",
        type="test_skill",
        policy={"allowed_skills": ["test_skill"], "budget_cap": 100},
        sig="hmac-sig-123",
        step=2,
        depth=1,
        parent_hash="parent-hash-789",
    )

    data_dict = to_dict(payload)
    assert data_dict["job_id"] == "job-123"
    assert data_dict["policy"]["allowed_skills"] == ["test_skill"]
    assert data_dict["sig"] == "hmac-sig-123"
    assert data_dict["step"] == 2
    assert data_dict["depth"] == 1
    assert data_dict["parent_hash"] == "parent-hash-789"

    restored = from_dict(TaskPayload, data_dict)
    assert restored.job_id == "job-123"
    assert restored.policy == {"allowed_skills": ["test_skill"], "budget_cap": 100}
    assert restored.sig == "hmac-sig-123"
    assert restored.step == 2
    assert restored.depth == 1
    assert restored.parent_hash == "parent-hash-789"


def test_task_payload_policy_headers_defaults_and_edge_cases() -> None:
    payload_default = TaskPayload(job_id="j1", task_id="t1", type="s1")
    assert payload_default.policy is None
    assert payload_default.sig is None
    assert payload_default.step == 0
    assert payload_default.depth == 0
    assert payload_default.parent_hash is None

    payload_boundary = TaskPayload(
        job_id="j2",
        task_id="t2",
        type="s2",
        policy={},
        sig="",
        step=1000,
        depth=10,
        parent_hash="abc",
    )
    dict_b = to_dict(payload_boundary)
    assert dict_b["policy"] == {}
    assert dict_b["step"] == 1000
    assert dict_b["depth"] == 10
    assert dict_b["parent_hash"] == "abc"

    restored_b = from_dict(TaskPayload, dict_b)
    assert restored_b.policy == {}
    assert restored_b.step == 1000
    assert restored_b.depth == 10
    assert restored_b.parent_hash == "abc"


def test_task_payload_policy_headers_negative_cases() -> None:
    invalid_dict = {
        "job_id": "j1",
        "task_id": "t1",
        "type": "s1",
        "step": "invalid_number",
    }
    with raises(ValueError, match="Failed to instantiate TaskPayload"):
        from_dict(TaskPayload, invalid_dict)

    invalid_policy_dict = {
        "job_id": "j1",
        "task_id": "t1",
        "type": "s1",
        "policy": ["not", "a", "dict"],
    }
    with raises(ValueError, match="Failed to instantiate TaskPayload"):
        from_dict(TaskPayload, invalid_policy_dict)


def test_task_result_costs_happy_path_and_edge_cases() -> None:
    result = TaskResult(
        job_id="job-123",
        task_id="task-456",
        status="success",
        data={"output": "ok"},
        costs={"tokens": 1500, "usd": 0.02, "integer_float": 1.0},
    )

    data_dict = to_dict(result)
    assert data_dict["costs"] == {"tokens": 1500, "usd": 0.02, "integer_float": 1}

    restored = from_dict(TaskResult, data_dict)
    assert restored.costs == {"tokens": 1500, "usd": 0.02, "integer_float": 1}

    result_none = TaskResult(job_id="j1", task_id="t1")
    assert result_none.costs is None


def test_task_result_costs_negative_cases() -> None:
    invalid_costs = {
        "job_id": "j1",
        "task_id": "t1",
        "costs": 12345,
    }
    with raises(ValueError, match="Failed to instantiate TaskResult"):
        from_dict(TaskResult, invalid_costs)


def test_utils_to_dict_fallback_handler() -> None:
    mock_struct = MagicMock(spec=Struct)

    with (
        patch("msgspec.to_builtins", side_effect=RuntimeError("Mock struct error")),
        patch.object(mock_struct, "__str__", return_value="MockStructFallback"),
    ):
        res = to_dict(mock_struct)
        assert res == "MockStructFallback"
