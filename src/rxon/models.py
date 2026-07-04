# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from typing import Any

import fastjsonschema
import msgspec

from rxon.schema import translate_error, validate_data

__all__ = [
    "HardwareDevice",
    "DeviceUsage",
    "ResourcesUsage",
    "Resources",
    "InstalledArtifact",
    "SkillInfo",
    "WorkerCapabilities",
    "FileMetadata",
    "SecurityContext",
    "WorkerRegistration",
    "TokenResponse",
    "WorkerEventPayload",
    "WorkerCommand",
    "TaskPayload",
    "TaskError",
    "TaskResult",
    "Heartbeat",
]


class HardwareDevice(msgspec.Struct, omit_defaults=True, frozen=True):
    type: str
    model: str | None = None
    id: str | None = None
    properties: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None

    def matches(self, req: "HardwareDevice") -> bool:
        """Checks if this device matches the requirements (GE logic for numbers, inclusion for lists)."""
        if req.type and self.type != req.type:
            return False

        if req.model and (not self.model or req.model.lower() not in self.model.lower()):
            return False

        if req.id and self.id != req.id:
            return False

        if not req.properties:
            return True

        my_props = self.properties or {}
        for k, req_v in req.properties.items():
            my_v = my_props.get(k)
            if my_v is None:
                return False

            if isinstance(req_v, (int, float)) and isinstance(my_v, (int, float)):
                if my_v < req_v:
                    return False
            elif isinstance(req_v, (frozenset, set, list)):
                req_set = req_v if isinstance(req_v, (frozenset, set)) else set(req_v)
                if isinstance(my_v, (frozenset, set, list)):
                    my_set = my_v if isinstance(my_v, (frozenset, set)) else set(my_v)
                    if not (my_set & req_set):
                        return False
                elif my_v not in req_set:
                    return False
            elif isinstance(my_v, (frozenset, set, list)):
                my_set = my_v if isinstance(my_v, (frozenset, set)) else set(my_v)
                if req_v not in my_set:
                    return False
            elif my_v != req_v:
                return False
        return True


class DeviceUsage(msgspec.Struct, omit_defaults=True, frozen=True):
    unit_id: str
    load_percent: float
    metrics: dict[str, Any] | None = None


class ResourcesUsage(msgspec.Struct, omit_defaults=True, frozen=True):
    cpu_load_percent: float = 0.0
    ram_used_gb: float = 0.0
    devices_usage: list[DeviceUsage] | None = None


class Resources(msgspec.Struct, omit_defaults=True, frozen=True):
    devices: list[HardwareDevice] | None = None
    properties: dict[str, Any] | None = None

    def matches(self, req: "Resources") -> bool:
        """Checks if these resources meet the requirements (GE logic for numeric properties, inclusion for lists)."""
        if req.devices:
            my_devices = list(self.devices or [])
            for req_dev in req.devices:
                found_idx = -1
                for i, my_dev in enumerate(my_devices):
                    if my_dev.matches(req_dev):
                        found_idx = i
                        break
                if found_idx == -1:
                    return False
                my_devices.pop(found_idx)

        if req.properties:
            my_props = self.properties or {}
            for k, req_v in req.properties.items():
                my_v = my_props.get(k)
                if my_v is None:
                    return False
                if isinstance(req_v, (int, float)) and isinstance(my_v, (int, float)):
                    if my_v < req_v:
                        return False
                elif isinstance(req_v, (frozenset, set, list)):
                    req_set = req_v if isinstance(req_v, (frozenset, set)) else set(req_v)
                    if isinstance(my_v, (frozenset, set, list)):
                        my_set = my_v if isinstance(my_v, (frozenset, set)) else set(my_v)
                        if not (my_set & req_set):
                            return False
                    elif my_v not in req_set:
                        return False
                elif isinstance(my_v, (frozenset, set, list)):
                    my_set = my_v if isinstance(my_v, (frozenset, set)) else set(my_v)
                    if req_v not in my_set:
                        return False
                elif my_v != req_v:
                    return False
        return True


class InstalledArtifact(msgspec.Struct, omit_defaults=True, frozen=True):
    name: str
    version: str = "unknown"
    type: str | None = None
    properties: dict[str, Any] | None = None

    def matches(self, req: "InstalledArtifact") -> bool:
        """Checks if this artifact matches the requirements (GE logic for numeric properties, inclusion for lists)."""
        if self.name != req.name:
            return False
        if req.version != "unknown" and req.version != self.version:
            return False

        if not req.properties:
            return True

        my_props = self.properties or {}
        for k, req_v in req.properties.items():
            my_v = my_props.get(k)
            if my_v is None:
                return False
            if isinstance(req_v, (int, float)) and isinstance(my_v, (int, float)):
                if my_v < req_v:
                    return False
            elif isinstance(req_v, (frozenset, set, list)):
                req_set = req_v if isinstance(req_v, (frozenset, set)) else set(req_v)
                if isinstance(my_v, (frozenset, set, list)):
                    my_set = my_v if isinstance(my_v, (frozenset, set)) else set(my_v)
                    if not (my_set & req_set):
                        return False
                elif my_v not in req_set:
                    return False
            elif isinstance(my_v, (frozenset, set, list)):
                my_set = my_v if isinstance(my_v, (frozenset, set)) else set(my_v)
                if req_v not in my_set:
                    return False
            elif my_v != req_v:
                return False
        return True


class SkillInfo(msgspec.Struct, omit_defaults=True, frozen=True):
    name: str
    type: str | None = None
    description: str | None = None
    version: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    events_schema: dict[str, dict[str, Any]] | None = None
    output_statuses: list[str] | None = None
    schema_dialect: str = "json-schema"
    properties: dict[str, Any] | None = None
    _input_validator: Any = None
    _output_validator: Any = None

    @property
    def input_validator(self) -> Any:
        val = getattr(self, "_input_validator", None)
        if val is None and self.input_schema:
            try:
                val = fastjsonschema.compile(self.input_schema)
                object.__setattr__(self, "_input_validator", val)
            except Exception:
                pass
        return val

    @property
    def output_validator(self) -> Any:
        val = getattr(self, "_output_validator", None)
        if val is None and self.output_schema:
            try:
                val = fastjsonschema.compile(self.output_schema)
                object.__setattr__(self, "_output_validator", val)
            except Exception:
                pass
        return val

    def matches(self, req: "SkillInfo") -> bool:
        """Checks if this skill meets the requirements."""
        if self.name != req.name:
            return False
        if req.type is not None and self.type != req.type:
            return False
        return req.version is None or self.version == req.version

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, SkillInfo):
            return NotImplemented
        return self.name < other.name


class SecurityContext(msgspec.Struct, omit_defaults=True, frozen=True):
    """Security metadata for Zero Trust identity and verification."""

    signature: str | None = None
    signer_id: str | None = None
    identity_chain: list[str] | None = None
    metadata: dict[str, Any] | None = None


class WorkerCapabilities(msgspec.Struct, omit_defaults=True, frozen=True):
    hostname: str = "unknown"
    ip_address: str = "0.0.0.0"
    cost_per_skill: dict[str, float] | None = None
    s3_config_hash: str | None = None
    extra: dict[str, Any] | None = None


class FileMetadata(msgspec.Struct, omit_defaults=True, frozen=True):
    uri: str
    size: int = 0
    etag: str | None = None
    metadata: dict[str, Any] | None = None


# TODO: Extract domain-specific models to external packages:
# - rxon-media (ImageMetadata, AudioMetadata, TensorMetadata)
# - rxon-robotics (RoboticJointState, RoboticLinkState, RoboticsTelemetry)
# - rxon-ai (AI agent state models, decision trees, prompt context models)


class WorkerRegistration(msgspec.Struct, omit_defaults=True, frozen=True):
    worker_id: str
    worker_type: str = "generic"
    supported_skills: list[SkillInfo] | None = None
    available_skills: list[str] | None = None
    hot_skills: list[str] | None = None
    resources: Resources | None = None
    installed_software: dict[str, str] | None = None
    installed_artifacts: list[InstalledArtifact] | None = None
    capabilities: WorkerCapabilities | None = None
    skills_hash: str | None = None
    security: SecurityContext | None = None
    metadata: dict[str, Any] | None = None
    timestamp: int | None = None


class TokenResponse(msgspec.Struct, omit_defaults=True, frozen=True):
    access_token: str
    expires_in: int
    worker_id: str
    refresh_token: str | None = None
    metadata: dict[str, Any] | None = None


class WorkerEventPayload(msgspec.Struct, omit_defaults=True, frozen=True):
    event_id: str
    worker_id: str
    origin_worker_id: str
    event_type: str
    payload: dict[str, Any]
    origin_task_id: str | None = None
    bubbling_chain: list[str] | None = None
    target_job_id: str | None = None
    target_task_id: str | None = None
    trace_context: dict[str, str] | None = None
    priority: float = 0.0
    timestamp: int | None = None
    security: SecurityContext | None = None
    metadata: dict[str, Any] | None = None


class WorkerCommand(msgspec.Struct, omit_defaults=True, frozen=True):
    command: str
    task_id: str | None = None
    job_id: str | None = None
    params: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class TaskPayload(msgspec.Struct, omit_defaults=True, frozen=True):
    job_id: str
    task_id: str
    type: str
    params: dict[str, Any] | None = None
    tracing_context: dict[str, str] | None = None
    params_metadata: dict[str, FileMetadata] | None = None
    priority: float = 0.0
    deadline: int | None = None
    security: SecurityContext | None = None
    metadata: dict[str, Any] | None = None
    timestamp: int | None = None

    def validate_params(self, skill: SkillInfo) -> tuple[bool, str | None]:
        """
        Validates task params against the skill's input schema.
        Returns (is_valid, error_message).
        """
        validator = skill.input_validator
        if validator is not None:
            try:
                validator(self.params)
                return True, None
            except Exception as e:
                msg = getattr(e, "message", str(e))
                return False, translate_error(msg, self.params)

        return validate_data(self.params, skill.input_schema)


class TaskError(msgspec.Struct, omit_defaults=True, frozen=True):
    code: str
    message: str
    details: dict[str, Any] | None = None


class TaskResult(msgspec.Struct, omit_defaults=True, frozen=True):
    job_id: str
    task_id: str
    worker_id: str | None = None
    origin_worker_id: str | None = None
    status: str = "success"
    data: dict[str, Any] | None = None
    error: TaskError | None = None
    data_metadata: dict[str, FileMetadata] | None = None
    security: SecurityContext | None = None
    metadata: dict[str, Any] | None = None
    timestamp: int | None = None


class Heartbeat(msgspec.Struct, omit_defaults=True, frozen=True):
    worker_id: str
    status: str
    usage: ResourcesUsage | None = None
    current_tasks: list[str] | None = None
    supported_skills: list[SkillInfo] | None = None
    available_skills: list[str] | None = None
    hot_skills: list[str] | None = None
    skills_hash: str | None = None
    security: SecurityContext | None = None
    metadata: dict[str, Any] | None = None
    timestamp: int | None = None
