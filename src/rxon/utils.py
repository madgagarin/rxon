# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import Any
from uuid import UUID

import msgspec
from orjson import OPT_NON_STR_KEYS, OPT_SORT_KEYS, dumps, loads

__all__ = [
    "to_dict",
    "from_dict",
    "json_dumps",
    "loads",
    "calculate_dict_hash",
]


def to_dict(obj: Any, _depth: int = 0) -> Any:
    """
    Converts any object to a JSON-serializable dictionary/list/scalar.
    Uses orjson round-trip to ensure consistency between signing and verification.
    """
    if _depth > 100:
        raise RecursionError("Maximum recursion depth (100) exceeded in to_dict")

    if obj is None:
        return None

    def default_handler(o: Any) -> Any:
        if isinstance(o, msgspec.Struct):
            try:
                return {k: v for k, v in msgspec.to_builtins(o).items() if not k.startswith("_")}
            except Exception:
                return str(o)
        if isinstance(o, Enum):
            return o.value
        if isinstance(o, (UUID, datetime)):
            return str(o)
        return str(o)

    try:
        # Round-trip through JSON ensures stable sorting and normalization for signing
        json_bytes = dumps(obj, default=default_handler, option=OPT_SORT_KEYS | OPT_NON_STR_KEYS)
    except TypeError as e:
        if "Recursion limit reached" in str(e):
            raise RecursionError("Maximum recursion depth (100) exceeded in to_dict") from e
        raise e
    normalized = loads(json_bytes)

    return _finalize_structure(normalized, _depth)


def _finalize_structure(data: Any, _depth: int = 0) -> Any:
    """Recursively removes None values and normalizes floats to ints."""
    if _depth > 100:
        raise RecursionError("Maximum recursion depth (100) exceeded in to_dict")
    if isinstance(data, dict):
        return {str(k): _finalize_structure(v, _depth + 1) for k, v in data.items() if v is not None}
    if isinstance(data, list):
        return [_finalize_structure(i, _depth + 1) for i in data]
    if isinstance(data, float) and data.is_integer():
        return int(data)
    return data


def from_dict(cls: Any, data: Any) -> Any:
    """Deeply restores Models from dictionaries using msgspec."""
    if data is None:
        return data

    try:
        if isinstance(data, cls):
            return data
    except TypeError:
        pass

    if isinstance(cls, type) and issubclass(cls, msgspec.Struct) and not isinstance(data, dict):
        return data

    try:
        return msgspec.convert(data, cls)
    except Exception as e:
        raise ValueError(f"Failed to instantiate {cls.__name__ if hasattr(cls, '__name__') else str(cls)}: {e}") from e


def json_dumps(obj: Any) -> str:
    """Wrapper for orjson.dumps returning str."""
    return dumps(to_dict(obj)).decode("utf-8")


def calculate_dict_hash(obj: Any) -> str:
    """Generates a stable SHA256 hash of an object."""
    message = dumps(to_dict(obj), option=OPT_SORT_KEYS)
    h: str = sha256(message).hexdigest()
    return h
