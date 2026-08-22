# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ssl import SSLContext
from typing import Any

from rxon.testing import MockTransport

from .base import Transport
from .http import HttpTransport


def create_transport(
    url: str, worker_id: str, token: str, ssl_context: SSLContext | None = None, **kwargs: Any
) -> Transport:
    """
    Factory function to create the appropriate Transport based on the URL scheme.
    Currently supports: http://, https://, mock://
    """
    if url.startswith(("http://", "https://", "ws://", "wss://")):
        base_url = url
        if url.startswith("ws"):
            base_url = url.replace("ws", "http", 1)
        return HttpTransport(base_url=base_url, worker_id=worker_id, token=token, ssl_context=ssl_context, **kwargs)

    if url.startswith("mock://"):
        return MockTransport(worker_id=worker_id, token=token, **kwargs)

    raise ValueError(f"Unsupported transport scheme in URL: {url}")
