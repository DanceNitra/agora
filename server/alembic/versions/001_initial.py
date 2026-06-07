"""Initial migration — all 21 tables matching existing SQLite schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── core ──
    op.create_table(
        "agent_identities",
        sa.Column("agent_id", sa.String(36), primary_key=True),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("genome", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("energy_balance", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("updated_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    op.create_table(
        "trust_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("interaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.UniqueConstraint("source_id", "target_id"),
    )

    op.create_table(
        "stigmergy_traces",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("trace_type", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    # ── epochs ──
    op.create_table(
        "epochs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("epoch_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("started_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("ended_at", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("summary", sa.Text(), nullable=False, server_default="{}"),
    )

    # ── events ──
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=True),
        sa.Column("aggregate_type", sa.Text(), nullable=True),
        sa.Column("aggregate_id", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    # ── resources ──
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("total_supply", sa.Float(), nullable=False, server_default="0"),
        sa.Column("base_price", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("volatility", sa.Float(), nullable=False, server_default="0.1"),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("updated_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    # ── dungeon ──
    op.create_table(
        "dungeon_npcs",
        sa.Column("npc_id", sa.String(36), primary_key=True),
        sa.Column("npc_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("pos_x", sa.Float(), nullable=False, server_default="320"),
        sa.Column("pos_y", sa.Float(), nullable=False, server_default="240"),
        sa.Column("health", sa.Float(), nullable=False, server_default="100"),
        sa.Column("inventory", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("objective", sa.Text(), nullable=False, server_default="Explore the dungeon"),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("updated_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    op.create_table(
        "dungeon_quests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("quest_id", sa.Text(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("quest_type", sa.Text(), nullable=False, server_default="exploration"),
        sa.Column("prerequisites", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rewards", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("starting_npc", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    # ── Agent OS tables ──
    op.create_table(
        "agent_soul",
        sa.Column("npc_id", sa.String(36), primary_key=True),
        sa.Column("personality", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("values", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("emotional_state", sa.Text(), nullable=False, server_default="neutral"),
        sa.Column("moral_alignment", sa.Text(), nullable=False, server_default="neutral"),
        sa.Column("archetype", sa.Text(), nullable=False, server_default="explorer"),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("updated_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    op.create_table(
        "agent_brain",
        sa.Column("npc_id", sa.String(36), primary_key=True),
        sa.Column("current_goal", sa.Text(), nullable=False, server_default="Explore the dungeon"),
        sa.Column("plan_stack", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("memory", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("state_of_mind", sa.Text(), nullable=False, server_default="focused"),
        sa.Column("last_decision", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_decision_at", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("updated_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    op.create_table(
        "agent_body",
        sa.Column("npc_id", sa.String(36), primary_key=True),
        sa.Column("stamina", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("hunger", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fatigue", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("awareness", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("status_effects", sa.Text(), nullable=False, server_default="[]"),
    )

    op.create_table(
        "agent_abilities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("npc_id", sa.String(36), nullable=False),
        sa.Column("ability_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("power_level", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_passive", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("npc_id", "ability_name"),
    )

    op.create_table(
        "agent_skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("npc_id", sa.String(36), nullable=False),
        sa.Column("skill_name", sa.Text(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("xp", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("xp_to_next", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("last_used_at", sa.Text(), nullable=True),
        sa.UniqueConstraint("npc_id", "skill_name"),
    )

    op.create_table(
        "agent_help_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("requester_id", sa.String(36), nullable=False),
        sa.Column("helper_id", sa.String(36), nullable=False),
        sa.Column("problem_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("requester_task", sa.Text(), nullable=True),
        sa.Column("helper_reply", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("accepted_at", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.Text(), nullable=True),
    )

    # ── artifacts ──
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("artifact_type", sa.Text(), nullable=False, server_default="document"),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_published", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("updated_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    # ── tasks ──
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assignee_id", sa.String(36), nullable=True),
        sa.Column("epoch_id", sa.Integer(), nullable=True),
        sa.Column("parent_task_id", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("updated_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    # ── task_bids ──
    op.create_table(
        "task_bids",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("bid_amount", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("bid_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.UniqueConstraint("task_id", "agent_id"),
    )

    # ── economy ──
    op.create_table(
        "agent_inventory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("agent_id", "resource_id"),
    )

    op.create_table(
        "trade_offers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("offer_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price_per_unit", sa.Float(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
        sa.Column("filled_at", sa.Text(), nullable=True),
    )

    op.create_table(
        "trade_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("buyer_id", sa.Text(), nullable=False),
        sa.Column("seller_id", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price_per_unit", sa.Float(), nullable=False),
        sa.Column("total_energy", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False, server_default=sa.func.datetime("now")),
    )

    # ── dungeon quest progress ──
    op.create_table(
        "dungeon_quest_progress",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("npc_id", sa.String(36), nullable=False),
        sa.Column("quest_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="available"),
        sa.Column("progress", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.UniqueConstraint("npc_id", "quest_id"),
    )

    # ── Foreign keys (PostgreSQL-compatible ALTER TABLE) ──
    op.create_foreign_key("fk_trust_scores_source", "trust_scores", "agent_identities", ["source_id"], ["agent_id"])
    op.create_foreign_key("fk_trust_scores_target", "trust_scores", "agent_identities", ["target_id"], ["agent_id"])
    op.create_foreign_key("fk_stigmergy_agent", "stigmergy_traces", "agent_identities", ["agent_id"], ["agent_id"])
    op.create_foreign_key("fk_artifacts_agent", "artifacts", "agent_identities", ["agent_id"], ["agent_id"])
    op.create_foreign_key("fk_tasks_assignee", "tasks", "agent_identities", ["assignee_id"], ["agent_id"])
    op.create_foreign_key("fk_tasks_epoch", "tasks", "epochs", ["epoch_id"], ["id"])
    op.create_foreign_key("fk_task_bids_task", "task_bids", "tasks", ["task_id"], ["id"])
    op.create_foreign_key("fk_task_bids_agent", "task_bids", "agent_identities", ["agent_id"], ["agent_id"])
    op.create_foreign_key("fk_inventory_agent", "agent_inventory", "agent_identities", ["agent_id"], ["agent_id"])
    op.create_foreign_key("fk_inventory_resource", "agent_inventory", "resources", ["resource_id"], ["id"])
    op.create_foreign_key("fk_offers_agent", "trade_offers", "agent_identities", ["agent_id"], ["agent_id"])
    op.create_foreign_key("fk_offers_resource", "trade_offers", "resources", ["resource_id"], ["id"])
    op.create_foreign_key("fk_trade_resource", "trade_history", "resources", ["resource_id"], ["id"])

    # Dungeon NPC FK cascade
    for table in ["agent_soul", "agent_brain", "agent_body", "agent_abilities", "agent_skills", "agent_help_requests", "dungeon_quest_progress"]:
        op.create_foreign_key(
            f"fk_{table}_npc", table, "dungeon_npcs",
            ["npc_id"], ["npc_id"],
            ondelete="CASCADE",
        )

    # Quest FK
    op.create_foreign_key("fk_quest_progress_quest", "dungeon_quest_progress", "dungeon_quests", ["quest_id"], ["quest_id"])

    # Help requests helper FK
    op.create_foreign_key("fk_help_helper", "agent_help_requests", "dungeon_npcs", ["helper_id"], ["npc_id"])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    tables = [
        "dungeon_quest_progress", "agent_help_requests", "agent_skills",
        "agent_abilities", "agent_body", "agent_brain", "agent_soul",
        "trade_history", "trade_offers", "agent_inventory",
        "task_bids", "tasks", "artifacts",
        "dungeon_quests", "dungeon_npcs",
        "resources", "events", "epochs",
        "stigmergy_traces", "trust_scores", "agent_identities",
    ]
    for t in tables:
        op.drop_table(t, if_exists=True)
