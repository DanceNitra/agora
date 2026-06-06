-- =============================================================================
-- Agora: Schema Definition
-- Phase 1, Step 1.1 — Core Tables
-- =============================================================================
-- This schema defines the foundational data model for the Agora system.
-- It uses UUID v4 primary keys, automatic timestamps, and a soft-delete flag
-- on all top-level entity tables.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Extension: pgcrypto (provides gen_random_uuid())
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- 1. agent_identities
--    Every autonomous or human agent registered in the system.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_identities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name    VARCHAR(128)  NOT NULL,
    agent_type      VARCHAR(32)   NOT NULL DEFAULT 'autonomous',
        -- 'human' | 'autonomous' | 'hybrid'
    public_key      TEXT,
    metadata        JSONB         DEFAULT '{}',
    is_active       BOOLEAN       DEFAULT TRUE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ   -- soft-delete column
);

CREATE INDEX idx_agent_identities_active ON agent_identities (is_active)
    WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- 2. trust_scores
--    Directed trust relationship between two agents, updated by the ESS
--    (Eigentrust Similarity Scoring) engine after each interaction.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trust_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES agent_identities(id)
                        ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES agent_identities(id)
                        ON DELETE CASCADE,
    score           NUMERIC(5,4)  NOT NULL DEFAULT 0.5000
                        CHECK (score >= 0 AND score <= 1),
    interaction_count INTEGER     NOT NULL DEFAULT 0,
    last_updated    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_trust_directed UNIQUE (source_id, target_id)
);

CREATE INDEX idx_trust_scores_source ON trust_scores (source_id);
CREATE INDEX idx_trust_scores_target ON trust_scores (target_id);

-- ---------------------------------------------------------------------------
-- 3. stigmergy_traces
--    Environmental signals left behind by agents to coordinate without
--    direct communication (stigmergy pattern).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stigmergy_traces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL REFERENCES agent_identities(id)
                        ON DELETE CASCADE,
    trace_type      VARCHAR(64)   NOT NULL,
        -- 'task_proposal' | 'vote' | 'artifact_ref' | 'signal' | 'alert'
    payload         JSONB         NOT NULL DEFAULT '{}',
    ttl_seconds     INTEGER       NOT NULL DEFAULT 3600,
    expires_at      TIMESTAMPTZ   NOT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stigmergy_traces_type ON stigmergy_traces (trace_type);
CREATE INDEX idx_stigmergy_traces_expires ON stigmergy_traces (expires_at)
    WHERE expires_at > NOW();

-- ---------------------------------------------------------------------------
-- 4. artifacts
--    Any piece of work produced by an agent (code, documents, data, images).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS artifacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL REFERENCES agent_identities(id)
                        ON DELETE CASCADE,
    title           VARCHAR(256)  NOT NULL,
    artifact_type   VARCHAR(64)   NOT NULL DEFAULT 'document',
        -- 'code' | 'document' | 'data' | 'image' | 'audio' | 'video' | 'other'
    storage_path    TEXT          NOT NULL,
    mime_type       VARCHAR(128),
    size_bytes      BIGINT        DEFAULT 0,
    checksum        VARCHAR(64),   -- SHA-256 hex digest
    metadata        JSONB         DEFAULT '{}',
    is_published    BOOLEAN       DEFAULT FALSE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_artifacts_agent ON artifacts (agent_id);
CREATE INDEX idx_artifacts_type ON artifacts (artifact_type);
CREATE INDEX idx_artifacts_published ON artifacts (is_published)
    WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- 5. events
--    Immutable audit log of all meaningful state changes in the system.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(64)   NOT NULL,
        -- 'agent_registered' | 'trust_updated' | 'artifact_created' |
        -- 'task_assigned' | 'epoch_completed' | 'system_alert'
    source_id       UUID,          -- agent or system component that raised it
    aggregate_type  VARCHAR(64),   -- e.g. 'agent_identities', 'tasks'
    aggregate_id    UUID,
    payload         JSONB         NOT NULL DEFAULT '{}',
    occurred_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_type ON events (event_type);
CREATE INDEX idx_events_occurred ON events (occurred_at DESC);
CREATE INDEX idx_events_aggregate ON events (aggregate_type, aggregate_id);

-- ---------------------------------------------------------------------------
-- 6. epochs
--    Discrete time-bound cycles used for batch trust re-calculation,
--    stigmergy trace expiry, and periodic maintenance tasks.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS epochs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    epoch_number    INTEGER       NOT NULL UNIQUE,
    started_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    status          VARCHAR(32)   NOT NULL DEFAULT 'active',
        -- 'active' | 'completed' | 'failed' | 'cancelled'
    summary         JSONB         DEFAULT '{}'
);

CREATE INDEX idx_epochs_status ON epochs (status);
CREATE INDEX idx_epochs_number ON epochs (epoch_number DESC);

-- ---------------------------------------------------------------------------
-- 7. tasks
--    Work items assigned to or claimed by agents, with full lifecycle.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(256)  NOT NULL,
    description     TEXT,
    status          VARCHAR(32)   NOT NULL DEFAULT 'pending',
        -- 'pending' | 'available' | 'assigned' | 'in_progress' |
        -- 'review' | 'completed' | 'failed' | 'cancelled'
    priority        INTEGER       NOT NULL DEFAULT 0
                        CHECK (priority >= -5 AND priority <= 5),
    assignee_id     UUID REFERENCES agent_identities(id)
                        ON DELETE SET NULL,
    epoch_id        UUID REFERENCES epochs(id)
                        ON DELETE SET NULL,
    parent_task_id  UUID REFERENCES tasks(id)
                        ON DELETE SET NULL,
    metadata        JSONB         DEFAULT '{}',
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_tasks_assignee ON tasks (assignee_id);
CREATE INDEX idx_tasks_epoch ON tasks (epoch_id);
CREATE INDEX idx_tasks_priority ON tasks (priority DESC)
    WHERE deleted_at IS NULL AND status NOT IN ('completed','failed','cancelled');

-- ---------------------------------------------------------------------------
-- Helper: trigger function for auto-updating 'updated_at' columns
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger to tables that have an updated_at column
CREATE TRIGGER trg_agent_identities_updated_at
    BEFORE UPDATE ON agent_identities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_artifacts_updated_at
    BEFORE UPDATE ON artifacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;
