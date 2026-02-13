from pathlib import Path
from functools import lru_cache
from typing import Any, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.logging import logger


_SETTINGS_ENV_KEYS = (
    "ENV",
    "TEST_ENVIRONMENT",
    "JSON_CONFIG_PATH",
    "DATABASE_URL",
    "DB_TYPE",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_HOST",
    "DB_PORT",
)


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
    use_ssl: Optional[bool] = None
    use_starttls: Optional[bool] = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=True,
    )

    env: Optional[str] = Field(default=None, alias="ENV")
    test_environment: bool = Field(default=False, alias="TEST_ENVIRONMENT")
    json_config_path: Optional[Path] = Field(default=None, alias="JSON_CONFIG_PATH")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    db_type: Optional[str] = Field(default=None, alias="DB_TYPE")
    db_user: Optional[str] = Field(default=None, alias="DB_USER")
    db_password: Optional[str] = Field(default=None, alias="DB_PASSWORD")
    db_name: Optional[str] = Field(default=None, alias="DB_NAME")
    db_host: Optional[str] = Field(default=None, alias="DB_HOST")
    db_port: Optional[int] = Field(default=None, alias="DB_PORT")

    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    server_url: Optional[str] = None
    repository: Optional[str] = None
    documentation: Optional[str] = None

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


@lru_cache(maxsize=1)
def _read_pyproject() -> dict[str, Any]:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if not pyproject_path.exists():
        return {}

    try:
        with pyproject_path.open("rb") as file_obj:
            import tomllib

            return tomllib.load(file_obj)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to read pyproject.toml: %s", exc)
        return {}


def _lower_keys(raw: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not raw:
        return {}
    return {str(key).lower(): value for key, value in raw.items()}


def _pyproject_defaults() -> dict[str, Any]:
    pyproject_data = _read_pyproject()
    project = pyproject_data.get("project", {})
    urls = project.get("urls", {})
    config = pyproject_data.get("tool", {}).get("userverse", {}).get("config", {})

    return {
        "env": config.get("environment") or config.get("env") or "development",
        "name": project.get("name") or config.get("name") or "Userverse",
        "version": project.get("version") or config.get("version") or "0.1.0",
        "description": project.get("description")
        or config.get("description")
        or "Userverse backend API",
        "server_url": config.get("server_url") or "http://localhost:8000/userverse",
        "repository": urls.get("Repository") or urls.get("repository"),
        "documentation": urls.get("Documentation") or urls.get("documentation"),
        "database": _lower_keys(config.get("database", {})),
        "cor_origins": _lower_keys(config.get("cor_origins", {})),
        "jwt": _lower_keys(config.get("jwt", {})),
        "email": _lower_keys(config.get("email", {})),
    }


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            for nested_key, nested_value in value.items():
                if nested_value is not None:
                    nested[nested_key] = nested_value
            merged[key] = nested
            continue
        merged[key] = value
    return merged


def _settings_env_snapshot() -> tuple[tuple[str, Optional[str]], ...]:
    import os

    return tuple((key, os.getenv(key)) for key in _SETTINGS_ENV_KEYS)


@lru_cache(maxsize=16)
def _resolve_settings(
    environment: Optional[str],
    env_snapshot: tuple[tuple[str, Optional[str]], ...],
) -> RuntimeSettings:
    defaults = _pyproject_defaults()
    env_settings = Settings().model_dump(mode="python")
    merged = _merge(defaults, env_settings)

    resolved_env = environment or merged.get("env") or "development"
    resolved_env = resolved_env.strip().lower()
    if merged.get("test_environment"):
        resolved_env = "test_environment"

    db_defaults = merged.get("database") or {}
    db_from_env = {
        "database_url": merged.get("database_url"),
        "type": merged.get("db_type"),
        "user": merged.get("db_user"),
        "password": merged.get("db_password"),
        "name": merged.get("db_name"),
        "host": merged.get("db_host"),
        "port": merged.get("db_port"),
    }
    db = DatabaseSettings(**_merge(db_defaults, db_from_env))
    cors = CorsSettings(**(merged.get("cor_origins") or {}))
    jwt = JwtSettings(**(merged.get("jwt") or {}))
    email = EmailSettings(**(merged.get("email") or {}))

    return RuntimeSettings(
        environment=resolved_env,
        database_url=db.build_url(resolved_env),
        server_url=merged.get("server_url") or "http://localhost:8000",
        cor_origins=cors,
        jwt=jwt,
        email=email,
        name=merged.get("name") or "Userverse",
        version=merged.get("version") or "0.1.0",
        description=merged.get("description") or "Userverse backend API",
        repository=merged.get("repository"),
        documentation=merged.get("documentation"),
    )


def get_settings(environment: Optional[str] = None) -> RuntimeSettings:
    # Return a copy so callers can mutate safely without affecting cache.
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
            "USE_SSL": runtime_settings.email.use_ssl,
            "USE_STARTTLS": runtime_settings.email.use_starttls,
        },
        "name": runtime_settings.name,
        "version": runtime_settings.version,
        "description": runtime_settings.description,
        "repository": runtime_settings.repository,
        "documentation": runtime_settings.documentation,
    }
