"""Add offline superuser bootstrap control and privileged audit events.

Revision ID: d1e5f7a9b302
Revises: c9f4a6b8d210
Create Date: 2026-08-07 18:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d1e5f7a9b302"
down_revision: Union[str, None] = "c9f4a6b8d210"
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
        "superuser_bootstrap_control",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bootstrap_user_id", sa.Uuid(), nullable=True),
        sa.Column("bootstrap_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bootstrap_method", sa.String(length=64), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["bootstrap_user_id"],
            ["user.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_superuser_bootstrap_singleton"),
    )
    op.create_table(
        "privileged_access_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=1024), nullable=False),
        sa.Column("previous_superuser", sa.Boolean(), nullable=False),
        sa.Column("resulting_superuser", sa.Boolean(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["user.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["user.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_privileged_access_event_target_created",
        "privileged_access_event",
        ["target_user_id", "_created_at"],
        unique=False,
    )
    op.bulk_insert(
        sa.table(
            "superuser_bootstrap_control",
            sa.column("id", sa.Integer()),
            sa.column("primary_meta_data", sa.JSON()),
            sa.column("secondary_meta_data", sa.JSON()),
        ),
        [
            {
                "id": 1,
                "primary_meta_data": {},
                "secondary_meta_data": {},
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_privileged_access_event_target_created",
        table_name="privileged_access_event",
    )
    op.drop_table("privileged_access_event")
    op.drop_table("superuser_bootstrap_control")
