from typing import Any

from orjson import dumps

__all__ = [
    "to_dict",
    "json_dumps",
]


def to_dict(obj: Any) -> Any:
    """
    Recursively converts NamedTuples and Dataclasses to dicts for JSON serialization.
    Useful when not using orjson's native capabilities or for other serializers.
    """
    if hasattr(obj, "_asdict"):  # NamedTuple
        return {k: to_dict(v) for k, v in obj._asdict().items()}
    if hasattr(obj, "__dataclass_fields__"):  # Dataclass
        from dataclasses import asdict

        return {k: to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj


def json_dumps(obj: Any) -> str:
    """
    Wrapper for orjson.dumps that returns str (required by aiohttp).
    Automatically converts NamedTuples to dicts.
    """
    return dumps(to_dict(obj)).decode("utf-8")
