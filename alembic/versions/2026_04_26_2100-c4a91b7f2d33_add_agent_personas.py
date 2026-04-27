"""add agent personas

Revision ID: c4a91b7f2d33
Revises: 9b6d8a72f3c1
Create Date: 2026-04-26 21:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c4a91b7f2d33"
down_revision = "9b6d8a72f3c1"
branch_labels = None
depends_on = None


persona_gender_enum = postgresql.ENUM(
    "FEMALE",
    "MALE",
    "NON_BINARY",
    "UNSPECIFIED",
    name="persona_gender_enum",
    create_type=False,
)


def upgrade() -> None:
    persona_gender_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "agent_personas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=True),
        sa.Column("gender", persona_gender_enum, nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("voice_provider", sa.String(length=80), nullable=False),
        sa.Column("voice_id", sa.String(length=160), nullable=True),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("communication_style", sa.Text(), nullable=True),
        sa.Column("background", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_personas_is_default"), "agent_personas", ["is_default"], unique=False)
    op.create_index(op.f("ix_agent_personas_tenant_id"), "agent_personas", ["tenant_id"], unique=False)
    op.add_column("scenarios", sa.Column("persona_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_scenarios_persona_id"), "scenarios", ["persona_id"], unique=False)
    op.create_foreign_key(
        "fk_scenarios_persona_id_agent_personas",
        "scenarios",
        "agent_personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_scenarios_persona_id_agent_personas", "scenarios", type_="foreignkey")
    op.drop_index(op.f("ix_scenarios_persona_id"), table_name="scenarios")
    op.drop_column("scenarios", "persona_id")
    op.drop_index(op.f("ix_agent_personas_tenant_id"), table_name="agent_personas")
    op.drop_index(op.f("ix_agent_personas_is_default"), table_name="agent_personas")
    op.drop_table("agent_personas")
    persona_gender_enum.drop(op.get_bind(), checkfirst=True)
