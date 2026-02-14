from ssl import SSLContext
from typing import Any

from .base import Transport
from .http import HttpTransport


def create_transport(
    url: str, worker_id: str, token: str, ssl_context: SSLContext | None = None, **kwargs: Any
) -> Transport:
    """
    Factory function to create the appropriate Transport based on the URL scheme.
    Currently supports: http://, https://, mock://
    """
    if url.startswith("http://") or url.startswith("https://"):
        return HttpTransport(base_url=url, worker_id=worker_id, token=token, ssl_context=ssl_context, **kwargs)

    if url.startswith("mock://"):
        from ..testing import MockTransport

        return MockTransport(worker_id=worker_id, token=token)

    raise ValueError(f"Unsupported transport scheme in URL: {url}")
