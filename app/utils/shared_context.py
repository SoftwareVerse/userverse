# app/utils/shared_context.py
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.user.account_status import UserAccountStatus
from app.models.user.user import UserReadModel
from app.utils.logging import logger


class SharedContext:
    def __init__(
        self,
        configs: dict,
        db_session: Session,
        user: Optional[UserReadModel] = None,
        enforce_status_check: bool = False,  # <-- optional control
    ):
        self.configs: dict = configs
        if user:
            self.user: UserReadModel = user
        self.db_session = db_session

        if enforce_status_check:
            self._check_user_status()

    def _check_user_status(self):
        if self.user.status != UserAccountStatus.ACTIVE.name_value:
            raise ValueError(
                "Account is not active. Please verify your email or contact support.",
            )

    def get_user_email(self) -> str:
        """
        -  Returns the email of the user associated with this context.
        """
        return self.user.email

    def get_user(self) -> UserReadModel:
        """
        -  Returns the user object associated with this context.
        """
        return self.user

    def log_context(self) -> Dict[str, Any]:
        """
        -  Returns a dictionary containing the user email for logging purposes.
        """
        return {
            "user_email": self.get_user_email(),
        }

    def log_info(self, message: str):
        """
        -  Logs an informational message with the user email.
        """
        logger.info("user_email=%s, message=%s", self.get_user_email(), message)

    def log_error(self, message: str):
        """
        -  Logs an error message with the user email.
        """
        logger.error(
            "user_email=%s, message=%s",
            self.get_user_email(),
            message,
        )

    @staticmethod
    def safe_json(data: Any) -> Any:
        """
        - Converts various data types to a JSON-serializable format.
        - Handles datetime, date, Decimal, dict, and list types.
        - Returns the original data for other types.
        """
        if isinstance(data, (datetime, date)):
            return data.isoformat()
        if isinstance(data, Decimal):
            return float(data)  # or str(data) if you prefer string representation
        if isinstance(data, dict):
            return {k: SharedContext.safe_json(v) for k, v in data.items()}
        if isinstance(data, list):
            return [SharedContext.safe_json(i) for i in data]
        return data
