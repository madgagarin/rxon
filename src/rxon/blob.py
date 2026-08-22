# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from abc import ABC, abstractmethod
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse

from rxon.models import FileMetadata

__all__ = [
    "RXON_BLOB_SCHEME",
    "calculate_config_hash",
    "parse_uri",
    "BlobProvider",
]

RXON_BLOB_SCHEME = "s3"


class BlobProvider(ABC):
    """
    Abstract interface for Blob Storage providers (S3, GCS, Local).
    RXON uses URIs like s3://bucket/key to reference heavy data.
    """

    @abstractmethod
    async def upload(self, local_path: str, uri: str) -> "FileMetadata":
        """Uploads a local file to the storage and returns FileMetadata."""
        pass

    @abstractmethod
    async def download(self, uri: str, local_path: str) -> bool:
        """Downloads a file from storage to local path."""
        pass

    @abstractmethod
    async def get_metadata(self, uri: str) -> dict[str, Any] | None:
        """Returns metadata (size, etag, content-type) for a URI."""
        pass

    @abstractmethod
    async def delete(self, uri: str) -> bool:
        """Deletes a single object from storage."""
        pass

    @abstractmethod
    async def delete_dir(self, uri: str) -> bool:
        """Deletes all objects under a specific URI prefix."""
        pass


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


def parse_uri(uri: str, default_bucket: str | None = None, prefix: str = "") -> tuple[str, str, bool]:
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
