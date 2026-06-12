"""Dream Engine — dreams and inspirations for dungeon agents.

Every N ticks, resting agents may dream — processing their memories
into symbolic narratives. Dreams can affect mood, goals, and relationships.

Inspirations are rare breakthroughs that change an agent's understanding.
"""
import json
import random
from datetime import datetime


class DreamEngine:
    """Generates dreams and inspirations for agents."""

    def __init__(self, db, llm_client=None):
        self.db = db
        self.llm_client = llm_client  # optional: call_llm for richer dreams

    # ── Generate a dream for an agent ───────────

    async def generate_dream(self, npc_id: str, name: str, role: str,
                              recent_memories: list, mood: float,
                              broadcast_fn=None) -> dict | None:
        """Generate a dream based on recent memories and emotional state.

        Returns the dream dict or None if agent didn't dream.
        """
        # Not every attempt produces a dream (40% chance)
        if random.random() > 0.4:
            return None

        # Determine dream type based on mood
        dream_type = "dream"
        if mood < 0.3:
            dream_type = random.choice(["nightmare", "dream"])
        elif mood > 0.7:
            dream_type = random.choice(["dream", "vision"])

        # Build dream from memories
        dream_content = self._generate_dream_text(name, role, recent_memories, dream_type)

        # Impact
        impact_mood = random.uniform(-0.1, 0.15)
        new_goal = None
        if random.random() < 0.2 and dream_type == "vision":
            # Vision inspired a new goal
            new_goal = random.choice([
                f"Follow the vision: explore where the dream led",
                f"Seek answers about {random.choice(['the runes', 'the crystal', 'the ancient ones', 'the hidden passage'])}",
                f"Share this vision with {random.choice(['High Priest Orin', 'Sage Mira', 'Shadow Kael'])}",
            ])

        await self.db.execute(
            "INSERT INTO agent_dreams (id, npc_id, dream_type, content, emotion_felt, "
            "impact_mood, impact_goal) VALUES (lower(hex(randomblob(16))), ?, ?, ?, ?, ?, ?)",
            (npc_id, dream_type, dream_content[:500],
             random.choice(["curious", "fearful", "hopeful", "confused", "inspired"]),
             impact_mood, new_goal[:100] if new_goal else None),
        )
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("agent_dream", {
                "agent": name,
                "dream_type": dream_type,
                "content": dream_content[:200],
            })

        return {
            "dream_type": dream_type,
            "content": dream_content,
            "impact_mood": impact_mood,
            "new_goal": new_goal,
        }

    # ── Generate an inspiration (rare) ──────────

    async def generate_inspiration(self, npc_id: str, name: str, role: str,
                                    vault_reader=None, broadcast_fn=None) -> dict | None:
        """Generate a rare insight/inspiration.

        Only happens ~5% chance per check.
        """
        if random.random() > 0.05:
            return None

        # Get vault knowledge for inspiration
        vault_context = ""
        if vault_reader:
            try:
                results = await vault_reader.query(f"{role} insight discovery", top_k=1)
                if results:
                    vault_context = results[0].get("text", "")[:100]
            except Exception:
                pass

        inspiration_types = [
            "realization about the dungeon's nature",
            "connection between two previously unrelated concepts",
            "new way to use an existing ability",
            "understanding of another agent's motivation",
            "glimpse of a larger pattern in agent behavior",
        ]
        insp_type = random.choice(inspiration_types)
        vault_ref = f" Related to vault concept: {vault_context}." if vault_context else ""

        content = (
            f"{name} had a sudden {insp_type}! "
            f"A moment of clarity that changes how they see things.{vault_ref}"
        )

        await self.db.execute(
            "INSERT INTO agent_dreams (id, npc_id, dream_type, content, emotion_felt, "
            "impact_mood) VALUES (lower(hex(randomblob(16))), ?, 'inspiration', ?, 'inspired', 0.2)",
            (npc_id, content[:500]),
        )
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("agent_inspiration", {
                "agent": name,
                "content": content[:200],
            })

        return {
            "dream_type": "inspiration",
            "content": content,
            "impact_mood": 0.2,
        }

    # ── Text generation for dreams ──────────────

    def _generate_dream_text(self, name: str, role: str,
                              memories: list, dream_type: str) -> str:
        """Build dream narrative from available data."""
        memory_refs = memories[-3:] if memories else []
        mem_text = ""
        if memory_refs:
            mem_text = ", ".join(
                m.get("content", "")[:40] if isinstance(m, dict) else str(m)[:40]
                for m in memory_refs
            )

        if dream_type == "nightmare":
            templates = [
                f"{name} dreams of darkness closing in. The dungeon corridors twist endlessly. {mem_text} echoes in the distance.",
                f"A shadow chases {name} through familiar rooms that have become strange and threatening.",
                f"{name} sees the other agents as statues, frozen mid-motion, unable to help.",
            ]
        elif dream_type == "vision":
            templates = [
                f"{name} sees a vision of the dungeon from above — a pattern in the rooms emerges like a star chart.",
                f"A glowing figure speaks to {name}: 'The path is not where you look, but how you see.'",
                f"{name} glimpses a room that doesn't exist yet — a place of perfect coordination between all agents.",
            ]
        else:
            templates = [
                f"{name} dreams of floating through the dungeon's halls. {mem_text} drifts by like clouds.",
                f"A warm light fills the cavern as {name} dreams of the surface world above.",
                f"{name} dreams of a conversation with an old friend. The words are forgotten on waking.",
                f"Strange symbols dance before {name}'s eyes — not runes, but something deeper.",
            ]

        return random.choice(templates)