from typing import Any

__all__ = [
    "to_dict",
]


def to_dict(obj: Any) -> Any:
    """
    Recursively converts NamedTuples to dicts for JSON serialization.
    Useful when not using orjson's native capabilities or for other serializers.
    """
    if hasattr(obj, "_asdict"):
        return {k: to_dict(v) for k, v in obj._asdict().items()}
    if isinstance(obj, list):
        return [to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj
