"""Link company memberships to company-scoped roles.

Revision ID: 9552b9fc884a
Revises: 9e858906b135
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9552b9fc884a"
down_revision: Union[str, None] = "9e858906b135"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_FOREIGN_KEY = "fk_association_user_company_role"


def upgrade() -> None:
    """Replace the legacy membership level with a role reference."""
    with op.batch_alter_table("association_user_company") as batch_op:
        batch_op.add_column(
            sa.Column("role_name", sa.String(length=256), nullable=True)
        )

    connection = op.get_bind()
    connection.execute(sa.text("""
            INSERT INTO role (company_id, name, description, _created_at)
            SELECT DISTINCT
                membership.company_id,
                COALESCE(membership.user_level, 'Member'),
                NULL,
                CURRENT_TIMESTAMP
            FROM association_user_company AS membership
            WHERE NOT EXISTS (
                SELECT 1
                FROM role
                WHERE role.company_id = membership.company_id
                  AND role.name = COALESCE(membership.user_level, 'Member')
            )
            """))
    connection.execute(sa.text("""
            UPDATE association_user_company
            SET role_name = COALESCE(user_level, 'Member')
            """))

    with op.batch_alter_table("association_user_company") as batch_op:
        batch_op.alter_column(
            "role_name",
            existing_type=sa.String(length=256),
            nullable=False,
        )
        batch_op.create_foreign_key(
            ROLE_FOREIGN_KEY,
            "role",
            ["company_id", "role_name"],
            ["company_id", "name"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("user_level")

    with op.batch_alter_table("company") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=255),
            type_=sa.String(length=256),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "description",
            existing_type=sa.String(length=255),
            type_=sa.String(length=512),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "industry",
            existing_type=sa.String(length=255),
            type_=sa.String(length=128),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            type_=sa.String(length=256),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "phone_number",
            existing_type=sa.String(length=255),
            type_=sa.String(length=16),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Restore the legacy membership level column."""
    with op.batch_alter_table("company") as batch_op:
        batch_op.alter_column(
            "phone_number",
            existing_type=sa.String(length=16),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=256),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "industry",
            existing_type=sa.String(length=128),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "description",
            existing_type=sa.String(length=512),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=256),
            type_=sa.String(length=255),
            existing_nullable=True,
        )

    with op.batch_alter_table("association_user_company") as batch_op:
        batch_op.add_column(
            sa.Column("user_level", sa.String(length=255), nullable=True)
        )

    op.execute(sa.text("""
            UPDATE association_user_company
            SET user_level = role_name
            """))

    with op.batch_alter_table("association_user_company") as batch_op:
        batch_op.drop_constraint(ROLE_FOREIGN_KEY, type_="foreignkey")
        batch_op.drop_column("role_name")
