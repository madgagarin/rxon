# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from typing import Any

from pytest import mark, raises

from rxon.blob import BlobProvider, calculate_config_hash, parse_uri
from rxon.models import FileMetadata


def test_calculate_config_hash() -> None:
    h1 = calculate_config_hash("http://s3.local", "key123", "my-bucket")
    h2 = calculate_config_hash("http://s3.local", "key123", "my-bucket")
    assert h1 is not None
    assert h1 == h2
    assert len(h1) == 16

    assert calculate_config_hash(None, "key", "bucket") is None
    assert calculate_config_hash("http", "", "bucket") is None


def test_parse_uri_full() -> None:
    bucket, key, is_dir = parse_uri("s3://models/vision/yolo.pt")
    assert bucket == "models"
    assert key == "vision/yolo.pt"
    assert not is_dir


def test_parse_uri_directory() -> None:
    bucket, key, is_dir = parse_uri("s3://datasets/training/")
    assert bucket == "datasets"
    assert key == "training/"
    assert is_dir


def test_parse_uri_relative() -> None:
    bucket, key, is_dir = parse_uri("logs/today.txt", default_bucket="my-logs", prefix="worker-1/")
    assert bucket == "my-logs"
    assert key == "worker-1/logs/today.txt"


def test_parse_uri_negative() -> None:
    with raises(ValueError, match="without a default bucket"):
        parse_uri("some/path")

    with raises(ValueError):
        parse_uri("http://wrong-scheme.com/file")


def test_parse_uri_empty() -> None:
    with raises(ValueError):
        parse_uri("", default_bucket=None)


class MockBlobProvider(BlobProvider):
    async def upload(self, local_path: str, uri: str) -> FileMetadata:
        return FileMetadata(uri=uri, size=100, etag="fake-etag")

    async def download(self, uri: str, local_path: str) -> bool:
        return True

    async def get_metadata(self, uri: str) -> dict[str, Any] | None:
        return {}

    async def delete(self, uri: str) -> bool:
        return True

    async def delete_dir(self, uri: str) -> bool:
        return True


@mark.asyncio
async def test_blob_provider_interface() -> None:
    provider = MockBlobProvider()
    assert await provider.delete("s3://b/f") is True
    assert await provider.delete_dir("s3://b/d/") is True
