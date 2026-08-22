# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pytest import raises

from rxon.validators import is_valid_identifier, validate_identifier


def test_valid_identifiers() -> None:
    assert is_valid_identifier("worker-1")
    assert is_valid_identifier("job_123")
    assert is_valid_identifier("Complex-ID_01")


def test_invalid_identifiers() -> None:
    assert not is_valid_identifier("worker 1")
    assert not is_valid_identifier("worker/1")
    assert not is_valid_identifier("../etc/passwd")
    assert not is_valid_identifier("job; DROP TABLE")
    assert not is_valid_identifier("id$@#")
    assert not is_valid_identifier("")


def test_validate_identifier_raises() -> None:
    validate_identifier("valid-id")
    with raises(ValueError, match="Invalid test_id"):
        validate_identifier("invalid id!", name="test_id")
