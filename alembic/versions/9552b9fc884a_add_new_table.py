"""Add roles and link company users to roles.

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


def upgrade() -> None:
    op.create_table(
        "role",
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column(
            "_created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("_updated_at", sa.DateTime(), nullable=True),
        sa.Column("_closed_at", sa.DateTime(), nullable=True),
        sa.Column("primary_meta_data", sa.JSON(), nullable=True),
        sa.Column("secondary_meta_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id", "name"),
    )
    op.add_column(
        "association_user_company",
        sa.Column("role_name", sa.String(length=256), nullable=True),
    )

    # Preserve existing associations when upgrading an older deployed database.
    op.execute(
        sa.text(
            "INSERT INTO role (company_id, name, description) "
            "SELECT DISTINCT company_id, 'MEMBER', 'Migrated default role' "
            "FROM association_user_company"
        )
    )
    op.execute(
        sa.text(
            "UPDATE association_user_company SET role_name = 'MEMBER' "
            "WHERE role_name IS NULL"
        )
    )

    op.alter_column(
        "association_user_company",
        "role_name",
        existing_type=sa.String(length=256),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_association_user_company_role",
        "association_user_company",
        "role",
        ["company_id", "role_name"],
        ["company_id", "name"],
        ondelete="CASCADE",
    )
    op.drop_column("association_user_company", "user_level")
    op.alter_column(
        "company",
        "name",
        existing_type=sa.String(length=255),
        type_=sa.String(length=256),
        existing_nullable=True,
    )
    op.alter_column(
        "company",
        "description",
        existing_type=sa.String(length=255),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
    op.alter_column(
        "company",
        "industry",
        existing_type=sa.String(length=255),
        type_=sa.String(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "company",
        "email",
        existing_type=sa.String(length=255),
        type_=sa.String(length=256),
        existing_nullable=False,
    )
    op.alter_column(
        "company",
        "phone_number",
        existing_type=sa.String(length=255),
        type_=sa.String(length=16),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "company",
        "phone_number",
        existing_type=sa.String(length=16),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "company",
        "email",
        existing_type=sa.String(length=256),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "company",
        "industry",
        existing_type=sa.String(length=128),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "company",
        "description",
        existing_type=sa.String(length=512),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "company",
        "name",
        existing_type=sa.String(length=256),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.add_column(
        "association_user_company",
        sa.Column("user_level", sa.String(length=255), nullable=True),
    )
    op.drop_constraint(
        "fk_association_user_company_role",
        "association_user_company",
        type_="foreignkey",
    )
    op.drop_column("association_user_company", "role_name")
    op.drop_table("role")
