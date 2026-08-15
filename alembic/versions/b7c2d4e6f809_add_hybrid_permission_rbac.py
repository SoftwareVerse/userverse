"""Add hybrid global and company-scoped RBAC permissions.

Revision ID: b7c2d4e6f809
Revises: a4e8c1b7d2f9
Create Date: 2026-08-07 12:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7c2d4e6f809"
down_revision: Union[str, None] = "a4e8c1b7d2f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "_created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("_closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("primary_meta_data", sa.JSON(), nullable=False),
        sa.Column("secondary_meta_data", sa.JSON(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "global_permission",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "company_permission",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "id",
            name="uq_company_permission_company_id_id",
        ),
        sa.UniqueConstraint(
            "company_id",
            "name",
            name="uq_company_permission_company_name",
        ),
    )
    op.create_table(
        "role_global_permission",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("global_permission_id", sa.Uuid(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["global_permission_id"],
            ["global_permission.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "global_permission_id"),
    )
    op.create_table(
        "company_role_permission",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("company_permission_id", sa.Uuid(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["company_id", "company_permission_id"],
            ["company_permission.company_id", "company_permission.id"],
            name="fk_company_role_permission_company_permission",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "role_id"],
            ["company_role.company_id", "company_role.role_id"],
            name="fk_company_role_permission_company_role",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "company_id",
            "role_id",
            "company_permission_id",
        ),
        sa.UniqueConstraint(
            "company_id",
            "role_id",
            "company_permission_id",
            name="uq_company_role_permission",
        ),
    )
    op.create_index(
        "ix_company_role_permission_company_permission",
        "company_role_permission",
        ["company_id", "company_permission_id"],
        unique=False,
    )
    op.create_table(
        "user_role",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )


def downgrade() -> None:
    op.drop_table("user_role")
    op.drop_index(
        "ix_company_role_permission_company_permission",
        table_name="company_role_permission",
    )
    op.drop_table("company_role_permission")
    op.drop_table("role_global_permission")
    op.drop_table("company_permission")
    op.drop_table("global_permission")
