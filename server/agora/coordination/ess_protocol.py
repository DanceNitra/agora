"""
ESS Protocol — Evolutionarily Stable Strategy for multi-agent trust.

Implements Axelrod's Tit-for-Tat with four properties:
  Nice:       Never defect first. Start with Commit(goal).
  Retaliatory:Immediately punish defection (trust -= 0.3, alert).
  Forgiving:  After 5 cooperative moves, reset trust to baseline.
  Clear:      Fixed JSON message schema: {type, agent_id, payload, trust_sig, ts}
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from cryptography.signing import Ed25519PrivateKey
import json

class MessageType(str, Enum):
    COMMIT = "commit"        # "I intend to do X"
    DATA = "data"            # "Here is my work output"
    DEFECT = "defect"        # "You defected — alerting network"
    RECONCILE = "reconcile"  # "I apologize, let me make it right"
    ALERT = "alert"          # "Broadcast: agent X defected on task Y"

@dataclass
class ESSMessage:
    type: MessageType
    agent_id: str
    target_id: str | None = None
    payload: dict | None = None
    trust_sig: str = ""       # Cryptographic signature
    timestamp: str = ""

    def sign(self, private_key: Ed25519PrivateKey) -> str:
        data = f"{self.type}:{self.agent_id}:{json.dumps(self.payload)}:{self.timestamp}"
        sig = private_key.sign(data.encode())
        self.trust_sig = sig.hex()[:16]  # Store signature prefix
        return self.trust_sig

    def verify(self, public_key_hex: str) -> bool:
        # Verify Ed25519 signature
        data = f"{self.type}:{self.agent_id}:{json.dumps(self.payload)}:{self.timestamp}"
        # Simplified — real implementation would use Ed25519PublicKey
        return True


class TrustEngine:
    """Sliding-window trust scoring with TFT dynamics."""

    WINDOW_SIZE = 20
    BASELINE_TRUST = 0.3
    COOPERATE_BONUS = 0.1
    DEFECT_PENALTY = 0.3
    FORGIVENESS_THRESHOLD = 5
    DECAY_RATE = 0.95  # Exponential decay per tick without interaction

    def __init__(self, db):
        self.db = db

    async def record_interaction(
        self, agent_id: str, target_id: str, outcome: str
    ) -> dict:
        """Record an interaction and return updated trust scores."""
        trust = await self._get_trust(agent_id, target_id)

        if outcome == "cooperate":
            trust["score"] = min(1.0, trust["score"] + self.COOPERATE_BONUS)
            trust["consecutive_cooperations"] += 1
            trust["consecutive_defections"] = 0
        elif outcome == "defect":
            trust["score"] = max(0.0, trust["score"] - self.DEFECT_PENALTY)
            trust["consecutive_defections"] += 1
            trust["consecutive_cooperations"] = 0
            # Broadcast alert
            await self._broadcast_alert(agent_id, target_id)

        # Forgiveness: after N consecutive cooperations since last defection
        if trust["consecutive_cooperations"] >= self.FORGIVENESS_THRESHOLD:
            trust["score"] = self.BASELINE_TRUST

        trust["interactions"] += 1
        trust["last_interaction_at"] = datetime.utcnow()
        await self._persist(agent_id, target_id, trust)
        return trust

    async def get_trust(self, agent_id: str, target_id: str) -> float:
        trust = await self._get_trust(agent_id, target_id)
        # Apply exponential decay
        hours_since = (datetime.utcnow() - trust["last_interaction_at"]).total_seconds() / 3600
        decayed = trust["score"] * (self.DECAY_RATE ** hours_since)
        return max(0.0, min(1.0, decayed))

    async def _broadcast_alert(self, agent_id: str, target_id: str):
        alert = ESSMessage(
            type=MessageType.ALERT,
            agent_id=agent_id,
            payload={"defector": target_id, "reason": "defection"}
        )
        # Write to stigmergy pool
        await self.db.execute(
            "INSERT INTO stigmergy_traces (agent_id, task_type, result, trust_delta) "
            "VALUES ($1, 'alert', $2, $3)",
            agent_id, json.dumps(alert.payload), -0.3
        )

    async def _get_trust(self, agent_id: str, target_id: str) -> dict:
        row = await self.db.fetchrow(
            "SELECT * FROM trust_scores WHERE agent_id=$1 AND target_id=$2",
            agent_id, target_id
        )
        if not row:
            return {
                "score": self.BASELINE_TRUST,
                "interactions": 0,
                "consecutive_cooperations": 0,
                "consecutive_defections": 0,
                "last_interaction_at": datetime.utcnow()
            }
        return dict(row)

    async def _persist(self, agent_id: str, target_id: str, trust: dict):
        await self.db.execute(
            """INSERT INTO trust_scores (agent_id, target_id, score, interactions,
               consecutive_cooperations, consecutive_defections, last_interaction_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7)
               ON CONFLICT (agent_id, target_id) DO UPDATE SET
               score=EXCLUDED.score, interactions=EXCLUDED.interactions,
               consecutive_cooperations=EXCLUDED.consecutive_cooperations,
               consecutive_defections=EXCLUDED.consecutive_defections,
               last_interaction_at=EXCLUDED.last_interaction_at""",
            agent_id, target_id, trust["score"], trust["interactions"],
            trust["consecutive_cooperations"], trust["consecutive_defections"],
            trust["last_interaction_at"]
        )
