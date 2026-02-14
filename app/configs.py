from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
import tomllib

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_SETTINGS_ENV_KEYS = (
    "ENV",
    "SERVER_URL",
    "APP_NAME",
    "APP_DESCRIPTION",
    "APP_VERSION",
    "REPOSITORY",
    "DOCUMENTATION",
    # DB flat envs (optional)
    "DATABASE_URL",
    "DB_TYPE",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_HOST",
    "DB_PORT",
    # Nested settings
    "COR_ORIGINS__ALLOWED",
    "COR_ORIGINS__BLOCKED",
    "JWT__SECRET",
    "JWT__ALGORITHM",
    "JWT__TIMEOUT",
    "JWT__REFRESH_TIMEOUT",
    "EMAIL__HOST",
    "EMAIL__PORT",
    "EMAIL__USERNAME",
    "EMAIL__PASSWORD",
    "EMAIL__EMAIL_TLS",
    "EMAIL__EMAIL_SSL",
)


@lru_cache(maxsize=1)
def _project_defaults() -> dict[str, Optional[str]]:
    defaults = {
        "name": "Userverse",
        "version": "0.1.0",
        "description": "Userverse backend API",
        "repository": None,
        "documentation": None,
    }
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as file:
            project = tomllib.load(file).get("project", {})
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return defaults

    project_urls = project.get("urls") or {}
    normalized_urls = {str(k).lower(): str(v) for k, v in project_urls.items()}

    return {
        "name": str(project.get("name") or defaults["name"]),
        "version": str(project.get("version") or defaults["version"]),
        "description": str(project.get("description") or defaults["description"]),
        "repository": normalized_urls.get("repository", defaults["repository"]),
        "documentation": normalized_urls.get("documentation", defaults["documentation"]),
    }


_PROJECT_DEFAULTS = _project_defaults()


class DatabaseSettings(BaseModel):
    database_url: Optional[str] = None
    type: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    host: Optional[str] = None
    port: int = 5432

    def build_url(self, environment: str) -> str:
        if self.database_url:
            return self.database_url

        db_type = (self.type or "").strip().lower()
        if db_type == "sqlite":
            return f"sqlite:///{self.name or f'{environment}.db'}"

        if db_type in ("postgres", "postgresql"):
            required = [self.user, self.password, self.name, self.host]
            if all(required):
                return (
                    f"postgresql+psycopg2://{self.user}:{self.password}"
                    f"@{self.host}:{self.port}/{self.name}"
                )

        if db_type == "mysql":
            required = [self.user, self.password, self.name, self.host]
            if all(required):
                return (
                    f"mysql://{self.user}:{self.password}"
                    f"@{self.host}:{self.port}/{self.name}"
                )

        return f"sqlite:///{environment}.db"


class CorsSettings(BaseModel):
    allowed: list[str] = Field(default_factory=lambda: ["*"])
    blocked: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


class JwtSettings(BaseModel):
    secret: str = "secret1234"
    algorithm: str = "HS256"
    timeout: int = 15
    refresh_timeout: int = 60


class EmailSettings(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None

    # Match your JSON keys (EMAIL_TLS / EMAIL_SSL)
    email_tls: Optional[bool] = None
    email_ssl: Optional[bool] = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=True,
        validate_default=False,
    )

    # Base
    env: str = Field(default="development", alias="ENV")
    server_url: str = Field(default="http://localhost:8500", alias="SERVER_URL")
    name: str = Field(default=_PROJECT_DEFAULTS["name"], alias="APP_NAME")
    description: str = Field(default=_PROJECT_DEFAULTS["description"], alias="APP_DESCRIPTION")
    version: str = Field(default=_PROJECT_DEFAULTS["version"], alias="APP_VERSION")
    repository: Optional[str] = Field(default=_PROJECT_DEFAULTS["repository"], alias="REPOSITORY")
    documentation: Optional[str] = Field(default=_PROJECT_DEFAULTS["documentation"], alias="DOCUMENTATION")

    # DB (flat env aliases)
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    db_type: Optional[str] = Field(default=None, alias="DB_TYPE")
    db_user: Optional[str] = Field(default=None, alias="DB_USER")
    db_password: Optional[str] = Field(default=None, alias="DB_PASSWORD")
    db_name: Optional[str] = Field(default=None, alias="DB_NAME")
    db_host: Optional[str] = Field(default=None, alias="DB_HOST")
    db_port: Optional[int] = Field(default=None, alias="DB_PORT")

    # Nested blocks
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cor_origins: CorsSettings = Field(default_factory=CorsSettings)
    jwt: JwtSettings = Field(default_factory=JwtSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)


class RuntimeSettings(BaseModel):
    environment: str
    database_url: str
    server_url: str
    cor_origins: CorsSettings
    jwt: JwtSettings
    email: EmailSettings
    name: str
    version: str
    description: str
    repository: Optional[str] = None
    documentation: Optional[str] = None


def _settings_env_snapshot() -> tuple[tuple[str, Optional[str]], ...]:
    import os

    return tuple((key, os.getenv(key)) for key in _SETTINGS_ENV_KEYS)


@lru_cache(maxsize=16)
def _resolve_settings(
    environment: Optional[str],
    env_snapshot: tuple[tuple[str, Optional[str]], ...],
) -> RuntimeSettings:
    _ = env_snapshot  # used for cache key stability

    settings = Settings()

    resolved_env = (environment or settings.env or "development").strip().lower()

    # Build DB settings:
    db_from_env = {
        "database_url": settings.database_url,
        "type": settings.db_type,
        "user": settings.db_user,
        "password": settings.db_password,
        "name": settings.db_name,
        "host": settings.db_host,
        "port": settings.db_port,
    }
    db = DatabaseSettings(**{k: v for k, v in db_from_env.items() if v is not None})

    # Allow nested "database" block to fill anything missing
    # (env_nested_delimiter enables DATABASE__TYPE etc if you ever add them)
    merged_db = DatabaseSettings(**{**settings.database.model_dump(exclude_none=True), **db.model_dump(exclude_none=True)})

    return RuntimeSettings(
        environment=resolved_env,
        database_url=merged_db.build_url(resolved_env),
        server_url=settings.server_url,
        cor_origins=settings.cor_origins,
        jwt=settings.jwt,
        email=settings.email,
        name=settings.name,
        version=settings.version,
        description=settings.description,
        repository=settings.repository,
        documentation=settings.documentation,
    )


def get_settings(environment: Optional[str] = None) -> RuntimeSettings:
    return _resolve_settings(environment, _settings_env_snapshot()).model_copy(deep=True)


def get_config(environment: Optional[str] = None) -> dict[str, Any]:
    runtime_settings = get_settings(environment=environment)
    return {
        "environment": runtime_settings.environment,
        "database_url": runtime_settings.database_url,
        "server_url": runtime_settings.server_url,
        "cor_origins": {
            "allowed": runtime_settings.cor_origins.allowed,
            "blocked": runtime_settings.cor_origins.blocked,
        },
        "jwt": {
            "SECRET": runtime_settings.jwt.secret,
            "ALGORITHM": runtime_settings.jwt.algorithm,
            "TIMEOUT": int(runtime_settings.jwt.timeout),
            "REFRESH_TIMEOUT": int(runtime_settings.jwt.refresh_timeout),
        },
        "email": {
            "HOST": runtime_settings.email.host,
            "PORT": runtime_settings.email.port,
            "USERNAME": runtime_settings.email.username,
            "PASSWORD": runtime_settings.email.password,
            "EMAIL_TLS": runtime_settings.email.email_tls,
            "EMAIL_SSL": runtime_settings.email.email_ssl,
        },
        "name": runtime_settings.name,
        "version": runtime_settings.version,
        "description": runtime_settings.description,
        "repository": runtime_settings.repository,
        "documentation": runtime_settings.documentation,
    }
