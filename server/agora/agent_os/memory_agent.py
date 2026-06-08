"""
Per-agent memory system with importance scoring, decay, emotional tagging,
and multi-type retrieval (episodic/semantic/procedural).

Each agent has an independent memory store that persists in SQLite.
Memories decay over time unless they are important or frequently recalled.

Part of Agentic OS v2 (Phase 2.0) — Layer 1.
"""
import math
from datetime import datetime, timezone
from typing import Optional


class MemoryAgent:
    """Individual memory system for one NPC."""

    DECAY_RATE = 0.05            # loss per tick (simulated day)
    IMPORTANCE_THRESHOLD = 0.8   # memories above this survive pruning/forgetting
    MAX_EPISODIC = 100           # max episodic memories per agent (prune oldest)
    MAX_SEMANTIC = 50            # max semantic memories
    MAX_PROCEDURAL = 30          # max procedural (rarely added)

    def __init__(self, db, npc_id: str):
        self.db = db
        self.npc_id = npc_id

    async def store_memory(
        self,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5,
        emotional_tag: str = "neutral",
        source: str = "experience",
        related_npc_id: Optional[str] = None,
    ) -> int:
        """Store a new memory. Returns memory ID."""
        importance = max(0.0, min(1.0, importance))
        cursor = await self.db.execute(
            "INSERT INTO agent_memories (npc_id, memory_type, content, importance, "
            "emotional_tag, source, related_npc_id, decay_factor, last_recalled_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1.0, datetime('now'))",
            (self.npc_id, memory_type, content, importance, emotional_tag,
             source, related_npc_id),
        )
        await self.db.commit()
        mem_id = cursor.lastrowid

        # Prune if over capacity
        await self._prune_if_needed(memory_type)
        return mem_id

    async def recall(
        self,
        query: str = "",
        memory_type: Optional[str] = None,
        limit: int = 5,
        min_importance: float = 0.0,
        with_emotion: Optional[str] = None,
        about_npc: Optional[str] = None,
    ) -> list[dict]:
        """Recall memories matching the query. Uses keyword overlap scoring.

        Scoring: importance*0.6 + keyword_overlap*0.3 + recency_factor*0.1
        Returns top `limit` memories sorted by score descending.
        """
        conditions = ["npc_id=?"]
        params: list = [self.npc_id]

        if memory_type:
            conditions.append("memory_type=?")
            params.append(memory_type)
        if min_importance > 0:
            conditions.append("importance>=?")
            params.append(min_importance)
        if with_emotion:
            conditions.append("emotional_tag=?")
            params.append(with_emotion)
        if about_npc:
            conditions.append("related_npc_id=?")
            params.append(about_npc)

        cursor = await self.db.execute(
            f"SELECT * FROM agent_memories WHERE {' AND '.join(conditions)} "
            f"ORDER BY importance DESC, last_recalled_at DESC LIMIT ?",
            params + [limit * 3],  # fetch extra for scoring
        )
        rows = await cursor.fetchall()
        if not rows:
            return []

        query_keywords = set(
            w.lower() for w in query.split() if len(w) > 3
        ) if query else set()

        scored = []
        now = datetime.now(timezone.utc)
        for row in rows:
            mem = dict(row)
            last_recall = mem.get("last_recalled_at")
            recency_factor = 0.3
            if last_recall:
                try:
                    last_dt = (datetime.fromisoformat(last_recall)
                               if isinstance(last_recall, str) else last_recall)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    hours_ago = (now - last_dt).total_seconds() / 3600
                    recency_factor = math.exp(-hours_ago / 24)  # decays over 24h
                except Exception:
                    recency_factor = 0.5

            mem_content = (mem.get("content") or "").lower()
            keyword_overlap = 0.0
            if query_keywords and mem_content:
                overlap = sum(1 for kw in query_keywords if kw in mem_content)
                keyword_overlap = min(1.0, overlap / max(len(query_keywords), 1))

            score = mem["importance"] * 0.6 + keyword_overlap * 0.3 + recency_factor * 0.1
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        result = scored[:limit]

        # Reinforce recalled memories
        for _score, mem in result:
            await self.db.execute(
                "UPDATE agent_memories SET last_recalled_at=datetime('now'), "
                "decay_factor=MIN(1.0, decay_factor+0.1) WHERE id=?",
                (mem["id"],),
            )
        await self.db.commit()

        return [mem for _score, mem in result]

    async def remember_recent(self, limit: int = 10) -> list[dict]:
        """Get most recent memories (for LLM context injection)."""
        cursor = await self.db.execute(
            "SELECT * FROM agent_memories WHERE npc_id=? ORDER BY created_at DESC LIMIT ?",
            (self.npc_id, limit),
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_emotional_summary(self) -> dict:
        """Get emotional state summary from recent memories."""
        cursor = await self.db.execute(
            "SELECT emotional_tag, COUNT(*) as cnt FROM agent_memories "
            "WHERE npc_id=? AND emotional_tag!='neutral' "
            "GROUP BY emotional_tag ORDER BY cnt DESC",
            (self.npc_id,),
        )
        rows = await cursor.fetchall()
        return {r["emotional_tag"]: r["cnt"] for r in rows}

    async def _prune_if_needed(self, memory_type: str):
        """Prune oldest low-importance memories if over capacity."""
        max_map = {"episodic": self.MAX_EPISODIC, "semantic": self.MAX_SEMANTIC,
                   "procedural": self.MAX_PROCEDURAL}
        max_count = max_map.get(memory_type, 100)

        cursor = await self.db.execute(
            "SELECT COUNT(*) as c FROM agent_memories WHERE npc_id=? AND memory_type=? "
            "AND importance < ?",
            (self.npc_id, memory_type, self.IMPORTANCE_THRESHOLD),
        )
        row = await cursor.fetchone()
        low_imp_count = row["c"] if row else 0

        cursor = await self.db.execute(
            "SELECT COUNT(*) as c FROM agent_memories WHERE npc_id=? AND memory_type=?",
            (self.npc_id, memory_type),
        )
        row = await cursor.fetchone()
        total = row["c"] if row else 0

        if total > max_count and low_imp_count > 0:
            prune_count = total - max_count
            await self.db.execute(
                "DELETE FROM agent_memories WHERE id IN ("
                "SELECT id FROM agent_memories WHERE npc_id=? AND memory_type=? "
                "AND importance < ? ORDER BY last_recalled_at ASC LIMIT ?"
                ")",
                (self.npc_id, memory_type, self.IMPORTANCE_THRESHOLD, prune_count),
            )
            await self.db.commit()

    async def decay_all(self):
        """Apply decay to all memories. Called once per tick."""
        await self.db.execute(
            "UPDATE agent_memories SET decay_factor = MAX(0.0, decay_factor - ?) "
            "WHERE npc_id=? AND memory_type IN ('episodic', 'semantic') "
            "AND decay_factor > 0",
            (self.DECAY_RATE, self.npc_id),
        )
        # Forgetting: remove fully-decayed, non-important memories
        await self.db.execute(
            "DELETE FROM agent_memories WHERE npc_id=? AND decay_factor <= 0 "
            "AND importance < ?",
            (self.npc_id, self.IMPORTANCE_THRESHOLD),
        )
        await self.db.commit()

    async def get_relevant_memories_for_prompt(self, context: str, max_memories: int = 8) -> str:
        """Formatted string of relevant memories for LLM prompt injection."""
        recalled = await self.recall(context, limit=max_memories)
        if not recalled:
            recalled = await self.remember_recent(limit=3)
        if not recalled:
            return "--- Your Memories ---\n  (none yet)"

        lines = ["--- Your Memories ---"]
        for mem in recalled:
            mem_type = mem["memory_type"][:4]
            importance = mem["importance"]
            content = (mem["content"] or "")[:150]
            emotion = mem["emotional_tag"]
            emotion_tag = f" [{emotion}]" if emotion != "neutral" else ""
            lines.append(f"  [{mem_type}] [{importance:.2f}] {content}{emotion_tag}")
        return "\n".join(lines)
