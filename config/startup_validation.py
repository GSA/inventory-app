import os
from collections.abc import Mapping, Sequence

REQUIRED_ENV_VARS = (
    "CKAN___SECRET_KEY",
    "CKAN___WTF_CSRF_SECRET_KEY",
    "CKAN_SQLALCHEMY_URL",
)
NULL_LIKE_PLACEHOLDER_VALUES = frozenset(
    {"null", "none", "nil", "undefined", "change_me"}
)


class StartupValidationError(RuntimeError):
    """Raised when the application cannot safely start."""


def _is_missing_required_value(value: str | None) -> bool:
    if value is None:
        return True

    stripped_value = value.strip()
    if not stripped_value:
        return True

    normalized_value = stripped_value.lower()
    if normalized_value.startswith("string:"):
        normalized_value = normalized_value[len("string:"):]

    return normalized_value in NULL_LIKE_PLACEHOLDER_VALUES


def validate_required_env_vars(
    required_env_vars: Sequence[str] = REQUIRED_ENV_VARS,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = os.environ if environ is None else environ
    missing_env_vars = [
        env_var
        for env_var in required_env_vars
        if _is_missing_required_value(env.get(env_var))
    ]

    if missing_env_vars:
        missing_list = ", ".join(missing_env_vars)
        raise StartupValidationError(
            f"Missing required environment variable(s): {missing_list}"
        )

    return {env_var: env[env_var] for env_var in required_env_vars}
