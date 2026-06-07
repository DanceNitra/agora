"""002_add_interaction_log

Revision ID: 002
Revises: 001
Create Date: 2026-06-07

Adds the TFT interaction_log table for tracking every agent-agent
interaction, enabling Tit-for-Tat compliance analysis.
"""

from typing import Optional

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Optional[str] = "001_initial"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_table(
        "interaction_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("agent_identities.agent_id"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            sa.String(36),
            sa.ForeignKey("agent_identities.agent_id"),
            nullable=False,
        ),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("round_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trust_before", sa.Float(), nullable=True),
        sa.Column("trust_after", sa.Float(), nullable=True),
        sa.Column("context", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Text(), nullable=False,
                  server_default="datetime('now')"),
    )
    op.create_index(
        "ix_interaction_log_source_id", "interaction_log", ["source_id"]
    )
    op.create_index(
        "ix_interaction_log_target_id", "interaction_log", ["target_id"]
    )
    op.create_index(
        "ix_interaction_log_source_target",
        "interaction_log",
        ["source_id", "target_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_interaction_log_source_target", table_name="interaction_log")
    op.drop_index("ix_interaction_log_target_id", table_name="interaction_log")
    op.drop_index("ix_interaction_log_source_id", table_name="interaction_log")
    op.drop_table("interaction_log")
