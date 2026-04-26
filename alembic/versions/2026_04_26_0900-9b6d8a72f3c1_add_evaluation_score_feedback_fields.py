"""add evaluation score feedback fields

Revision ID: 9b6d8a72f3c1
Revises: a1b2c3d4e5f6
Create Date: 2026-04-26 09:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "9b6d8a72f3c1"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evaluation_scores", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("evaluation_scores", sa.Column("example_quote", sa.Text(), nullable=True))
    op.add_column("evaluation_scores", sa.Column("improvement", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluation_scores", "improvement")
    op.drop_column("evaluation_scores", "example_quote")
    op.drop_column("evaluation_scores", "summary")
