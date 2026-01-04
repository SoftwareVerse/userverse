from app.utils.logging import logger


class DatabaseConfig:
    """
    Database configuration class.
    """

    REQUIRED_FIELDS = ["TYPE", "HOST", "PORT", "USER", "PASSWORD", "NAME"]

    @classmethod
    def get_connection_string(
        cls, configs: dict, environment: str = "development"
    ) -> str:
        """
        Returns the connection string for the database.

        Args:
            configs (dict): Configuration data.
            environment (str): Current environment (e.g., 'development', 'production').

        Returns:
            str: Database connection string.
        """
        if environment == "test_environment":
            return f"sqlite:///{environment}.db"

        db_config = configs.get("database", {})
        if not db_config:
            logger.warning("No database config found. Falling back to SQLite.")
            return f"sqlite:///{environment}.db"

        db_type = db_config.get("TYPE", "").lower()

        # Only enforce required fields if not SQLite
        if db_type != "sqlite":
            missing_fields = [
                field for field in cls.REQUIRED_FIELDS if not db_config.get(field)
            ]
            if missing_fields:
                logger.warning(
                    "Missing database config fields: %s. Falling back to SQLite.", missing_fields
                )
                return f"sqlite:///{environment}.db"

        host = db_config.get("HOST", "")
        port = db_config.get("PORT", "")
        user = db_config.get("USER", "")
        password = db_config.get("PASSWORD", "")
        db_name = db_config.get("NAME", "")

        if db_type in ("postgresql", "postgres"):
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
        elif db_type == "mysql":
            return f"mysql://{user}:{password}@{host}:{port}/{db_name}"
        elif db_type == "sqlite":
            return f"sqlite:///{db_name or f'{environment}.db'}"
        else:
            logger.warning(
                "Unsupported database type: %s. Falling back to SQLite.", db_type
            )
            return f"sqlite:///{environment}.db"
