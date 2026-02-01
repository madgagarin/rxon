from pathlib import Path
from ssl import CERT_OPTIONAL, CERT_REQUIRED, Purpose, SSLContext, create_default_context
from typing import Any, Optional

__all__ = [
    "create_server_ssl_context",
    "create_client_ssl_context",
    "extract_cert_identity",
]


def create_server_ssl_context(
    cert_path: str | Path,
    key_path: str | Path,
    ca_path: Optional[str | Path] = None,
    require_client_cert: bool = False,
) -> SSLContext:
    """
    Creates an SSLContext for the server.

    :param cert_path: Path to the server's certificate.
    :param key_path: Path to the server's private key.
    :param ca_path: Path to the CA certificate to verify clients (required for mTLS).
    :param require_client_cert: If True, the server will demand a valid client certificate.
    """
    context = create_default_context(Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

    if ca_path:
        context.load_verify_locations(cafile=str(ca_path))

    if require_client_cert:
        context.verify_mode = CERT_REQUIRED
    else:
        context.verify_mode = CERT_OPTIONAL

    return context


def create_client_ssl_context(
    ca_path: Optional[str | Path] = None,
    cert_path: Optional[str | Path] = None,
    key_path: Optional[str | Path] = None,
) -> SSLContext:
    """
    Creates an SSLContext for the client (Worker).

    :param ca_path: Path to the CA certificate to verify the server.
    :param cert_path: Path to the client's certificate (for mTLS).
    :param key_path: Path to the client's private key (for mTLS).
    """
    context = create_default_context(Purpose.SERVER_AUTH)

    if ca_path:
        context.load_verify_locations(cafile=str(ca_path))

    if cert_path and key_path:
        context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

    return context


def extract_cert_identity(request: Any) -> Optional[str]:
    """
    Extracts the identity (Common Name) from the client certificate.
    Works with aiohttp request transport.
    """
    ssl_obj = request.transport.get_extra_info("ssl_object")
    if not ssl_obj:
        return None

    cert = ssl_obj.getpeercert()
    if not cert:
        return None

    for subject_parts in cert.get("subject", []):
        for rdn in subject_parts:
            if rdn[0] == "commonName":
                return rdn[1]
    return None
