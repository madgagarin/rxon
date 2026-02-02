from importlib.metadata import PackageNotFoundError, version

from .blob import RXON_BLOB_SCHEME, calculate_config_hash, parse_uri
from .constants import (
    AUTH_HEADER_CLIENT,
    AUTH_HEADER_WORKER,
    COMMAND_CANCEL_TASK,
    ENDPOINT_TASK_NEXT,
    ENDPOINT_TASK_RESULT,
    ENDPOINT_WORKER_HEARTBEAT,
    ENDPOINT_WORKER_REGISTER,
    ERROR_CODE_DEPENDENCY,
    ERROR_CODE_INTEGRITY_MISMATCH,
    ERROR_CODE_INTERNAL,
    ERROR_CODE_INVALID_INPUT,
    ERROR_CODE_PERMANENT,
    ERROR_CODE_RESOURCE_EXHAUSTED,
    ERROR_CODE_SECURITY,
    ERROR_CODE_TIMEOUT,
    ERROR_CODE_TRANSIENT,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_ERROR,
    JOB_STATUS_FAILED,
    JOB_STATUS_FINISHED,
    JOB_STATUS_PENDING,
    JOB_STATUS_QUARANTINED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_WAITING_FOR_HUMAN,
    JOB_STATUS_WAITING_FOR_PARALLEL,
    JOB_STATUS_WAITING_FOR_WORKER,
    MSG_TYPE_PROGRESS,
    PROTOCOL_VERSION,
    STS_TOKEN_ENDPOINT,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_FAILURE,
    TASK_STATUS_SUCCESS,
    WORKER_API_PREFIX,
    WS_ENDPOINT,
)
from .exceptions import (
    IntegrityError,
    ParamValidationError,
    RxonAuthError,
    RxonError,
    RxonNetworkError,
    RxonProtocolError,
    S3ConfigMismatchError,
)
from .models import (
    FileMetadata,
    GPUInfo,
    Heartbeat,
    InstalledModel,
    ProgressUpdatePayload,
    Resources,
    TaskError,
    TaskPayload,
    TaskResult,
    TokenResponse,
    WorkerCapabilities,
    WorkerCommand,
    WorkerRegistration,
)
from .security import (
    create_client_ssl_context,
    create_server_ssl_context,
    extract_cert_identity,
)
from .transports.base import Listener, Transport
from .transports.factory import create_transport
from .transports.http import HttpTransport
from .transports.http_server import HttpListener
from .utils import to_dict
from .validators import is_valid_identifier, validate_identifier

__all__ = [
    # Blob
    "RXON_BLOB_SCHEME",
    "calculate_config_hash",
    "parse_uri",
    # Constants
    "AUTH_HEADER_CLIENT",
    "AUTH_HEADER_WORKER",
    "COMMAND_CANCEL_TASK",
    "ENDPOINT_TASK_NEXT",
    "ENDPOINT_TASK_RESULT",
    "ENDPOINT_WORKER_HEARTBEAT",
    "ENDPOINT_WORKER_REGISTER",
    "ERROR_CODE_DEPENDENCY",
    "ERROR_CODE_INTEGRITY_MISMATCH",
    "ERROR_CODE_INTERNAL",
    "ERROR_CODE_INVALID_INPUT",
    "ERROR_CODE_PERMANENT",
    "ERROR_CODE_RESOURCE_EXHAUSTED",
    "ERROR_CODE_SECURITY",
    "ERROR_CODE_TIMEOUT",
    "ERROR_CODE_TRANSIENT",
    "JOB_STATUS_CANCELLED",
    "JOB_STATUS_ERROR",
    "JOB_STATUS_FAILED",
    "JOB_STATUS_FINISHED",
    "JOB_STATUS_PENDING",
    "JOB_STATUS_QUARANTINED",
    "JOB_STATUS_RUNNING",
    "JOB_STATUS_WAITING_FOR_HUMAN",
    "JOB_STATUS_WAITING_FOR_PARALLEL",
    "JOB_STATUS_WAITING_FOR_WORKER",
    "MSG_TYPE_PROGRESS",
    "PROTOCOL_VERSION",
    "STS_TOKEN_ENDPOINT",
    "TASK_STATUS_CANCELLED",
    "TASK_STATUS_FAILURE",
    "TASK_STATUS_SUCCESS",
    "WORKER_API_PREFIX",
    "WS_ENDPOINT",
    # Exceptions
    "RxonError",
    "RxonNetworkError",
    "RxonAuthError",
    "RxonProtocolError",
    "IntegrityError",
    "ParamValidationError",
    "S3ConfigMismatchError",
    # Models
    "FileMetadata",
    "GPUInfo",
    "Heartbeat",
    "InstalledModel",
    "ProgressUpdatePayload",
    "Resources",
    "TaskError",
    "TaskPayload",
    "TaskResult",
    "TokenResponse",
    "WorkerCapabilities",
    "WorkerCommand",
    "WorkerRegistration",
    # Security
    "create_client_ssl_context",
    "create_server_ssl_context",
    "extract_cert_identity",
    # Transports
    "Listener",
    "Transport",
    "create_transport",
    "HttpTransport",
    "HttpListener",
    # Utils
    "to_dict",
    # Validators
    "is_valid_identifier",
    "validate_identifier",
]

try:
    __version__ = version("rxon")
except PackageNotFoundError:
    __version__ = "unknown"
