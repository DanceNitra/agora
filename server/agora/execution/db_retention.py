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

# Operational-log tables pruned to a rolling window: (table, time_column, extra_where).
# Knowledge tables are deliberately absent — they are never pruned.
_PRUNE = [
    ("event_store", "occurred_at", ""),
    ("agent_help_requests", "created_at", ""),
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
    # artifacts: prune only ephemeral game-social/movement types; keep research/writing/analysis
    ("artifacts", "created_at", " AND artifact_type IN ('interaction','exploration')"),
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
        for t, col, extra in _PRUNE:
            delete(t, f"{col} < ?{extra}", cutoff)
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
