from ssl import SSLContext
from typing import Any, Optional

from .base import Transport
from .http import HttpTransport


def create_transport(
    url: str, worker_id: str, token: str, ssl_context: Optional[SSLContext] = None, **kwargs: Any
) -> Transport:
    """
    Factory function to create the appropriate Transport based on the URL scheme.
    Currently supports: http://, https://
    """
    if url.startswith("http://") or url.startswith("https://"):
        return HttpTransport(base_url=url, worker_id=worker_id, token=token, ssl_context=ssl_context, **kwargs)

    raise ValueError(f"Unsupported transport scheme in URL: {url}")
