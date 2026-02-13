from app.configs import DatabaseSettings, _lower_keys
from app.utils.logging import logger


class DatabaseConfig:
    """Compatibility wrapper around app.configs.DatabaseSettings."""

    REQUIRED_FIELDS = ["TYPE", "HOST", "PORT", "USER", "PASSWORD", "NAME"]

    @classmethod
    def get_connection_string(
        cls, configs: dict, environment: str = "development"
    ) -> str:
        if environment == "test_environment":
            return "sqlite:///test_environment.db"

        db_config = configs.get("database", {})
        if not db_config:
            logger.warning("No database config found. Falling back to SQLite.")
            return f"sqlite:///{environment}.db"

        normalized = _lower_keys(db_config)
        if "username" in normalized and "user" not in normalized:
            normalized["user"] = normalized["username"]

        db_type = (normalized.get("type") or "").lower()
        if db_type not in ("", "sqlite"):
            missing_fields = [
                field for field in cls.REQUIRED_FIELDS if not db_config.get(field)
            ]
            if missing_fields:
                logger.warning(
                    "Missing database config fields: %s. Falling back to SQLite.",
                    missing_fields,
                )
                return f"sqlite:///{environment}.db"

        if db_type and db_type not in ("sqlite", "postgres", "postgresql", "mysql"):
            logger.warning(
                f"Unsupported database type: '{db_type}'. Falling back to SQLite."
            )
            return f"sqlite:///{environment}.db"

        return DatabaseSettings(**normalized).build_url(environment)
