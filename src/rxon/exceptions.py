__all__ = [
    "RXONProtocolError",
    "S3ConfigMismatchError",
    "IntegrityError",
    "ParamValidationError",
]


class RXONProtocolError(Exception):
    """Base exception for all protocol-related errors."""

    pass


class S3ConfigMismatchError(RXONProtocolError):
    """Raised when Worker and Orchestrator S3 configurations do not match."""

    pass


class IntegrityError(RXONProtocolError):
    """Raised when file integrity check (size/hash) fails."""

    pass


class ParamValidationError(RXONProtocolError):
    """Raised when task parameters fail validation."""

    pass
