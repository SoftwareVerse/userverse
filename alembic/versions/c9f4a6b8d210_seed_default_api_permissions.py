"""Seed protected default API permissions.

Revision ID: c9f4a6b8d210
Revises: b7c2d4e6f809
Create Date: 2026-08-07 16:00:00.000000

"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import NAMESPACE_URL, UUID, uuid5

from alembic import op
import sqlalchemy as sa

revision: str = "c9f4a6b8d210"
down_revision: Union[str, None] = "b7c2d4e6f809"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_PERMISSION_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "https://userverse.softwareverse.co.za/system-permissions",
)

PERMISSIONS = (
    ("company.read", "Read company details.", ("Owner", "Administrator", "Viewer")),
    ("company.update", "Update company details.", ("Owner", "Administrator")),
    ("company.delete", "Delete a company.", ("Owner",)),
    (
        "company.members.read",
        "Read company members.",
        ("Owner", "Administrator", "Viewer"),
    ),
    (
        "company.members.add",
        "Add members to a company.",
        ("Owner", "Administrator"),
    ),
    (
        "company.members.role.update",
        "Update a company member's role.",
        ("Owner", "Administrator"),
    ),
    (
        "company.members.remove",
        "Remove members from a company.",
        ("Owner", "Administrator"),
    ),
    (
        "company.roles.read",
        "Read roles enabled for a company.",
        ("Owner", "Administrator"),
    ),
    (
        "company.roles.assign",
        "Enable a global role for a company.",
        ("Owner", "Administrator"),
    ),
    (
        "company.roles.unassign",
        "Disable a global role for a company.",
        ("Owner", "Administrator"),
    ),
    (
        "company.permissions.read",
        "Read company permissions and effective role permissions.",
        ("Owner", "Administrator"),
    ),
    (
        "company.permissions.create",
        "Create company permissions.",
        ("Owner", "Administrator"),
    ),
    (
        "company.permissions.update",
        "Update company permissions.",
        ("Owner", "Administrator"),
    ),
    (
        "company.permissions.delete",
        "Delete company permissions.",
        ("Owner", "Administrator"),
    ),
    (
        "company.permissions.assign",
        "Assign company permissions to company roles.",
        ("Owner", "Administrator"),
    ),
    (
        "company.permissions.unassign",
        "Remove company permissions from company roles.",
        ("Owner", "Administrator"),
    ),
)


def _permission_id(name: str) -> UUID:
    return uuid5(SYSTEM_PERMISSION_NAMESPACE, name)


def _tables():
    global_permission = sa.table(
        "global_permission",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("_created_at", sa.DateTime(timezone=True)),
        sa.column("_updated_at", sa.DateTime(timezone=True)),
        sa.column("_closed_at", sa.DateTime(timezone=True)),
        sa.column("primary_meta_data", sa.JSON()),
        sa.column("secondary_meta_data", sa.JSON()),
    )
    role = sa.table(
        "role",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("_closed_at", sa.DateTime(timezone=True)),
    )
    role_global_permission = sa.table(
        "role_global_permission",
        sa.column("role_id", sa.Uuid()),
        sa.column("global_permission_id", sa.Uuid()),
        sa.column("_created_at", sa.DateTime(timezone=True)),
        sa.column("_updated_at", sa.DateTime(timezone=True)),
        sa.column("_closed_at", sa.DateTime(timezone=True)),
        sa.column("primary_meta_data", sa.JSON()),
        sa.column("secondary_meta_data", sa.JSON()),
    )
    return global_permission, role, role_global_permission


def upgrade() -> None:
    connection = op.get_bind()
    global_permission, role, role_global_permission = _tables()
    now = datetime.now(timezone.utc)

    for name, description, default_roles in PERMISSIONS:
        permission_id = _permission_id(name)
        record_by_name = connection.execute(
            sa.select(global_permission.c.id).where(global_permission.c.name == name)
        ).scalar_one_or_none()
        record_by_id = connection.execute(
            sa.select(global_permission.c.name).where(
                global_permission.c.id == permission_id
            )
        ).scalar_one_or_none()
        if (
            record_by_name is not None and UUID(str(record_by_name)) != permission_id
        ) or (record_by_id is not None and record_by_id != name):
            raise RuntimeError(
                f"Reserved system permission conflict for '{name}' ({permission_id})."
            )
        if record_by_name is None:
            connection.execute(
                global_permission.insert().values(
                    id=permission_id,
                    name=name,
                    description=description,
                    _created_at=now,
                    _updated_at=now,
                    _closed_at=None,
                    primary_meta_data={
                        "system": True,
                        "kind": "default_api_permission",
                    },
                    secondary_meta_data={},
                )
            )

        role_rows = connection.execute(
            sa.select(role.c.id, role.c.name).where(
                role.c.name.in_(default_roles),
                role.c._closed_at.is_(None),
            )
        ).all()
        for role_id, role_name in role_rows:
            link_exists = connection.execute(
                sa.select(role_global_permission.c.role_id).where(
                    role_global_permission.c.role_id == role_id,
                    role_global_permission.c.global_permission_id == permission_id,
                )
            ).first()
            if link_exists is None:
                connection.execute(
                    role_global_permission.insert().values(
                        role_id=role_id,
                        global_permission_id=permission_id,
                        _created_at=now,
                        _updated_at=now,
                        _closed_at=None,
                        primary_meta_data={
                            "system_default": True,
                            "role": role_name,
                        },
                        secondary_meta_data={},
                    )
                )


def downgrade() -> None:
    connection = op.get_bind()
    global_permission, _, role_global_permission = _tables()
    permission_ids = [_permission_id(name) for name, _, _ in PERMISSIONS]
    connection.execute(
        role_global_permission.delete().where(
            role_global_permission.c.global_permission_id.in_(permission_ids)
        )
    )
    connection.execute(
        global_permission.delete().where(global_permission.c.id.in_(permission_ids))
    )
