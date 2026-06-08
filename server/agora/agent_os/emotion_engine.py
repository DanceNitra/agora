"""Emotion Engine — emotional states for dungeon agents.

Each agent has:
  - current: primary emotion (neutral, happy, sad, angry, fearful, surprised, curious, trusted, betrayed, grateful, hopeful, lonely)
  - intensity: 0-1 how strongly they feel it
  - valence: -1 (negative) to +1 (positive)
  - arousal: 0 (calm) to 1 (excited)
  - mood: 0 (terrible) to 1 (euphoric) — long-term emotional baseline
  - history: last 10 emotions with triggers

Emotions are triggered by events and decay naturally each tick.
Mood shifts slowly based on accumulated emotional experiences.
"""
import json
import math
import random


# ── Emotion definitions ─────────────────────────

EMOTION_DEFS = {
    "neutral":   {"valence": 0.0, "arousal": 0.0, "decay": 0.3},
    "happy":     {"valence": 0.7, "arousal": 0.5, "decay": 0.08},
    "sad":       {"valence": -0.6, "arousal": 0.2, "decay": 0.05},
    "angry":     {"valence": -0.7, "arousal": 0.8, "decay": 0.12},
    "fearful":   {"valence": -0.5, "arousal": 0.7, "decay": 0.15},
    "surprised": {"valence": 0.3, "arousal": 0.8, "decay": 0.25},
    "curious":   {"valence": 0.4, "arousal": 0.6, "decay": 0.06},
    "trusted":   {"valence": 0.6, "arousal": 0.3, "decay": 0.04},
    "betrayed":  {"valence": -0.8, "arousal": 0.7, "decay": 0.08},
    "grateful":  {"valence": 0.6, "arousal": 0.3, "decay": 0.07},
    "hopeful":   {"valence": 0.5, "arousal": 0.4, "decay": 0.05},
    "lonely":    {"valence": -0.4, "arousal": 0.1, "decay": 0.04},
}


class EmotionEngine:
    """Manages emotional states for all dungeon agents."""

    def __init__(self, db):
        self.db = db

    # ── Trigger emotion from an event ───────────

    async def trigger(self, npc_id: str, emotion: str, intensity: float = 0.5,
                      trigger: str = "", broadcast_fn=None):
        """Set an agent's current emotion.

        The new emotion replaces the current one if its intensity is higher,
        or blends if the current emotion is already strong.
        Returns the updated emotion state.
        """
        cursor = await self.db.execute(
            "SELECT current, intensity, valence, arousal, mood, history "
            "FROM agent_emotions WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        current_emotion = dict(row)
        hist = json.loads(current_emotion["history"])

        # Add to history
        hist.append({
            "emotion": emotion,
            "intensity": intensity,
            "trigger": trigger,
            "tick": 0,
        })
        hist = hist[-10:]  # keep last 10

        # Update current emotion
        defs = EMOTION_DEFS.get(emotion, EMOTION_DEFS["neutral"])
        new_valence = defs["valence"]
        new_arousal = defs["arousal"]
        new_decay = defs["decay"]

        # Mood shift (small, based on event intensity)
        mood_shift = intensity * new_valence * 0.05
        new_mood = max(0.0, min(1.0, current_emotion["mood"] + mood_shift))

        await self.db.execute(
            "UPDATE agent_emotions SET current=?, intensity=?, valence=?, arousal=?, "
            "trigger=?, history=?, decay_rate=?, mood=?, updated_at=datetime('now') "
            "WHERE npc_id=?",
            (emotion, intensity, new_valence, new_arousal, trigger,
             json.dumps(hist), new_decay, new_mood, npc_id),
        )
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("agent_emotion", {
                "agent_id": npc_id[:8],
                "emotion": emotion,
                "intensity": intensity,
                "trigger": trigger,
            })

        return {
            "current": emotion,
            "intensity": intensity,
            "mood": new_mood,
        }

    # ── Decay all emotions (called every tick) ──

    async def decay_all(self, broadcast_fn=None):
        """Decay emotions toward neutral. Also drift mood toward 0.5."""
        cursor = await self.db.execute("SELECT npc_id, current, intensity, decay_rate, mood FROM agent_emotions")
        rows = await cursor.fetchall()
        for row in rows:
            npc_id = row["npc_id"]
            current = row["current"]
            intensity = row["intensity"]
            decay = row["decay_rate"]
            mood = row["mood"]

            # Decay intensity
            new_intensity = max(0.0, intensity - decay)

            # If intensity reached zero, return to neutral
            if new_intensity <= 0.05 and current != "neutral":
                await self.db.execute(
                    "UPDATE agent_emotions SET current='neutral', intensity=0.1, "
                    "valence=0.0, arousal=0.0, trigger='decayed', updated_at=datetime('now') "
                    "WHERE npc_id=?",
                    (npc_id,),
                )
            else:
                # Scale valence and arousal with intensity
                defs = EMOTION_DEFS.get(current, EMOTION_DEFS["neutral"])
                scaled_valence = defs["valence"] * (new_intensity / max(intensity, 0.01))
                scaled_arousal = defs["arousal"] * (new_intensity / max(intensity, 0.01))
                await self.db.execute(
                    "UPDATE agent_emotions SET intensity=?, valence=?, arousal=?, "
                    "updated_at=datetime('now') WHERE npc_id=?",
                    (new_intensity, scaled_valence, scaled_arousal, npc_id),
                )

            # Mood drift toward 0.5 (regression to mean)
            mood_drift = (0.5 - mood) * 0.01
            new_mood = max(0.0, min(1.0, mood + mood_drift))
            await self.db.execute(
                "UPDATE agent_emotions SET mood=? WHERE npc_id=?",
                (new_mood, npc_id),
            )

        await self.db.commit()

    # ── Emotional state of a specific agent ─────

    async def get_state(self, npc_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM agent_emotions WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        result["history"] = json.loads(result["history"])
        return result

    # ── Emotional summary of all agents ─────────

    async def get_all_states(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT e.*, d.npc_name FROM agent_emotions e "
            "JOIN dungeon_npcs d ON d.npc_id = e.npc_id "
            "ORDER BY d.npc_name"
        )
        return [dict(r) for r in await cursor.fetchall()]

    # ── Map emotion name to color (for UI) ──────

    @staticmethod
    def emotion_color(emotion: str) -> str:
        return {
            "neutral": "#888888",
            "happy": "#44ff44",
            "sad": "#4488ff",
            "angry": "#ff4444",
            "fearful": "#ff8800",
            "surprised": "#ffff44",
            "curious": "#44ffff",
            "trusted": "#44ff88",
            "betrayed": "#ff44ff",
            "grateful": "#88ff44",
            "hopeful": "#88aaff",
            "lonely": "#8866aa",
        }.get(emotion, "#888888")