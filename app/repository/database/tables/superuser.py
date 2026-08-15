from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.repository.database.base_model import BaseModel


class SuperuserBootstrapControl(BaseModel):
    __tablename__ = "superuser_bootstrap_control"

    SINGLETON_ID = 1

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    bootstrap_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=True,
    )
    bootstrap_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    bootstrap_method: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )


class PrivilegedAccessEvent(BaseModel):
    __tablename__ = "privileged_access_event"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=True,
    )
    target_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(1024), nullable=False)
    previous_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resulting_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
