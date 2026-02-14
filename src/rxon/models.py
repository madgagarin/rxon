from typing import Any, NamedTuple

__all__ = [
    "GPUInfo",
    "Resources",
    "InstalledModel",
    "WorkerCapabilities",
    "FileMetadata",
    "WorkerRegistration",
    "TokenResponse",
    "ProgressUpdatePayload",
    "WorkerCommand",
    "TaskPayload",
    "TaskError",
    "TaskResult",
    "Heartbeat",
]


class GPUInfo(NamedTuple):
    model: str
    vram_gb: int


class Resources(NamedTuple):
    max_concurrent_tasks: int
    cpu_cores: int
    gpu_info: GPUInfo | None = None


class InstalledModel(NamedTuple):
    name: str
    version: str


class WorkerCapabilities(NamedTuple):
    hostname: str
    ip_address: str
    cost_per_skill: dict[str, float]
    s3_config_hash: str | None = None
    extra: dict[str, Any] | None = None


class FileMetadata(NamedTuple):
    uri: str
    size: int
    etag: str | None = None


class WorkerRegistration(NamedTuple):
    worker_id: str
    worker_type: str
    supported_skills: list[str]
    resources: Resources
    installed_software: dict[str, str]
    installed_models: list[InstalledModel]
    capabilities: WorkerCapabilities


class TokenResponse(NamedTuple):
    access_token: str
    expires_in: int
    worker_id: str


class ProgressUpdatePayload(NamedTuple):
    event: str
    task_id: str
    job_id: str
    progress: float
    message: str | None = None


class WorkerCommand(NamedTuple):
    command: str
    task_id: str | None = None
    job_id: str | None = None
    params: dict[str, Any] | None = None


class TaskPayload(NamedTuple):
    job_id: str
    task_id: str
    type: str
    params: dict[str, Any]
    tracing_context: dict[str, str]
    params_metadata: dict[str, FileMetadata] | None = None


class TaskError(NamedTuple):
    code: str
    message: str
    details: dict[str, Any] | None = None


class TaskResult(NamedTuple):
    job_id: str
    task_id: str
    worker_id: str
    status: str  # success, failure, cancelled
    data: dict[str, Any] | None = None
    error: TaskError | None = None
    data_metadata: dict[str, FileMetadata] | None = None


class Heartbeat(NamedTuple):
    worker_id: str
    status: str
    load: float
    current_tasks: list[str]
    supported_skills: list[str]
    hot_cache: list[str]
    skill_dependencies: dict[str, list[str]] | None = None
    hot_skills: list[str] | None = None
