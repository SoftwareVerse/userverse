import unittest
from unittest.mock import patch
from app.utils.config.environment import (
    EnvironmentManager,
)  # Replace with your actual module name


class TestEnvironmentManager(unittest.TestCase):

    @patch("os.getenv")
    def test_returns_test_environment_when_env_var_true(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default="": (
            "true" if key == "TEST_ENVIRONMENT" else default
        )
        env = EnvironmentManager.get_environment()
        self.assertEqual(env, "test_environment")

    @patch("os.getenv")
    def test_returns_env_from_config_data(self, mock_getenv):
        mock_getenv.return_value = ""  # Make sure TEST_ENVIRONMENT is not "true"
        config = {"env": "production"}
        env = EnvironmentManager.get_environment(config)
        self.assertEqual(env, "production")

    @patch("os.getenv")
    def test_returns_env_from_os_env_variable(self, mock_getenv):
        def getenv_side_effect(key, default=""):
            return "staging" if key == "env" else ""

        mock_getenv.side_effect = getenv_side_effect
        env = EnvironmentManager.get_environment()
        self.assertEqual(env, "staging")

    @patch("os.getenv")
    def test_returns_default_when_nothing_set(self, mock_getenv):
        mock_getenv.return_value = ""  # Nothing in env vars
        env = EnvironmentManager.get_environment({})
        self.assertEqual(env, "development")


if __name__ == "__main__":
    # uv run -m tests.utils.config.test_environment_manager
    unittest.main()
