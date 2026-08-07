from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.models.user.account_status import UserAccountStatus
from app.repository.database.tables import (
    PrivilegedAccessEvent,
    SuperuserBootstrapControl,
    User,
)


class SuperuserBootstrapError(RuntimeError):
    """Raised when the one-time superuser bootstrap cannot safely proceed."""


@dataclass(frozen=True)
class SuperuserBootstrapCandidate:
    user_id: UUID
    email: str


@dataclass(frozen=True)
class SuperuserBootstrapResult:
    user_id: UUID
    changed: bool


class SuperuserBootstrapService:
    ACTION = "superuser_bootstrapped"
    SOURCE = "operator_cli"
    MAX_REASON_LENGTH = 1024

    def __init__(self, session: Session):
        self.db_session = session

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = email.strip().lower()
        if not normalized:
            raise SuperuserBootstrapError("An existing user's email is required.")
        return normalized

    def _get_target(self, email: str) -> User:
        normalized_email = self._normalize_email(email)
        user = (
            self.db_session.query(User)
            .filter(
                func.lower(User.email) == normalized_email,
                User._closed_at.is_(None),
            )
            .one_or_none()
        )
        if user is None:
            raise SuperuserBootstrapError(
                "No active user exists for the supplied email. Register and verify "
                "the account before bootstrapping."
            )
        status = (user.primary_meta_data or {}).get("status")
        if status != UserAccountStatus.ACTIVE.name_value:
            raise SuperuserBootstrapError(
                "The bootstrap target must be active and verified."
            )
        return user

    def get_candidate(self, email: str) -> SuperuserBootstrapCandidate:
        user = self._get_target(email)
        return SuperuserBootstrapCandidate(user_id=user.id, email=user.email)

    def _lock_control(self) -> SuperuserBootstrapControl:
        lock_result = self.db_session.execute(
            update(SuperuserBootstrapControl)
            .where(
                SuperuserBootstrapControl.id == SuperuserBootstrapControl.SINGLETON_ID
            )
            .values(_updated_at=datetime.now(timezone.utc))
        )
        if lock_result.rowcount != 1:
            raise SuperuserBootstrapError(
                "Superuser bootstrap control is missing. Apply Alembic migrations "
                "before running this command."
            )
        return (
            self.db_session.query(SuperuserBootstrapControl)
            .filter_by(id=SuperuserBootstrapControl.SINGLETON_ID)
            .with_for_update()
            .one()
        )

    @classmethod
    def _validate_reason(cls, reason: str) -> str:
        normalized = reason.strip()
        if not normalized:
            raise SuperuserBootstrapError("A bootstrap reason is required.")
        if len(normalized) > cls.MAX_REASON_LENGTH:
            raise SuperuserBootstrapError(
                f"The bootstrap reason cannot exceed {cls.MAX_REASON_LENGTH} characters."
            )
        return normalized

    def bootstrap(
        self,
        *,
        email: str,
        reason: str,
        expected_user_id: UUID,
    ) -> SuperuserBootstrapResult:
        normalized_reason = self._validate_reason(reason)
        try:
            control = self._lock_control()
            target = self._get_target(email)
            if target.id != expected_user_id:
                raise SuperuserBootstrapError(
                    "The confirmed user ID no longer matches the requested account."
                )

            if control.bootstrap_completed_at is not None:
                if control.bootstrap_user_id == target.id and target.is_superuser:
                    self.db_session.rollback()
                    return SuperuserBootstrapResult(
                        user_id=target.id,
                        changed=False,
                    )
                raise SuperuserBootstrapError(
                    "Initial superuser bootstrap has already been completed. Future "
                    "changes must use the superuser administration workflow."
                )

            existing_superuser = (
                self.db_session.query(User).filter(User.is_superuser.is_(True)).first()
            )
            if existing_superuser is not None:
                raise SuperuserBootstrapError(
                    "A superuser already exists, so initial bootstrap is disabled."
                )

            metadata = dict(target.primary_meta_data or {})
            try:
                refresh_token_version = int(metadata.get("refresh_token_version", 0))
            except (TypeError, ValueError):
                refresh_token_version = 0
            metadata["refresh_token_version"] = refresh_token_version + 1
            target.primary_meta_data = metadata
            target.is_superuser = True

            completed_at = datetime.now(timezone.utc)
            control.bootstrap_user_id = target.id
            control.bootstrap_completed_at = completed_at
            control.bootstrap_method = self.SOURCE
            self.db_session.add(
                PrivilegedAccessEvent(
                    actor_user_id=None,
                    target_user_id=target.id,
                    action=self.ACTION,
                    source=self.SOURCE,
                    reason=normalized_reason,
                    previous_superuser=False,
                    resulting_superuser=True,
                    request_id=None,
                    primary_meta_data={},
                    secondary_meta_data={},
                )
            )
            self.db_session.commit()
            return SuperuserBootstrapResult(user_id=target.id, changed=True)
        except Exception:
            self.db_session.rollback()
            raise
