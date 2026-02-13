import os
from typing import Optional


class EnvironmentManager:
    @classmethod
    def get_environment(cls, config_data: Optional[dict] = None) -> str:
        if os.getenv("TEST_ENVIRONMENT", "").strip().lower() == "true":
            return "test_environment"

        env_keys = ["env", "environment"]

        if config_data:
            for key in env_keys:
                value = config_data.get(key)
                if value:
                    return value.strip().lower()

        for key in env_keys:
            value = os.getenv(key, "").strip().lower()
            if value:
                return value

        return "development"
