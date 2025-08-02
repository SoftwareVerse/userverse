import os
import sys
import json
from pathlib import Path
from app.utils.config.cors import CorsConfig
from app.utils.config.database import DatabaseConfig
from app.utils.config.environment import EnvironmentManager
from app.utils.logging import logger

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class ConfigLoader:
    """
    Loads application configuration from JSON or pyproject.toml.
    Falls back to default test config if no valid configuration is found.
    """

    def __init__(self, environment: str = None):
        self.json_config_path = self._resolve_json_path(os.getenv("JSON_CONFIG_PATH"))
        self.environment = environment
        self.config = self._load_config()

    def _resolve_json_path(self, path_str):
        if not path_str:
            return None
        path = Path(path_str).resolve()
        if not path.exists():
            raise ValueError(f"JSON config file does not exist: {path}")
        return path

    def _set_environment(self, config_data):
        return self.environment or EnvironmentManager.get_environment(config_data)

    def _load_config(self):
        if self.json_config_path:
            try:
                logger.info("Loading configuration from JSON")
                with open(self.json_config_path) as f:
                    config_data = json.load(f)
                return self._build_config_dict(config_data)
            except Exception as e:
                logger.error("Error loading JSON configuration: %s", e)
                raise ValueError(f"Error loading configuration: {e}")

        try:
            return self._load_from_toml()
        except Exception as e:
            logger.error("Error loading configuration from pyproject.toml: %s", e)
            logger.warning("Falling back to default test config.")
            return self._default_test_config()

    def _load_from_toml(self):
        logger.info("Loading configuration from pyproject.toml")
        pyproject_path = Path(__file__).resolve().parents[3] / "pyproject.toml"

        if not pyproject_path.exists():
            logger.warning("pyproject.toml not found — using default test config.")
            return self._default_test_config()

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Extract sections
        userverse_config = (
            pyproject_data.get("tool", {}).get("userverse", {}).get("config", {})
        )
        project_config = pyproject_data.get("project", {})

        logger.info("📦 [project] section loaded from pyproject.toml:")
        for key, val in project_config.items():
            logger.info(f"  {key} = {val}")

        # Merge configuration
        config_data = {
            "name": project_config.get("name") or userverse_config.get("name"),
            "version": project_config.get("version") or userverse_config.get("version"),
            "server_url": project_config.get("server_url")
            or userverse_config.get("server_url"),
            "description": project_config.get("description")
            or userverse_config.get("description"),
            "database": userverse_config.get("database", {}),
            "cor_origins": userverse_config.get("cor_origins", {}),
            "jwt": userverse_config.get("jwt", {}),
            "email": userverse_config.get("email", {}),
        }

        return self._build_config_dict(config_data)

    def _build_config_dict(self, config_data: dict):
        if not isinstance(config_data, dict):
            raise TypeError("Expected config_data to be a dict")

        environment = self._set_environment(config_data)
        return {
            "environment": environment,
            "database_url": DatabaseConfig.get_connection_string(
                config_data, environment
            ),
            "server_url": config_data.get("server_url", "http://localhost:8000"),
            "cor_origins": CorsConfig.get_cors(config_data, environment),
            "jwt": config_data.get("jwt", {}),
            "email": config_data.get("email", {}),
            "name": config_data.get("name", "Userverse"),
            "version": config_data.get("version", "0.1.0"),
            "description": config_data.get("description", "Userverse backend API"),
        }

    def _default_test_config(self):
        logger.info("Using default test configuration")
        return self._build_config_dict({})

    def get_config(self):
        return self.config
