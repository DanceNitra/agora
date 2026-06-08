"""Diary Engine — agents write personal journals and autobiographies.

Every N ticks, agents write diary entries about their experiences.
On lifecycle milestone events, they write reflections.
At the end of their lifecycle, they write an autobiography (legacy note).
"""
import json
import random
from datetime import datetime


class DiaryEngine:
    """Generates diary entries and legacy notes for agents."""

    def __init__(self, db, vault_writer=None):
        self.db = db
        self.vault_writer = vault_writer  # optional: write to Obsidian vault

    # ── Write a diary entry ─────────────────────

    async def write_entry(self, npc_id: str, name: str, role: str,
                           goal: str, mood: float, emotion: str,
                           recent_memories: list, tick: int,
                           vault_reader=None, broadcast_fn=None) -> dict | None:
        """Generate a diary entry for an agent.

        Happens every ~20 ticks per agent.
        """
        if random.random() > 0.4:  # 40% chance per check
            return None

        # Build content from agent state
        entries = []
        if recent_memories:
            top_mem = recent_memories[-1] if isinstance(recent_memories, list) else ""
            mem_text = top_mem.get("content", "")[:60] if isinstance(top_mem, dict) else str(top_mem)[:60]
            entries.append(f"Today I recall: {mem_text}.")

        entries.append(f"My goal remains: {goal[:60]}.")

        # Mood reflection
        if mood < 0.3:
            entries.append("I feel heavy today. The dungeon weighs on me.")
        elif mood > 0.7:
            entries.append("I feel light and hopeful. There's magic in the air.")
        else:
            entries.append("Another day in the dungeon. Things continue.")

        # Role-specific reflections
        role_reflections = {
            "adventurer": "There's always another door to open, another passage to explore.",
            "scout": "I've mapped another section today. The dungeon reveals itself slowly.",
            "sage": "Knowledge accumulates like sediment. Patterns emerge over time.",
            "blacksmith": "The forge speaks to me. Each strike teaches something new.",
            "alchemist": "Ingredients whisper their secrets if you listen carefully.",
            "merchant": "Every interaction is a negotiation. Trust is the real currency.",
            "guard": "Order must be maintained. I watch, I wait, I protect.",
        }
        entries.append(role_reflections.get(role, "I continue my work."))

        content = "\n\n".join(entries)
        title = f"{name}'s Journal — Day {tick // 20}"

        await self.db.execute(
            "INSERT INTO agent_diaries (npc_id, entry_type, title, content, "
            "mood_at_time, emotion_at_time, tick) "
            "VALUES (?, 'diary', ?, ?, ?, ?, ?)",
            (npc_id, title[:100], content[:1000], mood, emotion, tick),
        )
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("agent_diary", {
                "agent": name,
                "title": title,
            })

        return {"title": title, "content": content[:200]}

    # ── Write a reflection (on milestone) ───────

    async def write_reflection(self, npc_id: str, name: str, role: str,
                                milestone: str, tick: int,
                                broadcast_fn=None) -> dict:
        """Write a reflection on a milestone event.

        milestone: first_quest, first_conversation, helped_someone,
                   learned_skill, changed_goal, reached_elder, etc.
        """
        reflections = {
            "first_quest": f"I remember my first quest. I was uncertain, but I succeeded. The dungeon taught me that courage is not the absence of fear.",
            "first_conversation": f"I spoke with another being today — truly spoke. We shared thoughts. I am not alone in this place.",
            "helped_someone": f"I helped another agent today. The gratitude in their eyes... this is what cooperation feels like.",
            "learned_skill": f"I've mastered something new. Each skill is a tool, but more than that — it's a part of who I'm becoming.",
            "changed_goal": f"My purpose shifts. The dungeon changes, and I change with it. Growth is the only constant.",
            "reached_elder": f"I have seen much. The young agents remind me of who I once was. It is time to teach.",
            "legacy": f"If this is my last entry, let it be known: I was here. I explored, I learned, I helped. The dungeon remembers.",
        }
        content = reflections.get(milestone, f"A milestone reached: {milestone}. I pause to reflect.")

        await self.db.execute(
            "INSERT INTO agent_diaries (npc_id, entry_type, title, content, "
            "mood_at_time, emotion_at_time, tick) "
            "VALUES (?, 'reflection', ?, ?, 0.6, 'grateful', ?)",
            (npc_id, f"{name}'s Reflection: {milestone}", content[:500], tick),
        )
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("agent_reflection", {
                "agent": name,
                "milestone": milestone,
            })

        return {"title": f"Reflection: {milestone}", "content": content[:200]}

    # ── Write an autobiography (legacy) ─────────

    async def write_autobiography(self, npc_id: str, name: str, role: str,
                                   tick: int, broadcast_fn=None) -> str:
        """Write a final autobiography entry — the agent's legacy.

        Returns the vault note path if vault_writer is available.
        """
        # Get all diary entries
        cursor = await self.db.execute(
            "SELECT title, content, mood_at_time, tick FROM agent_diaries "
            "WHERE npc_id=? ORDER BY tick ASC",
            (npc_id,),
        )
        entries = [dict(r) for r in await cursor.fetchall()]

        # Get lifecycle info
        cursor = await self.db.execute(
            "SELECT life_goal, peak_experience, wisdom, legacy "
            "FROM agent_lifecycles WHERE npc_id=?", (npc_id,)
        )
        lc = await cursor.fetchone()

        # Build autobiography
        lines = [f"# The Story of {name}", f"*Role: {role}*", ""]
        if lc:
            lines.append(f"**Life Goal:** {lc['life_goal']}")
            if lc['peak_experience']:
                lines.append(f"**Peak Experience:** {lc['peak_experience']}")
            lines.append(f"**Final Wisdom:** {lc['wisdom']:.2f}")
            lines.append("")

        lines.append("## My Journey")
        for e in entries[-20:]:  # last 20 entries
            lines.append(f"- *Day {e['tick'] // 20}* — {e['title']}")

        lines.append("")
        lines.append(f"*Written on tick {tick}*")
        lines.append(f"*{name} — signing off*")

        content = "\n".join(lines)

        # Store in DB
        await self.db.execute(
            "INSERT INTO agent_diaries (npc_id, entry_type, title, content, "
            "mood_at_time, emotion_at_time, tick) "
            "VALUES (?, 'autobiography', ?, ?, 0.8, 'grateful', ?)",
            (npc_id, f"The Story of {name}", content[:5000], tick),
        )
        await self.db.commit()

        # Write to vault if available
        vault_path = None
        if self.vault_writer:
            try:
                vault_path = await self.vault_writer.write_note(
                    title=f"The Story of {name} — Agent Autobiography",
                    content=content,
                    tags=["dungeon", "autobiography", role],
                    agent_name=name,
                )
                await self.vault_writer.git_commit_and_push(
                    vault_path,
                    f"[Dungeon Agent] {name}: Autobiography",
                )
            except Exception as e:
                print(f"[Diary] Vault write error: {e}")

        if broadcast_fn:
            await broadcast_fn("agent_autobiography", {
                "agent": name,
                "vault_path": vault_path or "",
            })

        return vault_path or "db_only"

    # ── Get diary entries for an agent ─────────

    async def get_entries(self, npc_id: str, limit: int = 20) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM agent_diaries WHERE npc_id=? ORDER BY created_at DESC LIMIT ?",
            (npc_id, limit),
        )
        return [dict(r) for r in await cursor.fetchall()]