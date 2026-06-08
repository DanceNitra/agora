"""Conflict Engine — disputes, mediation, and resolution between agents.

Conflicts arise from resource disputes, goal clashes, personality differences,
and trust violations. The system supports:
  1. Direct resolution (agents talk it out)
  2. Mediation (third agent intervenes)
  3. Vote (all agents decide)
  4. Escalation (system steps in)
"""
import json
import random
from datetime import datetime


class ConflictEngine:
    """Manages conflicts between agents."""

    def __init__(self, db):
        self.db = db

    # ── Create a conflict ───────────────────────

    async def create(self, agent_a_id: str, agent_b_id: str,
                      issue: str, conflict_type: str = "dispute",
                      severity: int = 5, broadcast_fn=None) -> str | None:
        """Create a new conflict between two agents.

        Returns conflict_id, or None if conflict already exists.
        """
        # Check if active conflict already exists
        cursor = await self.db.execute(
            "SELECT COUNT(*) as c FROM agent_conflicts "
            "WHERE ((agent_a_id=? AND agent_b_id=?) OR (agent_a_id=? AND agent_b_id=?)) "
            "AND status IN ('active', 'mediated')",
            (agent_a_id, agent_b_id, agent_b_id, agent_a_id),
        )
        row = await cursor.fetchone()
        if row and row["c"] > 0:
            return None  # already in conflict

        await self.db.execute(
            "INSERT INTO agent_conflicts (agent_a_id, agent_b_id, issue, "
            "conflict_type, severity) VALUES (?, ?, ?, ?, ?)",
            (agent_a_id, agent_b_id, issue[:200], conflict_type,
             max(1, min(10, severity))),
        )
        await self.db.commit()
        cursor = await self.db.execute("SELECT last_insert_rowid()")
        row = await cursor.fetchone()
        conflict_id = str(row[0]) if row else ""

        if broadcast_fn:
            await broadcast_fn("conflict_created", {
                "agent_a": agent_a_id[:8],
                "agent_b": agent_b_id[:8],
                "issue": issue[:80],
                "type": conflict_type,
                "severity": severity,
            })

        return conflict_id

    # ── Check for potential conflicts (called in tick loop) ──

    async def check_for_conflicts(self, npc_id: str, name: str, goal: str,
                                   nearby_ids: list[str], broadcast_fn=None) -> list[str]:
        """Check if this agent is in conflict with nearby agents.

        Returns list of conflict_ids created (usually 0 or 1).
        """
        # 5% chance per check
        if random.random() > 0.05:
            return []

        if not nearby_ids:
            return []

        created = []
        for other_id in nearby_ids:
            # Random personality clash or goal conflict
            if random.random() < 0.3:
                conflict_types = {
                    "resource_conflict": f"{name} thinks {other_id[:8]} took something that belongs to them",
                    "goal_clash": f"{name}'s goal '{goal[:30]}' conflicts with {other_id[:8]}'s current objective",
                    "personality_clash": f"{name} finds {other_id[:8]}'s behavior difficult to tolerate",
                }
                ctype = random.choice(list(conflict_types.keys()))
                issue = conflict_types[ctype]

                cid = await self.create(
                    npc_id, other_id, issue, ctype,
                    severity=random.randint(3, 7),
                    broadcast_fn=broadcast_fn,
                )
                if cid:
                    created.append(cid)
                    break  # one conflict per tick per agent

        return created

    # ── Attempt resolution ─────────────────────

    async def attempt_resolution(self, conflict_id: int, broadcast_fn=None) -> dict | None:
        """Try to resolve a conflict. Returns resolution dict if successful."""
        cursor = await self.db.execute(
            "SELECT * FROM agent_conflicts WHERE id=?", (conflict_id,)
        )
        conflict = await cursor.fetchone()
        if not conflict:
            return None

        # 40% chance of spontaneous resolution
        if random.random() > 0.4:
            return None

        resolution = random.choice([
            "The agents talked it through and reached an understanding.",
            "They agreed to disagree and focus on their shared goals.",
            "One agent apologized. The other accepted.",
            "They realized the conflict was based on a misunderstanding.",
            "A third agent helped them see each other's perspective.",
        ])

        await self.db.execute(
            "UPDATE agent_conflicts SET status='resolved', resolution=?, "
            "resolved_at=datetime('now') WHERE id=?",
            (resolution[:300], conflict_id),
        )
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("conflict_resolved", {
                "conflict_id": conflict_id,
                "resolution": resolution[:100],
            })

        return {"status": "resolved", "resolution": resolution}

    # ── Find a mediator (highest respect agent) ─

    async def find_mediator(self, agent_a_id: str, agent_b_id: str) -> str | None:
        """Find the best mediator for a conflict between two agents.

        The mediator is the agent with highest combined respect from both parties.
        """
        # Get all agents except the two in conflict
        cursor = await self.db.execute(
            "SELECT npc_id FROM dungeon_npcs WHERE status='active' "
            "AND npc_id NOT IN (?, ?)",
            (agent_a_id, agent_b_id),
        )
        potential = [r["npc_id"] for r in await cursor.fetchall()]
        if not potential:
            return None

        best_mediator = None
        best_score = -1

        for mediator_id in potential:
            # Get respect scores from both parties toward this mediator
            score = 0
            for party in (agent_a_id, agent_b_id):
                a_id, b_id = sorted([party, mediator_id])
                cursor = await self.db.execute(
                    "SELECT respect FROM agent_relationships WHERE agent_a_id=? AND agent_b_id=?",
                    (a_id, b_id),
                )
                row = await cursor.fetchone()
                if row:
                    score += row["respect"]
            if score > best_score:
                best_score = score
                best_mediator = mediator_id

        return best_mediator

    # ── Assign a mediator ───────────────────────

    async def assign_mediator(self, conflict_id: int, broadcast_fn=None) -> str | None:
        """Assign a mediator to a conflict."""
        cursor = await self.db.execute(
            "SELECT * FROM agent_conflicts WHERE id=? AND status='active'",
            (conflict_id,),
        )
        conflict = await cursor.fetchone()
        if not conflict:
            return None

        mediator_id = await self.find_mediator(conflict["agent_a_id"], conflict["agent_b_id"])
        if not mediator_id:
            return None

        await self.db.execute(
            "UPDATE agent_conflicts SET status='mediated', mediator_id=? WHERE id=?",
            (mediator_id, conflict_id),
        )
        await self.db.commit()

        cursor = await self.db.execute(
            "SELECT npc_name FROM dungeon_npcs WHERE npc_id=?", (mediator_id,)
        )
        mediator_name_row = await cursor.fetchone()
        mediator_name = mediator_name_row["npc_name"] if mediator_name_row else "unknown"

        if broadcast_fn:
            await broadcast_fn("conflict_mediation", {
                "conflict_id": conflict_id,
                "mediator": mediator_name,
            })

        return mediator_name

    # ── Get active conflicts for an agent ───────

    async def get_active(self, npc_id: str) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT c.*, a1.npc_name as name_a, a2.npc_name as name_b "
            "FROM agent_conflicts c "
            "JOIN dungeon_npcs a1 ON a1.npc_id = c.agent_a_id "
            "JOIN dungeon_npcs a2 ON a2.npc_id = c.agent_b_id "
            "WHERE (c.agent_a_id=? OR c.agent_b_id=?) AND c.status IN ('active', 'mediated') "
            "ORDER BY c.severity DESC",
            (npc_id, npc_id),
        )
        return [dict(r) for r in await cursor.fetchall()]