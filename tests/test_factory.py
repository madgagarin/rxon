# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from typing import cast

from pytest import raises

from rxon.transports.factory import create_transport
from rxon.transports.http import HttpTransport


def test_create_transport_http() -> None:
    t = create_transport("http://localhost:8080", "worker-1", "token")
    assert cast(HttpTransport, t).base_url == "http://localhost:8080"


def test_create_transport_https() -> None:
    t = create_transport("https://api.example.com", "worker-1", "token")
    assert cast(HttpTransport, t).base_url == "https://api.example.com"


def test_create_transport_invalid_scheme() -> None:
    with raises(ValueError) as exc:
        create_transport("ftp://localhost", "worker-1", "token")
    assert "Unsupported transport scheme" in str(exc.value)
