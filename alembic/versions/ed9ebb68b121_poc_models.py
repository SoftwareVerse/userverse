"""Preserve the historical revision without recreating existing tables.

Revision ID: ed9ebb68b121
Revises: 84fe79d842e9
"""

from typing import Sequence, Union

revision: str = "ed9ebb68b121"
down_revision: Union[str, None] = "84fe79d842e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """The following revision creates the remaining initial tables."""


def downgrade() -> None:
    """No schema changes belong to this historical marker revision."""
