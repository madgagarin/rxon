from hashlib import sha256
from typing import Tuple
from urllib.parse import urlparse

__all__ = [
    "RXON_BLOB_SCHEME",
    "calculate_config_hash",
    "parse_uri",
]

RXON_BLOB_SCHEME = "s3"


def calculate_config_hash(endpoint: str | None, access_key: str | None, bucket: str | None) -> str | None:
    """
    Calculates a consistent hash of the Blob/S3 configuration.
    Used to ensure Workers and Orchestrators are talking to the same storage.
    Uses '|' as separator.
    """
    if not endpoint or not access_key or not bucket:
        return None

    config_str = f"{endpoint}|{access_key}|{bucket}"
    return sha256(config_str.encode()).hexdigest()[:16]


def parse_uri(uri: str, default_bucket: str | None = None, prefix: str = "") -> Tuple[str, str, bool]:
    """
    Parses a Blob/S3 URI or relative path into (bucket, key, is_directory).
    Protocol: s3://bucket/key

    :param uri: Full URI (s3://bucket/key) or relative path (key)
    :param default_bucket: Bucket to use if URI is relative
    :param prefix: Optional prefix to prepend to relative paths
    :return: (bucket, key, is_directory)
    :raises ValueError: If URI format is invalid or bucket is missing
    """
    is_dir = uri.endswith("/")

    if uri.startswith(f"{RXON_BLOB_SCHEME}://"):
        parsed = urlparse(uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        return bucket, key, is_dir
    else:
        if not default_bucket:
            raise ValueError(f"Cannot parse relative path '{uri}' without a default bucket.")

        clean_path = uri.lstrip("/")
        key = f"{prefix}{clean_path}" if prefix else clean_path
        return default_bucket, key, is_dir
