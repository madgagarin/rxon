from __future__ import annotations

import re
from collections.abc import Callable
from enum import Enum
from threading import Lock
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID

import fastjsonschema
import msgspec
import orjson
from msgspec.structs import fields as msgspec_fields


def extract_json_schema(
    schema_type: Any, extractor: Callable[[Any], dict[str, Any] | None] | None = None
) -> dict[str, Any] | None:
    if schema_type is None:
        return None
    if isinstance(schema_type, dict):
        return schema_type

    if extractor:
        custom_schema = extractor(schema_type)
        if custom_schema is not None:
            return custom_schema

    if isinstance(schema_type, type) and issubclass(schema_type, msgspec.Struct):
        properties = {}
        required = []
        for field_info in msgspec_fields(schema_type):
            if field_info.name.startswith("_"):
                continue
            properties[field_info.name] = _python_type_to_json_schema(field_info.type)
            if field_info.default is msgspec.NODEFAULT and not _is_optional(field_info.type):
                required.append(field_info.name)
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    try:
        return _python_type_to_json_schema(schema_type)
    except Exception:
        return None


def _is_optional(tp: Any) -> bool:
    if isinstance(tp, UnionType):
        return type(None) in get_args(tp)
    origin = get_origin(tp)
    return origin is Union and type(None) in get_args(tp)


def _python_type_to_json_schema(tp: Any) -> dict[str, Any]:
    if tp is Any:
        return {}

    mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        None: "null",
        type(None): "null",
        UUID: "string",
    }

    if tp in mapping:
        return {"type": mapping[tp]}

    if isinstance(tp, type) and issubclass(tp, Enum):
        return {"type": "string", "enum": [e.value for e in tp]}

    if isinstance(tp, UnionType):
        return {"anyOf": [_python_type_to_json_schema(a) for a in get_args(tp)]}

    origin = get_origin(tp)
    args = get_args(tp)

    if origin is Union:
        return {"anyOf": [_python_type_to_json_schema(a) for a in args]}

    if origin is list or tp is list:
        item_type = args[0] if args else Any
        return {"type": "array", "items": _python_type_to_json_schema(item_type)}

    if origin is dict or tp is dict:
        return {"type": "object"}

    if isinstance(tp, type) and issubclass(tp, msgspec.Struct):
        nested = extract_json_schema(tp)
        return nested if nested else {"type": "object"}

    return {"type": "string"}


_validators_cache: dict[bytes, Any] = {}
_cache_lock = Lock()


def _get_val_by_path(data: Any, path_str: str) -> Any:
    if not path_str:
        return data
    parts = path_str.split(".")
    curr = data
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        elif isinstance(curr, (list, tuple)) and p.isdigit():
            curr = curr[int(p)]
        else:
            return None
    return curr


def translate_error(msg: str, data: Any) -> str:
    # Normalize index brackets e.g. data.tags[1] -> data.tags.1
    msg = re.sub(r"\[(\d+)\]", r".\1", msg)

    if "cannot be validated by any definition" in msg or "anyOf" in msg:
        return "Value does not match any schemas"

    # enum failure
    m = re.match(r"data(\.(.*)|) must be one of (.*)", msg)
    if m:
        _, path, enum_list = m.groups()
        val = _get_val_by_path(data, path)
        prefix = ""
        if path:
            parts = path.split(".")
            prefix = "".join(f"Field '{p}': " for p in parts)
        return f"{prefix}Value '{val}' is not allowed. Must be one of: {enum_list}"

    # Missing required field
    m = re.match(r"data(.*) must contain \[(.*)\]", msg)
    if m:
        path, field = m.groups()
        field_name = field.strip("'\"")
        prefix = ""
        if path:
            parts = [p.strip(".") for p in path.split(".") if p.strip(".")]
            if parts:
                prefix = "".join(f"Field '{p}': " for p in parts)
        return f"{prefix}Missing required field: '{field_name}'"

    # Unexpected field
    m = re.match(r"data(.*) must not contain \{(.*)\} properties", msg)
    if m:
        path, field = m.groups()
        field_name = field.strip("'\"")
        prefix = ""
        if path:
            parts = [p.strip(".") for p in path.split(".") if p.strip(".")]
            if parts:
                prefix = "".join(f"Field '{p}': " for p in parts)
        return f"{prefix}Unexpected field: '{field_name}'"

    # Type/value mismatch (with path)
    m = re.match(r"data\.(.*) must be (.*)", msg)
    if m:
        path, expected = m.groups()
        parts = path.split(".")
        prefix = "".join(f"Field '{p}': " for p in parts[:-1])
        last_field = parts[-1]

        # Check if list index
        if last_field.isdigit():
            if len(parts) >= 2:
                array_field = parts[-2]
                prefix = "".join(f"Field '{p}': " for p in parts[:-2])
                return f"{prefix}Field '{array_field}': Item at index {last_field}: Expected {expected}"
            else:
                return f"Item at index {last_field}: Expected {expected}"

        val = _get_val_by_path(data, path)
        if val is None:
            return f"{prefix}Field '{last_field}': Expected {expected}, got null"
        return f"{prefix}Field '{last_field}': Expected {expected}"

    # Type/value mismatch (top level, no path)
    m = re.match(r"data must be (.*)", msg)
    if m:
        expected = m.group(1)
        if data is None:
            return f"Expected {expected}, got null"
        return f"Expected {expected}"

    return msg


def validate_data(data: Any, schema: dict[str, Any] | None) -> tuple[bool, str | None]:
    if schema is None or not schema:
        return True, None

    schema_key = orjson.dumps(schema, option=orjson.OPT_SORT_KEYS)
    validator = _validators_cache.get(schema_key)
    if not validator:
        with _cache_lock:
            validator = _validators_cache.get(schema_key)
            if not validator:
                try:
                    validator = fastjsonschema.compile(schema)
                    _validators_cache[schema_key] = validator
                except Exception as e:
                    return False, f"Failed to compile schema: {e}"

    try:
        validator(data)
        return True, None
    except fastjsonschema.JsonSchemaValueException as e:
        return False, translate_error(e.message, data)
    except Exception as e:
        return False, str(e)


def extract_schema_from_func(
    func: Any, arg_name: str, extractor: Callable[[Any], dict[str, Any] | None] | None = None
) -> dict[str, Any] | None:
    try:
        hints = get_type_hints(func)
        param_hint = hints.get(arg_name)
        if param_hint:
            return extract_json_schema(param_hint, extractor=extractor)
    except Exception:
        pass
    return None


def extract_output_schema_from_func(
    func: Any, extractor: Callable[[Any], dict[str, Any] | None] | None = None
) -> dict[str, Any] | None:
    try:
        hints = get_type_hints(func)
        return_hint = hints.get("return")
        if return_hint:
            if get_origin(return_hint) is dict or return_hint is dict:
                return None
            return extract_json_schema(return_hint, extractor=extractor)
    except Exception:
        pass
    return None


def extract_skill_contract(
    blueprint: Any, extractor: Callable[[Any], dict[str, Any] | None] | None = None
) -> dict[str, Any]:
    """Analyzes a blueprint or function and returns its inferred interface contract."""
    input_schema = None
    if hasattr(blueprint, "start_state") and blueprint.start_state:
        start_handler = blueprint.handlers.get(blueprint.start_state)
        if not start_handler and hasattr(blueprint, "conditional_handlers"):
            for ch in blueprint.conditional_handlers:
                if ch.state == blueprint.start_state:
                    start_handler = ch.func
                    break
        if start_handler:
            input_schema = extract_schema_from_func(start_handler, "initial_data", extractor=extractor)

    end_schemas = []
    if hasattr(blueprint, "end_states"):
        for state in blueprint.end_states:
            handler = blueprint.handlers.get(state)
            if handler:
                schema = extract_output_schema_from_func(handler, extractor=extractor)
                if schema and schema not in end_schemas:
                    end_schemas.append(schema)

    output_schema = None
    if len(end_schemas) == 1:
        output_schema = end_schemas[0]
    elif len(end_schemas) > 1:
        output_schema = {"anyOf": end_schemas}

    output_statuses = set()
    if hasattr(blueprint, "_get_all_transitions"):
        if hasattr(blueprint, "end_states"):
            output_statuses.update(blueprint.end_states)
        if not output_statuses:
            output_statuses.update(["success", "failure"])

    return {
        "input_schema": input_schema,
        "output_schema": output_schema,
        "events_schema": getattr(blueprint, "events_schema", None),
        "output_statuses": sorted(output_statuses) if output_statuses else ["success", "failure"],
    }
