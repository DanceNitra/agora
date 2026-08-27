"""Agora — FastAPI server entry point (SQLite dev mode)."""

import asyncio
import json
import random
import re as _re
import sys as _sys
import uuid

# ── No flashing console windows ── the brain runs WITHOUT a console (launched hidden), so every
# subprocess that runs a console program (git, gh, …) makes Windows pop a NEW console window. Default
# all children to CREATE_NO_WINDOW so they stay invisible (run/call/check_output go through Popen;
# explicit creationflags are left untouched).
if _sys.platform == "win32":
    import subprocess as _sp
    _CREATE_NO_WINDOW = 0x08000000
    _orig_popen_init = _sp.Popen.__init__

    def _popen_no_window(self, *a, **kw):
        if not kw.get("creationflags"):
            kw["creationflags"] = _CREATE_NO_WINDOW
        return _orig_popen_init(self, *a, **kw)

    _sp.Popen.__init__ = _popen_no_window

# Make stdout/stderr UTF-8 so emoji/Slovak prints don't crash on a non-UTF-8 console
# (Windows cp1250) — otherwise any print() inside a request handler 500s the request.
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load server/.env into os.environ so non-pydantic consumers (e.g. Telegram) see it too.
import os
import os as _os
from pathlib import Path as _Path
_envf = _Path(__file__).resolve().parent.parent / ".env"
if _envf.exists():
    for _ln in _envf.read_text(encoding="utf-8", errors="replace").splitlines():
        _ln = _ln.strip()
        if _ln and not _ln.startswith("#") and "=" in _ln:
            _k, _v = _ln.split("=", 1)
            _os.environ.setdefault(_k.strip(), _v.strip())
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite

from agora.config import settings
from agora.coordination.ess_protocol import TrustEngine
from agora.coordination.tft_verifier import TFTVerifier
from agora.coordination.event_bus import EventBus
from agora.coordination.eigen_trust import EigenTrustSolver
from agora.coordination.economy_config import get_role_config, ROLE_ECONOMY
from agora.coordination.stigmergy import StigmergyPool
from agora.coordination.economy import EconomyEngine
from agora.dungeon_os.state import OsState, ensure_os_state_tables
from agora.dungeon_os.roles import build_role_prompt, NPC_ROLE_MAP
from agora.dungeon_os.quests import QuestEngine, ensure_quest_tables
from agora.agent_os.agent_os import AgentOS
from agora.agent_os.physical_world import PhysicalWorld
from agora.harness.state_store import StateStore
from agora.harness.lifecycle_hooks import LifecycleHooks
from agora.harness.tool_registry import ToolRegistry
from agora.harness.execution_loop import ExecutionEngine
from agora.harness.context_manager import ContextManager
from agora.harness.evaluation import EpochEvaluator
from agora.scheduler.room_cluster import RoomClusterScheduler
from agora.controller.controller import Controller
from agora.execution.task_executor import TaskExecutor
from agora.lifecycle.agent_lifecycle import AgentLifecycle
from agora.lifecycle.epoch_engine import EpochEngine
from agora.observability.csd import CSDMonitor
from agora.api import agents as agents_api, tasks as tasks_api, god as god_api, graph as graph_api, dungeon as dungeon_api, economy as economy_api
from agora.api import dungeon_persistence as persistence_api
from agora.api import artifacts as artifacts_api
from agora.api import agent_os_api
from agora.api import physical_api
from agora.api import tool_registry_api as tool_registry_api
from agora.api import evaluation_api
from agora.api import god_console_v2
from agora.api import dungeon_os_api
from agora.api import ess as ess_api
from agora.coordination.ess_protocol import ESS_TOPICS


async def init_db(app: FastAPI):
    """Initialize database connections (SQLite dev or PostgreSQL prod)."""
    from agora.storage.db import init_database

    await init_database(app, settings.database_url)
    db = app.state.db

    # Migration: add content column to artifacts (if SQLite)
    if db:
        try:
            await db.execute("ALTER TABLE artifacts ADD COLUMN content TEXT DEFAULT ''")
            await db.commit()
        except Exception:
            pass  # column already exists

    # Migration (ESS 1.4): trust_scores forgiveness state + sliding window (existing DBs)
    if db:
        for _col_ddl in (
            "ALTER TABLE trust_scores ADD COLUMN consecutive_cooperations INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE trust_scores ADD COLUMN consecutive_defections INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE trust_scores ADD COLUMN sliding_window TEXT NOT NULL DEFAULT '[]'",
        ):
            try:
                await db.execute(_col_ddl)
                await db.commit()
            except Exception:
                pass  # column already exists

    # Initialize state objects
    app.state.trust = TrustEngine(db) if db else TrustEngine(None)
    app.state.tft_verifier = TFTVerifier(db) if db else None
    # Wire TFTVerifier → TrustEngine for provokability queries (ESS 1.4)
    if app.state.tft_verifier:
        app.state.tft_verifier.trust_engine = app.state.trust
    app.state.stigmergy = StigmergyPool(redis_client=None, db=db)
    if db:
        await app.state.stigmergy.load_from_db()
    app.state.economy = EconomyEngine(db)
    await app.state.economy.init_resources()

    app.state.task_executor = TaskExecutor(db)
    app.state.state_store = StateStore(db)
    app.state.lifecycle_hooks = LifecycleHooks(app.state.state_store, db)
    app.state.tool_registry = ToolRegistry(app.state.state_store, db)
    # ExecutionEngine LLM think DISABLED (llm_client=None): it was a SECOND per-agent decision loop
    # (pick one tool) that duplicated AgentOS._think — the agents' rich primary cognition that already
    # decides AND executes visible actions. One cognition loop is enough; the engine falls back to its
    # built-in rule-based action, so agents still act. NOTE: the metered 'agent-think' 1.7M-tok / value-0
    # sink is NOT this loop — it is the tick_loop roleplay batch near line 1600 (see roleplay_use_llm,
    # which is the real lever). Reversible: restore the agent_think lambda.
    app.state.execution_engine = ExecutionEngine(
        app.state.state_store, app.state.tool_registry, db,
        llm_client=None,
    )
    app.state.context_manager = ContextManager(app.state.state_store, db)
    app.state.epoch_evaluator = EpochEvaluator(
        app.state.state_store, db, app.state.lifecycle_hooks
    )
    app.state.agent_os = AgentOS(db, state_store=app.state.state_store, llm_enabled=settings.llm_enabled)
    await app.state.agent_os.ensure_os_initialized()

    # Seed inventories for dungeon NPCs (must come AFTER ensure_os_initialized creates NPC agent identities)
    if db:
        await _seed_npc_inventories(db)
    app.state.physical_world = PhysicalWorld(db, llm_enabled=settings.llm_enabled)
    app.state.scheduler = RoomClusterScheduler(db)
    app.state.controller = Controller(app, db, app.state.state_store)
    app.state.controller._enable_multiprocessing(max_workers=4)
    app.state.agent_lifecycle = AgentLifecycle(db)
    app.state.csd_monitor = CSDMonitor(window_size=200, z_threshold_warning=2.0, z_threshold_critical=3.5)
    app.state.epoch_engine = EpochEngine(db)
    app.state.eigen_trust = EigenTrustSolver(db) if db else None
    # EventBus — topic-based pub/sub
    app.state.event_bus = EventBus(app)
    await app.state.event_bus.start()

    # ── 1.7: stream ESS events in real time via the EventBus (ess:trust / ess:tft) ──
    if getattr(app.state, "trust", None):
        app.state.trust.event_bus = app.state.event_bus
    if getattr(app.state, "tft_verifier", None):
        app.state.tft_verifier.event_bus = app.state.event_bus

    # ── 1.9: give the dungeon NPC brain access to ESS trust, stigmergy, event bus ──
    if getattr(app.state, "agent_os", None):
        app.state.agent_os.trust_engine = getattr(app.state, "trust", None)
        app.state.agent_os.stigmergy = getattr(app.state, "stigmergy", None)
        app.state.agent_os.event_bus = app.state.event_bus

    # ── Event Sourcing: append-only EventStore (ESS 1.1) ──
    from agora.coordination.event_store import EventStore
    if db:
        # schema.sql is not auto-applied at runtime (ORM create_all is used),
        # so ensure the event_store table exists here (idempotent).
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS event_store (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                aggregate_type  TEXT NOT NULL,
                aggregate_id    TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                event_type      TEXT NOT NULL,
                payload         TEXT NOT NULL DEFAULT '{}',
                metadata        TEXT NOT NULL DEFAULT '{}',
                occurred_at     TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(aggregate_type, aggregate_id, sequence_number)
            );
            CREATE INDEX IF NOT EXISTS idx_event_store_aggregate
                ON event_store(aggregate_type, aggregate_id);
            CREATE INDEX IF NOT EXISTS idx_event_store_sequence
                ON event_store(aggregate_type, aggregate_id, sequence_number);

            CREATE TABLE IF NOT EXISTS checkpoints (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                aggregate_type  TEXT NOT NULL,
                aggregate_id    TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                state           TEXT NOT NULL DEFAULT '{}',
                checksum        TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(aggregate_type, aggregate_id, sequence_number)
            );
            CREATE INDEX IF NOT EXISTS idx_checkpoints_lookup
                ON checkpoints(aggregate_type, aggregate_id, sequence_number DESC);
            """
        )
        await db.commit()
    app.state.event_store = EventStore(db)

    # ── Agentic OS v3 — emócie, vzťahy, život, príbehy ──
    if db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_emotions (
                npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                current         TEXT NOT NULL DEFAULT 'neutral',
                intensity       REAL NOT NULL DEFAULT 0.5,
                valence         REAL NOT NULL DEFAULT 0.0,
                arousal         REAL NOT NULL DEFAULT 0.5,
                trigger         TEXT NOT NULL DEFAULT '',
                history         TEXT NOT NULL DEFAULT '[]',
                decay_rate      REAL NOT NULL DEFAULT 0.1,
                mood            REAL NOT NULL DEFAULT 0.7,
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS agent_relationships (
                id              TEXT PRIMARY KEY,
                agent_a_id      TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                agent_b_id      TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                friendship      REAL NOT NULL DEFAULT 0.3,
                respect         REAL NOT NULL DEFAULT 0.5,
                rivalry         REAL NOT NULL DEFAULT 0.0,
                attraction      REAL NOT NULL DEFAULT 0.0,
                debt            REAL NOT NULL DEFAULT 0.0,
                conversations_count INTEGER NOT NULL DEFAULT 0,
                last_topic      TEXT,
                emotional_bond  TEXT NOT NULL DEFAULT 'strangers',
                history         TEXT NOT NULL DEFAULT '[]',
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(agent_a_id, agent_b_id)
            );
            CREATE TABLE IF NOT EXISTS agent_lifecycles (
                npc_id          TEXT PRIMARY KEY REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                age_ticks       INTEGER NOT NULL DEFAULT 0,
                stage           TEXT NOT NULL DEFAULT 'infancy',
                maturity        REAL NOT NULL DEFAULT 0.0,
                wisdom          REAL NOT NULL DEFAULT 0.0,
                total_decisions INTEGER NOT NULL DEFAULT 0,
                total_vault_notes INTEGER NOT NULL DEFAULT 0,
                total_conversations INTEGER NOT NULL DEFAULT 0,
                legacy          TEXT NOT NULL DEFAULT '',
                mentor_id       TEXT REFERENCES dungeon_npcs(npc_id),
                life_goal       TEXT NOT NULL DEFAULT '',
                life_goal_progress REAL NOT NULL DEFAULT 0.0,
                peak_experience TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS agent_dreams (
                id              TEXT PRIMARY KEY,
                npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                dream_type      TEXT NOT NULL DEFAULT 'dream',
                content         TEXT NOT NULL DEFAULT '',
                emotion_felt    TEXT NOT NULL DEFAULT 'neutral',
                impact_mood     REAL NOT NULL DEFAULT 0.0,
                impact_goal     TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS agent_diaries (
                id              TEXT PRIMARY KEY,
                npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                entry_type      TEXT NOT NULL DEFAULT 'diary',
                title           TEXT NOT NULL DEFAULT '',
                content         TEXT NOT NULL DEFAULT '',
                mood_at_time    REAL NOT NULL DEFAULT 0.7,
                emotion_at_time TEXT NOT NULL DEFAULT 'neutral',
                tick            INTEGER NOT NULL DEFAULT 0,
                vault_note_path TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS agent_culture (
                id              TEXT PRIMARY KEY,
                culture_type    TEXT NOT NULL,
                content         TEXT NOT NULL,
                originator_id   TEXT REFERENCES dungeon_npcs(npc_id),
                originator_name TEXT NOT NULL DEFAULT '',
                spread_count    INTEGER NOT NULL DEFAULT 1,
                is_active       INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                last_used_at    TEXT
            );
            CREATE TABLE IF NOT EXISTS agent_conflicts (
                id              TEXT PRIMARY KEY,
                agent_a_id      TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                agent_b_id      TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                issue           TEXT NOT NULL,
                conflict_type   TEXT NOT NULL DEFAULT 'dispute',
                severity        INTEGER NOT NULL DEFAULT 5,
                status          TEXT NOT NULL DEFAULT 'active',
                mediator_id     TEXT REFERENCES dungeon_npcs(npc_id),
                resolution      TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                resolved_at     TEXT
            );
            CREATE TABLE IF NOT EXISTS agent_metamemory (
                id              TEXT PRIMARY KEY,
                npc_id          TEXT NOT NULL REFERENCES dungeon_npcs(npc_id) ON DELETE CASCADE,
                topic           TEXT NOT NULL,
                old_belief      TEXT NOT NULL DEFAULT '',
                new_belief      TEXT NOT NULL DEFAULT '',
                trigger_event   TEXT NOT NULL DEFAULT '',
                significance    REAL NOT NULL DEFAULT 0.5,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        await db.commit()
        print("[Agentic OS v3] Tables created (emotions, relationships, lifecycles, dreams, diaries, culture, conflicts, metamemory)")
    # Wire the event store into the coordination subsystems
    if getattr(app.state, "trust", None):
        app.state.trust.event_store = app.state.event_store
    if getattr(app.state, "tft_verifier", None):
        app.state.tft_verifier.event_store = app.state.event_store
    if getattr(app.state, "stigmergy", None):
        app.state.stigmergy.event_store = app.state.event_store

    # Checkpointer — state snapshots from event streams (ESS 1.2)
    from agora.coordination.checkpointer import Checkpointer
    app.state.checkpointer = Checkpointer(db, app.state.event_store)

    # ── Agentic OS v2 (Phase 2.0) — Brain Ecosystem tables (idempotent) ──
    if db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL,
                memory_type TEXT NOT NULL DEFAULT 'episodic',
                content TEXT NOT NULL,
                importance REAL NOT NULL DEFAULT 0.5,
                emotional_tag TEXT DEFAULT 'neutral',
                source TEXT DEFAULT 'experience',
                related_npc_id TEXT,
                decay_factor REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_recalled_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_memories_npc ON agent_memories(npc_id, memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON agent_memories(npc_id, importance DESC);

            CREATE TABLE IF NOT EXISTS agent_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                speaker_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                message TEXT NOT NULL,
                intent TEXT DEFAULT 'chat',
                turn_number INTEGER NOT NULL DEFAULT 1,
                speaker_name TEXT NOT NULL DEFAULT '',
                target_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_conv_session ON agent_conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_conv_npcs ON agent_conversations(speaker_id, target_id);

            CREATE TABLE IF NOT EXISTS agent_brainstorm_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                topic TEXT NOT NULL,
                initiator_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS agent_brainstorm_ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                npc_id TEXT NOT NULL,
                idea_content TEXT NOT NULL,
                idea_type TEXT DEFAULT 'concept',
                builds_on_id INTEGER,
                votes INTEGER NOT NULL DEFAULT 0,
                impact_score REAL DEFAULT 0.5,
                feasibility REAL DEFAULT 0.5,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_bs_session ON agent_brainstorm_ideas(session_id);
            CREATE INDEX IF NOT EXISTS idx_bs_npc ON agent_brainstorm_ideas(npc_id);

            CREATE TABLE IF NOT EXISTS collective_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                contributor_id TEXT NOT NULL,
                contributor_name TEXT NOT NULL DEFAULT '',
                knowledge_type TEXT DEFAULT 'observation',
                confidence REAL DEFAULT 0.7,
                verification_count INTEGER DEFAULT 0,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ck_type ON collective_knowledge(knowledge_type);

            CREATE TABLE IF NOT EXISTS agent_thoughts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL,
                thought_type TEXT NOT NULL DEFAULT 'reasoning',
                content TEXT NOT NULL,
                context TEXT DEFAULT '',
                importance REAL DEFAULT 0.5,
                related_npc_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_thoughts_npc ON agent_thoughts(npc_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS system_upgrade_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposer_id TEXT NOT NULL,
                proposer_name TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                upgrade_type TEXT NOT NULL DEFAULT 'feature',
                impact_estimate TEXT DEFAULT 'medium',
                effort_estimate TEXT DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'proposed',
                vote_count INTEGER DEFAULT 0,
                implemented_by TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                implemented_at TEXT
            );
            """
        )
        await db.commit()
        # agent_soul.mood — idempotent ALTER (existing DBs)
        try:
            await db.execute("ALTER TABLE agent_soul ADD COLUMN mood REAL NOT NULL DEFAULT 0.7")
            await db.commit()
        except Exception:
            pass  # column already exists

    app.state.active_connections = []
    app.state.tick_count = 0

    # ── Dungeon OS: osState ──
    await ensure_os_state_tables(db)
    app.state.os_state = OsState(db)
    await app.state.os_state.load()

    # ── Dungeon OS: Quest Engine ──
    await ensure_quest_tables(db)
    try:
        app.state.quest_engine = QuestEngine(db, os_state=app.state.os_state)
        await app.state.quest_engine.seed_default_quests()
        print(f"[Quests] Engine initialized OK")
    except Exception as e:
        print(f"[ERROR] Quest engine init failed: {e}")
        import traceback
        traceback.print_exc()
        app.state.quest_engine = None

    # ── Agentic OS v3 — init engines ──
    from agora.agent_os.emotion_engine import EmotionEngine
    from agora.agent_os.relationship_web import RelationshipWeb
    from agora.agent_os.dream_engine import DreamEngine
    from agora.agent_os.diary_engine import DiaryEngine
    from agora.agent_os.culture_engine import CultureEngine
    from agora.agent_os.conflict_engine import ConflictEngine
    from agora.agent_os.meta_memory import MetaMemory
    app.state.emotion_engine = EmotionEngine(db) if db else None
    app.state.relationship_web = RelationshipWeb(db) if db else None
    app.state.dream_engine = DreamEngine(db) if db else None
    app.state.diary_engine = DiaryEngine(db) if db else None
    app.state.culture_engine = CultureEngine(db) if db else None
    app.state.conflict_engine = ConflictEngine(db) if db else None
    app.state.meta_memory = MetaMemory(db) if db else None

    # ── VaultBridge (2.1) — connect agents to the Obsidian "second brain" ──
    from agora.agent_os.vault_bridge import create_vault_reader, create_vault_writer
    app.state.vault_reader = create_vault_reader(settings)
    app.state.vault_writer = create_vault_writer(settings)
    _vault_mode = "REAL vault" if app.state.vault_reader.is_real() else "mock concepts"
    print(f"[VaultBridge] reader+writer ready ({_vault_mode}; path={settings.vault_path or '(unset)'})")

    # Wire vault_writer into diary engine for vault exports
    if app.state.diary_engine and getattr(app.state, "vault_writer", None):
        app.state.diary_engine.vault_writer = app.state.vault_writer
    print(f"[Agentic OS v3] Engines initialized (emotion, relationships, dreams, diary, culture, conflict, metamemory)")

    # ── Real Action Engine (Phase 2.3) ──
    from agora.agent_os.real_action_engine import RealActionEngine
    vault_reader = getattr(app.state, "vault_reader", None)
    vault_writer = getattr(app.state, "vault_writer", None)
    app.state.real_action_engine = RealActionEngine(
        vault_writer=vault_writer,
        vault_reader=vault_reader,
        db=db,
    )
    # Wire into agent_os so LLM decisions can trigger real actions
    if getattr(app.state, "agent_os", None):
        app.state.agent_os.set_real_action_engine(app.state.real_action_engine)
    print(f"[RealAction] Engine initialized (send_telegram, write_note, write_article, run_script, git_commit)")

    # ── Vault Company OS — autonomous vault night cycle ──
    from agora.agent_os.vault_company import VaultCompanyEngine
    app.state.vault_company_engine = VaultCompanyEngine(
        real_action_engine=app.state.real_action_engine,
        vault_reader=vault_reader,
        vault_writer=vault_writer,
        db=db,
        llm_enabled=settings.llm_enabled,
    )
    # Wire into agent_os for agent definitions/reports
    if getattr(app.state, "agent_os", None):
        app.state.agent_os.vault_company_engine = app.state.vault_company_engine

    # ── Vault Company API ──
    from agora.api.vault_company_api import router as vault_company_router
    app.include_router(vault_company_router)
    print(f"[VaultCompany] Engine + API initialized (6 agents, night cycle at 02:00 UTC)")

    # (Removed: the old abstract researcher/writer/critic agents are purged. The dungeon characters'
    # identities are created via the dungeon/agent_os path, never seeded here — so an empty
    # agent_identities table no longer respawns the old trio.)

    print(f"[Agora] DB initialized ({settings.database_url[:50]}...)")


async def _seed_npc_inventories(db):
    """Seed initial agent inventories for dungeon NPCs."""
    cursor = await db.execute(
        "SELECT COUNT(*) as c FROM agent_inventory"
    )
    row = await cursor.fetchone()
    if row and row["c"] == 0:
        import uuid
        cursor = await db.execute("SELECT id, name FROM resources")
        rows = await cursor.fetchall()
        res_by_name = {r["name"]: r["id"] for r in rows}
        # Only seed inventory for agents that actually exist (roster may change —
        # e.g. Finn ...006 was removed; its FK would otherwise fail).
        agent_rows = await (await db.execute("SELECT agent_id FROM agent_identities")).fetchall()
        existing_agents = {r["agent_id"] for r in agent_rows}
        seed_data = [
            ("00000000-0000-0000-0000-000000000001", "gold_ore", 5.0),
            ("00000000-0000-0000-0000-000000000002", "herbs", 4.0),
            ("00000000-0000-0000-0000-000000000003", "scroll_fragment", 3.0),
            ("00000000-0000-0000-0000-000000000003", "crystal_shards", 2.0),
            ("00000000-0000-0000-0000-000000000004", "iron_ingot", 4.0),
            ("00000000-0000-0000-0000-000000000004", "gold_ore", 2.0),
            ("00000000-0000-0000-0000-000000000005", "herbs", 5.0),
            ("00000000-0000-0000-0000-000000000005", "crystal_shards", 1.0),
            ("00000000-0000-0000-0000-000000000006", "gold_ore", 3.0),
            ("00000000-0000-0000-0000-000000000006", "iron_ingot", 3.0),
            ("00000000-0000-0000-0000-000000000007", "iron_ingot", 2.0),
        ]
        for agent_id, res_name, qty in seed_data:
            if agent_id not in existing_agents:
                continue  # roster changed — skip inventory for absent agents
            rid = res_by_name.get(res_name)
            if not rid:
                print(f"[WARN] Resource '{res_name}' not found, skipping")
                continue
            inv_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO agent_inventory (id, agent_id, resource_id, quantity) VALUES (?, ?, ?, ?)",
                (inv_id, agent_id, rid, qty),
            )
        await db.commit()
        print(f"[Economy] Seeded inventories for {len(set(a[0] for a in seed_data))} agents")


async def envoy_watch_loop(app: FastAPI):
    """The Envoy's heartbeat: sweep every posted outreach thread on a slow cadence and alert the
    owner via Telegram the moment a real human reply or reaction appears — so no one has to watch
    a GitHub tab. Read-only; never posts (the reply itself stays gated through the Correspondent)."""
    import asyncio as _aio
    await _aio.sleep(60)                                  # let startup settle
    while True:
        try:
            from agora.execution.envoy import sweep
            from agora.api.agent_os_api import _send_telegram
            r = await _aio.to_thread(sweep)
            # Each NEW named reply: (1) file a 'Correspondence reply by <user>' inbox task so Claude
            # processes it (evaluates as untrusted argument, briefs the owner in Slovak, proposes a
            # gated reply); (2) push a Slovak heads-up to Telegram. Previously fresh_replies was
            # harvested (and marked seen) but DISCARDED — only a terse English ping went out, so the
            # owner never got a real briefing and the reply never reached Claude's inbox.
            fresh = r.get("fresh_replies", [])
            for fr in fresh:
                who = fr.get("by", "?")
                repo, issue = fr.get("repo", ""), fr.get("issue", "")
                snippet = (fr.get("text", "") or "").replace("\n", " ")[:300]
                try:
                    from agora.execution.claude_inbox import add_task
                    # The reply text goes through `untrusted=`, not into the instruction string.
                    # This loop is the one that actually fires every 30 min; the shielded copy was
                    # the on-demand endpoint, so the prose warning below was the ONLY defence on the
                    # live path and the mechanical strips (zero-width, bidi, fence collapse) never
                    # ran on it.
                    add_task(f"Correspondence reply by {who} on {repo}#{issue}. If substantive: "
                             f"brief the owner in Slovak (their point + our answer + how we use "
                             f"it), and if a reply is warranted draft it GATED into the same "
                             f"thread via /brain/correspondent/draft "
                             f"{{repo:'{repo}',issue_number:{issue}}}.",
                             untrusted=snippet, source=f"GitHub user {who} on {repo}#{issue}")
                except Exception as _e:
                    print(f"[Envoy] inbox file error: {_e}")
                await _send_telegram(
                    f"🛰 *Envoy* — nová reakcia na náš outreach\n"
                    f"*{who}* na `{repo}#{issue}`:\n_{snippet[:200]}…_\n"
                    f"Claude to spracuje a pripraví ti slovenský briefing + návrh odpovede.")
            # reactions (no body) still get a short ping
            for ev in r.get("new_events", []):
                if "reaction" in ev:
                    await _send_telegram(f"🛰 *Envoy* — reakcia: {ev}")
        except Exception as e:
            print(f"[Envoy] sweep error: {e}")
        await _aio.sleep(1800)                            # every 30 min


async def frontier_harvest_loop(app: FastAPI):
    """Background feed for the standing frontier: every couple of hours, pull fresh arXiv papers in
    the frontier domains and stock the Library's reading list, so the OS never idles for lack of
    new external material to digest. Read-only (search + queue); the gated outreach path is untouched."""
    import asyncio as _aio
    await _aio.sleep(120)                                    # let startup settle
    while True:
        try:
            from agora.execution.frontier_harvest import harvest
            r = await _aio.to_thread(harvest, 5)
            print(f"[FrontierHarvest] {r.get('topic')}: +{r.get('queued', 0)} papers queued")
        except Exception as e:
            print(f"[FrontierHarvest] error: {e}")
        # WEB-SCOUT (#6, owner 2026-06-27): widest-reach free external search → file a couple of fresh,
        # high-signal leads to the Claude inbox as Crucible/frontier candidates (deduped vs seen; NOT
        # into the raw discovery stream). Read-only data fetch; fail-soft.
        try:
            from agora.execution.web_search import web_scout_pass
            from agora.execution.claude_inbox import add_task
            ws = await _aio.to_thread(web_scout_pass, add_task, 2, 2)
            print(f"[WebScout] filed {ws.get('filed')} fresh external leads ({ws.get('pooled')} pooled): {ws.get('leads')}")
        except Exception as e:
            print(f"[WebScout] error: {e}")
        await _aio.sleep(7200)                               # every 2 hours


async def idea_forge_loop(app: FastAPI):
    """The Idea Forge cadence: ~twice a day, file a 'Forge ideas' inbox task so the main loop runs
    the /idea-forge skill — read the whole brain (canon, beliefs, replications, the ~6000-note
    vault) and generate GROUNDBREAKING ideas across the four targets (OS, Agora, MCP memory,
    real-world product). Skips if a Forge task is already pending, so it never stacks.

    RESTART-RESILIENT: the 12h cadence is anchored to a PERSISTED last-fire time (server/
    .ideation_lastrun, falling back to the newest ts in server/.ideation.json), not to an
    in-process timer. Previously the loop just slept 12h at the bottom of each iteration, so every
    brain restart reset the clock to boot+12h — several restarts in a day starved the forge and it
    never fired. Now it wakes often, computes wall-clock elapsed, and fires whenever >12h have
    passed, so frequent restarts can no longer prevent a fire."""
    import asyncio as _aio
    import json as _json
    import time as _time
    from pathlib import Path as _P
    _root = _P(__file__).resolve().parent.parent             # server/
    _marker = _root / ".ideation_lastrun"
    _ledger = _root / ".ideation.json"
    _INTERVAL = 12 * 3600                                     # ~twice a day

    def _last_fire() -> float:
        # Prefer the explicit marker; fall back to the newest idea ts so a missing marker (first
        # run after this upgrade, or a restart) does not trigger an immediate double-fire.
        try:
            return float(_marker.read_text(encoding="utf-8").strip())
        except Exception:
            pass
        try:
            items = _json.loads(_ledger.read_text(encoding="utf-8"))
            return max((float(it.get("ts", 0) or 0) for it in items), default=0.0)
        except Exception:
            return 0.0

    def _mark(now: float) -> None:
        try:
            _marker.write_text(str(now), encoding="utf-8")
        except Exception as _e:
            print(f"[IdeaForge] marker write error: {_e}")

    await _aio.sleep(120)                                     # short startup settle; overdue fires fast
    while True:
        try:
            from agora.execution.claude_inbox import add_task, pending
            now = _time.time()
            overdue = (now - _last_fire()) > _INTERVAL
            if overdue and not any("Forge ideas" in (t.get("text", "") or "") for t in pending()):
                add_task(
                    "Forge ideas: run the /idea-forge skill — GET /brain/ideation/inputs (canon, "
                    "beliefs, lessons, reproduced+failed replications, analogies, theory, synthesis "
                    "precursors, frontier, the ~6000-note vault corpus by target), then generate 4-6 "
                    "GROUNDBREAKING, non-obvious, buildable ideas spread across the four targets "
                    "(os|agora|mcp_memory|realworld). Each: mechanism + falsifier + first step, "
                    "grounded in specific vault knowledge, deduped against recent ideas. Push ONE "
                    "vault note, POST /brain/ideation/record per idea, Telegram a short digest.")
                _mark(now)
                print("[IdeaForge] queued a Forge ideas task")
        except Exception as e:
            print(f"[IdeaForge] loop error: {e}")
        await _aio.sleep(90 * 60)                             # re-check every ~90 min


async def library_loop(app: FastAPI):
    """Drain the Library's reading list: ~once a day, file a 'Read paper' inbox task so the main loop
    deep-reads ONE queued paper end to end and writes a structured note.

    THIS LOOP DID NOT EXIST. frontier_harvest_loop stocked the reading list every 2h and nothing ever
    emptied it: `gather_paper_inputs` was reachable only from an on-demand endpoint, so the deep-read
    organ ran exactly as often as someone called it by hand. Measured 2026-07-29: 199 papers queued,
    202 read in total, and the newest read was 2026-07-03 -- 26 days idle. The whole point of the
    Library is that the rest of the system grounds itself in abstracts, so an idle Library means no
    part of Agora had read a full paper in almost a month.

    RESTART-RESILIENT the same way idea_forge_loop is: the cadence is anchored to the newest ts in
    server/.library.json (the real record of when we last read something) rather than to an in-process
    timer, so restarts cannot keep pushing the next fire out of reach. That failure mode is why the
    forge needed the same treatment; a loop whose clock resets on restart fires only if the process
    happens to outlive its own interval.
    """
    import asyncio as _aio
    import json as _json
    import time as _time
    from pathlib import Path as _P
    _ledger = _P(__file__).resolve().parent.parent / ".library.json"
    _INTERVAL = 24 * 3600

    def _last_read() -> float:
        try:
            items = _json.loads(_ledger.read_text(encoding="utf-8"))
            return max((float(it.get("ts", 0) or 0) for it in items), default=0.0)
        except Exception:
            return 0.0

    await _aio.sleep(180)
    while True:
        try:
            from agora.execution.claude_inbox import add_task, pending
            from agora.execution.library import prune_reading_list
            # Prune here too, not only on serve: this is where we can SEE it, and a queue quietly
            # pointed at a retired frontier is the failure the last audit found.
            pr = prune_reading_list()
            if pr.get("pruned"):
                print(f"[Library] pruned {pr['pruned']} papers queued under retired frontier queries "
                      f"({pr.get('kept')} remain)")
            if (_time.time() - _last_read()) > _INTERVAL and \
                    not any("Read paper" in (t.get("text", "") or "") for t in pending()):
                _before = {t.get("id") for t in pending()}
                _tid = add_task(
                    "Read paper: GET /brain/library-inputs to pull ONE queued paper's FULL TEXT, then "
                    "read it properly — central claims, strength of evidence (N, method, limitations, "
                    "what the authors themselves scope out), and what it changes for us. Link it to "
                    "the owner's real notes. Push ONE vault note via safe_vault_push.py, POST "
                    "/brain/library-record with the arxiv_id + note path so it is not re-read, then "
                    "POST /brain/claude-inbox/done and send ONE ASCII Telegram line.")
                # add_task returns the EXISTING id when its 36h dedup fires, so printing "queued"
                # unconditionally reports a success it never checked -- the same shape of defect as a
                # surface returning a clean verdict about input it never examined. Say which happened.
                print(f"[Library] queued a Read paper task ({_tid})" if _tid not in _before
                      else f"[Library] Read paper task NOT queued — deduped against {_tid}")
        except Exception as e:
            print(f"[Library] loop error: {e}")
        await _aio.sleep(4 * 3600)


async def exaptation_scan_loop(app: FastAPI):
    """The OUTWARD scanner cadence: ~once a day, file an 'Exaptation scan' inbox task so the main
    loop turns Agora outward — GET /brain/exaptation/supply (our proven mechanisms + ready-made
    world-search queries), WebSearch the live world for fresh real-world pain, match each to the
    mechanism that solves it, record the demand->supply matches, and Telegram a digest of 'new
    problems the world has + what we can do about it'. This is what makes the scanner autonomous
    instead of only-when-Claude-runs-it. RESTART-RESILIENT: anchored to a persisted last-fire time
    (server/.exaptation_lastrun, fallback newest ts in server/.exaptation.json), not an in-process
    timer, so frequent brain restarts can't starve it."""
    import asyncio as _aio
    import json as _json
    import time as _time
    from pathlib import Path as _P
    _root = _P(__file__).resolve().parent.parent             # server/
    _marker = _root / ".exaptation_lastrun"
    _ledger = _root / ".exaptation.json"
    _INTERVAL = 24 * 3600                                     # ~once a day

    def _last_fire() -> float:
        try:
            return float(_marker.read_text(encoding="utf-8").strip())
        except Exception:
            pass
        try:
            items = _json.loads(_ledger.read_text(encoding="utf-8"))
            return max((float(it.get("ts", 0) or 0) for it in items), default=0.0)
        except Exception:
            return 0.0

    await _aio.sleep(300)                                     # startup settle
    while True:
        try:
            from agora.execution.claude_inbox import add_task, pending
            now = _time.time()
            overdue = (now - _last_fire()) > _INTERVAL
            if overdue and not any("Exaptation scan" in (t.get("text", "") or "") for t in pending()):
                add_task(
                    "Exaptation scan: turn Agora OUTWARD. GET /brain/exaptation/supply (our proven "
                    "mechanisms + ready-made world-search queries), then WebSearch the live world "
                    "(forums/Reddit/HN/news) for FRESH real-world pain in those areas. For each strong "
                    "fit, POST /brain/exaptation/record {mechanism_id,pain_title,url,community,score} "
                    "(dedup vs existing ledger urls; score 0-100 by demand strength x match cleanliness). "
                    "Then Telegram a short digest: the new problems + which of our mechanisms solves each. "
                    "Any match scoring >=88 with a real first-customer: flag it for a gated outreach draft "
                    "or a one-page product spec.")
                try:
                    _marker.write_text(str(now), encoding="utf-8")
                except Exception:
                    pass
                print("[Exaptation] queued an outward scan task")
        except Exception as e:
            print(f"[Exaptation] loop error: {e}")
        await _aio.sleep(3 * 3600)                            # re-check every ~3h


async def second_brain_loop(app: FastAPI):
    """The thinking-second-brain cadence: ~once a day, file a 'Second-brain briefing' inbox task so
    the main loop runs the high-quality briefing on the OWNER'S OWN vault — read a real domain
    cluster of his notes and GROUND claims vs literature, find GAPS, CHALLENGE beliefs, CONNECT
    distant notes, and GENERATE ideas BY his own documented methods. This is the product (a second
    brain that THINKS, not stores) dogfooded on the founder first. Skips if one is already pending.
    RESTART-RESILIENT: anchored to a persisted last-fire time (server/.secondbrain_lastrun)."""
    import asyncio as _aio
    import time as _time
    from pathlib import Path as _P
    _marker = _P(__file__).resolve().parent.parent / ".secondbrain_lastrun"
    _INTERVAL = 24 * 3600                                     # ~once a day

    def _last() -> float:
        try:
            return float(_marker.read_text(encoding="utf-8").strip())
        except Exception:
            return 0.0

    def _mark(now: float) -> None:
        try:
            _marker.write_text(str(now), encoding="utf-8")
        except Exception as _e:
            print(f"[SecondBrain] marker write error: {_e}")

    await _aio.sleep(180)                                     # startup settle
    while True:
        try:
            from agora.execution.claude_inbox import add_task, pending
            now = _time.time()
            if (now - _last()) > _INTERVAL and not any(
                    "Second-brain briefing" in (t.get("text", "") or "") for t in pending()):
                add_task(
                    "Second-brain briefing: think about the OWNER'S OWN vault notes (not the abstract "
                    "frontier). Pick a real domain cluster under my-second-brain '04 Resources' "
                    "(rotate domains), read 6-10 of his real notes (skip Agora-Agents/autolinker/"
                    "vault-digest artifacts), then do four moves tied to specific notes: (1) GROUND up "
                    "to 3 claims vs real literature (SUPPORTED/CONTRADICTED/EXTENDED), (2) find up to 2 "
                    "GAPS between his notes, (3) CHALLENGE up to 2 beliefs with disconfirming evidence, "
                    "(4) make up to 2 non-obvious CONNECTIONS. Then GENERATE 2-3 ideas, each BY one of "
                    "his documented methods (ARI hidden-connection bridge, missing-reciprocity, "
                    "abstraction-ladder lift, gap-scan, link-density emergence). Quote real note "
                    "titles, cite real sources, be honest in caveats. Push ONE briefing vault note + "
                    "Telegram a short digest. Any claim with a one-Lab-run falsifier -> severe-test it "
                    "the same cycle (no claim without a measured baseline).")
                _mark(now)
                print("[SecondBrain] queued a Second-brain briefing task")
        except Exception as e:
            print(f"[SecondBrain] loop error: {e}")
        await _aio.sleep(120 * 60)                            # re-check every ~2h


async def seminar_report_loop(app: FastAPI):
    """While the owner is away, push a Telegram research report every ~3h: what the team
    researched, what was skipped and why, what got synthesized. Also seeds the shared INSPEXIMUS
    store once at startup so the contribution gate isn't cold."""
    import asyncio as _aio
    await _aio.sleep(240)                                     # let startup settle
    try:
        from agora.execution.inspeximus_bridge import seed_recent
        n = await _aio.to_thread(seed_recent)
        print(f"[Seminar] INSPEXIMUS seeded with {n} memories")
    except Exception as e:
        print(f"[Seminar] INSPEXIMUS seed error: {e}")
    while True:
        await _aio.sleep(3 * 3600)                            # every ~3h
        try:
            from agora.execution.seminar import research_report
            from agora.execution.telegram_bot import send
            report = research_report(hours=3)
            await send(report)
            print("[Seminar] research report sent")
        except Exception as e:
            print(f"[Seminar] report error: {e}")
        # ~3h autonomous yield snapshot so the self-improving-scientist trend accumulates on its own
        try:
            from agora.execution.self_scientist import snapshot as _ys
            s = await _aio.to_thread(_ys)
            print(f"[Self-Scientist] yield snapshot {s.get('yield_score')}")
        except Exception as e:
            print(f"[Self-Scientist] snapshot error: {e}")


async def db_retention_loop(app: FastAPI):
    """Keep agora.db bounded: once a day, prune operational-log tables to a rolling window and
    drop stale byzantine-violation noise, then reclaim space. Knowledge tables are never touched.
    This is what stops the dungeon-lag regression (unbounded log growth) from recurring."""
    import asyncio as _aio
    await _aio.sleep(1800)                                    # let startup settle
    while True:
        try:
            from agora.execution.db_retention import prune
            res = await _aio.to_thread(prune, 14, 2, True)    # 14d logs, 2d byzantine, vacuum
            print(f"[Retention] pruned {res.get('_total_deleted', 0)} log rows "
                  f"(vacuum {res.get('_vacuum_seconds', '-')}s)")
        except Exception as e:
            print(f"[Retention] loop error: {e}")
        await _aio.sleep(24 * 3600)                           # daily


async def prediction_resolve_loop(app: FastAPI):
    """Close the RESOLUTION bottleneck. Predictions were recorded but NOTHING ever called
    resolve_due(), so the ledger stayed 0-resolved and the Brier was unmeasurable forever — the
    credibility track record (the moat) could never become real. Once a day, resolve every matured
    prediction and any due oracle market so calibration actually accumulates. Purely additive: it
    only scores forecasts whose horizon has elapsed (the >=1-day age guard still binds)."""
    import asyncio as _aio
    await _aio.sleep(1200)                                    # let startup settle
    while True:
        try:
            from agora.execution.prediction_ledger import resolve_due, calibration
            resolved = await resolve_due()
            cal = calibration()
            print(f"[Predict-Resolve] resolved {len(resolved)} due; track record "
                  f"{cal.get('correct')}/{cal.get('resolved')} (Brier {cal.get('brier')})")
        except Exception as e:
            print(f"[Predict-Resolve] ledger error: {e}")
        try:
            from agora.execution.oracle import resolve_open
            o = await _aio.to_thread(resolve_open)
            if o:
                print(f"[Predict-Resolve] oracle resolved {len(o)} markets")
        except Exception as e:
            print(f"[Predict-Resolve] oracle error: {e}")
        await _aio.sleep(24 * 3600)                           # daily


async def hypothesis_loop(app: FastAPI):
    """Close the gap Agora's self-reflection flagged: thousands of findings, zero hypotheses. Every
    ~6h, bridge a coherent cross-domain finding cluster into ONE hypothesis, TEST it against real
    literature, RECORD it (knowledge_type='hypothesis'), and register its falsifier as an open
    question so the agents go test it. Isolated facts become science only when something bridges
    them — this is the trigger that existed in code but was never fired by any loop."""
    import asyncio as _aio
    await _aio.sleep(900)                                     # let startup + the finding stream settle
    while True:
        try:
            from agora.execution.hypothesis_induction import synthesize_and_record_hypothesis
            res = await synthesize_and_record_hypothesis(app.state.db, settings.vault_path)
            if res.get("status") == "recorded":
                print(f"[Hypothesis] recorded [{res.get('verdict')}]: {res.get('hypothesis','')[:70]}")
                try:
                    from agora.execution.telegram_bot import send
                    from agora.execution.scientist import format_hypothesis
                    await send("🧬 New hypothesis formed, tested + recorded:\n\n"
                               + format_hypothesis(res.get("formatted", {})))
                except Exception:
                    pass
            else:
                print(f"[Hypothesis] skip: {res.get('reason','?')}")
        except Exception as e:
            print(f"[Hypothesis] loop error: {e}")
        await _aio.sleep(6 * 3600)                            # every ~6h


async def scout_digest_loop(app: FastAPI):
    """VISIBILITY for the GitHub Opportunity Scout. The scan itself runs autonomously from the
    dungeon supervisor (~2.4h) and writes server/.scout.json, but nothing ever pushed the owner a
    digest — so GitHub scanning was invisible unless they manually typed /scout. Every ~8h this
    reads the scout ledger and Telegrams what issues were scanned + the outcome split, and flags a
    STALLED scan (e.g. dungeon down) when nothing new was engaged. Read-only; reuses the existing
    ledger + _send_telegram. Does NOT scan itself (that would double-queue and burn rate limit)."""
    import asyncio as _aio
    import time as _t
    await _aio.sleep(600)                                     # let startup settle
    window = 8 * 3600
    while True:
        try:
            from agora.execution.scout import _load, find_opportunity
            from agora.api.agent_os_api import _send_telegram
            items = _load()
            cutoff = _t.time() - window
            fresh = [x for x in items if x.get("ts", 0) >= cutoff]
            if fresh:
                drafted = sum(1 for x in fresh if "no real fit" not in (x.get("outcome", "") or "").lower())
                nofit = len(fresh) - drafted
                lines = [f"\U0001F52D *Scout digest* — {len(fresh)} GitHub issues scanned in ~8h "
                         f"({drafted} drafted, {nofit} no-fit)"]
                for x in fresh[-6:][::-1]:
                    lines.append(f"• [{x.get('outcome','?')[:40]}] {x.get('repo','')}#{x.get('issue','')}")
            else:
                # NAME THE STAGE THAT IS ACTUALLY STUCK. This used to read "no new issues engaged in
                # ~8h (scan may be idle — check the dungeon supervisor is running)" and both halves
                # misled: nothing was engaged for SIX DAYS, not eight hours, and the scan was not
                # idle at all — discovery kept filling the box while TRIAGE (a Claude inbox task) was
                # the stalled stage. The advice pointed at a supervisor that is not the mechanism in
                # use. A digest that cannot tell which stage stopped reads exactly like a healthy one.
                from agora.execution.scout import box_stats as _bs
                try:
                    st = _bs()
                except Exception:
                    st = {}
                since = ""
                last_t = max((x.get("ts", 0) for x in items), default=0.0)
                if last_t:
                    d = (_t.time() - last_t) / 86400.0
                    since = f" — last triaged {d:.1f}d ago" if d >= 1 else f" — last triaged {d * 24:.0f}h ago"
                if st.get("open"):
                    lines = [f"\U0001F52D *Scout digest* — TRIAGE is the blocker{since}. "
                             f"Discovery is running: *{st['open']}* lead(s) waiting in the box "
                             f"(oldest {st.get('oldest_open_days', 0)}d, {st.get('total_seen', 0)} seen). "
                             f"Drain them with the `Scout triage` task in the Claude inbox."]
                else:
                    lines = [f"\U0001F52D *Scout digest* — nothing engaged and the box is EMPTY{since}: "
                             f"discovery itself is not producing. Check the dungeon is running its "
                             f"scan cycle (`mcp_server.py` alive, loop_n advancing)."]
            try:
                tgt = await _aio.to_thread(find_opportunity)
                if tgt and tgt.get("url"):
                    lines.append(f"_Now eyeing:_ {tgt.get('repo','')}#{tgt.get('issue_number','')} "
                                 f"(fit {tgt.get('score','?')})")
            except Exception:
                pass
            await _send_telegram("\n".join(lines))
            print(f"[ScoutDigest] sent ({len(fresh)} fresh of {len(items)})")
        except Exception as e:
            print(f"[ScoutDigest] loop error: {e}")
        await _aio.sleep(window)                              # every ~8h


async def receipt_rot_loop(app: FastAPI):
    """Re-RUN the artifacts we publicly offered, daily, and speak only when a receipt CHANGES state.

    Why this is a timed organ and not a publish-time check: rot does not arrive when we publish, it
    arrives in between. `corroboration_poison.py` — linked from openclaw#35203 under the words "happy
    to share the runnable replications" — was broken by three unrelated upstream changes over months
    (a new guard against opening an empty store, _GRADUATE_VALUE 1.0 -> 5.0, and graduation moving to
    consolidate()). Nobody published anything on those days. It printed FAIL and exited 0, so an
    exit-code check would have called it green, and it stayed that way until someone ran it.

    Why it reports only TRANSITIONS: a daily "all good" message is a message nobody reads by week
    three, and then the one that matters arrives in the same shape as the noise. It speaks when a
    receipt leaves PASS, and when one comes back.

    tools/public_receipts.py is the gate; this is the thing that calls it. Building the gate and
    leaving it for someone to remember is the exact failure it exists to catch — and the reason
    construction_audit.py sat unwired for a day.
    """
    import asyncio as _aio, json as _json, subprocess as _sp, sys as _sys, time as _t
    from pathlib import Path as _P
    _root = _P(__file__).resolve().parents[2]
    _tool = _root / "tools" / "public_receipts.py"
    _state = _root / "server" / ".receipt_rot_state.json"
    _INTERVAL = 24 * 3600

    def _last_fire() -> float:
        try:
            return float(_json.loads(_state.read_text(encoding="utf-8")).get("ts", 0) or 0)
        except Exception:
            return 0.0                       # no marker yet -> run once shortly after startup

    await _aio.sleep(2400)                                     # let startup settle
    while True:
        try:
            if not _tool.exists():
                print(f"[ReceiptRot] tool missing at {_tool} — not silently skipping, saying so")
            elif (_t.time() - _last_fire()) > _INTERVAL:
                # locomo needs two embedding models and ~20 minutes; it carries a dated waiver and is
                # excluded here so a daily organ never holds the GPU. Its cost is stated in its own
                # preflight, which is where a reader meets it.
                r = await _aio.to_thread(
                    lambda: _sp.run([_sys.executable, "-X", "utf8", str(_tool), "--timeout", "180"],
                                    capture_output=True, text=True, timeout=1500, cwd=str(_root)))
                out = (r.stdout or "") + (r.stderr or "")
                now = {}
                for line in out.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] in (
                            "PASS", "FAIL", "CRASHED", "TIMEOUT", "UNKNOWN", "NEEDS-RESOURCE",
                            "INFRA", "waived"):
                        now[parts[1]] = parts[0]
                prev = {}
                try:
                    prev = _json.loads(_state.read_text(encoding="utf-8")).get("verdicts", {}) or {}
                except Exception:
                    pass

                broke = [k for k, v in now.items() if v not in ("PASS", "waived")
                         and prev.get(k) in ("PASS", "waived")]
                healed = [k for k, v in now.items() if v in ("PASS", "waived")
                          and prev.get(k) not in ("PASS", "waived", None)]
                if not now:
                    print("[ReceiptRot] the run produced NO verdict lines — treating as a fault, "
                          "not as 'nothing changed'")
                _state.write_text(_json.dumps({"ts": _t.time(), "verdicts": now}, indent=1),
                                  encoding="utf-8")
                print(f"[ReceiptRot] {sum(1 for v in now.values() if v == 'PASS')}/{len(now)} pass, "
                      f"{len(broke)} newly broken, {len(healed)} recovered")
                if broke or healed:
                    from agora.execution.telegram_bot import send as _tg
                    msg = []
                    if broke:
                        msg.append("Public receipts BROKE: " + ", ".join(
                            f"{k.split('/')[-1]} -> {now[k]}" for k in broke[:6]))
                        msg.append("We told readers these are runnable. Fix or stop citing.")
                    if healed:
                        msg.append("Recovered: " + ", ".join(k.split("/")[-1] for k in healed[:6]))
                    await _tg(" | ".join(msg)[:900])
        except Exception as e:
            print(f"[ReceiptRot] loop error: {e}")
        await _aio.sleep(3600)                                 # check hourly, fire daily


async def self_audit_loop(app: FastAPI):
    """THE SELF-AUDIT — Agora keeps its own house in order with its own tools, and tracks its health
    over time. Every ~12h: (1) consolidate the brain's inspeximus store (link near-duplicates, drop
    nothing), (2) promote grounded+sourced+falsifiable contributions to VERIFIED (the higher-trust
    tier value_points already rewards but nothing wrote back), (3) append a health snapshot so trends
    are visible (server/.self_audit_history.json). The full 8-tool audit is tools/self_audit.py;
    this is the live hygiene + trend recorder. Purely additive and idempotent."""
    import asyncio as _aio, json as _json, time as _t
    from pathlib import Path as _P
    _hist = _P(__file__).resolve().parent.parent / ".self_audit_history.json"
    await _aio.sleep(1500)                                    # let startup settle
    while True:
        try:
            from agora.execution.inspeximus_bridge import consolidate_brain_memory
            from agora.execution.seminar import verify_contributions, seminar_stats
            cons = await _aio.to_thread(consolidate_brain_memory)
            ver = await _aio.to_thread(verify_contributions)
            stats = seminar_stats()
            snap = {"ts": _t.time(), "memories": cons.get("total"),
                    "linked_pairs": cons.get("linked_pairs"), "newly_verified": ver.get("newly_verified"),
                    "contributions": stats.get("contributions"), "grounded": stats.get("grounded"),
                    "verified": stats.get("verified")}
            hist = []
            if _hist.exists():
                try:
                    hist = _json.loads(_hist.read_text())
                except Exception:
                    hist = []
            # Self-governance: apply our own Anchor Law to ourselves — track external-grounding φ and
            # ALARM autonomously if it drifts toward the self-confirming lock-in threshold. The loop
            # closing on itself (the system governed by the law it discovered).
            try:
                from agora.execution.self_improvement import govern
                g = await _aio.to_thread(govern)
                snap["grounding_phi"] = g.get("phi")
                if g.get("alarm"):
                    from agora.api.agent_os_api import _send_telegram
                    await _send_telegram(
                        f"⚠️ Self-governance ALARM (Anchor Law): external grounding phi={g['phi']:.2f} "
                        f"near the lock-in threshold — predicts self-confirming drift. Raise paper/vault grounding.")
            except Exception as _e:
                print(f"[Self-Govern] {_e}")
            # Consensus lock-in guard: apply Agora's own minority-tipping / Grounding-Coupling law to
            # its OWN consensus stream — alarm if one theme crosses the critical mass without the
            # external grounding + domain diversity the law requires (automated retrospective check).
            try:
                from agora.execution.self_tipping import assess as _tip_assess
                ta = await _aio.to_thread(_tip_assess)
                if ta.get("status") == "ok":
                    snap["consensus_top_theme"] = ta.get("top_theme")
                    snap["consensus_top_share"] = ta.get("top_share")
                    snap["consensus_lock_in_risk"] = ta.get("lock_in_risk")
                    if ta.get("lock_in_risk"):
                        from agora.api.agent_os_api import _send_telegram
                        await _send_telegram(
                            f"⚠️ Consensus lock-in guard (minority-tipping law): {ta.get('verdict')}")
            except Exception as _e:
                print(f"[Lock-in Guard] {_e}")
            # The self-improving scientist: track validated-discovery yield over time so the
            # capstone question — does applying our own laws raise our yield? — is measurable.
            try:
                from agora.execution.self_scientist import snapshot as _yield_snap, apply_policy as _apply_pol
                ys = await _aio.to_thread(_yield_snap)
                snap["validated_yield"] = ys.get("yield_score")
                pol = await _aio.to_thread(_apply_pol)   # v2: the controller ACTS — tune organs by our own laws
                snap["policy"] = {"grounding_floor": pol.get("grounding_floor"), "dedup": pol.get("dedup_threshold")}
            except Exception as _e:
                print(f"[Self-Scientist] {_e}")
            hist.append(snap)
            _hist.write_text(_json.dumps(hist[-200:], indent=2))
            print(f"[Self-Audit] verified {stats.get('verified')}/{stats.get('contributions')} contributions, "
                  f"mem {cons.get('total')} (+{cons.get('linked_pairs')} links), phi={snap.get('grounding_phi')}; "
                  f"snapshot #{len(hist)}")
        except Exception as e:
            print(f"[Self-Audit] loop error: {e}")
        await _aio.sleep(12 * 3600)                           # ~2x/day


async def lifespan(app: FastAPI):
    try:
        await init_db(app)
    except Exception as e:
        print(f"[FATAL] Lifespan init_db failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise
    loop = asyncio.get_event_loop()
    loop.create_task(tick_loop(app))
    try:
        from agora.execution.telegram_bot import poll_loop
        loop.create_task(poll_loop(app))           # two-way Telegram command center
    except Exception as _e:
        print(f"[Telegram] poller not started: {_e}")
    try:
        from agora.execution.watchdog import watch_dungeon_forever
        loop.create_task(watch_dungeon_forever())  # the brain keeps the dungeon alive
    except Exception as _e:
        print(f"[Watchdog] not started: {_e}")
    try:
        loop.create_task(envoy_watch_loop(app))    # the Envoy watches our outreach for replies
    except Exception as _e:
        print(f"[Envoy] watch loop not started: {_e}")
    try:
        loop.create_task(frontier_harvest_loop(app))  # keep the frontier reading list stocked
    except Exception as _e:
        print(f"[FrontierHarvest] not started: {_e}")
    try:
        loop.create_task(idea_forge_loop(app))     # ~2x/day: queue a Forge ideas task for the loop
    except Exception as _e:
        print(f"[IdeaForge] not started: {_e}")
    try:
        loop.create_task(library_loop(app))        # ~daily: DRAIN the reading list (nothing did)
    except Exception as _e:
        print(f"[Library] not started: {_e}")
    try:
        loop.create_task(exaptation_scan_loop(app))  # ~daily: queue an outward real-world scan task
    except Exception as _e:
        print(f"[Exaptation] scan loop not started: {_e}")
    try:
        loop.create_task(db_retention_loop(app))   # daily: keep agora.db bounded (anti-lag)
        loop.create_task(receipt_rot_loop(app))    # daily: re-RUN the receipts we publicly offered
    except Exception as _e:
        print(f"[Retention] not started: {_e}")
    try:
        loop.create_task(prediction_resolve_loop(app))  # daily: resolve matured forecasts -> real Brier track record
    except Exception as _e:
        print(f"[Predict-Resolve] not started: {_e}")
    try:
        loop.create_task(seminar_report_loop(app))  # ~3h: Telegram research report + seed INSPEXIMUS
    except Exception as _e:
        print(f"[Seminar] report loop not started: {_e}")
    try:
        loop.create_task(hypothesis_loop(app))     # ~6h: findings -> a tested, recorded hypothesis
    except Exception as _e:
        print(f"[Hypothesis] loop not started: {_e}")
    try:
        loop.create_task(scout_digest_loop(app))   # ~8h: Telegram digest of what GitHub issues were scanned
    except Exception as _e:
        print(f"[ScoutDigest] loop not started: {_e}")
    try:
        loop.create_task(second_brain_loop(app))   # ~daily: queue a Second-brain briefing on the owner's notes
    except Exception as _e:
        print(f"[SecondBrain] loop not started: {_e}")
    try:
        loop.create_task(self_audit_loop(app))     # ~12h: run our own tools on ourselves (consolidate + verify + health snapshot)
    except Exception as _e:
        print(f"[Self-Audit] loop not started: {_e}")
    yield
    if hasattr(app.state, 'db') and app.state.db:
        await app.state.db.close()

app = FastAPI(title="Agora", version="0.1.0", lifespan=lifespan)

# Defense-in-depth for a no-auth, RCE-capable (POST /brain/lab/run), loopback-only API. Binding to
# 127.0.0.1 stops the network, but a malicious page in the owner's own browser could still POST to
# 127.0.0.1:8000 (CSRF) or reach it via DNS-rebinding (a hostile domain resolving to 127.0.0.1).
# Reject any request whose Host header isn't loopback (DNS-rebinding) or whose Origin is a foreign
# site (browser CSRF). Server-side clients (the dungeon, local scripts) send a loopback Host and no
# Origin, so they're unaffected; the local renderer on :5174 sends a loopback Origin and is allowed.
_LOCAL_HOST_RE = _re.compile(r"^(127\.0\.0\.1|localhost|\[::1\]|::1)(:\d+)?$", _re.I)
_LOCAL_ORIGIN_RE = _re.compile(r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$", _re.I)


@app.middleware("http")
async def _local_only_guard(request, call_next):
    from fastapi.responses import JSONResponse
    host = (request.headers.get("host") or "").strip()
    if host and not _LOCAL_HOST_RE.match(host):
        return JSONResponse({"detail": "non-loopback Host rejected"}, status_code=403)
    origin = (request.headers.get("origin") or "").strip()
    if origin and not _LOCAL_ORIGIN_RE.match(origin):
        return JSONResponse({"detail": "cross-site Origin rejected"}, status_code=403)
    return await call_next(request)


# CORS limited to loopback origins (the local renderer), not '*' — no foreign page may read responses.
app.add_middleware(CORSMiddleware,
                   allow_origin_regex=r"https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def _tag_organ(request, call_next):
    """METABOLISM: tag the request's organ from the route's last path segment so every LLM call
    it makes (even via asyncio.to_thread) is attributed to that capability."""
    try:
        seg = [s for s in request.url.path.split("/") if s]
        if seg:
            from agora.execution.metabolism import set_organ
            set_organ(seg[-1])
    except Exception:
        pass
    return await call_next(request)

# Mount API routes
app.include_router(agents_api.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tasks_api.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(god_api.router, prefix="/api/v1/god", tags=["god"])
app.include_router(graph_api.router, prefix="/api/v1", tags=["graph"])
app.include_router(dungeon_api.router)
app.include_router(economy_api.router)
app.include_router(persistence_api.router)
app.include_router(artifacts_api.router)
app.include_router(agent_os_api.router)
app.include_router(physical_api.router)
app.include_router(tool_registry_api.router)
app.include_router(evaluation_api.router)
app.include_router(god_console_v2.router)
app.include_router(dungeon_os_api.router)
app.include_router(ess_api.router)


# ── Event topic mapping ───────────────────────────────────────

_EVENT_TOPIC_MAP = {
    "agent_thought": "system",
    "resource_drop": "economy",
    "heartbeat": "system",
    "byzantine_violation": "byzantine",
    "csd_alert": "csd",
    "stigmergy_insight": "stigmergy",
    "death": "system",
    "respawn": "system",
    "trade": "economy",
    "epoch_update": "epoch",
    "violation": "byzantine",
}


def _topics_for_event(event_type: str, payload: dict) -> list[str]:
    """Derive topic(s) from event type and payload.

    Returns a list of topics this event should be published to.
    """
    base = _EVENT_TOPIC_MAP.get(event_type, "system")
    topics = [base]
    # Agent-specific topic if payload has agent_id
    if isinstance(payload, dict):
        aid = payload.get("agent_id") or payload.get("npc_id")
        if aid:
            topics.append(f"agent:{aid}")
        # Room-specific topic
        room = payload.get("room") or payload.get("room_name")
        if room:
            topics.append(f"room:{room}")
    return topics


async def broadcast(app: FastAPI, event_type: str, payload: dict):
    """Publish event via EventBus (topic-based routing + Redis pub/sub).

    Falls back to legacy direct WebSocket broadcast if EventBus is not
    initialised (backward compat).
    """
    event_bus = getattr(app.state, "event_bus", None)
    if event_bus:
        topics = _topics_for_event(event_type, payload)
        for topic in topics:
            await event_bus.publish(topic, event_type, payload)
    else:
        # Legacy fallback
        event = {"type": event_type, "payload": payload,
                 "timestamp": datetime.now(timezone.utc).isoformat()}
        for ws in app.state.active_connections:
            try:
                await ws.send_json(event)
            except Exception:
                pass


async def _process_agent_thought(
    app: FastAPI, db, trust_engine, stigmergy,
    agent, partner_id, tier, thought, tick_count
):
    """Process a single agent's thought: trust update, TFT verification,
    trace, economy, broadcast."""
    agent_id = agent["agent_id"]
    role = agent["role"]
    agent_trust = agent["trust_score"]

    action = thought.get("action", "unknown")
    insight = thought.get("insight", thought.get("content_preview",
              thought.get("feedback", thought.get("discovery", json.dumps(thought)))))

    task_types = ["research", "writing", "review", "analysis", "exploration"]
    task_type = random.choice(task_types)

    trust_before = agent_trust

    if partner_id:
        current_trust = await trust_engine.get_trust(agent_id, partner_id)
        cursor_check = await db.execute(
            "SELECT COUNT(*) as cnt FROM trust_scores WHERE source_id=? AND target_id=?",
            (agent_id, partner_id),
        )
        row_check = await cursor_check.fetchone()
        is_first = row_check["cnt"] == 0

        if is_first or current_trust >= 0.2:
            outcome = "cooperate"
            trust_delta = 0.1
        else:
            outcome = "defect"
            trust_delta = -0.3

        trust_record = await trust_engine.record_interaction(agent_id, partner_id, outcome)
        trust_after = trust_record["score"]
    else:
        outcome = "cooperate"
        trust_delta = 0.0
        trust_after = agent_trust

    # ── Record interaction in TFT log ──
    tft = app.state.tft_verifier
    if tft and partner_id:
        await tft.record_interaction(
            source_id=agent_id,
            target_id=partner_id,
            outcome=outcome,
            round_num=tick_count,
            trust_before=trust_before,
            trust_after=trust_after,
            context={"role": role, "tier": tier, "action": action},
        )

    await stigmergy.write_trace(
        agent_id=agent_id,
        task_type=task_type,
        result=f"[{role}] {str(insight)[:200]}",
        trust_delta=trust_delta,
    )

    # Economy: random resource drop from exploration
    if role in ("explorer", "scout", "adventurer") or task_type == "exploration":
        drop = await app.state.economy.random_resource_drop(agent_id)
        if drop:
            await broadcast(app, "resource_drop", {
                "agent_id": agent_id[:8], "role": role,
                "resource": drop["resource"], "quantity": drop["quantity"],
            })

    energy_cost = 10 if tier == "expert" else 5 if tier == "medium" else 3
    trust_change = trust_delta if outcome == "cooperate" else trust_delta * 2
    updated_trust = min(1.0, max(0.0, agent_trust + trust_change))

    # ── TFT-weighted trust blend: 30% TFT, 70% ESS ──
    if tft and partner_id and await tft._has_history(agent_id):
        tft_eval = await tft.evaluate(agent_id)
        tft_score = tft_eval["tft_score"]
        blended_trust = round(0.7 * updated_trust + 0.3 * tft_score, 4)
        blended_trust = max(0.0, min(1.0, blended_trust))
    else:
        blended_trust = updated_trust

    await db.execute(
        "UPDATE agent_identities SET trust_score=?, energy_balance=energy_balance-?, "
        "updated_at=datetime('now') WHERE agent_id=?",
        (blended_trust, energy_cost, agent_id),
    )

    await broadcast(app, "agent_thought", {
        "agent_id": agent_id[:8], "role": role, "tier": tier,
        "action": action, "insight": str(insight)[:200],
        "trust": round(blended_trust, 3), "trust_raw": round(updated_trust, 3),
        "energy_cost": energy_cost,
    })

    if tick_count % 5 == 0 and action != "error":
        await db.execute(
            "INSERT INTO artifacts (id, agent_id, title, artifact_type, storage_path, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, agent_id, f"{role} thought #{tick_count}", task_type,
             f"memory/tick-{tick_count}", json.dumps(thought)),
        )


@app.get("/api/v1/health")
async def health(request: Request):
    db = request.app.state.db
    cursor = await db.execute("SELECT COUNT(*) as c FROM agent_identities WHERE status='active'")
    row = await cursor.fetchone()
    count = row["c"] if row else 0
    return {"status": "ok", "agents": count,
            "tick": request.app.state.tick_count}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    event_bus = getattr(websocket.app.state, "event_bus", None)
    if event_bus:
        # Default: subscribe to 'all' topic (receives everything)
        await event_bus.subscribe(websocket, ["all"])
    else:
        # Legacy mode
        websocket.app.state.active_connections.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            if msg_type == "subscribe" and event_bus:
                topics = msg.get("topics", [])
                await event_bus.subscribe(websocket, topics)
                # Send confirmation + replay
                replay_count = await event_bus.replay(websocket, topics, limit=20)
                await websocket.send_json({
                    "type": "subscribed",
                    "topics": topics,
                    "replayed": replay_count,
                })
            elif msg_type == "unsubscribe" and event_bus:
                topics = msg.get("topics", [])
                await event_bus.unsubscribe(websocket, topics)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "topics": topics,
                })
            elif msg_type == "replay" and event_bus:
                topics = msg.get("topics", ["all"])
                limit = msg.get("limit", 20)
                count = await event_bus.replay(websocket, topics, limit=limit)
                await websocket.send_json({
                    "type": "replayed",
                    "topics": topics,
                    "count": count,
                })
            elif msg_type == "list" and event_bus:
                # Keep the old broadcast for generic text messages
                await broadcast(websocket.app, "message", {"text": data})
            else:
                await broadcast(websocket.app, "message", {"text": data})
    except WebSocketDisconnect:
        if event_bus:
            await event_bus._remove_websocket(websocket)
        else:
            try:
                websocket.app.state.active_connections.remove(websocket)
            except ValueError:
                pass


@app.websocket("/ws/ess")
async def ws_ess_endpoint(websocket: WebSocket):
    """WebSocket pre-subscribed to all ESS topics (ess:trust, ess:tft, ess:stability).

    Connect to /ws/ess to receive only ESS events (trust updates, TFT evaluations,
    stability checks) — no dungeon/heartbeat noise. Receive-only apart from ping/pong.
    """
    await websocket.accept()
    event_bus = getattr(websocket.app.state, "event_bus", None)
    if event_bus:
        await event_bus.subscribe(websocket, ESS_TOPICS)
        # Replay recent ESS events so a fresh subscriber sees current state.
        try:
            replayed = await event_bus.replay(websocket, ESS_TOPICS, limit=20)
            await websocket.send_json({
                "type": "subscribed", "topics": ESS_TOPICS, "replayed": replayed,
            })
        except Exception:
            pass
    else:
        websocket.app.state.active_connections.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if event_bus:
            await event_bus._remove_websocket(websocket)
        else:
            try:
                websocket.app.state.active_connections.remove(websocket)
            except ValueError:
                pass


async def _brain_ecosystem_tick(app: FastAPI):
    """Agentic OS v2 (Phase 2.0) cognition — gated internally by tick count.

    - memory decay for every NPC (every 20 ticks)
    - a group brainstorm session (every 30 ticks; runs in the background)
    - a self-improvement proposal (every 50 ticks; background)

    Per-agent memory recall, mood, and thought-journaling already happen inside
    AgentOS._think (driven by cluster_tick). This drives the *collective* layers.
    """
    db = getattr(app.state, "db", None)
    agent_os = getattr(app.state, "agent_os", None)
    if not db or not agent_os:
        return
    tick = getattr(app.state, "tick_count", 0)
    if tick <= 0 or tick % 20 != 0:
        return  # cheapest gate: only do anything on 20-tick boundaries

    # `role` is NOT optional here: the group seminar keys each agent's memory-recall hint off it
    # (seminar._run_group_seminar_inner). Selecting only (npc_id, npc_name) made n.get("role")
    # always None, so every agent's hint silently degraded to its own NAME — measured gate
    # inflation (name-prefixed hint passed 78/80 sampled topics for every agent vs a 67/80
    # no-prefix baseline), which is why server/.contributions.json shows all present agents
    # contributing to essentially every round. See the WHY block in seminar.py.
    cursor = await db.execute(
        "SELECT npc_id, npc_name, role FROM dungeon_npcs WHERE status='active'")
    npcs = [dict(r) for r in await cursor.fetchall()]
    if not npcs:
        return

    from agora.agent_os.memory_agent import MemoryAgent
    event_bus = getattr(app.state, "event_bus", None)

    async def _bcast(etype, payload):
        if event_bus:
            try:
                await event_bus.publish("agent:events", etype, payload)
            except Exception:
                pass

    # Memory decay (fast, inline) — every 20 ticks
    for n in npcs:
        try:
            await MemoryAgent(db, n["npc_id"]).decay_all()
        except Exception:
            pass

    # GROUP SEMINAR — all agents work ONE topic together; each contributes only if INSPEXIMUS says it
    # genuinely can, the rest pass (honestly logged). A rapporteur synthesizes one grounded
    # Contribution from the multi-agent exchange. Replaces the old dungeon-fiction pairwise chat
    # that burned ~2.36M tokens for zero captured value.
    if len(npcs) >= 2 and random.random() < 0.5:
        async def _run_seminar():
            try:
                from agora.execution import seminar
                from agora.config import settings
                vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
                res = await asyncio.to_thread(seminar.run_group_seminar, npcs, vault)
                if res.get("role_missing"):
                    # Surface the degradation where the operational log is read; a role-less agent
                    # falls back to a name-keyed recall hint, which inflates the contribution gate.
                    print(f"[Seminar] DEGRADED: no role for {res['role_missing']} - "
                          f"recall hint fell back to the agent name")
                c = res.get("contribution")
                if c and res.get("contributors"):
                    # ECONOMY (Layer 4): every agent whose angle fed a real contribution is paid;
                    # passing (nothing relevant) pays nothing — value-production is the incentive.
                    for cc in res["contributors"]:
                        if cc.get("id"):
                            await db.execute("UPDATE agent_identities SET energy_balance = "
                                             "energy_balance + 3 WHERE agent_id=?", (cc["id"],))
                    await db.commit()
                    print(f"[Seminar] GROUP contribution on '{res['topic']}' by "
                          f"{len(res['contributors'])} agents: {c['claim'][:60]}")
                else:
                    print(f"[Seminar] group round on '{res.get('topic')}' — "
                          f"{len(res.get('contributors', []))} spoke, no contribution")
            except Exception as e:
                print(f"[Seminar] group error: {e}")
        asyncio.create_task(_run_seminar())

    # Group brainstorm REMOVED (was every 30 ticks). It ran 3 UNCONDITIONAL LLM rounds across ALL
    # agents — generate -> build -> vote (~3xN model calls) — then tried to salvage one contribution
    # at the end. Metered at ROI 0.04 (5.2M tok / value ~220): the single biggest token sink, because
    # most of those calls were ungrounded free-association. The INSPEXIMUS-gated GROUP SEMINAR above already
    # produces the grounded group Contribution AND only spends the model on agents whose memory
    # actually surfaces relevant knowledge (the rest pass for free). So the seminar is now the SOLE
    # group-cognition path: no ungated free-association survives. This is a root-cause removal of the
    # waste source, not a cadence throttle.

    # Self-improvement proposal — every 50 ticks (background)
    if tick % 50 == 0:
        async def _run_upgrade():
            try:
                await agent_os._propose_upgrade(random.choice(npcs)["npc_id"], broadcast_fn=_bcast)
            except Exception as e:
                print(f"[BrainEcosystem] upgrade error: {e}")
        asyncio.create_task(_run_upgrade())


async def _economy_tick(app: FastAPI):
    """Production, consumption, and auto-trading for all active agents."""
    eco = app.state.economy
    db = app.state.db

    # Get active agents with their roles
    cursor = await db.execute(
        "SELECT a.agent_id, a.role, a.energy_balance, d.npc_name "
        "FROM agent_identities a "
        "LEFT JOIN dungeon_npcs d ON a.agent_id = d.npc_id "
        "WHERE a.status='active'"
    )
    agents = await cursor.fetchall()

    for agent in agents:
        agent_id = agent["agent_id"]
        role = agent["role"]
        npc_name = agent["npc_name"] or ""
        energy = agent["energy_balance"] or 0

        # Determine config by NPC name first, then by role
        cfg = get_role_config(npc_name)
        if not cfg.get("produces") and not cfg.get("consumes"):
            cfg = get_role_config(role)

        # Skip if agent has no production/consumption (generic agents)
        if not cfg.get("produces") and not cfg.get("consumes"):
            continue

        # 1. PRODUCTION — each tick, agents produce role-specific resources
        for res_id, qty in cfg.get("produces", []):
            if energy >= 5:  # need at least some energy to produce
                await eco.add_to_inventory(agent_id, res_id, qty)
                await db.execute(
                    "UPDATE agent_identities SET energy_balance=MAX(energy_balance-1, 0) WHERE agent_id=?",
                    (agent_id,),
                )

        # 2. CONSUMPTION — agents consume resources they need
        for res_id, qty in cfg.get("consumes", []):
            removed = await eco.remove_from_inventory(agent_id, res_id, qty)
            if not removed:
                # Can't consume → auto-create a buy offer
                open_offers = await eco.get_open_offers(res_id)
                existing_buy = [o for o in open_offers if o["agent_id"] == agent_id and o["offer_type"] == "buy"]
                if not existing_buy:  # don't spam duplicate offers
                    # Price: 80% of market → competitive buy
                    price = await eco.get_market_price(res_id)
                    await eco.create_offer(agent_id, "buy", res_id, qty * 2, round(price * 0.8, 2))

        # 3. AUTO-SELL — surplus resources → create sell offers
        surplus = cfg.get("surplus_threshold", 3.0)
        deficit = cfg.get("deficit_threshold", 1.0)

        # Check inventory for resources this role produces
        inv = await eco.get_agent_inventory(agent_id)
        for item in inv:
            res_id = item["resource_id"]
            qty = item["quantity"]

            # Is this a resource the role produces? (resolve config ids → UUIDs)
            produces_ids = [await eco._resolve_rid(p[0]) for p in cfg.get("produces", [])]
            if res_id in produces_ids and qty > surplus:
                # Sell surplus
                sell_qty = qty - deficit
                if sell_qty > 0.5:
                    open_offers = await eco.get_open_offers(res_id)
                    existing_sell = [o for o in open_offers if o["agent_id"] == agent_id and o["offer_type"] == "sell"]
                    if not existing_sell:
                        price = await eco.get_market_price(res_id)
                        result = await eco.create_offer(agent_id, "sell", res_id, sell_qty, round(price * 1.1, 2))
                        if result.get("status") == "filled":
                            await app.state.stigmergy.write_trace(
                                agent_id=agent_id,
                                task_type="trade",
                                result=f"[{npc_name or role}] Sold {sell_qty:.1f}x resource #{res_id} for {result.get('total_energy', 0)} energy",
                                trust_delta=0.05,
                            )



async def tick_loop(app: FastAPI):
    """Main loop: agent interactions every N seconds (simulated thoughts when LLM disabled)."""
    task_types = ["research", "writing", "review", "analysis", "exploration"]

    while True:
        await asyncio.sleep(settings.tick_interval)
        try:
            app.state.tick_count += 1
            db = app.state.db
            trust_engine = app.state.trust
            stigmergy = app.state.stigmergy

            # ── 1. DEATH DETECTION (before replenish, global) ──
            try:
                life_events = await app.state.agent_lifecycle.tick(app)
                for ev in life_events:
                    await broadcast(app, ev["type"], ev["payload"])
            except Exception as e:
                print(f"[Lifecycle] Tick error: {e}")

            # ── 2. REFRESH active agents after lifecycle changes ──
            cursor = await db.execute(
                "SELECT agent_id, role, trust_score, energy_balance, genome "
                "FROM agent_identities WHERE status='active'"
            )
            agents = await cursor.fetchall()

            if len(agents) < 2:
                await broadcast(app, "heartbeat", {
                    "tick": app.state.tick_count, "agents": len(agents),
                    "message": "Not enough agents for interaction"
                })
                await db.commit()
                continue

            # ── 2.5. LIFECYCLE HOOKS — pre-tick byzantine validation ──
            npc_ids = []
            try:
                hooks = app.state.lifecycle_hooks
                all_active_npcs = await app.state.state_store.get_all_active_npcs()
                npc_ids = [n["npc_id"] for n in all_active_npcs]
                pre_violations = await hooks.pre_tick(npc_ids)
                for v in pre_violations:
                    await broadcast(app, "byzantine_violation", {
                        "phase": "pre_tick",
                        "type": v["type"],
                        "detail": v["detail"],
                    })
            except Exception as e:
                print(f"[LifecycleHooks] Pre-tick error: {e}")

            # ── 3. CONTROLLER — room cluster dispatch ──
            # Each room = independent cluster dispatched by Controller
            try:
                controller_events = await app.state.controller.tick()
                for ev in controller_events:
                    await broadcast(app, ev["type"], ev["payload"])
            except Exception as e:
                print(f"[Controller] Error: {e}")
                import traceback
                traceback.print_exc()

            # ── 3.5. LIFECYCLE HOOKS — post-tick byzantine validation ──
            try:
                hooks = app.state.lifecycle_hooks
                post_violations = await hooks.post_tick(npc_ids)
                for v in post_violations:
                    await broadcast(app, "byzantine_violation", {
                        "phase": "post_tick",
                        "type": v["type"],
                        "severity": v.get("severity", "warning"),
                        "detail": v["detail"],
                    })

                # Periodic deep checks (every 10 ticks)
                if app.state.tick_count % 10 == 0:
                    for nid in npc_ids:
                        skill_v = await hooks.validate_skill_limits(nid)
                        if skill_v:
                            await broadcast(app, "byzantine_violation", {
                                "phase": "deep_check",
                                "type": skill_v["type"],
                                "severity": skill_v.get("severity", "warning"),
                                "detail": skill_v["detail"],
                            })

                    dup_violations = await hooks.detect_duplicate_help_requests()
                    for v in dup_violations:
                        await broadcast(app, "byzantine_violation", {
                            "phase": "deep_check",
                            "type": v["type"],
                            "severity": v.get("severity", "warning"),
                            "detail": v["detail"],
                        })
            except Exception as e:
                print(f"[LifecycleHooks] Post-tick error: {e}")

            # ── 4. PROCESS THOUGHTS — REMOVED. This block was the old abstract researcher/writer/critic
            # agents' roleplay cognition: it sampled agent_identities, called agent_think() (the value-0
            # 'agent-think' organ) or canned SIMULATED_THOUGHTS, and fed _process_agent_thought. The old
            # agents are purged; the dungeon characters' real cognition (AgentOS._think) and the gated
            # seminar are the cognition paths now. Nothing here is replaced — the tick still runs
            # lifecycle/controller/byzantine hooks above and the v3 emotion/dream/diary layer below.
            await db.commit()

            # ── Agentic OS v3 — emócie, vzťahy, sny, denníky, kultúra, konflikty ──
            try:
                v3_tick = app.state.tick_count

                # Decay emotions every tick
                if app.state.emotion_engine:
                    await app.state.emotion_engine.decay_all()

                # Get all active NPCs for v3 processing
                cursor_npcs = await db.execute(
                    "SELECT d.npc_id, d.npc_name, d.role, b.current_goal, b.state_of_mind, "
                    "e.current as emotion, e.mood "
                    "FROM dungeon_npcs d "
                    "LEFT JOIN agent_brain b ON b.npc_id = d.npc_id "
                    "LEFT JOIN agent_emotions e ON e.npc_id = d.npc_id "
                    "WHERE d.status='active'"
                )
                all_npcs = await cursor_npcs.fetchall()

                for npc in all_npcs:
                    npc = dict(npc)  # sqlite3.Row has no .get()
                    npc_id = npc["npc_id"]
                    name = npc["npc_name"]
                    role = npc["role"]
                    goal = npc.get("current_goal", "")
                    emotion = npc.get("emotion", "neutral")
                    mood = npc.get("mood", 0.7)

                    # Random vault insight broadcast (every 5 ticks)
                    if v3_tick % 5 == 0 and v3_tick > 0:
                        vault_reader = getattr(app.state, "vault_reader", None)
                        if vault_reader:
                            try:
                                insight = await vault_reader.get_random_insight()
                                if insight:
                                    await broadcast(app, "vault_insight", {
                                        "agent": name,
                                        "book": insight.get("book", ""),
                                        "text": insight.get("text", "")[:150],
                                    })
                            except Exception:
                                pass

                    # Dreams (every 15 ticks)
                    if v3_tick > 0 and v3_tick % 15 == 0 and app.state.dream_engine:
                        # Get recent memories
                        mem_cursor = await db.execute(
                            "SELECT content FROM agent_memories WHERE npc_id=? "
                            "ORDER BY created_at DESC LIMIT 5",
                            (npc_id,),
                        )
                        recent_mems = [dict(r) for r in await mem_cursor.fetchall()]
                        await app.state.dream_engine.generate_dream(
                            npc_id, name, role, recent_mems, mood,
                            broadcast_fn=lambda t, p: broadcast(app, t, p),
                        )

                    # Inspirations (every 30 ticks)
                    if v3_tick > 0 and v3_tick % 30 == 0 and app.state.dream_engine:
                        vault_reader = getattr(app.state, "vault_reader", None)
                        await app.state.dream_engine.generate_inspiration(
                            npc_id, name, role, vault_reader,
                            broadcast_fn=lambda t, p: broadcast(app, t, p),
                        )

                    # Diary entries (every 20 ticks)
                    if v3_tick > 0 and v3_tick % 20 == 0 and app.state.diary_engine:
                        mem_cursor = await db.execute(
                            "SELECT content FROM agent_memories WHERE npc_id=? "
                            "ORDER BY created_at DESC LIMIT 3",
                            (npc_id,),
                        )
                        recent_mems = [dict(r) for r in await mem_cursor.fetchall()]
                        await app.state.diary_engine.write_entry(
                            npc_id, name, role, goal, mood, emotion,
                            recent_mems, v3_tick,
                            vault_reader=getattr(app.state, "vault_reader", None),
                            broadcast_fn=lambda t, p: broadcast(app, t, p),
                        )

                # Conflicts (every 3 ticks, 5% chance each)
                if v3_tick > 0 and v3_tick % 3 == 0 and app.state.conflict_engine:
                    for npc in all_npcs:
                        npc = dict(npc)  # sqlite3.Row has no .get()
                        nearby_ids_list = []
                        if app.state.agent_os:
                            try:
                                nearby = await app.state.agent_os._get_nearby_npcs(npc["npc_id"])
                                nearby_ids_list = [n["npc_id"] for n in nearby]
                            except Exception:
                                pass
                        await app.state.conflict_engine.check_for_conflicts(
                            npc["npc_id"], npc["npc_name"],
                            npc.get("current_goal", ""), nearby_ids_list,
                            broadcast_fn=lambda t, p: broadcast(app, t, p),
                        )
                    # Try to resolve active conflicts
                    cursor_conflicts = await db.execute(
                        "SELECT id FROM agent_conflicts WHERE status IN ('active', 'mediated')"
                    )
                    active_conflicts = await cursor_conflicts.fetchall()
                    for c in active_conflicts:
                        await app.state.conflict_engine.attempt_resolution(
                            c["id"],
                            broadcast_fn=lambda t, p: broadcast(app, t, p),
                        )

                # Culture spread (every 8 ticks)
                if v3_tick > 0 and v3_tick % 8 == 0 and app.state.culture_engine:
                    await app.state.culture_engine.spread(
                        "system",
                        broadcast_fn=lambda t, p: broadcast(app, t, p),
                    )

                # Update lifecycle tracking
                if app.state.relationship_web:
                    pass  # relationships are updated via record_interaction

            except Exception as e:
                print(f"[v3 Tick] Error: {e}")
                import traceback
                traceback.print_exc()

            # ── 6. CSD monitoring (metrics + drift detection) ──
            try:
                monitor = app.state.csd_monitor
                for agent in agents:
                    monitor.push_metric("trust_score", agent["trust_score"],
                                        labels={"agent": agent["agent_id"][:8], "role": agent["role"]})
                    monitor.push_metric("energy_level", agent["energy_balance"],
                                        labels={"agent": agent["agent_id"][:8], "role": agent["role"]})
                monitor.push_metric("active_agents", len(agents))
                if app.state.tick_count % 5 == 0:
                    alerts = monitor.check_all()
                    for alert in alerts:
                        await broadcast(app, "csd_alert", {
                            "metric": alert.metric_name,
                            "severity": alert.severity.value,
                            "current": round(alert.current_value, 2),
                            "baseline_mean": round(alert.baseline_mean, 2),
                            "z_score": alert.deviation_z,
                            "message": alert.message,
                        })
            except Exception as e:
                print(f"[CSD] Error: {e}")

            # ── 7. Epoch lifecycle ──
            try:
                epoch_events = await app.state.epoch_engine.tick(app)
                for ev in epoch_events:
                    await broadcast(app, ev["type"], ev["payload"])
            except Exception as e:
                print(f"[Epoch] Error: {e}")

            # ── 8. Task pipeline tick ──
            try:
                task_events = await app.state.task_executor.tick(app)
                for ev in task_events:
                    await broadcast(app, ev["type"], ev["payload"])
            except Exception as e:
                print(f"[Tasks] Tick error: {e}")
                import traceback
                traceback.print_exc()

            # ── 9. Economy tick (production, consumption, auto-trade) ──
            if app.state.tick_count % 2 == 0:  # every 2 ticks
                try:
                    await _economy_tick(app)
                except Exception as e:
                    print(f"[Economy] Tick error: {e}")
                    import traceback
                    traceback.print_exc()

            # ── 10. Stigmergic economy signals (every 10 ticks) ──
            if app.state.tick_count > 0 and app.state.tick_count % 10 == 0:
                try:
                    resources = await app.state.economy.get_all_resources()
                    price_signals = []
                    for r in resources:
                        price = await app.state.economy.get_market_price(r["id"])
                        price_signals.append(f"{r['name']}={price}")
                    await app.state.stigmergy.write_trace(
                        agent_id="system",
                        task_type="market_prices",
                        result=" | ".join(price_signals),
                        trust_delta=0.0,
                    )
                    await app.state.stigmergy.write_trace(
                        agent_id="system",
                        task_type="market_activity",
                        result=f"Active agents: {len(agents)}. Total energy: {sum(a['energy_balance'] for a in agents):.0f}",
                        trust_delta=0.0,
                    )
                except Exception as e:
                    print(f"[Stigmergy] Market signal error: {e}")

            # ── 11. CORPORATION WORKER TICK (every 18 ticks ~ 90s) ──
            if app.state.tick_count > 0 and app.state.tick_count % 18 == 0:
                try:
                    worker = getattr(app.state, "agent_worker", None)
                    if worker is None:
                        qe = getattr(app.state, "quest_engine", None)
                        if qe:
                            from agora.dungeon_os.agent_worker import CorporationWorker
                            db = app.state.db
                            config = {
                                "quest_engine": qe,
                                "os_state": getattr(app.state, "os_state", None),
                                "log_dir": "/tmp/hermes-logs",
                                "vault_path": os.path.expanduser("~/Obsidian Vault"),
                                "telegram_chat_id": os.getenv("HERMES_TELEGRAM_CHAT_ID"),
                                "telegram_bot_token": os.getenv("HERMES_TELEGRAM_BOT_TOKEN"),
                            }
                            worker = CorporationWorker(qe, db, config)
                            app.state.agent_worker = worker
                    # Run the corp tick in the BACKGROUND — its literature fetches + LLM research/
                    # eval take minutes, and awaiting it here throttled the whole brain tick loop
                    # (the rest of the OS crawled). A guard prevents overlapping corp ticks.
                    if worker and not getattr(app.state, "_corp_running", False):
                        app.state._corp_running = True
                        async def _run_corp(_w, _tc):
                            try:
                                r = await _w.tick(tick_count=_tc)
                                print(f"[Corporation] Tick #{r['tick']} done in {r['duration_seconds']}s ({len(r['results'])} steps)")
                            except Exception as _e:
                                print(f"[Corporation] Tick error: {_e}")
                            finally:
                                app.state._corp_running = False
                        asyncio.create_task(_run_corp(worker, app.state.tick_count))
                except Exception as e:
                    print(f"[Corporation] Tick error: {e}")
                    import traceback
                    traceback.print_exc()

            # ── 12. Checkpointing (ESS 1.2) — snapshot trust/tft state ──
            from agora.coordination.checkpointer import CHECKPOINT_INTERVAL
            if (app.state.tick_count > 0
                    and app.state.tick_count % CHECKPOINT_INTERVAL == 0
                    and getattr(app.state, "checkpointer", None)):
                try:
                    cp_trust = await app.state.checkpointer.checkpoint_all("trust")
                    cp_tft = await app.state.checkpointer.checkpoint_all("tft")
                    if cp_trust or cp_tft:
                        print(f"[Checkpoint] tick {app.state.tick_count}: "
                              f"{len(cp_trust)} trust, {len(cp_tft)} tft snapshots")
                except Exception as e:
                    print(f"[Checkpoint] Tick error: {e}")

            # ── 13. Agentic OS v2 (Phase 2.0) — brain ecosystem cognition ──
            try:
                await _brain_ecosystem_tick(app)
            except Exception as e:
                print(f"[BrainEcosystem] Tick error: {e}")

            if app.state.tick_count % 5 == 0:
                best_agents = {}
                for tt in task_types:
                    best = await stigmergy.best_agent(tt, min_traces=2)
                    if best:
                        best_agents[tt] = best
                await broadcast(app, "stigmergy_insight", {
                    "tick": app.state.tick_count, "best_agents": best_agents,
                })

            total_energy = sum(a["energy_balance"] for a in agents)
            await broadcast(app, "heartbeat", {
                "tick": app.state.tick_count, "agents": len(agents),
                "total_energy": total_energy,
            })
        except Exception as e:
            print(f"[Tick] Error at tick {app.state.tick_count}: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(1)
