"""Corporation Memory — persistent learning from compound lessons.

Every compound cycle extracts lessons. This module:
  1. Stores lessons in `corporation_memory` DB table (structured)
  2. Builds enriched prompts for agent roles (PromptEngine)
  3. Feeds accumulated wisdom back into every agent's context
  4. Tracks which lessons have been applied to which roles

This is Phase 3's recursive self-improvement: what agents learn
permanently changes how they think on the next tick.
"""

import json
import sqlite3
from datetime import datetime
from typing import Optional

from agora.dungeon_os.actions.role_prompts import CORPORATION_ROLES, get_role_prompt


# ═══════════════════════════════════════════
# DB SCHEMA
# ═══════════════════════════════════════════

CORPORATION_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS corporation_memory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson          TEXT NOT NULL,
    source_quest    TEXT,
    source_phase    TEXT,
    role_target     TEXT,       -- which role this lesson is relevant to
    category        TEXT DEFAULT 'general',  -- technical | strategic | process | tooling
    impact_score    REAL DEFAULT 0.5,        -- 0.0=trivial, 1.0=game-changing
    applied_at      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_corp_memory_role ON corporation_memory(role_target);
CREATE INDEX IF NOT EXISTS idx_corp_memory_cat ON corporation_memory(category);
"""


# ═══════════════════════════════════════════
# MEMORY MANAGER
# ═══════════════════════════════════════════

class CorporationMemory:
    """Manages persistent corporation memory — lessons learned across cycles."""

    def __init__(self, db):
        self.db = db

    async def ensure_tables(self):
        """Create the corporation_memory table if it doesn't exist."""
        # aiosqlite can only execute one statement at a time
        statements = [s.strip() for s in CORPORATION_MEMORY_SCHEMA.split(";") if s.strip()]
        for stmt in statements:
            try:
                await self.db.execute(stmt)
            except Exception as e:
                # Table/index might already exist
                print(f"[Memory] Schema stmt skipped (may already exist): {e}")
        await self.db.commit()

    async def store_lesson(
        self,
        lesson: str,
        source_quest: str = "",
        source_phase: str = "",
        role_target: str = "",
        category: str = "general",
        impact_score: float = 0.5,
    ) -> int:
        """Store a compound lesson for future agent enhancement."""
        await self.ensure_tables()
        cursor = await self.db.execute(
            """INSERT INTO corporation_memory
               (lesson, source_quest, source_phase, role_target, category, impact_score)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (lesson, source_quest, source_phase, role_target, category, impact_score),
        )
        await self.db.commit()
        print(f"[Memory] Stored lesson #{cursor.lastrowid}: {lesson[:60]}...")
        return cursor.lastrowid

    async def get_memories(
        self,
        role_target: str = "",
        category: str = "",
        limit: int = 20,
        min_impact: float = 0.0,
    ) -> list[dict]:
        """Retrieve corporation memories, optionally filtered."""
        await self.ensure_tables()
        parts = ["SELECT * FROM corporation_memory WHERE 1=1"]
        params = []

        if role_target:
            parts.append("AND (role_target = ? OR role_target = '' OR role_target IS NULL)")
            params.append(role_target)
        if category:
            parts.append("AND category = ?")
            params.append(category)
        if min_impact > 0:
            parts.append("AND impact_score >= ?")
            params.append(min_impact)

        parts.append("ORDER BY impact_score DESC, created_at DESC LIMIT ?")
        params.append(limit)

        cursor = await self.db.execute(" ".join(parts), params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_stats(self) -> dict:
        """Get aggregate memory statistics."""
        await self.ensure_tables()
        cursor = await self.db.execute("SELECT COUNT(*) as total FROM corporation_memory")
        total = (await cursor.fetchone())[0]  # simple tuple

        cursor = await self.db.execute(
            "SELECT category, COUNT(*) as cnt FROM corporation_memory GROUP BY category ORDER BY cnt DESC"
        )
        by_category = {r["category"]: r["cnt"] for r in await cursor.fetchall()}

        cursor = await self.db.execute(
            "SELECT role_target, COUNT(*) as cnt FROM corporation_memory WHERE role_target != '' GROUP BY role_target ORDER BY cnt DESC"
        )
        by_role = {r["role_target"]: r["cnt"] for r in await cursor.fetchall()}

        cursor = await self.db.execute(
            "SELECT AVG(impact_score) as avg FROM corporation_memory"
        )
        avg_impact = (await cursor.fetchone())[0] or 0.0

        return {
            "total": total,
            "by_category": by_category,
            "by_role": by_role,
            "avg_impact": round(avg_impact, 2),
        }

    async def get_recent_high_impact(self, limit: int = 5) -> list[dict]:
        """Get the most impactful recent lessons."""
        return await self.get_memories(min_impact=0.7, limit=limit)


# ═══════════════════════════════════════════
# PROMPT ENGINE — injects memory into prompts
# ═══════════════════════════════════════════

class PromptEngine:
    """Builds enriched agent prompts by injecting corporation memory.

    Each agent role gets:
      1. Base role prompt (from role_prompts.py)
      2. Relevant memories from past cycles (filtered by role + category)
      3. Recent high-impact lessons (if none role-specific)
      4. System health context (optional)
    """

    def __init__(self, memory: CorporationMemory):
        self.memory = memory

    async def build_prompt(
        self,
        role_name: str,
        extra_context: str = "",
        include_system_health: bool = False,
    ) -> str:
        """Build an enriched system prompt for a role.

        Args:
            role_name: The agent role (ceo, cto, researcher, etc.)
            extra_context: Optional task-specific context
            include_system_health: If True, add tick-level system context

        Returns:
            Full system prompt string with injected memories
        """
        base_prompt = get_role_prompt(role_name)

        # Get role-specific memories
        role_memories = await self.memory.get_memories(
            role_target=role_name, limit=5, min_impact=0.3
        )

        # Get high-impact general memories if none role-specific
        if not role_memories:
            role_memories = await self.memory.get_recent_high_impact(limit=3)

        # Build memory section
        if role_memories:
            memory_section = ["", "## 🧠 Corporation Memory (lessons from past cycles)", ""]
            for m in role_memories:
                impact_bar = "⭐" * max(1, int(m["impact_score"] * 3))
                memory_section.append(
                    f"- {m['lesson'][:200]} {impact_bar}"
                )
            memory_section.append("")
        else:
            memory_section = []

        # Time awareness
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Assemble final prompt
        parts = [
            base_prompt,
            "",
            f"*Corporation timestamp: {now}*",
        ]

        if memory_section:
            parts.extend(memory_section)

        if extra_context:
            parts.extend(["", "## Current Task Context", "", extra_context])

        return "\n".join(parts)

    async def apply_lesson_to_role(
        self, lesson: str, role_name: str, impact_score: float = 0.5
    ) -> str:
        """Immediately apply a lesson to a role — returns the new prompt."""
        # Just store in memory — it'll be picked up on next build_prompt()
        await self.memory.store_lesson(
            lesson=lesson,
            role_target=role_name,
            category="process",
            impact_score=impact_score,
        )
        return await self.build_prompt(role_name)
