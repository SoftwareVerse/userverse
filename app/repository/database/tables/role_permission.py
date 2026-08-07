from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repository.database.base_model import BaseModel


class RoleGlobalPermission(BaseModel):
    __tablename__ = "role_global_permission"

    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
    )
    global_permission_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_permission.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role = relationship("Role", back_populates="global_permission_links")
    permission = relationship("GlobalPermission", back_populates="role_links")


class CompanyRolePermission(BaseModel):
    __tablename__ = "company_role_permission"

    company_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    role_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    company_permission_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "role_id"],
            ["company_role.company_id", "company_role.role_id"],
            ondelete="CASCADE",
            name="fk_company_role_permission_company_role",
        ),
        ForeignKeyConstraint(
            ["company_id", "company_permission_id"],
            ["company_permission.company_id", "company_permission.id"],
            ondelete="CASCADE",
            name="fk_company_role_permission_company_permission",
        ),
        UniqueConstraint(
            "company_id",
            "role_id",
            "company_permission_id",
            name="uq_company_role_permission",
        ),
        Index(
            "ix_company_role_permission_company_permission",
            "company_id",
            "company_permission_id",
        ),
    )

    company_role = relationship(
        "CompanyRole",
        back_populates="company_permission_links",
        overlaps="permission,role_links",
    )
    permission = relationship(
        "CompanyPermission",
        back_populates="role_links",
        overlaps="company_role,company_permission_links",
    )
