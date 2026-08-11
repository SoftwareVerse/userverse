"""Add the legacy company-scoped role table.

Revision ID: c539ec0c41d5
Revises: ed9ebb68b121
Create Date: 2025-05-10 16:55:31.258995

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c539ec0c41d5"
down_revision: Union[str, None] = "ed9ebb68b121"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the role catalog expected by the next legacy revision."""
    op.create_table(
        "role",
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column(
            "_created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("_updated_at", sa.DateTime(), nullable=True),
        sa.Column("_closed_at", sa.DateTime(), nullable=True),
        sa.Column("primary_meta_data", sa.JSON(), nullable=True),
        sa.Column("secondary_meta_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("company_id", "name"),
    )


def downgrade() -> None:
    """Remove the legacy company-scoped role table."""
    op.drop_table("role")
