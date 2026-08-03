from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repository.database.base_model import BaseModel


class CompanyRole(BaseModel):
    __tablename__ = "company_role"

    company_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("company.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (UniqueConstraint("company_id", "role_id", name="uq_company_role"),)

    company = relationship("Company", back_populates="roles", overlaps="role")
    role = relationship("Role", back_populates="companies", overlaps="company")
