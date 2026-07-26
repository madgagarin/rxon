# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from enum import Enum
from typing import Any

import msgspec

from rxon.schema import (
    extract_json_schema,
    extract_output_schema_from_func,
    extract_schema_from_func,
    validate_data,
)


class SimpleConfig(msgspec.Struct):
    enabled: bool
    retry_count: int = 3
    api_key: str | None = None


class NestedConfig(msgspec.Struct):
    name: str
    config: SimpleConfig
    tags: list[str]


class NTConfig(msgspec.Struct):
    name: str
    port: int = 8080
    debug: bool | None = None


def test_extract_json_schema_primitives() -> None:
    assert extract_json_schema(str) == {"type": "string"}
    assert extract_json_schema(int) == {"type": "integer"}
    assert extract_json_schema(float) == {"type": "number"}
    assert extract_json_schema(bool) == {"type": "boolean"}
    assert extract_json_schema(None) is None


def test_extract_json_schema_optional() -> None:
    schema = extract_json_schema(str | None)
    assert schema is not None
    assert "anyOf" in schema
    assert {"type": "string"} in schema["anyOf"]
    assert {"type": "null"} in schema["anyOf"]


def test_extract_json_schema_union() -> None:
    schema = extract_json_schema(int | str)
    assert schema is not None
    assert "anyOf" in schema
    assert {"type": "integer"} in schema["anyOf"]
    assert {"type": "string"} in schema["anyOf"]


def test_extract_json_schema_struct() -> None:
    schema = extract_json_schema(SimpleConfig)
    assert schema is not None
    assert schema["type"] == "object"
    assert schema["properties"]["enabled"] == {"type": "boolean"}
    assert schema["properties"]["retry_count"] == {"type": "integer"}
    assert "enabled" in schema["required"]
    assert "retry_count" not in schema["required"]


def test_extract_json_schema_struct2() -> None:
    schema = extract_json_schema(NTConfig)
    assert schema is not None
    assert schema["type"] == "object"
    assert schema["properties"]["name"] == {"type": "string"}
    assert "name" in schema["required"]
    assert "port" not in schema["required"]
    assert "debug" not in schema["required"]


def test_validate_data_negative() -> None:
    schema = extract_json_schema(NTConfig)

    is_valid, err = validate_data({"name": 123}, schema)
    assert not is_valid
    assert err is not None
    assert "Field 'name': Expected string" in err

    is_valid, err = validate_data({"port": 9000}, schema)
    assert not is_valid
    assert err is not None
    assert "Missing required field: 'name'" in err

    is_valid, err = validate_data({"name": "test", "extra": True}, schema)
    assert not is_valid
    assert err is not None
    assert "Unexpected field: 'extra'" in err

    is_valid, err = validate_data({"name": None}, schema)
    assert not is_valid
    assert err is not None
    assert "Field 'name': Expected string, got null" in err


def test_validate_nested_negative() -> None:
    schema = extract_json_schema(NestedConfig)

    data = {
        "name": "root",
        "config": {"enabled": "not-a-bool"},
        "tags": ["a", "b"],
    }
    is_valid, err = validate_data(data, schema)
    assert not is_valid
    assert err is not None
    assert "Field 'config': Field 'enabled': Expected boolean" in err

    data2 = {
        "name": "root",
        "config": {"enabled": True},
        "tags": ["a", 1],
    }
    is_valid, err = validate_data(data2, schema)
    assert not is_valid
    assert err is not None
    assert "Field 'tags': Item at index 1: Expected string" in err


def test_extract_from_func() -> None:
    def my_skill(initial_data: SimpleConfig) -> NTConfig:
        return NTConfig(name="dummy")

    input_schema = extract_schema_from_func(my_skill, "initial_data")
    assert input_schema is not None
    assert input_schema["properties"]["enabled"] == {"type": "boolean"}

    output_schema = extract_output_schema_from_func(my_skill)
    assert output_schema is not None
    assert output_schema["properties"]["name"] == {"type": "string"}


def test_extract_json_schema_enum() -> None:
    class Color(Enum):
        RED = "red"
        BLUE = "blue"

    schema = extract_json_schema(Color)
    assert schema == {"type": "string", "enum": ["red", "blue"]}


def test_extract_json_schema_any() -> None:
    schema = extract_json_schema(Any)
    assert schema == {}


def test_validate_data_enum() -> None:
    schema = {"type": "string", "enum": ["a", "b"]}
    is_valid, err = validate_data("a", schema)
    assert is_valid

    is_valid, err = validate_data("c", schema)
    assert not is_valid
    assert "is not allowed" in str(err)


def test_validate_data_nested_arrays() -> None:
    # A schema representing list of lists of strings
    schema = {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}

    assert validate_data([["a", "b"], ["c"]], schema)[0] is True
    assert validate_data([["a", 1]], schema)[0] is False
    assert validate_data(["a"], schema)[0] is False


def test_validate_data_union_anyof_failure() -> None:
    # Schema requires either a number > 100 or a specific string
    schema = {"anyOf": [{"type": "integer"}, {"type": "string", "enum": ["start", "stop"]}]}

    assert validate_data(123, schema)[0] is True
    assert validate_data("start", schema)[0] is True

    is_valid, err = validate_data("other", schema)
    assert not is_valid
    assert "Value does not match any schemas" in str(err)
