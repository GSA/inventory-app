import sys
from pathlib import Path

import pytest

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
sys.path.insert(0, str(CONFIG_DIR))

from startup_validation import (  # noqa: E402
    REQUIRED_ENV_VARS,
    StartupValidationError,
    validate_required_env_vars,
)


def test_validate_required_env_vars_returns_values_for_required_names():
    env_values = validate_required_env_vars(
        ("FIRST_REQUIRED_ENV_VAR", "SECOND_REQUIRED_ENV_VAR"),
        {
            "FIRST_REQUIRED_ENV_VAR": "first-value",
            "SECOND_REQUIRED_ENV_VAR": "second-value",
            "UNRELATED_ENV_VAR": "unrelated-value",
        },
    )

    assert env_values == {
        "FIRST_REQUIRED_ENV_VAR": "first-value",
        "SECOND_REQUIRED_ENV_VAR": "second-value",
    }


def test_validate_required_env_vars_rejects_missing_and_blank_values():
    with pytest.raises(StartupValidationError) as exc_info:
        validate_required_env_vars(
            (
                "PRESENT_ENV_VAR",
                "MISSING_ENV_VAR",
                "BLANK_ENV_VAR",
                "NULL_PLACEHOLDER_ENV_VAR",
                "NONE_PLACEHOLDER_ENV_VAR",
                "NIL_PLACEHOLDER_ENV_VAR",
                "UNDEFINED_PLACEHOLDER_ENV_VAR",
                "CHANGE_ME_PLACEHOLDER_ENV_VAR",
                "STRING_PREFIX_PLACEHOLDER_ENV_VAR",
            ),
            {
                "PRESENT_ENV_VAR": "present-value",
                "BLANK_ENV_VAR": "   ",
                "NULL_PLACEHOLDER_ENV_VAR": "null",
                "NONE_PLACEHOLDER_ENV_VAR": " None ",
                "NIL_PLACEHOLDER_ENV_VAR": "NIL",
                "UNDEFINED_PLACEHOLDER_ENV_VAR": "undefined",
                "CHANGE_ME_PLACEHOLDER_ENV_VAR": "CHANGE_ME",
                "STRING_PREFIX_PLACEHOLDER_ENV_VAR": "string:CHANGE_ME",
            },
        )

    expected = (
        "Missing required environment variable(s): MISSING_ENV_VAR, "
        "BLANK_ENV_VAR, NULL_PLACEHOLDER_ENV_VAR, NONE_PLACEHOLDER_ENV_VAR, "
        "NIL_PLACEHOLDER_ENV_VAR, UNDEFINED_PLACEHOLDER_ENV_VAR, "
        "CHANGE_ME_PLACEHOLDER_ENV_VAR, STRING_PREFIX_PLACEHOLDER_ENV_VAR"
    )
    assert str(exc_info.value) == expected


def test_required_env_vars_match_inventory_configuration():
    assert REQUIRED_ENV_VARS == (
        "CKAN___SECRET_KEY",
        "CKAN___WTF_CSRF_SECRET_KEY",
        "CKAN_SQLALCHEMY_URL",
    )


def test_validate_required_env_vars_accepts_inventory_defaults():
    env_values = validate_required_env_vars(
        environ={
            "CKAN___SECRET_KEY": "local-dev-secret-key",
            "CKAN___WTF_CSRF_SECRET_KEY": "local-dev-csrf-secret-key",
            "CKAN_SQLALCHEMY_URL": "postgresql://ckan:pass@db/ckan",
        }
    )

    assert env_values == {
        "CKAN___SECRET_KEY": "local-dev-secret-key",
        "CKAN___WTF_CSRF_SECRET_KEY": "local-dev-csrf-secret-key",
        "CKAN_SQLALCHEMY_URL": "postgresql://ckan:pass@db/ckan",
    }
