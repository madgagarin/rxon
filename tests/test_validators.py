import pytest

from rxon.validators import is_valid_identifier, validate_identifier


def test_is_valid_identifier():
    assert is_valid_identifier("worker-01") is True
    assert is_valid_identifier("gpu_worker") is True
    assert is_valid_identifier("Task123") is True
    assert is_valid_identifier("simple") is True

    assert is_valid_identifier("invalid space") is False
    assert is_valid_identifier("invalid/slash") is False
    assert is_valid_identifier("invalid.dot") is False
    assert is_valid_identifier("") is False
    assert is_valid_identifier(None) is False


def test_validate_identifier_raises():
    with pytest.raises(ValueError) as excinfo:
        validate_identifier("bad/id")
    assert "Invalid identifier" in str(excinfo.value)


def test_validate_identifier_success():
    try:
        validate_identifier("good-id")
    except ValueError:
        pytest.fail("validate_identifier raised ValueError unexpectedly")
