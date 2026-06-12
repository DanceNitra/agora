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
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# ── ESS Topic Constants (task 1.7) ──
ESS_TOPIC_TRUST = "ess:trust"          # Trust score updates
ESS_TOPIC_TFT = "ess:tft"              # TFT compliance evaluations
ESS_TOPIC_STABILITY = "ess:stability"  # Provokability / ESS stability tests
ESS_TOPICS = [ESS_TOPIC_TRUST, ESS_TOPIC_TFT, ESS_TOPIC_STABILITY]


class MessageType(str, Enum):
    """The fixed ESS message vocabulary (Axelrod TFT: Clear)."""

    COMMIT = "commit"
    COOPERATE = "cooperate"
    DEFECT = "defect"
    ALERT = "alert"          # retaliation / defection notice
    ACK = "ack"


@dataclass
class ESSMessage:
    """A signed ESS protocol message.

    Wire schema is fixed (Clear). Signing covers type+agent_id+payload+timestamp;
    target_id is routing metadata and is intentionally not part of the signed body.
    """

    type: MessageType
    agent_id: str
    target_id: str
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trust_sig: str = ""

    # ── Canonical signing body ──────────────────
    def _signed_data(self) -> bytes:
        """Deterministic bytes that sign() and verify() both operate on."""
        type_str = self.type.value if isinstance(self.type, MessageType) else str(self.type)
        data = f"{type_str}:{self.agent_id}:{json.dumps(self.payload, sort_keys=True)}:{self.timestamp}"
        return data.encode()

    def sign(self, private_key: Ed25519PrivateKey) -> str:
        """Sign the message with an Ed25519 private key.

        Returns the full 64-byte signature as a 128-char hex string and stores it
        in ``self.trust_sig`` as a side effect.
        """
        sig_hex = private_key.sign(self._signed_data()).hex()
        self.trust_sig = sig_hex
        return sig_hex

    def verify(self, public_key: Ed25519PublicKey) -> bool:
        """Verify the Ed25519 signature against a public key.

        Returns True only if the signature matches the current message content.
        Never raises.
        """
        if not self.trust_sig:
            return False
        try:
            signature = bytes.fromhex(self.trust_sig)
            public_key.verify(signature, self._signed_data())
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False

    def to_dict(self) -> dict:
        """Serialise for transport / WS broadcast."""
        type_str = self.type.value if isinstance(self.type, MessageType) else str(self.type)
        return {
            "type": type_str,
            "agent_id": self.agent_id,
            "target_id": self.target_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "trust_sig": self.trust_sig,
        }

    # ── Key (de)serialisation helpers ───────────
    @staticmethod
    def public_key_to_hex(pub_key: Ed25519PublicKey) -> str:
        """Serialise an Ed25519 public key to a hex string (for DB storage)."""
        return pub_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()

    @staticmethod
    def hex_to_public_key(hex_str: str) -> Ed25519PublicKey:
        """Deserialise a hex string back into an Ed25519PublicKey."""
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_str))

    @staticmethod
    def private_key_to_hex(priv_key: Ed25519PrivateKey) -> str:
        """Serialise a private key to hex (dev/secure storage)."""
        return priv_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        ).hex()

    @staticmethod
    def hex_to_private_key(hex_str: str) -> Ed25519PrivateKey:
        """Deserialise a hex string back into an Ed25519PrivateKey."""
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hex_str))

    @staticmethod
    def generate_keypair() -> "tuple[Ed25519PrivateKey, Ed25519PublicKey]":
        """Generate a fresh Ed25519 key pair."""
        private_key = Ed25519PrivateKey.generate()
        return private_key, private_key.public_key()


class TrustEngine:
    """Sliding-window trust scoring with TFT dynamics."""

    BASELINE_TRUST = 0.3
    COOPERATE_BONUS = 0.1
    DEFECT_PENALTY = 0.3
    FORGIVENESS_THRESHOLD = 5
    DECAY_RATE = 0.95
    SLIDING_WINDOW_SIZE = 20       # Only the last N interactions matter
    PROVOKABILITY_THRESHOLD = 0.7  # ESS stability threshold

    def __init__(self, db, event_store=None, event_bus=None):
        self.db = db
        self.event_store = event_store  # Optional event-sourcing integration
        self.event_bus = event_bus      # Optional EventBus for real-time streaming (1.7)

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

        # Forgiveness (TFT, healing-only): a sustained run of cooperation HEALS a bond.
        # It only ever lifts trust UP to at least the neutral baseline (forgiving past
        # defections) — it never pulls an already-trusting relationship back down. So
        # sustained cooperation keeps building trust toward 1.0 (talking = bonding).
        if trust["consecutive_cooperations"] >= self.FORGIVENESS_THRESHOLD:
            trust["score"] = max(trust["score"], self.BASELINE_TRUST)

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

        # Real-time publish via EventBus (non-blocking, best-effort) — task 1.7
        if self.event_bus:
            try:
                await self.event_bus.publish(
                    topic=ESS_TOPIC_TRUST,
                    event_type=f"trust_{outcome}",
                    payload={
                        "agent_id": agent_id,
                        "target_id": target_id,
                        "outcome": outcome,
                        "score": trust["score"],
                        "interactions": trust["interactions"],
                        "consecutive_cooperations": trust.get("consecutive_cooperations", 0),
                        "consecutive_defections": trust.get("consecutive_defections", 0),
                    },
                )
            except Exception:
                pass

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

    async def apply_decay(self, step: float = 0.02) -> None:
        """Activity decay: nudge every stored trust score toward baseline so reputation
        stays DYNAMIC (must be re-earned). Complements the time-based decay in get_trust;
        callers tick this on their own cadence (e.g. the dungeon every ~30s)."""
        try:
            await self.db.execute(
                "UPDATE trust_scores SET score = score * (1 - ?) + ? * ?",
                (step, self.BASELINE_TRUST, step))
            await self.db.commit()
        except Exception:
            pass

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
                """INSERT INTO trust_scores (id, source_id, target_id, score, interaction_count,
                   consecutive_cooperations, consecutive_defections, sliding_window, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (uuid.uuid4().hex, agent_id, target_id, trust["score"], trust["interactions"],
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

        result = {
            "provokability_score": round(min(1.0, provokability), 4),
            "details": {
                "reciprocity": round(reciprocity, 4),
                "forgiveness_rate": round(forgiveness_rate, 4),
                "consistency": round(consistency, 4),
                "window_size": len(window),
            },
            "is_stable": provokability >= self.PROVOKABILITY_THRESHOLD,
        }

        # Real-time publish via EventBus (non-blocking, best-effort) — task 1.7
        if self.event_bus:
            try:
                await self.event_bus.publish(
                    topic=ESS_TOPIC_STABILITY,
                    event_type="provokability",
                    payload={"agent_id": agent_id, "target_id": target_id, **result},
                )
            except Exception:
                pass

        return result


def demo_sign_verify() -> bool:
    """Quick sanity check for Ed25519 signing (sync; no DB)."""
    priv, pub = ESSMessage.generate_keypair()

    msg = ESSMessage(
        type=MessageType.COMMIT,
        agent_id="test-agent",
        target_id="test-partner",
        payload={"goal": "test"},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    sig = msg.sign(priv)
    assert len(sig) == 128, f"Expected 128 hex chars, got {len(sig)}"
    assert msg.verify(pub), "Signature should verify"

    # Tampered message must NOT verify
    msg.payload = {"goal": "tampered"}
    assert not msg.verify(pub), "Tampered message should NOT verify"

    print(f"[ESS] Ed25519 signing OK: {sig[:16]}...")
    return True
