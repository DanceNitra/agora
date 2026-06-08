"""MetaMemory — agents remember how their own beliefs changed over time.

This creates GEB-style strange loops: an agent can reflect on its own
cognitive evolution. "I used to believe X, but now I believe Y.
The reason I changed was Z. This tells me something about how I learn."
"""
import json
import random


class MetaMemory:
    """Tracks how agent beliefs change over time."""

    def __init__(self, db):
        self.db = db

    async def record_change(self, npc_id: str, topic: str,
                             old_belief: str, new_belief: str,
                             trigger_event: str = "",
                             significance: float = 0.5):
        """Record that an agent changed their mind about something."""
        await self.db.execute(
            "INSERT INTO agent_metamemory (npc_id, topic, old_belief, new_belief, "
            "trigger_event, significance) VALUES (?, ?, ?, ?, ?, ?)",
            (npc_id, topic[:100], old_belief[:200], new_belief[:200],
             trigger_event[:200], max(0.0, min(1.0, significance))),
        )
        await self.db.commit()

    async def get_recent_changes(self, npc_id: str, limit: int = 5) -> list[dict]:
        """Get recent belief changes for an agent."""
        cursor = await self.db.execute(
            "SELECT * FROM agent_metamemory WHERE npc_id=? "
            "ORDER BY created_at DESC LIMIT ?",
            (npc_id, limit),
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_context(self, npc_id: str) -> str:
        """Get formatted meta-memory for LLM prompt injection."""
        changes = await self.get_recent_changes(npc_id, limit=3)
        if not changes:
            return ""

        lines = ["--- How Your Thinking Has Evolved ---"]
        for c in changes:
            lines.append(
                f"  🔄 You used to think '{c['old_belief'][:60]}' "
                f"but now you think '{c['new_belief'][:60]}'. "
                f"This changed because: {c['trigger_event'][:60]}."
            )
        return "\n".join(lines)