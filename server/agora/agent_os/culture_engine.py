"""Culture Engine — emergent social culture between dungeon agents.

Agents develop shared jokes, rituals, norms, taboos, and collective memories.
These emerge naturally from repeated interactions and significant events.
Culture spreads when agents talk to each other.
"""
import json
import random
from datetime import datetime


class CultureEngine:
    """Manages emergent culture among agents."""

    def __init__(self, db):
        self.db = db

    # ── Create a new cultural artifact ──────────

    async def create(self, culture_type: str, content: str,
                      originator_id: str, originator_name: str,
                      broadcast_fn=None) -> str:
        """Create a new piece of culture (joke, ritual, norm, taboo, memory).

        Returns the culture item ID.
        """
        await self.db.execute(
            "INSERT INTO agent_culture (culture_type, content, originator_id, "
            "originator_name, spread_count) VALUES (?, ?, ?, ?, 1)",
            (culture_type, content[:500], originator_id, originator_name),
        )
        await self.db.commit()
        cursor = await self.db.execute("SELECT last_insert_rowid()")
        row = await cursor.fetchone()
        culture_id = str(row[0]) if row else ""

        if broadcast_fn:
            await broadcast_fn("culture_created", {
                "type": culture_type,
                "content": content[:100],
                "originator": originator_name,
            })

        return culture_id

    # ── Spread culture between agents ───────────

    async def spread(self, agent_name: str, broadcast_fn=None) -> list[dict]:
        """When an agent talks, they spread culture they know.

        Returns list of culture items that spread.
        """
        # Get active culture items
        cursor = await self.db.execute(
            "SELECT * FROM agent_culture WHERE is_active=1 ORDER BY spread_count DESC LIMIT 10"
        )
        items = [dict(r) for r in await cursor.fetchall()]
        if not items:
            return []

        # Agent picks 1-2 items to share
        shared = random.sample(items, min(random.randint(1, 2), len(items)))
        for item in shared:
            # Increase spread count
            await self.db.execute(
                "UPDATE agent_culture SET spread_count=spread_count+1, "
                "last_used_at=datetime('now') WHERE id=?",
                (item["id"],),
            )

            # If spread count reaches a threshold, the culture becomes "established"
            cursor = await self.db.execute(
                "SELECT spread_count FROM agent_culture WHERE id=?", (item["id"],)
            )
            row = await cursor.fetchone()
            if row and row["spread_count"] >= 7:
                # Established! It's now part of dungeon culture
                pass  # could trigger special events

        await self.db.commit()

        if broadcast_fn:
            for item in shared:
                await broadcast_fn("culture_spread", {
                    "type": item["culture_type"],
                    "content": item["content"][:100],
                    "shared_by": agent_name,
                    "total_spread": item["spread_count"] + 1,
                })

        return shared

    # ── Generate culture from events ────────────

    async def observe_event(self, event_type: str, agents_involved: list[str],
                             context: str, broadcast_fn=None):
        """If a notable event happens, possibly create a culture item from it.

        event_type: big_cooperation, big_conflict, funny_moment, discovery, etc.
        """
        # 30% chance per notable event
        if random.random() > 0.3:
            return None

        culture_type = None
        content = ""

        if event_type == "big_cooperation" and len(agents_involved) >= 2:
            culture_type = "ritual"
            content = f"When {agents_involved[0]} and {agents_involved[1]} work together, great things happen. It has become tradition."
        elif event_type == "big_conflict":
            culture_type = "taboo"
            content = f"Let what happened between {' and '.join(agents_involved[:2])} be a lesson. Some lines should not be crossed."
        elif event_type == "funny_moment":
            culture_type = "joke"
            content = f"Did you hear about {agents_involved[0]}? {context[:100]}"
        elif event_type == "discovery":
            culture_type = "collective_memory"
            content = f"We remember when {agents_involved[0]} discovered {context[:50]}. That day changed everything."

        if culture_type and content:
            originator = agents_involved[0] if agents_involved else "unknown"
            await self.create(culture_type, content, "", originator, broadcast_fn)

    # ── Get culture for LLM prompt injection ────

    async def get_culture_context(self) -> str:
        """Return formatted culture for LLM prompt injection."""
        cursor = await self.db.execute(
            "SELECT * FROM agent_culture WHERE is_active=1 ORDER BY spread_count DESC LIMIT 5"
        )
        items = [dict(r) for r in await cursor.fetchall()]
        if not items:
            return ""

        lines = ["--- Dungeon Culture ---"]
        for item in items:
            emoji = {"joke": "😂", "ritual": "🔄", "norm": "📋", "taboo": "🚫", "collective_memory": "📜"}
            e = emoji.get(item["culture_type"], "📌")
            lines.append(f"  {e} [{item['culture_type']}] {item['content'][:100]}")
        return "\n".join(lines)