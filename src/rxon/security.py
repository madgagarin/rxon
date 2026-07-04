# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from hashlib import sha256
from hmac import compare_digest, new
from pathlib import Path
from ssl import CERT_OPTIONAL, CERT_REQUIRED, Purpose, SSLContext, create_default_context
from typing import Any, cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from orjson import OPT_SORT_KEYS, dumps

from .utils import to_dict

__all__ = [
    "create_server_ssl_context",
    "create_client_ssl_context",
    "extract_cert_identity",
    "sign_payload",
    "verify_signature",
    "sign_payload_ed25519",
    "verify_signature_ed25519",
    "sign_bubbling_chain",
    "verify_bubbling_chain_signature",
    "sign_bubbling_chain_hmac",
    "verify_bubbling_chain_hmac",
]


def sign_payload(payload: Any, secret: str, ignore_fields: list[str] | None = None) -> str:
    """
    Signs a payload using HMAC SHA256.
    :param payload: Data to sign (Model, dict, or list)
    :param secret: Secret key
    :param ignore_fields: List of top-level fields to exclude from signing (e.g., 'security')
    """
    if not secret:
        raise ValueError("Secret key for signing cannot be empty.")

    data = to_dict(payload)
    if isinstance(data, dict):
        data = dict(data)  # Shallow copy to avoid modifying original
        data.pop("security", None)
        if ignore_fields:
            for field in ignore_fields:
                data.pop(field, None)

    message = dumps(data, option=OPT_SORT_KEYS)
    return new(secret.encode("utf-8"), message, sha256).hexdigest()


def verify_signature(payload: Any, signature: str, secret: str, ignore_fields: list[str] | None = None) -> bool:
    """Verifies the HMAC SHA256 signature of a payload using constant-time comparison."""
    if not signature or not secret:
        return False
    expected_signature = sign_payload(payload, secret, ignore_fields=ignore_fields)
    return compare_digest(expected_signature, signature)


def sign_payload_ed25519(payload: Any, private_key_pem: str, ignore_fields: list[str] | None = None) -> str:
    """
    Signs a payload using Ed25519.
    :param payload: Data to sign (Model, dict, or list)
    :param private_key_pem: PEM-encoded private key
    :param ignore_fields: List of top-level fields to exclude from signing (e.g., 'security')
    """
    if not private_key_pem:
        raise ValueError("Private key for signing cannot be empty.")

    data = to_dict(payload)
    if isinstance(data, dict):
        data = dict(data)
        data.pop("security", None)
        if ignore_fields:
            for field in ignore_fields:
                data.pop(field, None)

    message = dumps(data, option=OPT_SORT_KEYS)

    private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise TypeError("Key is not an Ed25519 private key.")

    signature = private_key.sign(message)
    return signature.hex()


def verify_signature_ed25519(
    payload: Any, signature_hex: str, public_key_pem: str, ignore_fields: list[str] | None = None
) -> bool:
    """Verifies the Ed25519 signature of a payload."""
    if not signature_hex or not public_key_pem:
        return False

    data = to_dict(payload)
    if isinstance(data, dict):
        data = dict(data)
        data.pop("security", None)
        if ignore_fields:
            for field in ignore_fields:
                data.pop(field, None)

    message = dumps(data, option=OPT_SORT_KEYS)

    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            return False
        public_key.verify(bytes.fromhex(signature_hex), message)
        return True
    except Exception:
        return False


def sign_bubbling_chain(bubbling_chain: list[str], private_key_pem: str) -> str:
    """Signs the bubbling chain using Ed25519."""
    if not private_key_pem:
        raise ValueError("Private key cannot be empty.")

    message = dumps(bubbling_chain, option=OPT_SORT_KEYS)

    private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise TypeError("Key is not an Ed25519 private key.")

    signature = private_key.sign(message)
    return signature.hex()


def verify_bubbling_chain_signature(bubbling_chain: list[str], signature_hex: str, public_key_pem: str) -> bool:
    """Verifies the Ed25519 signature of the bubbling chain."""
    if not signature_hex or not public_key_pem:
        return False

    message = dumps(bubbling_chain, option=OPT_SORT_KEYS)

    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            return False
        public_key.verify(bytes.fromhex(signature_hex), message)
        return True
    except Exception:
        return False


def sign_bubbling_chain_hmac(bubbling_chain: list[str], secret: str) -> str:
    """Signs the bubbling chain using HMAC SHA256."""
    if not secret:
        raise ValueError("Secret cannot be empty.")
    message = dumps(bubbling_chain, option=OPT_SORT_KEYS)
    return new(secret.encode("utf-8"), message, sha256).hexdigest()


def verify_bubbling_chain_hmac(bubbling_chain: list[str], signature: str, secret: str) -> bool:
    """Verifies the HMAC SHA256 signature of the bubbling chain."""
    if not signature or not secret:
        return False
    expected = sign_bubbling_chain_hmac(bubbling_chain, secret)
    return compare_digest(expected, signature)


def create_server_ssl_context(
    cert_path: str | Path,
    key_path: str | Path,
    ca_path: str | Path | None = None,
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
    ca_path: str | Path | None = None,
    cert_path: str | Path | None = None,
    key_path: str | Path | None = None,
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


def extract_cert_identity(request: Any) -> str | None:
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
                return cast(str, rdn[1])
    return None
