"""
DB retention — keep the brain's operational exhaust bounded so the dungeon never lags again.

The agora.db grows from high-velocity OPERATIONAL logs (consensus violations, event-sourcing
records, agent chatter, trades, pheromone trails) — not from knowledge. Left unbounded it hit
83 MB / 130k+ log rows and full-table scans started lagging the dungeon. This prunes the log
tables to a rolling window and reclaims the space, while NEVER touching the knowledge tables
(collective_knowledge, research_findings, agent_memories, identities, quests, trust).

Run periodically from main.py's lifespan. Read-then-delete with a busy timeout; safe alongside
the live writers under WAL.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

_DB = Path(__file__).resolve().parents[2] / "agora.db"

# Operational-log tables pruned to a rolling window: (table, time_column, extra_where[, days_override]).
# Knowledge tables are deliberately absent — they are never pruned. A 4th element overrides the default
# window for high-velocity tables (agent_help_requests can fire 1000s/day even with the seek-help cooldown).
_PRUNE = [
    ("event_store", "occurred_at", ""),
    ("agent_help_requests", "created_at", "", 2),   # tight window: pure operational churn, very high volume
    ("trade_history", "created_at", ""),
    ("trade_offers", "created_at", ""),
    ("stigmergy_traces", "created_at", ""),
    ("interaction_log", "created_at", ""),
    ("agent_thoughts", "created_at", ""),
    ("agent_dreams", "created_at", ""),
    ("agent_diaries", "mood_at_time", ""),
    ("agent_conversations", "created_at", ""),
    ("agent_brainstorm_ideas", "created_at", ""),
    ("agent_brainstorm_sessions", "created_at", ""),
    ("agent_conflicts", "created_at", ""),
    ("checkpoints", "created_at", ""),
    ("state_snapshots", "created_at", ""),
    # artifacts: prune ephemeral game-social/movement types, AND anything the auto-task generator
    # minted. Keeping by TYPE alone was unsound: that generator stamps its output 'research',
    # 'writing' and 'analysis', so the clause meant to preserve research preserved 42,866 fantasy
    # artifacts, among them "Decode the rune tablet" 4,227 times. `storage_path` is the honest
    # discriminator because only `task_executor._complete_task` writes that prefix.
    ("artifacts", "created_at",
     " AND (artifact_type IN ('interaction','exploration') OR storage_path LIKE 'tasks/task-%')"),
    # tasks + events were never pruned at all, so both held every row back to 2026-06-12: 71,733
    # task rows from 17 distinct fantasy descriptions (25.6 MB) and 71,444 event rows (17.5 MB).
    ("tasks", "created_at", ""),
    ("events", "occurred_at", ""),
]


def prune(days: int = 14, byzantine_days: int = 2, vacuum: bool = False) -> dict:
    """Delete operational-log rows older than the window; byzantine_violations on a tighter window
    (they are pure consensus noise). Optionally VACUUM. Returns per-bucket counts."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    bcut = (datetime.utcnow() - timedelta(days=byzantine_days)).strftime("%Y-%m-%d")
    out: dict[str, int] = {}
    try:
        con = sqlite3.connect(_DB.as_posix(), timeout=20)
        con.execute("PRAGMA busy_timeout=20000")
        c = con.cursor()

        def delete(label, where, *a):
            try:
                tbl = "events" if label == "byzantine_violation" else label
                n = c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {where}", a).fetchone()[0]
                c.execute(f"DELETE FROM {tbl} WHERE {where}", a)
                out[label] = int(n)
            except Exception as e:
                out[label] = -1
                print(f"[Retention] {label} skipped: {e}")

        delete("byzantine_violation",
               "event_type='byzantine_violation' AND occurred_at < ?", bcut)
        for row in _PRUNE:
            t, col, extra = row[0], row[1], row[2]
            days_override = row[3] if len(row) > 3 else None
            cut = ((datetime.utcnow() - timedelta(days=days_override)).strftime("%Y-%m-%d")
                   if days_override is not None else cutoff)
            delete(t, f"{col} < ?{extra}", cut)
        con.commit()
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.commit()
        if vacuum:
            t0 = time.time()
            con.isolation_level = None
            con.execute("VACUUM")
            out["_vacuum_seconds"] = round(time.time() - t0, 1)
        con.close()
    except Exception as e:
        print(f"[Retention] prune failed: {e}")
        out["_error"] = str(e)[:120]
    out["_total_deleted"] = sum(v for k, v in out.items() if isinstance(v, int) and v > 0
                                and not k.startswith("_"))
    return out
