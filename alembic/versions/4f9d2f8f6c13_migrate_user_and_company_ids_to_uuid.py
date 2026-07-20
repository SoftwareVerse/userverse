"""Migrate user and company IDs to UUID.

Revision ID: 4f9d2f8f6c13
Revises: 9552b9fc884a
Create Date: 2026-07-20 20:05:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "4f9d2f8f6c13"
down_revision: Union[str, None] = "9552b9fc884a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_TEMP = "user_uuid_tmp"
COMPANY_TEMP = "company_uuid_tmp"
ROLE_TEMP = "role_uuid_tmp"
ASSOCIATION_TEMP = "association_user_company_uuid_tmp"


def _has_column(columns: list[dict], column_name: str) -> bool:
    return any(column["name"] == column_name for column in columns)


def _create_user_table(*, include_is_superuser: bool) -> None:
    columns = [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=255), nullable=True),
        sa.Column("password", sa.String(length=255), nullable=False),
    ]
    if include_is_superuser:
        columns.append(
            sa.Column(
                "is_superuser",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
    columns.extend(
        [
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
            sa.UniqueConstraint("email"),
        ]
    )
    op.create_table(USER_TEMP, *columns)


def _create_company_table() -> None:
    op.create_table(
        COMPANY_TEMP,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("phone_number", sa.String(length=16), nullable=True),
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
        sa.UniqueConstraint("email"),
    )


def _create_role_table() -> None:
    op.create_table(
        ROLE_TEMP,
        sa.Column("company_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["company_id"], [f"{COMPANY_TEMP}.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id", "name"),
    )


def _create_association_table() -> None:
    op.create_table(
        ASSOCIATION_TEMP,
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("role_name", sa.String(length=256), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], [f"{USER_TEMP}.id"]),
        sa.ForeignKeyConstraint(["company_id"], [f"{COMPANY_TEMP}.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "role_name"],
            [f"{ROLE_TEMP}.company_id", f"{ROLE_TEMP}.name"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "company_id"),
    )


def _reflect_table(connection, table_name: str) -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(table_name, metadata, autoload_with=connection)


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    user_columns = inspector.get_columns("user")
    include_is_superuser = _has_column(user_columns, "is_superuser")

    _create_user_table(include_is_superuser=include_is_superuser)
    _create_company_table()
    _create_role_table()
    _create_association_table()

    user_table = _reflect_table(connection, "user")
    company_table = _reflect_table(connection, "company")
    role_table = _reflect_table(connection, "role")
    association_table = _reflect_table(connection, "association_user_company")

    user_target = _reflect_table(connection, USER_TEMP)
    company_target = _reflect_table(connection, COMPANY_TEMP)
    role_target = _reflect_table(connection, ROLE_TEMP)
    association_target = _reflect_table(connection, ASSOCIATION_TEMP)

    user_rows = connection.execute(sa.select(user_table)).mappings().all()
    company_rows = connection.execute(sa.select(company_table)).mappings().all()
    role_rows = connection.execute(sa.select(role_table)).mappings().all()
    association_rows = connection.execute(sa.select(association_table)).mappings().all()

    user_id_map: dict[object, str] = {}
    company_id_map: dict[object, str] = {}

    for row in user_rows:
        user_id_map[row["id"]] = str(uuid4())
    for row in company_rows:
        company_id_map[row["id"]] = str(uuid4())

    for row in user_rows:
        payload = {
            "id": user_id_map[row["id"]],
            "first_name": row.get("first_name"),
            "last_name": row.get("last_name"),
            "email": row["email"],
            "phone_number": row.get("phone_number"),
            "password": row["password"],
            "_created_at": row.get("_created_at"),
            "_updated_at": row.get("_updated_at"),
            "_closed_at": row.get("_closed_at"),
            "primary_meta_data": row.get("primary_meta_data"),
            "secondary_meta_data": row.get("secondary_meta_data"),
        }
        if include_is_superuser:
            payload["is_superuser"] = bool(row.get("is_superuser", False))
        connection.execute(sa.insert(user_target).values(**payload))

    for row in company_rows:
        connection.execute(
            sa.insert(company_target).values(
                id=company_id_map[row["id"]],
                name=row.get("name"),
                description=row.get("description"),
                industry=row.get("industry"),
                email=row["email"],
                phone_number=row.get("phone_number"),
                _created_at=row.get("_created_at"),
                _updated_at=row.get("_updated_at"),
                _closed_at=row.get("_closed_at"),
                primary_meta_data=row.get("primary_meta_data"),
                secondary_meta_data=row.get("secondary_meta_data"),
            )
        )

    for row in role_rows:
        connection.execute(
            sa.insert(role_target).values(
                company_id=company_id_map[row["company_id"]],
                name=row["name"],
                description=row.get("description"),
                _created_at=row.get("_created_at"),
                _updated_at=row.get("_updated_at"),
                _closed_at=row.get("_closed_at"),
                primary_meta_data=row.get("primary_meta_data"),
                secondary_meta_data=row.get("secondary_meta_data"),
            )
        )

    for row in association_rows:
        connection.execute(
            sa.insert(association_target).values(
                user_id=user_id_map[row["user_id"]],
                company_id=company_id_map[row["company_id"]],
                role_name=row["role_name"],
                _created_at=row.get("_created_at"),
                _updated_at=row.get("_updated_at"),
                _closed_at=row.get("_closed_at"),
                primary_meta_data=row.get("primary_meta_data"),
                secondary_meta_data=row.get("secondary_meta_data"),
            )
        )

    op.drop_table("association_user_company")
    op.drop_table("role")
    op.drop_table("company")
    op.drop_table("user")

    op.rename_table(USER_TEMP, "user")
    op.rename_table(COMPANY_TEMP, "company")
    op.rename_table(ROLE_TEMP, "role")
    op.rename_table(ASSOCIATION_TEMP, "association_user_company")


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    user_columns = inspector.get_columns("user")
    include_is_superuser = _has_column(user_columns, "is_superuser")

    op.create_table(
        USER_TEMP,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=255), nullable=True),
        sa.Column("password", sa.String(length=255), nullable=False),
        *(
            [
                sa.Column(
                    "is_superuser",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            ]
            if include_is_superuser
            else []
        ),
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
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        COMPANY_TEMP,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("phone_number", sa.String(length=16), nullable=True),
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
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        ROLE_TEMP,
        sa.Column("company_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["company_id"], [f"{COMPANY_TEMP}.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id", "name"),
    )
    op.create_table(
        ASSOCIATION_TEMP,
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("role_name", sa.String(length=256), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], [f"{USER_TEMP}.id"]),
        sa.ForeignKeyConstraint(["company_id"], [f"{COMPANY_TEMP}.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "role_name"],
            [f"{ROLE_TEMP}.company_id", f"{ROLE_TEMP}.name"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "company_id"),
    )

    user_table = _reflect_table(connection, "user")
    company_table = _reflect_table(connection, "company")
    role_table = _reflect_table(connection, "role")
    association_table = _reflect_table(connection, "association_user_company")

    user_target = _reflect_table(connection, USER_TEMP)
    company_target = _reflect_table(connection, COMPANY_TEMP)
    role_target = _reflect_table(connection, ROLE_TEMP)
    association_target = _reflect_table(connection, ASSOCIATION_TEMP)

    user_rows = connection.execute(sa.select(user_table)).mappings().all()
    company_rows = connection.execute(sa.select(company_table)).mappings().all()
    role_rows = connection.execute(sa.select(role_table)).mappings().all()
    association_rows = connection.execute(sa.select(association_table)).mappings().all()

    user_id_map = {row["id"]: index for index, row in enumerate(user_rows, start=1)}
    company_id_map = {
        row["id"]: index for index, row in enumerate(company_rows, start=1)
    }

    for row in user_rows:
        payload = {
            "id": user_id_map[row["id"]],
            "first_name": row.get("first_name"),
            "last_name": row.get("last_name"),
            "email": row["email"],
            "phone_number": row.get("phone_number"),
            "password": row["password"],
            "_created_at": row.get("_created_at"),
            "_updated_at": row.get("_updated_at"),
            "_closed_at": row.get("_closed_at"),
            "primary_meta_data": row.get("primary_meta_data"),
            "secondary_meta_data": row.get("secondary_meta_data"),
        }
        if include_is_superuser:
            payload["is_superuser"] = bool(row.get("is_superuser", False))
        connection.execute(sa.insert(user_target).values(**payload))

    for row in company_rows:
        connection.execute(
            sa.insert(company_target).values(
                id=company_id_map[row["id"]],
                name=row.get("name"),
                description=row.get("description"),
                industry=row.get("industry"),
                email=row["email"],
                phone_number=row.get("phone_number"),
                _created_at=row.get("_created_at"),
                _updated_at=row.get("_updated_at"),
                _closed_at=row.get("_closed_at"),
                primary_meta_data=row.get("primary_meta_data"),
                secondary_meta_data=row.get("secondary_meta_data"),
            )
        )

    for row in role_rows:
        connection.execute(
            sa.insert(role_target).values(
                company_id=company_id_map[row["company_id"]],
                name=row["name"],
                description=row.get("description"),
                _created_at=row.get("_created_at"),
                _updated_at=row.get("_updated_at"),
                _closed_at=row.get("_closed_at"),
                primary_meta_data=row.get("primary_meta_data"),
                secondary_meta_data=row.get("secondary_meta_data"),
            )
        )

    for row in association_rows:
        connection.execute(
            sa.insert(association_target).values(
                user_id=user_id_map[row["user_id"]],
                company_id=company_id_map[row["company_id"]],
                role_name=row["role_name"],
                _created_at=row.get("_created_at"),
                _updated_at=row.get("_updated_at"),
                _closed_at=row.get("_closed_at"),
                primary_meta_data=row.get("primary_meta_data"),
                secondary_meta_data=row.get("secondary_meta_data"),
            )
        )

    op.drop_table("association_user_company")
    op.drop_table("role")
    op.drop_table("company")
    op.drop_table("user")

    op.rename_table(USER_TEMP, "user")
    op.rename_table(COMPANY_TEMP, "company")
    op.rename_table(ROLE_TEMP, "role")
    op.rename_table(ASSOCIATION_TEMP, "association_user_company")
