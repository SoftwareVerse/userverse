from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repository.database.base_model import BaseModel


class GlobalPermission(BaseModel):
    __tablename__ = "global_permission"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)

    role_links = relationship(
        "RoleGlobalPermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class CompanyPermission(BaseModel):
    __tablename__ = "company_permission"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_company_permission_company_name",
        ),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_company_permission_company_id_id",
        ),
    )

    company = relationship("Company", back_populates="permissions")
    role_links = relationship(
        "CompanyRolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )
