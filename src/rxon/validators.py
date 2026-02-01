from re import compile as re_compile

__all__ = [
    "is_valid_identifier",
    "validate_identifier",
]

# Standard identifier pattern: alphanumeric characters, underscores, and hyphens.
# This prevents path traversal, injection attacks, and ensuring compatibility with various backends.
ID_PATTERN = re_compile(r"^[a-zA-Z0-9_-]+$")


def is_valid_identifier(value: str) -> bool:
    """
    Checks if the provided string is a valid identifier for RXON ecosystem.
    Identifiers are used for worker_ids, job_ids, task_types, and blueprint_names.
    """
    if not value or not isinstance(value, str):
        return False
    return bool(ID_PATTERN.match(value))


def validate_identifier(value: str, name: str = "identifier") -> None:
    """
    Validates the identifier and raises a ValueError if invalid.
    """
    if not is_valid_identifier(value):
        raise ValueError(f"Invalid {name}: '{value}'. Must be alphanumeric, underscores, or hyphens only.")
