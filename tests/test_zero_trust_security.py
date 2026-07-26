# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time

import pytest

from rxon.models import (
    Heartbeat,
    SecurityContext,
    TaskResult,
    WorkerEventPayload,
    WorkerRegistration,
)
from rxon.security import sign_payload, verify_signature
from rxon.utils import from_dict, to_dict


def test_sign_and_verify_payload_basic() -> None:
    """Test basic HMAC SHA256 signing and verification."""
    payload = {"worker_id": "test-worker", "status": "active"}
    secret = "super-secret-key"

    signature = sign_payload(payload, secret)
    assert isinstance(signature, str)
    assert len(signature) > 10

    assert verify_signature(payload, signature, secret) is True

    tampered_payload = {"worker_id": "test-worker", "status": "hacked"}
    assert verify_signature(tampered_payload, signature, secret) is False

    assert verify_signature(payload, signature[:-1] + "0", secret) is False

    assert verify_signature(payload, signature, "wrong-secret") is False


def test_sign_payload_negative() -> None:
    """Test that signing with empty secret fails."""
    with pytest.raises(ValueError, match="Secret key for signing cannot be empty"):
        sign_payload({"foo": "bar"}, "")
    with pytest.raises(ValueError):
        sign_payload({"foo": "bar"}, None)  # type: ignore


def test_verify_signature_edge_cases() -> None:
    """Test verification with empty or invalid inputs."""
    payload = {"foo": "bar"}
    valid_secret = "secret"
    valid_sig = sign_payload(payload, valid_secret)

    assert verify_signature(payload, "", valid_secret) is False
    assert verify_signature(payload, valid_sig, "") is False
    assert verify_signature(payload, None, valid_secret) is False  # type: ignore[arg-type]
    assert verify_signature(payload, valid_sig, None) is False  # type: ignore[arg-type]


def test_sign_payload_stable_sorting() -> None:
    """Test that sign_payload handles key sorting (important for identical signatures)."""
    payload1 = {"a": 1, "b": 2, "c": 3}
    payload2 = {"c": 3, "a": 1, "b": 2}
    secret = "key"

    sig1 = sign_payload(payload1, secret)
    sig2 = sign_payload(payload2, secret)
    assert sig1 == sig2


def test_sign_payload_with_ignore_fields() -> None:
    """Test that ignore_fields are actually ignored during signing."""
    payload = {"worker_id": "w1", "status": "active", "temp_field": "ignore-me"}
    secret = "secret"

    # Sign ignoring temp_field
    sig_ignored = sign_payload(payload, secret, ignore_fields=["temp_field"])

    # Sign a payload that doesn't have the field at all
    payload_clean = {"worker_id": "w1", "status": "active"}
    sig_clean = sign_payload(payload_clean, secret)

    assert sig_ignored == sig_clean
    assert verify_signature(payload, sig_ignored, secret, ignore_fields=["temp_field"]) is True


def test_sign_payload_auto_ignores_security() -> None:
    """Test that 'security' field is always ignored by default."""
    payload = {"id": "1", "security": {"signature": "abc"}}
    secret = "key"

    sig1 = sign_payload(payload, secret)
    sig2 = sign_payload({"id": "1"}, secret)

    assert sig1 == sig2


def test_worker_registration_zero_trust_fields() -> None:
    """Test WorkerRegistration handles timestamp and security fields."""
    ts = int(time.time())
    security = SecurityContext(signature="test-sig", signer_id="worker-1")
    reg = WorkerRegistration(worker_id="worker-1", worker_type="test", timestamp=ts, security=security)

    reg_dict = to_dict(reg)
    assert reg_dict["timestamp"] == ts
    assert reg_dict["security"]["signature"] == "test-sig"
    assert reg_dict["security"]["signer_id"] == "worker-1"

    restored = from_dict(WorkerRegistration, reg_dict)
    assert restored.timestamp == ts
    assert restored.security is not None
    assert restored.security.signature == "test-sig"
    assert restored.security.signer_id == "worker-1"


def test_task_result_zero_trust_fields() -> None:
    """Test TaskResult handles timestamp and security fields."""
    ts = int(time.time())
    security = SecurityContext(signature="test-sig", signer_id="worker-1")
    res = TaskResult(job_id="j1", task_id="t1", worker_id="worker-1", status="success", timestamp=ts, security=security)

    res_dict = to_dict(res)
    assert res_dict["timestamp"] == ts
    assert res_dict["security"]["signature"] == "test-sig"

    restored = from_dict(TaskResult, res_dict)
    assert restored.timestamp == ts
    assert restored.security is not None
    assert restored.security.signature == "test-sig"


def test_heartbeat_zero_trust_fields() -> None:
    """Test Heartbeat handles timestamp and security fields."""
    ts = int(time.time())
    security = SecurityContext(signature="test-sig", signer_id="worker-1")
    hb = Heartbeat(worker_id="worker-1", status="ready", timestamp=ts, security=security)

    hb_dict = to_dict(hb)
    assert hb_dict["timestamp"] == ts
    assert hb_dict["security"]["signature"] == "test-sig"

    restored = from_dict(Heartbeat, hb_dict)
    assert restored.timestamp == ts
    assert restored.security is not None
    assert restored.security.signature == "test-sig"


def test_worker_event_payload_zero_trust_fields() -> None:
    """Test WorkerEventPayload handles timestamp and security fields."""
    ts = int(time.time())
    security = SecurityContext(signature="test-sig", signer_id="worker-1")
    event = WorkerEventPayload(
        event_id="e1",
        worker_id="worker-1",
        origin_worker_id="worker-1",
        event_type="progress",
        payload={"progress": 50},
        timestamp=ts,
        security=security,
        bubbling_chain=["proxy-1"],
    )

    event_dict = to_dict(event)
    assert event_dict["timestamp"] == ts
    assert event_dict["security"]["signature"] == "test-sig"
    assert "proxy-1" in event_dict["bubbling_chain"]

    restored = from_dict(WorkerEventPayload, event_dict)
    assert restored.timestamp == ts
    assert restored.security is not None
    assert restored.security.signature == "test-sig"
    assert restored.bubbling_chain == ["proxy-1"]
