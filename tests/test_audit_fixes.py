# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import UTC, datetime
from enum import Enum
from logging import WARNING
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pytest import LogCaptureFixture, raises

from rxon.models import InstalledArtifact, SkillInfo
from rxon.schema import _validators_cache, validate_data
from rxon.security import sign_payload, sign_payload_ed25519, verify_signature, verify_signature_ed25519
from rxon.validators import is_valid_identifier, validate_identifier


class PriorityEnum(Enum):
    HIGH = "high"
    LOW = "low"


def test_validator_positive_cases() -> None:
    """Positive: Valid identifiers."""
    assert is_valid_identifier("worker-1")
    assert is_valid_identifier("worker_node_99")
    assert is_valid_identifier("a" * 128)
    assert is_valid_identifier("Task-Type-123_abc")
    validate_identifier("worker-1", name="worker_id")


def test_validator_negative_cases() -> None:
    """Negative: Invalid identifiers with dangerous/illegal characters."""
    bad_ids = [
        "",
        " ",
        "worker 1",
        "worker/1",
        "worker\r\nnode",
        "worker\x00node",
        "../worker",
        "worker*",
        "worker;rm",
        "worker$",
        "worker@1",
        "worker`id`",
    ]
    for bad_id in bad_ids:
        assert not is_valid_identifier(bad_id), f"Expected '{bad_id}' to be invalid"
        with raises(ValueError, match="Invalid"):
            validate_identifier(bad_id, name="test_id")


def test_validator_edge_cases() -> None:
    """Edge cases: Exactly 128 characters vs 129 characters, non-string types."""
    valid_128 = "a" * 128
    invalid_129 = "a" * 129
    assert is_valid_identifier(valid_128)
    assert not is_valid_identifier(invalid_129)
    with raises(ValueError):
        validate_identifier(invalid_129)

    assert not is_valid_identifier(None)  # type: ignore[arg-type]
    assert not is_valid_identifier(12345)  # type: ignore[arg-type]
    assert not is_valid_identifier(["worker"])  # type: ignore[arg-type]


def test_signing_positive_with_complex_types() -> None:
    """Positive: Signing and verifying complex payloads with UUID, Enum, datetime, float."""
    uid = uuid4()
    now = datetime.now(UTC)
    payload = {
        "job_id": str(uid),
        "status": "running",
        "priority": PriorityEnum.HIGH,
        "created_at": now,
        "score": 100.0,
        "tags": ["prod", "gpu"],
        "metadata": {"nested_key": 42},
    }
    secret = "my-secret-test-key-32-chars-long!"

    sig = sign_payload(payload, secret)
    assert isinstance(sig, str)
    assert len(sig) == 64

    assert verify_signature(payload, sig, secret)


def test_signing_negative_tampered_payload() -> None:
    """Negative: Modifying any field causes signature verification to fail."""
    secret = "my-secret-test-key-32-chars-long!"
    payload = {"job_id": "job-1", "status": "running", "step": 1}
    sig = sign_payload(payload, secret)

    tampered1 = {"job_id": "job-1", "status": "failed", "step": 1}
    assert not verify_signature(tampered1, sig, secret)

    tampered2 = {"job_id": "job-1", "status": "running", "step": 2}
    assert not verify_signature(tampered2, sig, secret)

    assert not verify_signature(payload, sig, "wrong-secret-key")

    assert not verify_signature(payload, "0" * 64, secret)
    assert not verify_signature(payload, "", secret)


def test_signing_auto_ignores_security_and_signature_fields() -> None:
    """RXON-SEC-4: sign_payload and verify_signature automatically ignore _signature and security."""
    secret = "my-secret-test-key-32-chars-long!"
    base_payload = {"task_id": "task-99", "status": "finished", "output": {"res": 1}}

    sig = sign_payload(base_payload, secret)

    transport_payload = dict(base_payload)
    transport_payload["_signature"] = sig
    transport_payload["security"] = {"auth_mode": "token", "token": "masked"}

    assert verify_signature(transport_payload, sig, secret)


def test_to_dict_none_handling_resilience() -> None:
    """RXON-LOGIC-1: to_dict strips None values consistently so signing doesn't differ between None and missing."""
    secret = "my-secret-test-key-32-chars-long!"
    payload_with_none = {"job_id": "job-1", "params": None, "extra": "data"}
    payload_without_none = {"job_id": "job-1", "extra": "data"}

    sig1 = sign_payload(payload_with_none, secret)
    sig2 = sign_payload(payload_without_none, secret)

    assert sig1 == sig2
    assert verify_signature(payload_with_none, sig2, secret)
    assert verify_signature(payload_without_none, sig1, secret)


def test_schema_validators_cache_bounding() -> None:
    """RXON-VAL-1: Schema validator cache limit (1024) prevents unbounded memory growth."""
    for i in range(1100):
        schema = {
            "type": "object",
            "properties": {f"field_{i}": {"type": "string"}},
            "additionalProperties": True,
        }
        valid, err = validate_data({f"field_{i}": "val"}, schema)
        assert valid, f"Validation failed for schema {i}: {err}"

    assert len(_validators_cache) <= 1024


def test_skill_info_invalid_schema_logging(caplog: LogCaptureFixture) -> None:
    """RXON-VAL-2: SkillInfo with invalid JSON schema logs warning and returns None validator."""
    with caplog.at_level(WARNING):
        invalid_schema = {"type": "invalid_unsupported_type"}
        skill = SkillInfo(name="broken_skill", input_schema=invalid_schema, output_schema=invalid_schema)

        assert skill.input_validator is None
        assert any(
            "Failed to compile input schema for skill 'broken_skill'" in record.message for record in caplog.records
        )

        assert skill.output_validator is None
        assert any(
            "Failed to compile output schema for skill 'broken_skill'" in record.message for record in caplog.records
        )


def test_ed25519_auto_ignores_security_and_signature_fields() -> None:
    """RXON-SEC-5: Ed25519 sign and verify automatically ignore _signature and security."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    base_payload = {"job_id": "job-ed25519", "step": 1, "data": {"val": 42}}
    sig = sign_payload_ed25519(base_payload, private_pem)

    payload_with_meta = dict(base_payload)
    payload_with_meta["_signature"] = sig
    payload_with_meta["security"] = {"signature": sig, "signer_id": "w1"}

    assert verify_signature_ed25519(payload_with_meta, sig, public_pem)


def test_installed_artifact_property_list_matching() -> None:
    """RXON-MATCH-1: InstalledArtifact matches lists, sets, and scalars in properties."""
    art = InstalledArtifact(
        name="torch",
        version="2.3.0",
        properties={"backends": ["cuda", "rocm", "mps"], "driver_min": 525, "tags": "deep-learning"},
    )

    assert art.matches(InstalledArtifact(name="torch", properties={"backends": ["cuda", "vulkan"]}))
    assert art.matches(InstalledArtifact(name="torch", properties={"backends": "rocm"}))
    assert art.matches(InstalledArtifact(name="torch", properties={"driver_min": 500}))
    assert not art.matches(InstalledArtifact(name="torch", properties={"driver_min": 600}))
    assert not art.matches(InstalledArtifact(name="torch", properties={"backends": ["metal", "directx"]}))
    assert not art.matches(InstalledArtifact(name="torch", properties={"unknown": 1}))
