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
