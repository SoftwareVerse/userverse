"""Normalize roles to a global catalog shared across companies.

Revision ID: a4e8c1b7d2f9
Revises: 4f9d2f8f6c13
Create Date: 2026-08-03 18:45:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a4e8c1b7d2f9"
down_revision: Union[str, None] = "4f9d2f8f6c13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_TEMP = "role_global_tmp"
COMPANY_ROLE_TEMP = "company_role_tmp"
ASSOCIATION_TEMP = "association_user_company_tmp"


def _reflect_table(connection, table_name: str) -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(table_name, metadata, autoload_with=connection)


def _has_column(connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(connection)
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()

    if _has_column(connection, "role", "id") and not _has_column(
        connection, "role", "company_id"
    ):
        return

    op.create_table(
        ROLE_TEMP,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column(
            "_created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("_closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("primary_meta_data", sa.JSON(), nullable=True),
        sa.Column("secondary_meta_data", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        COMPANY_ROLE_TEMP,
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column(
            "_created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("_closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("primary_meta_data", sa.JSON(), nullable=True),
        sa.Column("secondary_meta_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], [f"{ROLE_TEMP}.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id", "role_id"),
        sa.UniqueConstraint("company_id", "role_id", name="uq_company_role"),
    )
    op.create_table(
        ASSOCIATION_TEMP,
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column(
            "_created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("_closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("primary_meta_data", sa.JSON(), nullable=True),
        sa.Column("secondary_meta_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["role_id"], [f"{ROLE_TEMP}.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "company_id"),
    )

    role_table = _reflect_table(connection, "role")
    association_table = _reflect_table(connection, "association_user_company")

    role_target = _reflect_table(connection, ROLE_TEMP)
    company_role_target = _reflect_table(connection, COMPANY_ROLE_TEMP)
    association_target = _reflect_table(connection, ASSOCIATION_TEMP)

    role_rows = connection.execute(sa.select(role_table)).mappings().all()
    association_rows = connection.execute(sa.select(association_table)).mappings().all()

    global_role_ids: dict[str, str] = {}
    role_descriptions: dict[str, str | None] = {}
    role_key_map: dict[tuple[str, str], str] = {}

    for row in role_rows:
        role_name = row["name"]
        company_id = str(row["company_id"])
        role_id = global_role_ids.get(role_name)
        if role_id is None:
            role_id = str(uuid4())
            global_role_ids[role_name] = role_id
            role_descriptions[role_name] = row.get("description")
            connection.execute(
                sa.insert(role_target).values(
                    id=role_id,
                    name=role_name,
                    description=row.get("description"),
                    _created_at=row.get("_created_at"),
                    _updated_at=row.get("_updated_at"),
                    _closed_at=row.get("_closed_at"),
                    primary_meta_data=row.get("primary_meta_data"),
                    secondary_meta_data=row.get("secondary_meta_data"),
                )
            )
        elif (
            role_descriptions[role_name] is None and row.get("description") is not None
        ):
            role_descriptions[role_name] = row.get("description")
            connection.execute(
                sa.update(role_target)
                .where(role_target.c.id == role_id)
                .values(description=row.get("description"))
            )

        role_key_map[(company_id, role_name)] = role_id
        connection.execute(
            sa.insert(company_role_target).values(
                company_id=row["company_id"],
                role_id=role_id,
                _created_at=row.get("_created_at"),
                _updated_at=row.get("_updated_at"),
                _closed_at=row.get("_closed_at"),
                primary_meta_data=row.get("primary_meta_data"),
                secondary_meta_data=row.get("secondary_meta_data"),
            )
        )

    for row in association_rows:
        role_id = role_key_map[(str(row["company_id"]), row["role_name"])]
        secondary_meta_data = row.get("secondary_meta_data") or {}
        secondary_meta_data["_legacy_role_name"] = row["role_name"]
        connection.execute(
            sa.insert(association_target).values(
                user_id=row["user_id"],
                company_id=row["company_id"],
                role_id=role_id,
                _created_at=row.get("_created_at"),
                _updated_at=row.get("_updated_at"),
                _closed_at=row.get("_closed_at"),
                primary_meta_data=row.get("primary_meta_data"),
                secondary_meta_data=secondary_meta_data,
            )
        )

    op.drop_table("association_user_company")
    if _has_column(connection, "company_role", "role_id"):
        op.drop_table("company_role")
    op.drop_table("role")

    op.rename_table(ROLE_TEMP, "role")
    op.rename_table(COMPANY_ROLE_TEMP, "company_role")
    op.rename_table(ASSOCIATION_TEMP, "association_user_company")


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError(
        "Downgrade is not supported for the role catalog normalization migration."
    )
