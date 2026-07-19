from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.utils.env import build_settings_env_snapshot, strip_matching_quotes
from app.utils.parsing import normalize_origins
from app.utils.project_metadata import load_project_defaults

load_dotenv()
_PROJECT_DEFAULTS = load_project_defaults(Path(__file__).resolve().parent.parent)
DEFAULT_JWT_SECRET = "secret1234"
INSECURE_JWT_SECRET_ALLOWED_ENVIRONMENTS = {"development", "testing", "test"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        validate_default=False,
    )

    ENVIRONMENT: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "ENV"),
    )
    SERVER_URL: str = Field(
        default="http://localhost:8500",
        validation_alias=AliasChoices("SERVER_URL"),
    )
    APP_NAME: str = Field(
        default=_PROJECT_DEFAULTS["name"] or "Userverse",
        validation_alias=AliasChoices("APP_NAME"),
    )
    APP_DESCRIPTION: str = Field(
        default=_PROJECT_DEFAULTS["description"] or "Userverse backend API",
        validation_alias=AliasChoices("APP_DESCRIPTION"),
    )
    APP_VERSION: str = Field(
        default=_PROJECT_DEFAULTS["version"] or "0.1.0",
        validation_alias=AliasChoices("APP_VERSION"),
    )
    REPOSITORY: str | None = Field(
        default=_PROJECT_DEFAULTS["repository"],
        validation_alias=AliasChoices("REPOSITORY"),
    )
    DOCUMENTATION: str | None = Field(
        default=_PROJECT_DEFAULTS["documentation"],
        validation_alias=AliasChoices("DOCUMENTATION"),
    )

    DATABASE_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL"),
    )
    DB_TYPE: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DB_TYPE"),
    )
    DB_USER: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DB_USER"),
    )
    DB_PASSWORD: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DB_PASSWORD"),
    )
    DB_NAME: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DB_NAME"),
    )
    DB_HOST: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DB_HOST"),
    )
    DB_PORT: int = Field(
        default=5432,
        validation_alias=AliasChoices("DB_PORT"),
    )
    DB_AUTO_CREATE: bool = Field(
        default=True,
        validation_alias=AliasChoices("DB_AUTO_CREATE"),
    )
    DB_ECHO: bool = Field(
        default=False,
        validation_alias=AliasChoices("DB_ECHO"),
    )
    DB_POOL_SIZE: int = Field(
        default=5,
        validation_alias=AliasChoices("DB_POOL_SIZE"),
    )
    DB_MAX_OVERFLOW: int = Field(
        default=10,
        validation_alias=AliasChoices("DB_MAX_OVERFLOW"),
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        validation_alias=AliasChoices("DB_POOL_TIMEOUT"),
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800,
        validation_alias=AliasChoices("DB_POOL_RECYCLE"),
    )
    TESTING: bool = Field(
        default=False,
        validation_alias=AliasChoices("TESTING"),
    )
    ENABLE_PROFILING: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_PROFILING"),
    )

    CORS_ALLOWED: list[str] = Field(
        default_factory=lambda: ["*"],
        validation_alias=AliasChoices("CORS_ALLOWED", "COR_ORIGINS__ALLOWED"),
    )
    CORS_BLOCKED: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias=AliasChoices("CORS_BLOCKED", "COR_ORIGINS__BLOCKED"),
    )

    JWT_SECRET: str = Field(
        default=DEFAULT_JWT_SECRET,
        validation_alias=AliasChoices("JWT_SECRET", "JWT__SECRET"),
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "JWT__ALGORITHM"),
    )
    JWT_TIMEOUT: int = Field(
        default=15,
        validation_alias=AliasChoices("JWT_TIMEOUT", "JWT__TIMEOUT"),
    )
    JWT_REFRESH_TIMEOUT: int = Field(
        default=60,
        validation_alias=AliasChoices("JWT_REFRESH_TIMEOUT", "JWT__REFRESH_TIMEOUT"),
    )

    EMAIL_HOST: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMAIL_HOST", "EMAIL__HOST"),
    )
    EMAIL_PORT: int | None = Field(
        default=None,
        validation_alias=AliasChoices("EMAIL_PORT", "EMAIL__PORT"),
    )
    EMAIL_USERNAME: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMAIL_USERNAME", "EMAIL__USERNAME"),
    )
    EMAIL_PASSWORD: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMAIL_PASSWORD", "EMAIL__PASSWORD"),
    )
    EMAIL_TLS: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("EMAIL_TLS", "EMAIL__EMAIL_TLS"),
    )
    EMAIL_SSL: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("EMAIL_SSL", "EMAIL__EMAIL_SSL"),
    )

    @model_validator(mode="after")
    def normalize_settings(self) -> "Settings":
        for field_name in self.__class__.model_fields:
            object.__setattr__(
                self,
                field_name,
                strip_matching_quotes(getattr(self, field_name)),
            )

        object.__setattr__(self, "ENVIRONMENT", self.ENVIRONMENT.strip().lower())
        object.__setattr__(self, "SERVER_URL", self.SERVER_URL.rstrip("/"))
        object.__setattr__(self, "CORS_ALLOWED", normalize_origins(self.CORS_ALLOWED))
        object.__setattr__(self, "CORS_BLOCKED", normalize_origins(self.CORS_BLOCKED))

        if (
            self.JWT_SECRET == DEFAULT_JWT_SECRET
            and not self.TESTING
            and self.ENVIRONMENT not in INSECURE_JWT_SECRET_ALLOWED_ENVIRONMENTS
        ):
            raise ValueError(
                "JWT_SECRET must be explicitly set outside development/testing environments"
            )

        if not self.DATABASE_URL:
            object.__setattr__(self, "DATABASE_URL", self._build_database_url())

        return self

    def _build_database_url(self) -> str:
        db_type = (self.DB_TYPE or "").strip().lower()
        if db_type == "sqlite":
            return f"sqlite:///{self.DB_NAME or f'{self.ENVIRONMENT}.db'}"

        if db_type in {"postgres", "postgresql"}:
            required = [self.DB_USER, self.DB_PASSWORD, self.DB_NAME, self.DB_HOST]
            if all(required):
                return (
                    f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
                    f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                )

        if db_type == "mysql":
            required = [self.DB_USER, self.DB_PASSWORD, self.DB_NAME, self.DB_HOST]
            if all(required):
                return (
                    f"mysql://{self.DB_USER}:{self.DB_PASSWORD}"
                    f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                )

        return f"sqlite:///./{self.ENVIRONMENT}.db"

    @property
    def PROJECT_ROOT(self) -> Path:
        return Path(__file__).resolve().parent.parent


def _settings_env_snapshot() -> tuple[tuple[str, str | None], ...]:
    return build_settings_env_snapshot()


@lru_cache(maxsize=16)
def _resolve_settings(env_snapshot: tuple[tuple[str, str | None], ...]) -> Settings:
    _ = env_snapshot
    return Settings()


def get_settings() -> Settings:
    return _resolve_settings(_settings_env_snapshot())


class _SettingsProxy:
    def __init__(self) -> None:
        object.__setattr__(self, "_overrides", {})

    def __getattr__(self, name: str) -> Any:
        overrides = object.__getattribute__(self, "_overrides")
        if name in overrides:
            return overrides[name]
        return getattr(get_settings(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_overrides":
            object.__setattr__(self, name, value)
            return
        object.__getattribute__(self, "_overrides")[name] = value

    def __delattr__(self, name: str) -> None:
        overrides = object.__getattribute__(self, "_overrides")
        if name in overrides:
            del overrides[name]
            return
        raise AttributeError(name)

    def __dir__(self) -> list[str]:
        current = set(dir(get_settings()))
        current.update(object.__getattribute__(self, "_overrides").keys())
        return sorted(current)


settings = _SettingsProxy()
