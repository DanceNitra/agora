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
    SLIDING_WINDOW_SIZE = 20       # Only the last N interactions matter
    PROVOKABILITY_THRESHOLD = 0.7  # ESS stability threshold

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

        # ── Sliding window: keep only the last N interactions ──
        trust.setdefault("sliding_window", [])
        trust["sliding_window"].append({
            "outcome": outcome,
            "timestamp": trust["last_interaction_at"],
            "score_before": trust["score"],
        })
        if len(trust["sliding_window"]) > self.SLIDING_WINDOW_SIZE:
            trust["sliding_window"] = trust["sliding_window"][-self.SLIDING_WINDOW_SIZE:]

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
            "SELECT score, interaction_count, consecutive_cooperations, "
            "consecutive_defections, sliding_window, last_updated "
            "FROM trust_scores WHERE source_id=? AND target_id=?",
            (agent_id, target_id),
        )
        row = await cursor.fetchone()
        if not row:
            return {
                "score": self.BASELINE_TRUST,
                "interactions": 0,
                "consecutive_cooperations": 0,
                "consecutive_defections": 0,
                "sliding_window": [],
                "last_interaction_at": datetime.now(timezone.utc).isoformat(),
            }
        sw_raw = row["sliding_window"]
        return {
            "score": row["score"],
            "interactions": row["interaction_count"],
            "consecutive_cooperations": row["consecutive_cooperations"],
            "consecutive_defections": row["consecutive_defections"],
            "sliding_window": json.loads(sw_raw) if sw_raw else [],
            "last_interaction_at": row["last_updated"] or datetime.now(timezone.utc).isoformat(),
        }

    async def _persist(self, agent_id: str, target_id: str, trust: dict):
        # Try update first
        cursor = await self.db.execute(
            "SELECT id FROM trust_scores WHERE source_id=? AND target_id=?",
            (agent_id, target_id),
        )
        existing = await cursor.fetchone()
        sliding_window_json = json.dumps(trust.get("sliding_window", []))
        if existing:
            await self.db.execute(
                """UPDATE trust_scores SET score=?, interaction_count=?,
                   consecutive_cooperations=?, consecutive_defections=?,
                   sliding_window=?, last_updated=datetime('now')
                   WHERE source_id=? AND target_id=?""",
                (trust["score"], trust["interactions"],
                 trust["consecutive_cooperations"], trust["consecutive_defections"],
                 sliding_window_json, agent_id, target_id),
            )
        else:
            await self.db.execute(
                """INSERT INTO trust_scores (source_id, target_id, score, interaction_count,
                   consecutive_cooperations, consecutive_defections, sliding_window, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (agent_id, target_id, trust["score"], trust["interactions"],
                 trust["consecutive_cooperations"], trust["consecutive_defections"],
                 sliding_window_json),
            )
        await self.db.commit()

    async def compute_provokability(self, agent_id: str, target_id: str) -> dict:
        """Measure whether the trust relationship is evolutionarily stable.

        Returns:
          provokability_score: 0.0 (fragile) to 1.0 (ESS-stable)
          details: breakdown of the score
        """
        trust = await self._get_trust(agent_id, target_id)
        window = trust.get("sliding_window", [])

        if len(window) < 5:
            return {
                "provokability_score": 0.5,  # neutral — insufficient data
                "details": {"reason": "insufficient_data", "window_size": len(window)},
            }

        # 1. Reciprocity — how often is defection answered by defection?
        defections_received = [w for w in window if w["outcome"] == "defect" and w["score_before"] >= 0]
        retaliations = 0
        for i, w in enumerate(window):
            if w["outcome"] == "defect":
                for j in range(i + 1, min(len(window), i + 3)):
                    if window[j]["outcome"] == "defect":
                        retaliations += 1
                        break
        reciprocity = min(1.0, retaliations / max(len(defections_received), 1))

        # 2. Forgiveness — after defection, does cooperation return?
        defection_idx = [i for i, w in enumerate(window) if w["outcome"] == "defect"]
        forgiveness_ops = 0
        forgiveness_taken = 0
        for idx in defection_idx:
            for j in range(idx + 1, min(len(window), idx + 4)):
                if window[j]["outcome"] == "cooperate":
                    forgiveness_ops += 1
                    if j + 1 < len(window) and window[j + 1]["outcome"] == "cooperate":
                        forgiveness_taken += 1
                    break
        forgiveness_rate = forgiveness_taken / max(forgiveness_ops, 1)

        # 3. Consistency — low variance of outcomes
        outcomes = [1.0 if w["outcome"] == "cooperate" else 0.0 for w in window]
        mean = sum(outcomes) / len(outcomes)
        variance = sum((o - mean) ** 2 for o in outcomes) / len(outcomes)
        consistency = max(0.0, 1.0 - variance * 4.0)

        provokability = reciprocity * 0.4 + forgiveness_rate * 0.3 + consistency * 0.3

        return {
            "provokability_score": round(min(1.0, provokability), 4),
            "details": {
                "reciprocity": round(reciprocity, 4),
                "forgiveness_rate": round(forgiveness_rate, 4),
                "consistency": round(consistency, 4),
                "window_size": len(window),
            },
            "is_stable": provokability >= self.PROVOKABILITY_THRESHOLD,
        }
