"""
Epoch Engine — runs inside the tick loop to manage epoch lifecycle.

Phases (within each epoch):
  - FORK (10%):   Spawn child agents from survivors
  - EVOLVE (60%): Normal agent operation (nothing extra needed)
  - CULL (20%):   Remove under-performing agents (trust < 0.2)
  - RESET (10%):  Reset economy, archive epoch data

Uses DB-backed epoch records from the schema.
"""
import json
import time
from typing import Any, Optional

EPOCH_TICK_DURATION = 60  # one epoch = 60 ticks
CULL_TRUST_THRESHOLD = 0.18


class EpochEngine:
    """Lightweight epoch manager that runs inside the tick loop."""

    def __init__(self, db):
        self.db = db
        self._current_epoch: int = 0
        self._tick_in_epoch: int = 0

    async def tick(self, app) -> list[dict]:
        """Run one epoch tick. Returns events to broadcast."""
        events = []
        db = self.db
        self._tick_in_epoch += 1

        # Check if we need to advance epoch
        if self._tick_in_epoch >= EPOCH_TICK_DURATION:
            await self._finalize_epoch(db, app)
            self._current_epoch += 1
            self._tick_in_epoch = 0
            await self._start_epoch(db, app)
            events.append({
                "type": "epoch_advanced",
                "payload": {"epoch": self._current_epoch, "tick": self._tick_in_epoch},
            })

        # Determine current phase
        phase = self._get_phase()

        # CULL phase: remove low-trust agents
        if phase == "cull":
            culled = await self._cull_agents(db, app)
            for c in culled:
                events.append({"type": "agent_culled", "payload": c})

        # FORK phase: spawn child agents from survivors
        if phase == "fork":
            # Only spawn on the first tick of FORK phase
            if self._tick_in_epoch % EPOCH_TICK_DURATION < int(EPOCH_TICK_DURATION * 0.1):
                forked = await self._fork_agents(db, app)
                for f in forked:
                    events.append({"type": "agent_forked", "payload": f})

        return events

    def _get_phase(self) -> str:
        """Determine current epoch phase based on tick position."""
        pct = self._tick_in_epoch / EPOCH_TICK_DURATION
        if pct < 0.10:
            return "fork"
        elif pct < 0.70:
            return "evolve"
        elif pct < 0.90:
            return "cull"
        else:
            return "reset"

    async def _start_epoch(self, db, app):
        """Initialize a new epoch in the DB."""
        await db.execute(
            "INSERT INTO epochs (epoch_number, status, summary) VALUES (?, 'active', ?)",
            (self._current_epoch, json.dumps({"phase": "fork", "start_tick": self._tick_in_epoch})),
        )
        await db.commit()

        try:
            await self._broadcast(app, "epoch_start", {
                "epoch": self._current_epoch,
                "phase": "fork",
            })
        except Exception:
            pass

    async def _finalize_epoch(self, db, app):
        """Finalize the current epoch."""
        cursor = await db.execute(
            "SELECT COUNT(*) as c FROM agent_identities WHERE status='active'"
        )
        active_count = (await cursor.fetchone())["c"]
        cursor = await db.execute("SELECT COUNT(*) as c FROM tasks WHERE status='completed'")
        tasks_done = (await cursor.fetchone())["c"]
        cursor = await db.execute("SELECT COUNT(*) as c FROM artifacts")
        artifact_count = (await cursor.fetchone())["c"]

        summary = json.dumps({
            "active_agents": active_count,
            "tasks_completed": tasks_done,
            "artifacts_created": artifact_count,
            "phase": "reset",
        })
        await db.execute(
            "UPDATE epochs SET status='completed', ended_at=datetime('now'), summary=? "
            "WHERE epoch_number=? AND status='active'",
            (summary, self._current_epoch),
        )
        await db.commit()

        # RESET phase: archive completed tasks
        await db.execute(
            "UPDATE tasks SET metadata=json_set(COALESCE(metadata,'{}'), '$.archived_in_epoch', ?) "
            "WHERE status='completed'",
            (self._current_epoch,),
        )
        await db.commit()

        try:
            await self._broadcast(app, "epoch_end", {
                "epoch": self._current_epoch,
                "active_agents": active_count,
                "tasks_completed": tasks_done,
                "artifacts_created": artifact_count,
            })
        except Exception:
            pass

    async def _cull_agents(self, db, app) -> list[dict]:
        """Cull agents with trust below threshold."""
        culled = []
        # Only cull once per epoch (first cull tick)
        if self._tick_in_epoch != int(EPOCH_TICK_DURATION * 0.70) + 1:
            return culled

        cursor = await db.execute(
            "SELECT agent_id, role, trust_score, energy_balance, generation "
            "FROM agent_identities WHERE status='active' AND trust_score < ?",
            (CULL_TRUST_THRESHOLD,),
        )
        doomed = await cursor.fetchall()

        for agent in doomed:
            await db.execute(
                "UPDATE agent_identities SET status='culled', updated_at=datetime('now') WHERE agent_id=?",
                (agent["agent_id"],),
            )
            culled.append({
                "agent_id": agent["agent_id"][:8],
                "role": agent["role"],
                "trust_score": round(agent["trust_score"], 3),
                "generation": agent["generation"],
            })

        if culled:
            await db.commit()
        return culled

    async def _fork_agents(self, db, app) -> list[dict]:
        """Spawn child agents if under capacity."""
        forked = []
        # Only fork once per epoch
        if self._tick_in_epoch != 1:
            return forked

        cursor = await db.execute(
            "SELECT COUNT(*) as c FROM agent_identities WHERE status='active'"
        )
        active_count = (await cursor.fetchone())["c"]

        from agora.lifecycle.genome_bridge import GenomeBridge

        # Fork if under 10 active agents
        if active_count >= 10:
            return forked

        # Pick best parent (highest trust)
        cursor = await db.execute(
            "SELECT agent_id, role, genome, trust_score FROM agent_identities "
            "WHERE status='active' ORDER BY trust_score DESC LIMIT 1"
        )
        parent = await cursor.fetchone()
        if not parent:
            return forked

        import uuid
        parent_genome = json.loads(parent["genome"] or "{}")
        child_genome = GenomeBridge.mutate_db_genome(parent_genome, parent["role"], parent.get("generation", 0) + 1)
        child_id = str(uuid.uuid4())
        child_role = parent["role"]

        await db.execute(
            "INSERT INTO agent_identities (agent_id, public_key, generation, genome, "
            "trust_score, energy_balance, role, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'active')",
            (child_id, f"fork_{child_id[:8]}", parent.get("generation", 0) + 1,
             json.dumps(child_genome), 0.35, 60.0, child_role),
        )
        await db.commit()

        forked.append({
            "agent_id": child_id[:8],
            "role": child_role,
            "parent_id": parent["agent_id"][:8],
            "generation": parent.get("generation", 0) + 1,
            "mutations": child_genome.get("_mutations_applied", 0),
        })

        return forked

    async def _broadcast(self, app, event_type: str, payload: dict):
        """Broadcast to all WebSocket connections."""
        try:
            import json as _json
            from datetime import datetime as _dt
            event = {"type": event_type, "payload": payload, "timestamp": _dt.utcnow().isoformat()}
            for ws in list(getattr(app.state, "active_connections", [])):
                try:
                    await ws.send_json(event)
                except Exception:
                    pass
        except Exception:
            pass

    async def get_stats(self) -> dict:
        """Return current epoch state."""
        return {
            "current_epoch": self._current_epoch,
            "tick_in_epoch": self._tick_in_epoch,
            "phase": self._get_phase(),
            "phase_progress": f"{self._tick_in_epoch / EPOCH_TICK_DURATION * 100:.0f}%",
            "ticks_per_epoch": EPOCH_TICK_DURATION,
        }
