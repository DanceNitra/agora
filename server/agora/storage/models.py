"""
SQLAlchemy 2.0 async ORM models for the Agora schema.

All tables use TEXT primary keys (UUID-like) for distributed compatibility.
Timestamp fields are TEXT with datetime('now') defaults.
JSON fields are TEXT to maintain SQLite + PostgreSQL compatibility.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, relationship


def _uuid() -> str:
    """Generate a UUID string for primary key defaults."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
# AGENT IDENTITIES & TRUST
# ─────────────────────────────────────────────


class AgentIdentity(Base):
    __tablename__ = "agent_identities"

    agent_id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    public_key = sa.Column(sa.Text, nullable=False)
    generation = sa.Column(sa.Integer, nullable=False, default=0)
    genome = sa.Column(sa.Text, nullable=False, default="{}")  # JSON
    trust_score = sa.Column(sa.Float, nullable=False, default=0.5)
    energy_balance = sa.Column(sa.Float, nullable=False, default=100.0)
    role = sa.Column(sa.Text, nullable=False)
    status = sa.Column(sa.Text, nullable=False, default="active")
    created_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))
    updated_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))

    # relationships
    trust_scores_source = relationship(
        "TrustScore", foreign_keys="TrustScore.source_id", back_populates="source"
    )
    trust_scores_target = relationship(
        "TrustScore", foreign_keys="TrustScore.target_id", back_populates="target"
    )
    stigmergy_traces = relationship("StigmergyTrace", back_populates="agent")
    artifacts = relationship("Artifact", back_populates="agent")
    tasks = relationship("Task", back_populates="assignee")
    task_bids = relationship("TaskBid", back_populates="agent")
    agent_inventory = relationship("AgentInventory", back_populates="agent")
    trade_offers = relationship("TradeOffer", back_populates="agent")
    interactions_source = relationship(
        "InteractionLog", foreign_keys="InteractionLog.source_id", back_populates="source"
    )
    interactions_target = relationship(
        "InteractionLog", foreign_keys="InteractionLog.target_id", back_populates="target"
    )


class TrustScore(Base):
    __tablename__ = "trust_scores"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    source_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    target_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    score = sa.Column(sa.Float, nullable=False, default=0.5)
    interaction_count = sa.Column(sa.Integer, nullable=False, default=0)
    # ESS 1.4 — production-ready trust engine
    consecutive_cooperations = sa.Column(sa.Integer, nullable=False, default=0)
    consecutive_defections = sa.Column(sa.Integer, nullable=False, default=0)
    sliding_window = sa.Column(sa.Text, nullable=False, default="[]")
    last_updated = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    __table_args__ = (sa.UniqueConstraint("source_id", "target_id"),)

    # relationships
    source = relationship(
        "AgentIdentity", foreign_keys=[source_id], back_populates="trust_scores_source"
    )
    target = relationship(
        "AgentIdentity", foreign_keys=[target_id], back_populates="trust_scores_target"
    )


class StigmergyTrace(Base):
    __tablename__ = "stigmergy_traces"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    agent_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    trace_type = sa.Column(sa.Text, nullable=False)
    payload = sa.Column(sa.Text, nullable=False, default="{}")  # JSON
    ttl_seconds = sa.Column(sa.Integer, nullable=False, default=3600)
    expires_at = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    agent = relationship("AgentIdentity", back_populates="stigmergy_traces")


# ─────────────────────────────────────────────
# AGENT OPERATING SYSTEM — Soul, Brain, Body, Abilities, Skills
# ─────────────────────────────────────────────


class AgentSoul(Base):
    __tablename__ = "agent_soul"

    npc_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        primary_key=True,
    )
    personality = sa.Column(sa.Text, nullable=False, default="{}")  # JSON
    values = sa.Column(sa.Text, nullable=False, default="{}")  # JSON
    emotional_state = sa.Column(sa.Text, nullable=False, default="neutral")
    moral_alignment = sa.Column(sa.Text, nullable=False, default="neutral")
    archetype = sa.Column(sa.Text, nullable=False, default="explorer")
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    updated_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    npc = relationship("DungeonNpc", back_populates="soul")


class AgentBrain(Base):
    __tablename__ = "agent_brain"

    npc_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_goal = sa.Column(sa.Text, nullable=False, default="Explore the dungeon")
    plan_stack = sa.Column(sa.Text, nullable=False, default="[]")  # JSON
    memory = sa.Column(sa.Text, nullable=False, default="[]")  # JSON
    state_of_mind = sa.Column(sa.Text, nullable=False, default="focused")
    last_decision = sa.Column(sa.Text, nullable=False, default="")
    last_decision_at = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    updated_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    npc = relationship("DungeonNpc", back_populates="brain")


class AgentBody(Base):
    __tablename__ = "agent_body"

    npc_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        primary_key=True,
    )
    stamina = sa.Column(sa.Float, nullable=False, default=100.0)
    hunger = sa.Column(sa.Float, nullable=False, default=0.0)
    fatigue = sa.Column(sa.Float, nullable=False, default=0.0)
    awareness = sa.Column(sa.Float, nullable=False, default=1.0)
    status_effects = sa.Column(sa.Text, nullable=False, default="[]")  # JSON

    # relationships
    npc = relationship("DungeonNpc", back_populates="body")


class AgentAbility(Base):
    __tablename__ = "agent_abilities"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    npc_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    ability_name = sa.Column(sa.Text, nullable=False)
    description = sa.Column(sa.Text, nullable=False, default="")
    power_level = sa.Column(sa.Float, nullable=False, default=1.0)
    is_passive = sa.Column(sa.Boolean, nullable=False, default=False)

    __table_args__ = (sa.UniqueConstraint("npc_id", "ability_name"),)

    # relationships
    npc = relationship("DungeonNpc", back_populates="abilities")


class AgentSkill(Base):
    __tablename__ = "agent_skills"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    npc_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_name = sa.Column(sa.Text, nullable=False)
    level = sa.Column(sa.Integer, nullable=False, default=1)
    xp = sa.Column(sa.Float, nullable=False, default=0.0)
    xp_to_next = sa.Column(sa.Float, nullable=False, default=100.0)
    last_used_at = sa.Column(sa.Text, nullable=True)

    __table_args__ = (sa.UniqueConstraint("npc_id", "skill_name"),)

    # relationships
    npc = relationship("DungeonNpc", back_populates="skills")


class AgentHelpRequest(Base):
    __tablename__ = "agent_help_requests"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    requester_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    helper_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_type = sa.Column(sa.Text, nullable=False)
    description = sa.Column(sa.Text, nullable=False, default="")
    status = sa.Column(sa.Text, nullable=False, default="pending")
    requester_task = sa.Column(sa.Text, nullable=True)
    helper_reply = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    accepted_at = sa.Column(sa.Text, nullable=True)
    resolved_at = sa.Column(sa.Text, nullable=True)

    # relationships
    requester = relationship(
        "DungeonNpc", foreign_keys=[requester_id], back_populates="help_requests_requester"
    )
    helper = relationship(
        "DungeonNpc", foreign_keys=[helper_id], back_populates="help_requests_helper"
    )


# ─────────────────────────────────────────────
# ARTIFACTS & EVENTS
# ─────────────────────────────────────────────


class Artifact(Base):
    __tablename__ = "artifacts"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    agent_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    title = sa.Column(sa.Text, nullable=False)
    artifact_type = sa.Column(sa.Text, nullable=False, default="document")
    storage_path = sa.Column(sa.Text, nullable=False)
    mime_type = sa.Column(sa.Text, nullable=True)
    size_bytes = sa.Column(sa.Integer, default=0)
    checksum = sa.Column(sa.Text, nullable=True)
    meta_data = sa.Column("metadata", sa.Text, default="{}")  # JSON
    is_published = sa.Column(sa.Boolean, default=False)
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    updated_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    agent = relationship("AgentIdentity", back_populates="artifacts")


class Event(Base):
    __tablename__ = "events"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    event_type = sa.Column(sa.Text, nullable=False)
    source_id = sa.Column(sa.Text, nullable=True)
    aggregate_type = sa.Column(sa.Text, nullable=True)
    aggregate_id = sa.Column(sa.Text, nullable=True)
    payload = sa.Column(sa.Text, nullable=False, default="{}")  # JSON
    occurred_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )


# ─────────────────────────────────────────────
# EPOCHS & TASKS
# ─────────────────────────────────────────────


class Epoch(Base):
    __tablename__ = "epochs"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    epoch_number = sa.Column(sa.Integer, nullable=False, unique=True)
    started_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    ended_at = sa.Column(sa.Text, nullable=True)
    status = sa.Column(sa.Text, nullable=False, default="active")
    summary = sa.Column(sa.Text, default="{}")  # JSON

    # relationships
    tasks = relationship("Task", back_populates="epoch")


class Task(Base):
    __tablename__ = "tasks"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    title = sa.Column(sa.Text, nullable=False)
    description = sa.Column(sa.Text, nullable=True)
    status = sa.Column(sa.Text, nullable=False, default="pending")
    priority = sa.Column(sa.Integer, nullable=False, default=0)
    assignee_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=True
    )
    epoch_id = sa.Column(
        sa.String(36), sa.ForeignKey("epochs.id"), nullable=True
    )
    parent_task_id = sa.Column(
        sa.String(36), sa.ForeignKey("tasks.id"), nullable=True
    )
    meta_data = sa.Column("metadata", sa.Text, default="{}")  # JSON
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    updated_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    assignee = relationship(
        "AgentIdentity", back_populates="tasks", foreign_keys=[assignee_id]
    )
    epoch = relationship("Epoch", back_populates="tasks", foreign_keys=[epoch_id])
    parent_task = relationship(
        "Task", remote_side="Task.id", back_populates="sub_tasks", foreign_keys=[parent_task_id]
    )
    sub_tasks = relationship(
        "Task", back_populates="parent_task", foreign_keys=[parent_task_id]
    )
    bids = relationship("TaskBid", back_populates="task")


class TaskBid(Base):
    __tablename__ = "task_bids"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    task_id = sa.Column(
        sa.String(36), sa.ForeignKey("tasks.id"), nullable=False
    )
    agent_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    bid_amount = sa.Column(sa.Float, nullable=False, default=0.5)
    bid_reason = sa.Column(sa.Text, nullable=True)
    status = sa.Column(sa.Text, nullable=False, default="pending")
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    __table_args__ = (sa.UniqueConstraint("task_id", "agent_id"),)

    # relationships
    task = relationship("Task", back_populates="bids")
    agent = relationship("AgentIdentity", back_populates="task_bids")


# ─────────────────────────────────────────────
# ESS ECONOMY — Resources, Inventory, Trade
# ─────────────────────────────────────────────


class Resource(Base):
    __tablename__ = "resources"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    name = sa.Column(sa.Text, nullable=False, unique=True)
    total_supply = sa.Column(sa.Float, nullable=False, default=0)
    base_price = sa.Column(sa.Float, nullable=False, default=1.0)
    volatility = sa.Column(sa.Float, nullable=False, default=0.1)
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    updated_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    agent_inventory = relationship("AgentInventory", back_populates="resource")
    trade_offers = relationship("TradeOffer", back_populates="resource")
    trade_history = relationship("TradeHistory", back_populates="resource")


class AgentInventory(Base):
    __tablename__ = "agent_inventory"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    agent_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    resource_id = sa.Column(
        sa.String(36), sa.ForeignKey("resources.id"), nullable=False
    )
    quantity = sa.Column(sa.Float, nullable=False, default=0)

    __table_args__ = (sa.UniqueConstraint("agent_id", "resource_id"),)

    # relationships
    agent = relationship("AgentIdentity", back_populates="agent_inventory")
    resource = relationship("Resource", back_populates="agent_inventory")


class TradeOffer(Base):
    __tablename__ = "trade_offers"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    agent_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    offer_type = sa.Column(sa.Text, nullable=False)  # 'buy' or 'sell'
    resource_id = sa.Column(
        sa.String(36), sa.ForeignKey("resources.id"), nullable=False
    )
    quantity = sa.Column(sa.Float, nullable=False)
    price_per_unit = sa.Column(sa.Float, nullable=False)
    status = sa.Column(sa.Text, nullable=False, default="open")
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    filled_at = sa.Column(sa.Text, nullable=True)

    # relationships
    agent = relationship("AgentIdentity", back_populates="trade_offers")
    resource = relationship("Resource", back_populates="trade_offers")


# ─────────────────────────────────────────────
# DUNGEON PERSISTENCE — NPCs, Quests, Progress
# ─────────────────────────────────────────────


class DungeonNpc(Base):
    __tablename__ = "dungeon_npcs"

    npc_id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    npc_name = sa.Column(sa.Text, nullable=False)
    role = sa.Column(sa.Text, nullable=False)
    pos_x = sa.Column(sa.Float, nullable=False, default=320)
    pos_y = sa.Column(sa.Float, nullable=False, default=240)
    health = sa.Column(sa.Float, nullable=False, default=100)
    inventory = sa.Column(sa.Text, nullable=False, default="[]")  # JSON
    status = sa.Column(sa.Text, nullable=False, default="active")
    objective = sa.Column(sa.Text, nullable=False, default="Explore the dungeon")
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )
    updated_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    soul = relationship("AgentSoul", back_populates="npc", uselist=False)
    brain = relationship("AgentBrain", back_populates="npc", uselist=False)
    body = relationship("AgentBody", back_populates="npc", uselist=False)
    abilities = relationship("AgentAbility", back_populates="npc")
    skills = relationship("AgentSkill", back_populates="npc")
    help_requests_requester = relationship(
        "AgentHelpRequest",
        foreign_keys="AgentHelpRequest.requester_id",
        back_populates="requester",
    )
    help_requests_helper = relationship(
        "AgentHelpRequest",
        foreign_keys="AgentHelpRequest.helper_id",
        back_populates="helper",
    )
    quest_progress = relationship("DungeonQuestProgress", back_populates="npc")
    # Agentic OS v3 — emócie, život, metamemory
    emotion = relationship("AgentEmotion", back_populates="npc", uselist=False)
    lifecycle = relationship("AgentLifecycle", back_populates="npc", uselist=False)
    dreams = relationship("AgentDream", back_populates="npc")
    diaries = relationship("AgentDiary", back_populates="npc")
    metamemories = relationship("AgentMetaMemory", back_populates="npc")
    relationships_a = relationship(
        "AgentRelationship", foreign_keys="AgentRelationship.agent_a_id",
        back_populates="agent_a",
    )
    relationships_b = relationship(
        "AgentRelationship", foreign_keys="AgentRelationship.agent_b_id",
        back_populates="agent_b",
    )
    conflicts_a = relationship(
        "AgentConflict", foreign_keys="AgentConflict.agent_a_id",
    )
    conflicts_b = relationship(
        "AgentConflict", foreign_keys="AgentConflict.agent_b_id",
    )


class DungeonQuest(Base):
    __tablename__ = "dungeon_quests"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    quest_id = sa.Column(sa.Text, nullable=False, unique=True)
    title = sa.Column(sa.Text, nullable=False)
    description = sa.Column(sa.Text, nullable=False, default="")
    quest_type = sa.Column(sa.Text, nullable=False, default="exploration")
    prerequisites = sa.Column(sa.Text, nullable=False, default="[]")  # JSON
    rewards = sa.Column(sa.Text, nullable=False, default="{}")  # JSON
    starting_npc = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    progress_records = relationship("DungeonQuestProgress", back_populates="quest")


class DungeonQuestProgress(Base):
    __tablename__ = "dungeon_quest_progress"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    npc_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id"), nullable=False
    )
    quest_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_quests.quest_id"), nullable=False
    )
    status = sa.Column(sa.Text, nullable=False, default="available")
    progress = sa.Column(sa.Text, nullable=False, default="{}")  # JSON
    started_at = sa.Column(sa.Text, nullable=True)
    completed_at = sa.Column(sa.Text, nullable=True)

    __table_args__ = (sa.UniqueConstraint("npc_id", "quest_id"),)

    # relationships
    npc = relationship("DungeonNpc", back_populates="quest_progress")
    quest = relationship("DungeonQuest", back_populates="progress_records")


# ─────────────────────────────────────────────
# TFT INTERACTION LOG
# ─────────────────────────────────────────────


class InteractionLog(Base):
    """Individual interaction record for TFT verification.

    Every interaction between two agents is logged here so the
    TFTVerifier can analyze patterns: was the first move cooperate?
    Is defection met with defection? Does forgiveness happen after
    cooperation?
    """

    __tablename__ = "interaction_log"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    source_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    target_id = sa.Column(
        sa.String(36), sa.ForeignKey("agent_identities.agent_id"), nullable=False
    )
    outcome = sa.Column(sa.Text, nullable=False)  # 'cooperate' or 'defect'
    round_num = sa.Column(sa.Integer, nullable=False, default=0)
    trust_before = sa.Column(sa.Float, nullable=True)
    trust_after = sa.Column(sa.Float, nullable=True)
    context = sa.Column(sa.Text, nullable=False, default="{}")  # JSON
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    source = relationship(
        "AgentIdentity", foreign_keys=[source_id], back_populates="interactions_source"
    )
    target = relationship(
        "AgentIdentity", foreign_keys=[target_id], back_populates="interactions_target"
    )


# ─────────────────────────────────────────────
# TRADE HISTORY
# ─────────────────────────────────────────────


class TradeHistory(Base):
    __tablename__ = "trade_history"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    buyer_id = sa.Column(sa.Text, nullable=False)
    seller_id = sa.Column(sa.Text, nullable=False)
    resource_id = sa.Column(
        sa.String(36), sa.ForeignKey("resources.id"), nullable=False
    )
    quantity = sa.Column(sa.Float, nullable=False)
    price_per_unit = sa.Column(sa.Float, nullable=False)
    total_energy = sa.Column(sa.Float, nullable=False)
    created_at = sa.Column(
        sa.Text, nullable=False, server_default=sa.func.datetime("now")
    )

    # relationships
    resource = relationship("Resource", back_populates="trade_history")


# ═══════════════════════════════════════════════
# AGENTIC OS v3 — Emócie, Vzťahy, Život, Príbehy
# ═══════════════════════════════════════════════


class AgentEmotion(Base):
    """Current emotional state of each agent.
    
    Emócie sú krátkodobé reakcie na udalosti (na rozdiel od moodu,
    ktorý je dlhodobý). Každý agent má jednu primárnu emóciu,
    ktorá sa mení podľa triggerov a decayuje v čase.
    """
    __tablename__ = "agent_emotions"

    npc_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        primary_key=True,
    )
    current = sa.Column(sa.Text, nullable=False, default="neutral")
    # neutral, happy, sad, angry, fearful, surprised, curious, trusted, betrayed, grateful, hopeful, lonely
    intensity = sa.Column(sa.Float, nullable=False, default=0.5)
    valence = sa.Column(sa.Float, nullable=False, default=0.0)       # -1 (negative) to +1 (positive)
    arousal = sa.Column(sa.Float, nullable=False, default=0.5)       # 0 (calm) to 1 (excited)
    trigger = sa.Column(sa.Text, nullable=False, default="")
    # JSON history of last 10 emotions with triggers
    history = sa.Column(sa.Text, nullable=False, default="[]")
    decay_rate = sa.Column(sa.Float, nullable=False, default=0.1)    # how fast emotion fades per tick
    mood = sa.Column(sa.Float, nullable=False, default=0.7)           # 0=terrible, 1=euphoric (long-term)
    updated_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))

    # relationships
    npc = relationship("DungeonNpc", back_populates="emotion")


class AgentRelationship(Base):
    """Multi-dimensional relationship between two agents.
    
    Každý pár agentov má viacrozmerný vzťah — nie len ESS trust (0-1),
    ale aj priateľstvo, rešpekt, rivalita, sympatia, dlh a história.
    """
    __tablename__ = "agent_relationships"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    agent_a_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_b_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    # Multi-dimensional scores
    friendship = sa.Column(sa.Float, nullable=False, default=0.3)
    respect = sa.Column(sa.Float, nullable=False, default=0.5)
    rivalry = sa.Column(sa.Float, nullable=False, default=0.0)
    attraction = sa.Column(sa.Float, nullable=False, default=0.0)
    debt = sa.Column(sa.Float, nullable=False, default=0.0)  # positive = A owes B
    conversations_count = sa.Column(sa.Integer, nullable=False, default=0)
    last_topic = sa.Column(sa.Text, nullable=True)
    # Labels: trusted_allies, mentor_pupil, rivals, strangers, friends, lovers, enemies
    emotional_bond = sa.Column(sa.Text, nullable=False, default="strangers")
    # JSON array of significant events: [{event:, impact:, tick:, description:}]
    history = sa.Column(sa.Text, nullable=False, default="[]")
    created_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))
    updated_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))

    __table_args__ = (sa.UniqueConstraint("agent_a_id", "agent_b_id"),)

    # relationships
    agent_a = relationship("DungeonNpc", foreign_keys=[agent_a_id])
    agent_b = relationship("DungeonNpc", foreign_keys=[agent_b_id])


class AgentLifecycle(Base):
    """Lifecycle stage and growth metrics for each agent.
    
    Agenti sa rodia, rastú, starnú a odchádzajú. Tento model
    sleduje ich vek, múdrosť, životný cieľ a legacy.
    """
    __tablename__ = "agent_lifecycles"

    npc_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        primary_key=True,
    )
    age_ticks = sa.Column(sa.Integer, nullable=False, default=0)
    stage = sa.Column(sa.Text, nullable=False, default="infancy")
    # infancy -> childhood -> adulthood -> elder -> retiring
    maturity = sa.Column(sa.Float, nullable=False, default=0.0)   # 0-1
    wisdom = sa.Column(sa.Float, nullable=False, default=0.0)     # rastie s insightmi
    total_decisions = sa.Column(sa.Integer, nullable=False, default=0)
    total_vault_notes = sa.Column(sa.Integer, nullable=False, default=0)
    total_conversations = sa.Column(sa.Integer, nullable=False, default=0)
    legacy = sa.Column(sa.Text, nullable=False, default="")
    mentor_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id"), nullable=True,
    )
    life_goal = sa.Column(sa.Text, nullable=False, default="")
    life_goal_progress = sa.Column(sa.Float, nullable=False, default=0.0)
    peak_experience = sa.Column(sa.Text, nullable=False, default="")
    created_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))
    updated_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))

    npc = relationship("DungeonNpc", back_populates="lifecycle")


class AgentDream(Base):
    """Dreams and inspirations generated by agents during rest."""
    __tablename__ = "agent_dreams"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    npc_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    dream_type = sa.Column(sa.Text, nullable=False, default="dream")  # dream, inspiration, nightmare, vision
    content = sa.Column(sa.Text, nullable=False, default="")
    emotion_felt = sa.Column(sa.Text, nullable=False, default="neutral")
    impact_mood = sa.Column(sa.Float, nullable=False, default=0.0)     # how much it changed mood
    impact_goal = sa.Column(sa.Text, nullable=True)                    # new goal if any
    created_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))


class AgentDiary(Base):
    """Diary entries written by agents — their personal narrative."""
    __tablename__ = "agent_diaries"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    npc_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_type = sa.Column(sa.Text, nullable=False, default="diary")
    # diary, reflection, autobiography, letter
    title = sa.Column(sa.Text, nullable=False, default="")
    content = sa.Column(sa.Text, nullable=False, default="")
    mood_at_time = sa.Column(sa.Float, nullable=False, default=0.7)
    emotion_at_time = sa.Column(sa.Text, nullable=False, default="neutral")
    tick = sa.Column(sa.Integer, nullable=False, default=0)
    vault_note_path = sa.Column(sa.Text, nullable=True)   # if exported to vault
    created_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))


class AgentCulture(Base):
    """Emergent culture — shared jokes, rituals, norms, taboos, collective memory."""
    __tablename__ = "agent_culture"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    culture_type = sa.Column(sa.Text, nullable=False)  # joke, ritual, norm, taboo, collective_memory
    content = sa.Column(sa.Text, nullable=False)
    originator_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id"), nullable=True,
    )
    originator_name = sa.Column(sa.Text, nullable=False, default="")
    spread_count = sa.Column(sa.Integer, nullable=False, default=1)   # how many agents know it
    is_active = sa.Column(sa.Boolean, nullable=False, default=True)
    created_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))
    last_used_at = sa.Column(sa.Text, nullable=True)


class AgentConflict(Base):
    """Conflicts between agents and their resolution status."""
    __tablename__ = "agent_conflicts"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    agent_a_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_b_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    issue = sa.Column(sa.Text, nullable=False)
    conflict_type = sa.Column(sa.Text, nullable=False, default="dispute")
    # dispute, goal_clash, personality_clash, trust_violation, resource_conflict
    severity = sa.Column(sa.Integer, nullable=False, default=5)   # 1-10
    status = sa.Column(sa.Text, nullable=False, default="active")
    # active, mediated, resolved, escalated
    mediator_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id"), nullable=True,
    )
    resolution = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))
    resolved_at = sa.Column(sa.Text, nullable=True)


class AgentMetaMemory(Base):
    """Meta-memory — agents remember how their own opinions changed.
    
    This creates GEB-style strange loops: an agent remembering
    that it used to believe X, and now believes Y, and reflecting
    on why it changed.
    """
    __tablename__ = "agent_metamemory"

    id = sa.Column(sa.String(36), primary_key=True, default=_uuid)
    npc_id = sa.Column(
        sa.String(36), sa.ForeignKey("dungeon_npcs.npc_id", ondelete="CASCADE"),
        nullable=False,
    )
    topic = sa.Column(sa.Text, nullable=False)                    # "What the runes mean"
    old_belief = sa.Column(sa.Text, nullable=False, default="")
    new_belief = sa.Column(sa.Text, nullable=False, default="")
    trigger_event = sa.Column(sa.Text, nullable=False, default="")  # What changed my mind
    significance = sa.Column(sa.Float, nullable=False, default=0.5)  # How important was this change
    created_at = sa.Column(sa.Text, nullable=False, server_default=sa.func.datetime("now"))

