# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from re import compile as re_compile

__all__ = [
    "is_valid_identifier",
    "validate_identifier",
]

ID_PATTERN = re_compile(r"^[a-zA-Z0-9_-]+$")


def is_valid_identifier(value: str) -> bool:
    """
    Checks if the provided string is a valid identifier for RXON ecosystem.
    Identifiers are used for worker_ids, job_ids, task_types, and blueprint_names.
    """
    if not value or not isinstance(value, str) or len(value) > 128:
        return False
    return bool(ID_PATTERN.match(value))


def validate_identifier(value: str, name: str = "identifier") -> None:
    """
    Validates the identifier and raises a ValueError if invalid.
    """
    if not is_valid_identifier(value):
        raise ValueError(
            f"Invalid {name}: '{value}'. Must be alphanumeric, underscores, or hyphens only (max 128 characters)."
        )
