import pytest

from rxon.blob import calculate_config_hash, parse_uri


class TestBlobParsing:
    def test_full_s3_uri(self):
        bucket, key, is_dir = parse_uri("s3://my-bucket/folder/file.txt")
        assert bucket == "my-bucket"
        assert key == "folder/file.txt"
        assert is_dir is False

    def test_full_s3_uri_directory(self):
        bucket, key, is_dir = parse_uri("s3://data-lake/raw/")
        assert bucket == "data-lake"
        assert key == "raw/"
        assert is_dir is True

    def test_relative_path_with_default_bucket(self):
        bucket, key, is_dir = parse_uri("models/v1.bin", default_bucket="default-store")
        assert bucket == "default-store"
        assert key == "models/v1.bin"
        assert is_dir is False

    def test_relative_path_with_prefix(self):
        bucket, key, is_dir = parse_uri("v1.bin", default_bucket="store", prefix="models/")
        assert bucket == "store"
        assert key == "models/v1.bin"
        assert is_dir is False

    def test_relative_path_no_bucket_error(self):
        with pytest.raises(ValueError):
            parse_uri("file.txt")


class TestConfigHash:
    def test_calculate_hash(self):
        h1 = calculate_config_hash("http://minio:9000", "access", "bucket1")
        h2 = calculate_config_hash("http://minio:9000", "access", "bucket1")
        assert h1 == h2
        assert len(h1) == 16  # Check truncation

    def test_calculate_hash_diff(self):
        h1 = calculate_config_hash("http://minio:9000", "access", "bucket1")
        h2 = calculate_config_hash("http://minio:9000", "access", "bucket2")
        assert h1 != h2

    def test_calculate_hash_none(self):
        assert calculate_config_hash(None, "key", "bucket") is None
