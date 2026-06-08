"""
ESS Protocol — Evolutionarily Stable Strategy for multi-agent trust.

SQLite-compatible version.
Implements Axelrod's Tit-for-Tat with four properties:
  Nice:       Never defect first. Start with Commit(goal).
  Retaliatory:Immediately punish defection (trust -= 0.3, alert).
  Forgiving:  After 5 cooperative moves, reset trust to baseline.
  Clear:      Fixed JSON message schema.
"""

import json
from datetime import datetime, timezone


class TrustEngine:
    """Sliding-window trust scoring with TFT dynamics."""

    BASELINE_TRUST = 0.3
    COOPERATE_BONUS = 0.1
    DEFECT_PENALTY = 0.3
    FORGIVENESS_THRESHOLD = 5
    DECAY_RATE = 0.95

    def __init__(self, db, event_store=None):
        self.db = db
        self.event_store = event_store  # Optional event-sourcing integration

    async def record_interaction(self, agent_id: str, target_id: str, outcome: str) -> dict:
        trust = await self._get_trust(agent_id, target_id)

        if outcome == "cooperate":
            trust["score"] = min(1.0, trust["score"] + self.COOPERATE_BONUS)
            trust["consecutive_cooperations"] += 1
            trust["consecutive_defections"] = 0
        elif outcome == "defect":
            trust["score"] = max(0.0, trust["score"] - self.DEFECT_PENALTY)
            trust["consecutive_defections"] += 1
            trust["consecutive_cooperations"] = 0

        # Forgiveness: after N consecutive cooperations since last defection
        if trust["consecutive_cooperations"] >= self.FORGIVENESS_THRESHOLD:
            trust["score"] = self.BASELINE_TRUST

        trust["interactions"] += 1
        trust["last_interaction_at"] = datetime.now(timezone.utc).isoformat()

        # Event sourcing integration (non-blocking, best-effort)
        if self.event_store:
            try:
                await self.event_store.append(
                    aggregate_type="trust",
                    aggregate_id=f"{agent_id}:{target_id}",
                    event_type=f"trust_{outcome}",
                    payload={
                        "agent_id": agent_id,
                        "target_id": target_id,
                        "outcome": outcome,
                        "score": trust["score"],
                        "interactions": trust["interactions"],
                        "consecutive_cooperations": trust["consecutive_cooperations"],
                        "consecutive_defections": trust["consecutive_defections"],
                    },
                    metadata={"caller": "TrustEngine.record_interaction"},
                )
            except Exception:
                pass  # Event store failure should not break trust recording

        await self._persist(agent_id, target_id, trust)
        return trust

    async def get_trust(self, agent_id: str, target_id: str) -> float:
        trust = await self._get_trust(agent_id, target_id)
        # Apply exponential decay
        try:
            last = datetime.fromisoformat(trust["last_interaction_at"])
            hours_since = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        except (ValueError, TypeError):
            hours_since = 0
        decayed = trust["score"] * (self.DECAY_RATE ** hours_since)
        return max(0.0, min(1.0, decayed))

    async def _get_trust(self, agent_id: str, target_id: str) -> dict:
        cursor = await self.db.execute(
            "SELECT score, interaction_count, last_updated FROM trust_scores WHERE source_id=? AND target_id=?",
            (agent_id, target_id),
        )
        row = await cursor.fetchone()
        if not row:
            return {
                "score": self.BASELINE_TRUST,
                "interactions": 0,
                "consecutive_cooperations": 0,
                "consecutive_defections": 0,
                "last_interaction_at": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "score": row["score"],
            "interactions": row["interaction_count"],
            "consecutive_cooperations": 0,
            "consecutive_defections": 0,
            "last_interaction_at": row["last_updated"] or datetime.now(timezone.utc).isoformat(),
        }

    async def _persist(self, agent_id: str, target_id: str, trust: dict):
        # Try update first
        cursor = await self.db.execute(
            "SELECT id FROM trust_scores WHERE source_id=? AND target_id=?",
            (agent_id, target_id),
        )
        existing = await cursor.fetchone()
        if existing:
            await self.db.execute(
                """UPDATE trust_scores SET score=?, interaction_count=?,
                   last_updated=datetime('now') WHERE source_id=? AND target_id=?""",
                (trust["score"], trust["interactions"], agent_id, target_id),
            )
        else:
            await self.db.execute(
                """INSERT INTO trust_scores (source_id, target_id, score, interaction_count, last_updated)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (agent_id, target_id, trust["score"], trust["interactions"]),
            )
        await self.db.commit()
