from typing import Optional

from app.configs import EmailSettings, get_settings
from app.utils.logging import logger


class EmailConfig:
    REQUIRED_FIELDS = ["HOST", "PORT", "USERNAME", "PASSWORD"]
    TEST_ENVIRONMENTS = {"test_environment", "testing", "test"}

    @classmethod
    def load(cls) -> Optional[EmailSettings]:
        settings = get_settings()
        if settings.environment in cls.TEST_ENVIRONMENTS:
            logger.warning("Skipping email config in test environment.")
            return None

        email_settings = settings.email
        if not email_settings.model_dump(exclude_none=True):
            logger.warning("Email configuration section is missing.")
            return None

        missing = [
            field
            for field, value in {
                "HOST": email_settings.host,
                "PORT": email_settings.port,
                "USERNAME": email_settings.username,
                "PASSWORD": email_settings.password,
            }.items()
            if not value
        ]
        if missing:
            logger.warning("Missing email config fields: %s", missing)
            return None

        return email_settings
