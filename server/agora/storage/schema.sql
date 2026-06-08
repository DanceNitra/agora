-- Agora: SQLite Dev Schema
-- Compatible with main.py expectations

CREATE TABLE IF NOT EXISTS agent_identities (
    agent_id        TEXT PRIMARY KEY,
    public_key      TEXT NOT NULL,
    generation      INTEGER NOT NULL DEFAULT 0,
    genome          TEXT NOT NULL DEFAULT '{}',
    trust_score     REAL NOT NULL DEFAULT 0.5,
    energy_balance  REAL NOT NULL DEFAULT 100.0,
    role            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trust_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       TEXT NOT NULL REFERENCES agent_identities(agent_id),
    target_id       TEXT NOT NULL REFERENCES agent_identities(agent_id),
    score           REAL NOT NULL DEFAULT 0.5 CHECK (score >= 0 AND score <= 1),
    interaction_count INTEGER NOT NULL DEFAULT 0,
    consecutive_cooperations INTEGER NOT NULL DEFAULT 0,  -- ESS 1.4: forgiveness state survives restart
    consecutive_defections   INTEGER NOT NULL DEFAULT 0,
    sliding_window  TEXT NOT NULL DEFAULT '[]',           -- ESS 1.4: last N interactions (JSON)
    last_updated    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_id, target_id)
);

CREATE TABLE IF NOT EXISTS stigmergy_traces (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL REFERENCES agent_identities(agent_id),
    trace_type      TEXT NOT NULL,
    payload         TEXT NOT NULL DEFAULT '{}',
    ttl_seconds     INTEGER NOT NULL DEFAULT 3600,
    expires_at      TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════
-- AGENT OPERATING SYSTEM — Soul, Brain, Body, Abilities, Skills
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS agent_soul (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    personality     TEXT NOT NULL DEFAULT '{}',
    "values"        TEXT NOT NULL DEFAULT '{}',
    emotional_state TEXT NOT NULL DEFAULT 'neutral',
    moral_alignment TEXT NOT NULL DEFAULT 'neutral',
    archetype       TEXT NOT NULL DEFAULT 'explorer',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_brain (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    current_goal    TEXT NOT NULL DEFAULT 'Explore the dungeon',
    plan_stack      TEXT NOT NULL DEFAULT '[]',
    memory          TEXT NOT NULL DEFAULT '[]',
    state_of_mind   TEXT NOT NULL DEFAULT 'focused',
    last_decision   TEXT NOT NULL DEFAULT '',
    last_decision_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_body (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    stamina         REAL NOT NULL DEFAULT 100.0,
    hunger          REAL NOT NULL DEFAULT 0.0,
    fatigue         REAL NOT NULL DEFAULT 0.0,
    awareness       REAL NOT NULL DEFAULT 1.0,
    status_effects  TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS agent_abilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    ability_name    TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    power_level     REAL NOT NULL DEFAULT 1.0 CHECK (power_level >= 0 AND power_level <= 10),
    is_passive      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(npc_id, ability_name)
);

CREATE TABLE IF NOT EXISTS agent_skills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    skill_name      TEXT NOT NULL,
    level           INTEGER NOT NULL DEFAULT 1 CHECK (level >= 0 AND level <= 100),
    xp              REAL NOT NULL DEFAULT 0.0,
    xp_to_next      REAL NOT NULL DEFAULT 100.0,
    last_used_at    TEXT,
    UNIQUE(npc_id, skill_name)
);

CREATE TABLE IF NOT EXISTS agent_help_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id    TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    helper_id       TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    problem_type    TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    requester_task  TEXT,
    helper_reply    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    accepted_at     TEXT,
    resolved_at     TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL REFERENCES agent_identities(agent_id),
    title           TEXT NOT NULL,
    artifact_type   TEXT NOT NULL DEFAULT 'document',
    storage_path    TEXT NOT NULL,
    mime_type       TEXT,
    size_bytes      INTEGER DEFAULT 0,
    checksum        TEXT,
    metadata        TEXT DEFAULT '{}',
    is_published    INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT NOT NULL,
    source_id       TEXT,
    aggregate_type  TEXT,
    aggregate_id    TEXT,
    payload         TEXT NOT NULL DEFAULT '{}',
    occurred_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════
-- EVENT SOURCING — Append-only event store
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS event_store (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregate_type  TEXT NOT NULL,           -- e.g. 'trust', 'tft', 'stigmergy', 'economy'
    aggregate_id    TEXT NOT NULL,           -- e.g. 'agent:alice:agent:bob', 'stigmergy:research'
    sequence_number INTEGER NOT NULL,        -- Monotonic per aggregate, starts at 1
    event_type      TEXT NOT NULL,           -- e.g. 'trust_updated', 'defection_recorded', 'trace_written'
    payload         TEXT NOT NULL DEFAULT '{}',  -- JSON: the actual event data
    metadata        TEXT NOT NULL DEFAULT '{}',  -- JSON: causation/correlation IDs, caller identity
    occurred_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(aggregate_type, aggregate_id, sequence_number)
);
CREATE INDEX IF NOT EXISTS idx_event_store_aggregate ON event_store(aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS idx_event_store_sequence ON event_store(aggregate_type, aggregate_id, sequence_number);

CREATE TABLE IF NOT EXISTS epochs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_number    INTEGER NOT NULL UNIQUE,
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at        TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    summary         TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    priority        INTEGER NOT NULL DEFAULT 0 CHECK (priority >= -5 AND priority <= 5),
    assignee_id     TEXT REFERENCES agent_identities(agent_id),
    epoch_id        INTEGER REFERENCES epochs(id),
    parent_task_id  INTEGER REFERENCES tasks(id),
    metadata        TEXT DEFAULT '{}',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_bids (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         INTEGER NOT NULL REFERENCES tasks(id),
    agent_id        TEXT NOT NULL REFERENCES agent_identities(agent_id),
    bid_amount      REAL NOT NULL DEFAULT 0.5 CHECK (bid_amount >= 0 AND bid_amount <= 1),
    bid_reason      TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(task_id, agent_id)
);

-- ═══════════════════════════════════════════
-- ESS ECONOMY — resource pool + trading
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS resources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    total_supply    REAL NOT NULL DEFAULT 0,
    base_price      REAL NOT NULL DEFAULT 1.0,
    volatility      REAL NOT NULL DEFAULT 0.1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_inventory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL REFERENCES agent_identities(agent_id),
    resource_id     INTEGER NOT NULL REFERENCES resources(id),
    quantity        REAL NOT NULL DEFAULT 0,
    UNIQUE(agent_id, resource_id)
);

CREATE TABLE IF NOT EXISTS trade_offers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL REFERENCES agent_identities(agent_id),
    offer_type      TEXT NOT NULL CHECK (offer_type IN ('buy', 'sell')),
    resource_id     INTEGER NOT NULL REFERENCES resources(id),
    quantity        REAL NOT NULL CHECK (quantity > 0),
    price_per_unit  REAL NOT NULL CHECK (price_per_unit > 0),
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'filled', 'cancelled')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    filled_at       TEXT
);

-- ═══════════════════════════════════════════
-- DUNGEON PERSISTENCE — NPCs, quests, items
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS dungeon_npcs (
    npc_id          TEXT PRIMARY KEY,
    npc_name        TEXT NOT NULL,
    role            TEXT NOT NULL,
    pos_x           REAL NOT NULL DEFAULT 320,
    pos_y           REAL NOT NULL DEFAULT 240,
    health          REAL NOT NULL DEFAULT 100,
    inventory       TEXT NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'active',
    objective       TEXT NOT NULL DEFAULT 'Explore the dungeon',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dungeon_quests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id        TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    quest_type      TEXT NOT NULL DEFAULT 'exploration',
    prerequisites   TEXT NOT NULL DEFAULT '[]',  -- list of quest_ids that must be completed first
    rewards         TEXT NOT NULL DEFAULT '{}',  -- {"items": ["..."], "xp": 10, "unlocks": ["..."]}
    starting_npc    TEXT,                         -- which NPC gives this quest
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════
-- AGENT OPERATING SYSTEM — Soul, Brain, Body, Abilities, Skills
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS agent_soul (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    personality     TEXT NOT NULL DEFAULT '{}',
    "values"        TEXT NOT NULL DEFAULT '{}',
    emotional_state TEXT NOT NULL DEFAULT 'neutral',
    moral_alignment TEXT NOT NULL DEFAULT 'neutral',
    archetype       TEXT NOT NULL DEFAULT 'explorer',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_brain (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    current_goal    TEXT NOT NULL DEFAULT 'Explore the dungeon',
    plan_stack      TEXT NOT NULL DEFAULT '[]',
    memory          TEXT NOT NULL DEFAULT '[]',
    state_of_mind   TEXT NOT NULL DEFAULT 'focused',
    last_decision   TEXT NOT NULL DEFAULT '',
    last_decision_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_body (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    stamina         REAL NOT NULL DEFAULT 100.0,
    hunger          REAL NOT NULL DEFAULT 0.0,
    fatigue         REAL NOT NULL DEFAULT 0.0,
    awareness       REAL NOT NULL DEFAULT 1.0,
    status_effects  TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS agent_abilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    ability_name    TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    power_level     REAL NOT NULL DEFAULT 1.0 CHECK (power_level >= 0 AND power_level <= 10),
    is_passive      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(npc_id, ability_name)
);

CREATE TABLE IF NOT EXISTS agent_skills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    skill_name      TEXT NOT NULL,
    level           INTEGER NOT NULL DEFAULT 1 CHECK (level >= 0 AND level <= 100),
    xp              REAL NOT NULL DEFAULT 0.0,
    xp_to_next      REAL NOT NULL DEFAULT 100.0,
    last_used_at    TEXT,
    UNIQUE(npc_id, skill_name)
);

CREATE TABLE IF NOT EXISTS agent_help_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id    TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    helper_id       TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    problem_type    TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    requester_task  TEXT,
    helper_reply    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    accepted_at     TEXT,
    resolved_at     TEXT
);

CREATE TABLE IF NOT EXISTS dungeon_quest_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id),
    quest_id        TEXT NOT NULL REFERENCES dungeon_quests(quest_id),
    status          TEXT NOT NULL DEFAULT 'available',  -- available, active, completed, failed
    progress        TEXT NOT NULL DEFAULT '{}',         -- {"step": 1, "total": 3, "details": {...}}
    started_at      TEXT,
    completed_at    TEXT,
    UNIQUE(npc_id, quest_id)
);

CREATE TABLE IF NOT EXISTS trade_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id        TEXT NOT NULL,
    seller_id       TEXT NOT NULL,
    resource_id     INTEGER NOT NULL REFERENCES resources(id),
    quantity        REAL NOT NULL,
    price_per_unit  REAL NOT NULL,
    total_energy    REAL NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════
-- AGENT OPERATING SYSTEM — Soul, Brain, Body, Abilities, Skills
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS agent_soul (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    personality     TEXT NOT NULL DEFAULT '{}',
    "values"        TEXT NOT NULL DEFAULT '{}',
    emotional_state TEXT NOT NULL DEFAULT 'neutral',
    moral_alignment TEXT NOT NULL DEFAULT 'neutral',
    archetype       TEXT NOT NULL DEFAULT 'explorer',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_brain (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    current_goal    TEXT NOT NULL DEFAULT 'Explore the dungeon',
    plan_stack      TEXT NOT NULL DEFAULT '[]',
    memory          TEXT NOT NULL DEFAULT '[]',
    state_of_mind   TEXT NOT NULL DEFAULT 'focused',
    last_decision   TEXT NOT NULL DEFAULT '',
    last_decision_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_body (
    npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    stamina         REAL NOT NULL DEFAULT 100.0,
    hunger          REAL NOT NULL DEFAULT 0.0,
    fatigue         REAL NOT NULL DEFAULT 0.0,
    awareness       REAL NOT NULL DEFAULT 1.0,
    status_effects  TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS agent_abilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    ability_name    TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    power_level     REAL NOT NULL DEFAULT 1.0 CHECK (power_level >= 0 AND power_level <= 10),
    is_passive      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(npc_id, ability_name)
);

CREATE TABLE IF NOT EXISTS agent_skills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    skill_name      TEXT NOT NULL,
    level           INTEGER NOT NULL DEFAULT 1 CHECK (level >= 0 AND level <= 100),
    xp              REAL NOT NULL DEFAULT 0.0,
    xp_to_next      REAL NOT NULL DEFAULT 100.0,
    last_used_at    TEXT,
    UNIQUE(npc_id, skill_name)
);

CREATE TABLE IF NOT EXISTS agent_help_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id    TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    helper_id       TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
    problem_type    TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    requester_task  TEXT,
    helper_reply    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    accepted_at     TEXT,
    resolved_at     TEXT
);
