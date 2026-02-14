from typing import Any

__all__ = [
    "RxonError",
    "RxonNetworkError",
    "RxonAuthError",
    "RxonProtocolError",
    "S3ConfigMismatchError",
    "IntegrityError",
    "ParamValidationError",
]


class RxonError(Exception):
    """Base exception for all RXON library errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RxonNetworkError(RxonError):
    """Raised when a network operation fails (connection refused, timeout, etc.)."""

    pass


class RxonAuthError(RxonError):
    """Raised when authentication fails (401/403) and cannot be recovered."""

    pass


class RxonProtocolError(RxonError):
    """Raised when the server response violates the protocol (unexpected status, bad JSON)."""

    pass


class S3ConfigMismatchError(RxonProtocolError):
    """Raised when Worker and Orchestrator S3 configurations do not match."""

    pass


class IntegrityError(RxonProtocolError):
    """Raised when file integrity check (size/hash) fails."""

    pass


class ParamValidationError(RxonProtocolError):
    """Raised when task parameters fail validation."""

    pass
