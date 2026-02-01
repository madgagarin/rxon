from typing import Any, Dict, List, NamedTuple, Optional

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
    gpu_info: Optional[GPUInfo] = None


class InstalledModel(NamedTuple):
    name: str
    version: str


class WorkerCapabilities(NamedTuple):
    hostname: str
    ip_address: str
    cost_per_skill: Dict[str, float]
    s3_config_hash: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class FileMetadata(NamedTuple):
    uri: str
    size: int
    etag: Optional[str] = None


class WorkerRegistration(NamedTuple):
    worker_id: str
    worker_type: str
    supported_tasks: List[str]
    resources: Resources
    installed_software: Dict[str, str]
    installed_models: List[InstalledModel]
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
    message: Optional[str] = None


class WorkerCommand(NamedTuple):
    command: str
    task_id: Optional[str] = None
    job_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class TaskPayload(NamedTuple):
    job_id: str
    task_id: str
    type: str
    params: Dict[str, Any]
    tracing_context: Dict[str, str]
    params_metadata: Optional[Dict[str, FileMetadata]] = None


class TaskError(NamedTuple):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class TaskResult(NamedTuple):
    job_id: str
    task_id: str
    worker_id: str
    status: str  # success, failure, cancelled
    data: Optional[Dict[str, Any]] = None
    error: Optional[TaskError] = None
    data_metadata: Optional[Dict[str, FileMetadata]] = None


class Heartbeat(NamedTuple):
    worker_id: str
    status: str
    load: float
    current_tasks: List[str]
    supported_tasks: List[str]
    hot_cache: List[str]
    skill_dependencies: Optional[Dict[str, List[str]]] = None
    hot_skills: Optional[List[str]] = None
