# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from msgspec import Struct
from pytest import raises

from rxon.utils import from_dict, json_dumps, to_dict


def test_to_dict_recursion_limit() -> None:
    a: dict[str, Any] = {}
    a["loop"] = a
    with raises(RecursionError, match="Maximum recursion depth"):
        to_dict(a)

    root: dict[str, Any] = {"v": 0}
    curr = root
    for i in range(1, 100):
        curr["n"] = {"v": i}
        curr = curr["n"]

    result = to_dict(root)
    assert result["n"]["v"] == 1

    curr["extra"] = {"final": True}
    with raises(RecursionError, match="Maximum recursion depth"):
        to_dict(root)

    complex_deep = {"a": [{"b": [{"c": "end"}]}]}
    assert to_dict(complex_deep)["a"][0]["b"][0]["c"] == "end"


def test_to_dict_normalization_floats() -> None:
    data = {"val": 10.0, "nested": [1.0, 2.5]}
    result = to_dict(data)

    assert isinstance(result["val"], int)
    assert result["val"] == 10
    assert isinstance(result["nested"][0], int)
    assert result["nested"][0] == 1
    assert isinstance(result["nested"][1], float)
    assert result["nested"][1] == 2.5


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Point(Struct):
    x: int
    y: int
    label: str | None = None


class Config(Struct):
    name: str
    points: list[Point]
    status: Status = Status.ACTIVE
    metadata: dict[str, str] | None = None


def test_to_dict_full() -> None:
    p1 = Point(1, 2, "start")
    c = Config(name="test", points=[p1], status=Status.INACTIVE, metadata={"env": "prod"})

    d = to_dict(c)
    assert d["name"] == "test"
    assert d["points"][0]["x"] == 1
    assert d["status"] == "inactive"
    assert d["metadata"] is not None
    assert d["metadata"]["env"] == "prod"


def test_to_dict_uuid() -> None:
    uid = uuid4()
    assert to_dict(uid) == str(uid)


def test_from_dict_full() -> None:
    data = {
        "name": "test",
        "points": [{"x": 10, "y": 20, "label": "A"}, {"x": 30, "y": 40}],
        "status": "inactive",
        "metadata": {"key": "val"},
    }

    c = from_dict(Config, data)
    assert isinstance(c, Config)
    assert len(c.points) == 2
    assert isinstance(c.points[0], Point)
    assert c.points[1].label is None
    assert c.status == Status.INACTIVE


def test_from_dict_negative() -> None:
    data = {"x": 1}
    with raises(ValueError, match="Failed to instantiate Point"):
        from_dict(Point, data)

    assert from_dict(Point, "not-a-dict") == "not-a-dict"
    assert from_dict(Point, None) is None


def test_json_dumps() -> None:
    p = Point(1, 2)
    s = json_dumps(p)
    assert '"x":1' in s
    assert '"y":2' in s


def test_from_dict_extra_fields() -> None:
    data = {"x": 10, "y": 20, "extra_garbage": "something"}
    p = from_dict(Point, data)
    assert p.x == 10
    assert p.y == 20
    assert not hasattr(p, "extra_garbage")


def test_from_dict_deep_nesting_and_mixed() -> None:
    class Deep(Struct):
        name: str
        config: Config
        meta: dict[str, Any]

    data = {
        "name": "deep",
        "config": {"name": "nested", "points": [{"x": 1, "y": 2}], "status": "active"},
        "meta": {"raw_list": [1, 2, {"a": 3}]},
    }

    res = from_dict(Deep, data)
    assert res.config.points[0].x == 1
    assert res.meta["raw_list"][2]["a"] == 3


def test_from_dict_extreme_chaos() -> None:
    data = {"points": "this-should-be-a-list-of-dicts"}
    with raises(ValueError, match="Failed to instantiate Config"):
        from_dict(Config, data)

    data2 = {"name": "test", "points": [123]}
    with raises(ValueError, match="Failed to instantiate Config"):
        from_dict(Config, data2)


def test_from_dict_optional_list() -> None:
    class Root(Struct):
        items: list[Point] | None = None

    r1 = from_dict(Root, {"items": None})
    assert r1.items is None

    r2 = from_dict(Root, {"items": [{"x": 1, "y": 2}]})
    assert r2.items is not None
    assert len(r2.items) == 1
    assert r2.items[0].x == 1


def test_from_dict_empty_collections() -> None:
    class Multi(Struct):
        tags: list[str] | None = None
        info: dict[str, int] | None = None

    m1 = from_dict(Multi, {"tags": None, "info": None})
    assert m1.tags is None
    assert m1.info is None

    m2 = from_dict(Multi, {"tags": [], "info": {}})
    assert m2.tags == []
    assert m2.info == {}


def test_from_dict_uuid() -> None:
    class Node(Struct):
        id: UUID
        tags: list[UUID] | None = None

    uid1 = uuid4()
    uid2 = uuid4()

    data = {"id": str(uid1), "tags": [str(uid2)]}

    node = from_dict(Node, data)
    assert node.id == uid1
    assert isinstance(node.id, UUID)
    assert node.tags is not None
    assert node.tags[0] == uid2
    assert isinstance(node.tags[0], UUID)


def test_from_dict_union_models_logic() -> None:
    class ModelA(Struct):
        a: int

    class Root(Struct):
        union: ModelA | str

    data_b = {"union": "hello"}

    res = from_dict(Root, data_b)
    assert res.union == "hello"

    data_a = {"union": {"a": 42}}
    res_a = from_dict(Root, data_a)
    assert isinstance(res_a.union, ModelA)
    assert res_a.union.a == 42


def test_from_dict_uuid_keys() -> None:
    class Registry(Struct):
        mapping: dict[UUID, str]

    uid = uuid4()
    data = {"mapping": {str(uid): "worker-1"}}

    res = from_dict(Registry, data)
    key = list(res.mapping.keys())[0]
    assert isinstance(key, UUID)
    assert key == uid
    assert res.mapping[key] == "worker-1"


def test_to_dict_none_preservation_in_lists() -> None:
    data = {"a": None, "b": [1, None, 2], "c": {"d": None, "e": 3}}
    result = to_dict(data)
    assert "a" not in result
    assert result["b"] == [1, None, 2]
    assert "d" not in result["c"]
    assert result["c"]["e"] == 3


def test_to_dict_integer_keys_normalization() -> None:
    data = {1: "int", "2": "str"}
    result = to_dict(data)
    assert result == {"1": "int", "2": "str"}
    assert all(isinstance(k, str) for k in result)


def test_to_dict_datetime_support() -> None:
    dt = datetime(2026, 5, 17, 12, 30, 0)
    result = to_dict(dt)
    assert isinstance(result, str)
    assert "2026-05-17" in result


def test_to_dict_float_normalization_edge_cases() -> None:
    data = {"normal": 10.5, "zero_frac": 10.0, "large": 1e10}
    result = to_dict(data)
    assert isinstance(result["normal"], float)
    assert isinstance(result["zero_frac"], int)
    assert isinstance(result["large"], int) or (isinstance(result["large"], float) and result["large"] == 1e10)

    data2 = {"small": 0.00000000000001}
    result2 = to_dict(data2)
    assert isinstance(result2["small"], float)


def test_from_dict_datetime() -> None:
    class Log(Struct):
        ts: datetime

    dt = datetime(2026, 5, 17, 12, 0, 0)
    data = {"ts": dt.isoformat()}

    res = from_dict(Log, data)
    assert isinstance(res.ts, datetime)
    assert res.ts == dt


def test_from_dict_datetime_negative() -> None:
    class Log(Struct):
        ts: datetime

    data = {"ts": "not-a-date"}
    with raises(ValueError, match="Failed to instantiate Log"):
        from_dict(Log, data)


def test_to_dict_deep_mixed_structures() -> None:
    class Node(Struct):
        val: int
        next: Any = None

    root = Node(0, {"a": [Node(1, None)]})
    result = to_dict(root)
    assert result["val"] == 0
    assert result["next"]["a"][0]["val"] == 1


def test_from_dict_container_list() -> None:
    data = [{"x": 1, "y": 2}, {"x": 3, "y": 4, "label": "test"}]
    res = from_dict(list[Point], data)
    assert isinstance(res, list)
    assert len(res) == 2
    assert isinstance(res[0], Point)
    assert res[0].x == 1
    assert res[0].y == 2
    assert isinstance(res[1], Point)
    assert res[1].label == "test"
