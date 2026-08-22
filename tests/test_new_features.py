# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from pytest import raises

from rxon.models import (
    HardwareDevice,
    Resources,
    SkillInfo,
    TaskPayload,
)
from rxon.schema import translate_error
from rxon.security import (
    sign_bubbling_chain,
    sign_bubbling_chain_hmac,
    sign_payload_ed25519,
    verify_bubbling_chain_hmac,
    verify_bubbling_chain_signature,
    verify_signature_ed25519,
)


def test_ed25519_signatures() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    payload = {"task_id": "t-1", "command": "run"}

    sig = sign_payload_ed25519(payload, private_pem)
    assert isinstance(sig, str)
    assert len(sig) > 0

    assert verify_signature_ed25519(payload, sig, public_pem) is True
    assert verify_signature_ed25519({"task_id": "t-2"}, sig, public_pem) is False
    assert verify_signature_ed25519(payload, sig + "0", public_pem) is False


def test_bubbling_chain_signatures() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    chain = ["worker-1", "worker-2"]
    sig = sign_bubbling_chain(chain, private_pem)
    assert isinstance(sig, str)

    assert verify_bubbling_chain_signature(chain, sig, public_pem) is True
    assert verify_bubbling_chain_signature(["worker-1"], sig, public_pem) is False

    secret = "hmac-secret"
    sig_hmac = sign_bubbling_chain_hmac(chain, secret)
    assert verify_bubbling_chain_hmac(chain, sig_hmac, secret) is True
    assert verify_bubbling_chain_hmac(["worker-1"], sig_hmac, secret) is False


def test_hardware_device_matching() -> None:
    device = HardwareDevice(type="gpu", model="NVIDIA GeForce RTX 4090", id="gpu-1")
    req1 = HardwareDevice(type="gpu", model="rtx")
    req2 = HardwareDevice(type="gpu", model="GTX")
    req_no_model = HardwareDevice(type="gpu")

    assert device.matches(req1) is True
    assert device.matches(req2) is False
    assert device.matches(req_no_model) is True

    assert device.matches(HardwareDevice(type="gpu", id="gpu-1")) is True
    assert device.matches(HardwareDevice(type="gpu", id="gpu-2")) is False

    assert device.matches(HardwareDevice(type="tpu")) is False


def test_resource_properties_matching() -> None:
    device = HardwareDevice(type="gpu", properties={"vram": 24, "cores": 1024})
    assert device.matches(HardwareDevice(type="gpu", properties={"vram": 16})) is True
    assert device.matches(HardwareDevice(type="gpu", properties={"vram": 24})) is True
    assert device.matches(HardwareDevice(type="gpu", properties={"vram": 32})) is False
    assert device.matches(HardwareDevice(type="gpu", properties={"vram": 16, "cores": 512})) is True
    assert device.matches(HardwareDevice(type="gpu", properties={"vram": 16, "cores": 2048})) is False

    device_list = HardwareDevice(type="gpu", properties={"os": ["linux", "darwin"]})
    assert device_list.matches(HardwareDevice(type="gpu", properties={"os": "linux"})) is True
    assert device_list.matches(HardwareDevice(type="gpu", properties={"os": "windows"})) is False

    device_scalar = HardwareDevice(type="gpu", properties={"os": "linux"})
    assert device_scalar.matches(HardwareDevice(type="gpu", properties={"os": ["linux", "darwin"]})) is True
    assert device_scalar.matches(HardwareDevice(type="gpu", properties={"os": ["windows", "darwin"]})) is False

    device_sets = HardwareDevice(type="gpu", properties={"os": ["linux", "darwin"]})
    assert device_sets.matches(HardwareDevice(type="gpu", properties={"os": ["linux", "windows"]})) is True
    assert device_sets.matches(HardwareDevice(type="gpu", properties={"os": ["windows", "freebsd"]})) is False

    assert device.matches(HardwareDevice(type="gpu", properties={"non_existent": 1})) is False
    assert device.matches(HardwareDevice(type="gpu", properties={"vram": "not-a-number"})) is False


def test_resources_matches_pop_logic() -> None:
    gpu1 = HardwareDevice(type="gpu", model="rtx 3080")
    gpu2 = HardwareDevice(type="gpu", model="rtx 4090")
    avail = Resources(devices=[gpu1, gpu2], properties={"ram": 64})

    assert avail.matches(Resources(devices=[HardwareDevice(type="gpu", model="3080")])) is True
    assert avail.matches(Resources(properties={"ram": 32})) is True

    assert avail.matches(Resources(properties={"ram": 128})) is False

    req_two = Resources(devices=[HardwareDevice(type="gpu"), HardwareDevice(type="gpu")])
    assert avail.matches(req_two) is True

    req_three = Resources(devices=[HardwareDevice(type="gpu"), HardwareDevice(type="gpu"), HardwareDevice(type="gpu")])
    assert avail.matches(req_three) is False


def test_error_translation() -> None:
    assert translate_error("data must match anyOf", None) == "Value does not match any schemas"
    assert translate_error("data cannot be validated by any definition", None) == "Value does not match any schemas"

    data_enum = {"status": "pending"}
    assert (
        translate_error("data.status must be one of ['active', 'inactive']", data_enum)
        == "Field 'status': Value 'pending' is not allowed. Must be one of: ['active', 'inactive']"
    )

    assert translate_error("data must contain ['name']", {}) == "Missing required field: 'name'"
    assert (
        translate_error("data.nested must contain ['id']", {"nested": {}})
        == "Field 'nested': Missing required field: 'id'"
    )

    assert translate_error("data must not contain {'extra'} properties", {"extra": 1}) == "Unexpected field: 'extra'"
    assert (
        translate_error("data.sub must not contain {'extra'} properties", {"sub": {"extra": 1}})
        == "Field 'sub': Unexpected field: 'extra'"
    )

    data_type = {"age": "old", "tags": [1, "two"]}
    assert translate_error("data.age must be integer", data_type) == "Field 'age': Expected integer"
    assert (
        translate_error("data.tags.1 must be integer", data_type) == "Field 'tags': Item at index 1: Expected integer"
    )
    assert translate_error("data.missing must be string", data_type) == "Field 'missing': Expected string, got null"

    assert translate_error("data must be integer", None) == "Expected integer, got null"
    assert translate_error("data must be integer", "str") == "Expected integer"


def test_skill_info_lazy_validator() -> None:
    skill = SkillInfo(
        name="test-skill", input_schema={"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
    )

    assert skill.input_validator is not None

    task = TaskPayload(job_id="j-1", task_id="t-1", type="test-skill", params={"x": 42})
    is_valid, err = task.validate_params(skill)
    assert is_valid is True

    task_invalid = TaskPayload(job_id="j-1", task_id="t-1", type="test-skill", params={"x": "string"})
    is_valid, err = task_invalid.validate_params(skill)
    assert is_valid is False
    assert "Expected integer" in str(err)


def test_edge_cases_and_coverage() -> None:
    skill_no_schema = SkillInfo(name="no-schema")
    assert skill_no_schema.input_validator is None
    assert skill_no_schema.output_validator is None

    task = TaskPayload(job_id="j-1", task_id="t-1", type="no-schema", params={"x": 42})
    is_valid, err = task.validate_params(skill_no_schema)
    assert is_valid is True
    assert err is None

    skill_a = SkillInfo(name="a")
    skill_b = SkillInfo(name="b")
    assert skill_a < skill_b
    with raises(TypeError):
        _ = skill_a < "not-a-skill"

    skill_invalid_schema = SkillInfo(name="invalid", input_schema={"type": "invalid_type"})
    assert skill_invalid_schema.input_validator is None

    skill_invalid_output = SkillInfo(name="invalid-out", output_schema={"type": "invalid_type"})
    assert skill_invalid_output.output_validator is None

    skill_with_out = SkillInfo(
        name="with-out", output_schema={"type": "object", "properties": {"y": {"type": "string"}}}
    )
    assert skill_with_out.output_validator is not None

    with raises(ValueError, match="Private key for signing cannot be empty"):
        sign_payload_ed25519({"x": 1}, "")

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    with raises(TypeError, match="Key is not an Ed25519 private key"):
        sign_payload_ed25519({"x": 1}, rsa_pem)

    assert verify_signature_ed25519({"x": 1}, "", "pub-key") is False
    assert verify_signature_ed25519({"x": 1}, "sig", "") is False

    with raises(ValueError, match="Private key cannot be empty"):
        sign_bubbling_chain(["w-1"], "")

    with raises(TypeError, match="Key is not an Ed25519 private key"):
        sign_bubbling_chain(["w-1"], rsa_pem)

    assert verify_bubbling_chain_signature(["w-1"], "", "pub-key") is False
    assert verify_bubbling_chain_signature(["w-1"], "sig", "") is False

    with raises(ValueError, match="Secret cannot be empty"):
        sign_bubbling_chain_hmac(["w-1"], "")

    assert verify_bubbling_chain_hmac(["w-1"], "", "secret") is False
    assert verify_bubbling_chain_hmac(["w-1"], "sig", "") is False

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    payload_with_extra = {"x": 1, "extra": "ignored"}
    sig_ignored = sign_payload_ed25519(payload_with_extra, private_pem, ignore_fields=["extra"])

    payload_modified = {"x": 1, "extra": "changed"}
    assert verify_signature_ed25519(payload_modified, sig_ignored, public_pem, ignore_fields=["extra"]) is True
