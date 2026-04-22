"""tenant_invites table and users onboarding json

Revision ID: a1b2c3d4e5f6
Revises: feccfb30f615
Create Date: 2026-04-22 12:00:00+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "feccfb30f615"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    org_role = postgresql.ENUM(
        "ORG_OWNER",
        "ORG_ADMIN",
        "INSTRUCTOR",
        "STUDENT",
        name="org_role_enum",
        create_type=False,
    )
    op.create_table(
        "tenant_invites",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", org_role, nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "invited_by_user_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_invites_token_hash"),
        "tenant_invites",
        ["token_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_invites_tenant_id"),
        "tenant_invites",
        ["tenant_id"],
        unique=False,
    )

    op.add_column(
        "users",
        sa.Column(
            "onboarding",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "onboarding")
    op.drop_index(op.f("ix_tenant_invites_tenant_id"), table_name="tenant_invites")
    op.drop_index(op.f("ix_tenant_invites_token_hash"), table_name="tenant_invites")
    op.drop_table("tenant_invites")
