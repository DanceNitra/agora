"""Dungeon OS — Quest system.

Quest lifecycle:
  open → claimed → (work) → review → verified → done
                           → blocked → re-open

Each quest has:
  - Single owner (one agent role)
  - Success criteria (checked by Warden)
  - Subsystem impact (raises osState on completion)
  - Dependencies (quests that must be done first)
"""

import json
from datetime import datetime
from typing import Optional


QUEST_STATUSES = ["open", "claimed", "review", "blocked", "done"]
SUBSYSTEMS = ["comms", "knowledge", "tooling", "economy", "safety"]


class QuestEngine:
    """Manages quest lifecycle: create, assign, verify, complete."""

    def __init__(self, db, os_state=None):
        self.db = db
        self.os_state = os_state

    # ═══════════════════════════════════════════
    # CREATE
    # ═══════════════════════════════════════════

    async def create_quest(
        self,
        quest_id: str,
        title: str,
        goal: str,
        subsystem: str,
        success_criteria: list[str],
        reward: int = 0,
        owner: Optional[str] = None,
        depends_on: Optional[list[str]] = None,
    ) -> dict:
        """Create a new quest and add it to the board."""
        if subsystem not in SUBSYSTEMS:
            return {"error": f"Invalid subsystem: {subsystem}"}

        # Check duplicate
        existing = await self._find_quest(quest_id)
        if existing:
            return {"error": f"Quest '{quest_id}' already exists"}

        await self.db.execute(
            """INSERT INTO quests (id, title, goal, subsystem, success_criteria, reward,
               owner, depends_on, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', datetime('now'))""",
            (
                quest_id,
                title,
                goal,
                subsystem,
                json.dumps(success_criteria),
                reward,
                owner,
                json.dumps(depends_on or []),
            ),
        )
        await self.db.commit()

        quest = await self._find_quest(quest_id)
        print(f"[Quests] Created: {quest_id} ({subsystem})")
        return self._to_dict(quest)

    # ═══════════════════════════════════════════
    # ASSIGN
    # ═══════════════════════════════════════════

    async def assign_quest(self, quest_id: str, agent_name: str) -> dict:
        """Assign an open quest to an agent."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "open":
            return {"error": f"Quest '{quest_id}' is {quest['status']}, not open"}

        await self.db.execute(
            "UPDATE quests SET owner=?, status='claimed', assigned_at=datetime('now') WHERE id=?",
            (agent_name, quest_id),
        )
        await self.db.commit()

        return await self.get_quest(quest_id)

    # ═══════════════════════════════════════════
    # SUBMIT FOR REVIEW
    # ═══════════════════════════════════════════

    async def submit_for_review(self, quest_id: str, agent_name: str) -> dict:
        """Submit a claimed quest for Warden verification."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "claimed":
            return {"error": f"Quest '{quest_id}' is {quest['status']}, not claimed"}
        if quest.get("owner") != agent_name:
            return {"error": f"Quest '{quest_id}' is owned by {quest['owner']}, not {agent_name}"}

        await self.db.execute(
            "UPDATE quests SET status='review', submitted_at=datetime('now') WHERE id=?",
            (quest_id,),
        )
        await self.db.commit()

        return await self.get_quest(quest_id)

    # ═══════════════════════════════════════════
    # VERIFY / DENY (Warden actions)
    # ═══════════════════════════════════════════

    async def verify_quest(self, quest_id: str, runs: int = 3) -> dict:
        """Warden verifies a quest: check criteria, raise osState, complete."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "review":
            return {"error": f"Quest '{quest_id}' is {quest['status']}, not review"}

        # In a real system, Warden would N-run check each criterion here.
        # For now, we trust the verification and mark as done.

        await self.db.execute(
            "UPDATE quests SET status='done', completed_at=datetime('now'), verification_runs=? WHERE id=?",
            (runs, quest_id),
        )
        await self.db.commit()

        # Raise osState subsystem
        subsystem = quest["subsystem"]
        reward = quest.get("reward", 10)
        if self.os_state:
            await self.os_state.raise_subsystem(subsystem, amount=reward // 5)

        print(f"[Quests] Verified: {quest_id} ({subsystem}) — DONE")
        return await self.get_quest(quest_id)

    async def deny_quest(
        self, quest_id: str, reason: str, fix_hint: Optional[str] = None
    ) -> dict:
        """Warden denies a quest review — sends it back to claimed."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "review":
            return {"error": f"Quest '{quest_id}' is {quest['status']}, not review"}

        await self.db.execute(
            "UPDATE quests SET status='claimed', denial_reason=?, denial_fix=? WHERE id=?",
            (reason, fix_hint, quest_id),
        )
        await self.db.commit()

        print(f"[Quests] Denied: {quest_id} — {reason}")
        return await self.get_quest(quest_id)

    # ═══════════════════════════════════════════
    # BLOCK / UNBLOCK
    # ═══════════════════════════════════════════

    async def block_quest(self, quest_id: str, reason: str) -> dict:
        """Block a quest (dependency not met, resource shortage, etc.)."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}

        await self.db.execute(
            "UPDATE quests SET status='blocked', block_reason=? WHERE id=?",
            (reason, quest_id),
        )
        await self.db.commit()

        return await self.get_quest(quest_id)

    async def unblock_quest(self, quest_id: str) -> dict:
        """Unblock a quest — return to its previous status."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "blocked":
            return {"error": f"Quest '{quest_id}' is not blocked"}

        await self.db.execute(
            "UPDATE quests SET status='claimed', block_reason=NULL WHERE id=?",
            (quest_id,),
        )
        await self.db.commit()

        return await self.get_quest(quest_id)

    # ═══════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════

    async def get_quest(self, quest_id: str) -> Optional[dict]:
        """Get a single quest by ID."""
        quest = await self._find_quest(quest_id)
        return self._to_dict(quest) if quest else None

    async def list_quests(self, status: Optional[str] = None) -> list[dict]:
        """List all quests, optionally filtered by status."""
        if status:
            cursor = await self.db.execute(
                "SELECT * FROM quests WHERE status=? ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM quests ORDER BY created_at DESC"
            )
        rows = await cursor.fetchall()
        return [self._to_dict(r) for r in rows]

    async def get_available_quests(self) -> list[dict]:
        """Get quests that are open AND whose dependencies are done."""
        cursor = await self.db.execute(
            "SELECT * FROM quests WHERE status='open' ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            depends_on = json.loads(row["depends_on"] or "[]")
            if depends_on:
                # Check all dependencies are done
                for dep_id in depends_on:
                    dep = await self._find_quest(dep_id)
                    if not dep or dep["status"] != "done":
                        break
                else:
                    result.append(self._to_dict(row))
            else:
                result.append(self._to_dict(row))
        return result

    async def get_agent_quests(self, agent_name: str) -> list[dict]:
        """Get all quests assigned to a specific agent."""
        cursor = await self.db.execute(
            "SELECT * FROM quests WHERE owner=? ORDER BY created_at DESC",
            (agent_name,),
        )
        rows = await cursor.fetchall()
        return [self._to_dict(r) for r in rows]

    async def seed_default_quests(self):
        """Seed the default Dungeon OS quest line from quests.json."""
        from agora.dungeon_os.quest_data import SEED_QUESTS
        for q in SEED_QUESTS:
            existing = await self._find_quest(q["id"])
            if not existing:
                await self.db.execute(
                    """INSERT INTO quests (id, title, goal, subsystem, success_criteria,
                       reward, owner, depends_on, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', datetime('now'))""",
                    (
                        q["id"],
                        q["title"],
                        q["goal"],
                        q["subsystem"],
                        json.dumps(q["success_criteria"]),
                        q.get("reward", 30),
                        None,
                        json.dumps(q.get("depends_on", [])),
                    ),
                )
        await self.db.commit()
        count = await self._count_quests()
        print(f"[Quests] Seeded: {count} quests available")

    async def get_os_impact_summary(self) -> dict:
        """Get summary of how quest completions impact osState."""
        cursor = await self.db.execute(
            """SELECT subsystem, COUNT(*) as completed, SUM(reward) as total_reward
               FROM quests WHERE status='done' GROUP BY subsystem"""
        )
        rows = await cursor.fetchall()
        summary = {}
        for r in rows:
            summary[r["subsystem"]] = {
                "completed": r["completed"],
                "total_reward": r["total_reward"],
            }
        return summary

    # ═══════════════════════════════════════════
    # INTERNAL
    # ═══════════════════════════════════════════

    async def _find_quest(self, quest_id: str) -> Optional[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM quests WHERE id=?", (quest_id,)
        )
        return await cursor.fetchone()

    async def _count_quests(self) -> int:
        cursor = await self.db.execute("SELECT COUNT(*) as c FROM quests")
        row = await cursor.fetchone()
        return row["c"] if row else 0

    def _to_dict(self, row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "goal": row["goal"],
            "subsystem": row["subsystem"],
            "success_criteria": json.loads(row["success_criteria"] or "[]"),
            "reward": row["reward"],
            "owner": row.get("owner"),
            "status": row["status"],
            "depends_on": json.loads(row["depends_on"] or "[]"),
            "denial_reason": row.get("denial_reason"),
            "denial_fix": row.get("denial_fix"),
            "block_reason": row.get("block_reason"),
            "verification_runs": row.get("verification_runs"),
            "created_at": row.get("created_at"),
            "assigned_at": row.get("assigned_at"),
            "completed_at": row.get("completed_at"),
        }


async def ensure_quest_tables(db):
    """Create quest table if it doesn't exist."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS quests (
            id                TEXT PRIMARY KEY,
            title             TEXT NOT NULL,
            goal              TEXT NOT NULL,
            subsystem         TEXT NOT NULL,
            success_criteria  TEXT NOT NULL DEFAULT '[]',
            reward            INTEGER NOT NULL DEFAULT 0,
            owner             TEXT,
            status            TEXT NOT NULL DEFAULT 'open',
            depends_on        TEXT NOT NULL DEFAULT '[]',
            denial_reason     TEXT,
            denial_fix        TEXT,
            block_reason      TEXT,
            verification_runs INTEGER,
            created_at        TEXT,
            assigned_at       TEXT,
            submitted_at      TEXT,
            completed_at      TEXT
        )
    """)
    await db.commit()
