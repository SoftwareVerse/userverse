from __future__ import annotations

import os
from typing import Any

SETTINGS_ENV_KEYS = (
    "ENVIRONMENT",
    "ENV",
    "SERVER_URL",
    "APP_NAME",
    "APP_DESCRIPTION",
    "APP_VERSION",
    "REPOSITORY",
    "DOCUMENTATION",
    "DATABASE_URL",
    "DB_TYPE",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_HOST",
    "DB_PORT",
    "DB_AUTO_CREATE",
    "DB_ECHO",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT",
    "DB_POOL_RECYCLE",
    "TESTING",
    "REQUIRE_EMAIL_VERIFICATION",
    "ENFORCE_EMAIL_VERIFICATION",
    "CORS_ALLOWED",
    "CORS_BLOCKED",
    "COR_ORIGINS__ALLOWED",
    "COR_ORIGINS__BLOCKED",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "JWT_TIMEOUT",
    "JWT_REFRESH_TIMEOUT",
    "JWT__SECRET",
    "JWT__ALGORITHM",
    "JWT__TIMEOUT",
    "JWT__REFRESH_TIMEOUT",
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_USERNAME",
    "EMAIL_PASSWORD",
    "EMAIL_TLS",
    "EMAIL_SSL",
    "EMAIL__HOST",
    "EMAIL__PORT",
    "EMAIL__USERNAME",
    "EMAIL__PASSWORD",
    "EMAIL__EMAIL_TLS",
    "EMAIL__EMAIL_SSL",
)


def strip_matching_quotes(value: Any) -> Any:
    if (
        isinstance(value, str)
        and len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    return value


def build_settings_env_snapshot() -> tuple[tuple[str, str | None], ...]:
    return tuple((key, os.getenv(key)) for key in SETTINGS_ENV_KEYS)
