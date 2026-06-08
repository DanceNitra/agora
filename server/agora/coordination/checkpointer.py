"""
Checkpointer — State snapshots from event_store streams.

Architecture:
  - Reads events from event_store and reconstructs state
  - Saves state as JSON checkpoint every N events (CHECKPOINT_INTERVAL)
  - On replay, loads latest checkpoint + replays subsequent events
  - SHA256 checksum prevents silent corruption

Usage:
  cp = Checkpointer(db, event_store)
  await cp.checkpoint('trust', 'alice:bob')
  state = await cp.replay('trust', 'alice:bob')
  # state = {'score': 0.7, 'interactions': 15, ...}
"""

import hashlib
import json
from typing import Optional

# ── Checkpoint interval ──────────────────────
# Every N events, save a snapshot. Tradeoff:
#   Small N = fast replay, more storage
#   Large N = slow replay, less storage
CHECKPOINT_INTERVAL = 50

# Trust reconstruction constants (mirror ess_protocol.TrustEngine)
BASELINE_TRUST = 0.3
COOPERATE_DELTA = 0.1
DEFECT_DELTA = 0.3
FORGIVENESS_THRESHOLD = 5
SLIDING_WINDOW_SIZE = 20


def _checksum(state_json: str) -> str:
    """SHA256 (truncated) of the exact JSON string we persist.

    Both the write path and the verify path hash the *stored string*, so the
    checksum is stable regardless of key ordering.
    """
    return hashlib.sha256(state_json.encode()).hexdigest()[:16]


class Checkpointer:
    """State snapshot manager for event-sourced aggregates."""

    def __init__(self, db, event_store):
        self.db = db
        self.event_store = event_store

    # ═══════════════════════════════════════════
    # RECONSTRUCT STATE FROM EVENTS
    # ═══════════════════════════════════════════

    def _reconstruct_trust_state(self, events: list[dict]) -> dict:
        """Reconstruct TrustEngine state from trust events.

        This is the core replay function for trust aggregates.
        It processes each event in order and produces the final state.
        """
        state = {
            "score": BASELINE_TRUST,
            "interactions": 0,
            "consecutive_cooperations": 0,
            "consecutive_defections": 0,
            "sliding_window": [],
        }

        for ev in events:
            self._apply_trust_event(state, ev)

        return state

    @staticmethod
    def _apply_trust_event(state: dict, ev: dict) -> None:
        """Apply a single trust event onto a mutable state dict (in-place)."""
        p = ev["payload"]
        outcome = p.get("outcome", "cooperate")
        state["interactions"] = state.get("interactions", 0) + 1

        if outcome == "cooperate":
            state["score"] = min(1.0, state.get("score", BASELINE_TRUST) + COOPERATE_DELTA)
            state["consecutive_cooperations"] = state.get("consecutive_cooperations", 0) + 1
            state["consecutive_defections"] = 0
        elif outcome == "defect":
            state["score"] = max(0.0, state.get("score", BASELINE_TRUST) - DEFECT_DELTA)
            state["consecutive_defections"] = state.get("consecutive_defections", 0) + 1
            state["consecutive_cooperations"] = 0

        # Forgiveness — a run of cooperations resets trust to baseline
        if state.get("consecutive_cooperations", 0) >= FORGIVENESS_THRESHOLD:
            state["score"] = BASELINE_TRUST

        # Sliding window (bounded)
        window = state.get("sliding_window", [])
        window.append({
            "outcome": outcome,
            "score": state["score"],
            "timestamp": ev.get("occurred_at", ""),
        })
        if len(window) > SLIDING_WINDOW_SIZE:
            window = window[-SLIDING_WINDOW_SIZE:]
        state["sliding_window"] = window

    def _reconstruct_tft_state(self, events: list[dict]) -> dict:
        """Reconstruct TFT compliance state from tft events."""
        interactions = []
        for ev in events:
            p = ev["payload"]
            interactions.append({
                "source_id": p.get("source_id", ""),
                "target_id": p.get("target_id", ""),
                "outcome": p.get("outcome", "cooperate"),
                "trust_before": p.get("trust_before"),
                "trust_after": p.get("trust_after"),
                "round_num": p.get("round_num", 0),
                "created_at": ev.get("occurred_at", ""),
            })

        nice = self._compute_nice(interactions)
        retaliatory = self._compute_retaliatory(interactions)
        forgiving = self._compute_forgiving(interactions)
        clear = self._compute_clear(interactions)

        tft_score = nice * 0.25 + retaliatory * 0.25 + forgiving * 0.25 + clear * 0.25

        return {
            "interaction_count": len(interactions),
            "tft_score": round(tft_score, 4),
            "components": {
                "nice": round(nice, 4),
                "retaliatory": round(retaliatory, 4),
                "forgiving": round(forgiving, 4),
                "clear": round(clear, 4),
            },
            "interactions": interactions[-50:],  # Keep last 50 for detail
        }

    def _compute_nice(self, history: list) -> float:
        first_moves = {}
        for h in history:
            if h["source_id"] not in first_moves:
                first_moves[h["source_id"]] = h["outcome"]
        if not first_moves:
            return 0.5
        nice = sum(1 for o in first_moves.values() if o == "cooperate")
        return nice / len(first_moves)

    def _compute_retaliatory(self, history: list) -> float:
        if len(history) < 2:
            return 0.5
        defections = 0
        retaliations = 0
        for i, h in enumerate(history):
            if h["outcome"] == "defect":
                for j in range(i + 1, min(len(history), i + 3)):
                    if history[j]["source_id"] != h["source_id"]:
                        continue
                    defections += 1
                    if history[j]["outcome"] == "defect":
                        retaliations += 1
                    break
        return retaliations / max(defections, 1)

    def _compute_forgiving(self, history: list) -> float:
        if len(history) < 3:
            return 0.5
        ops = 0
        forgiven = 0
        for i in range(len(history) - 2):
            if (history[i]["outcome"] == "defect" and
                not history[i + 1]["source_id"] == history[i]["source_id"] and
                    history[i + 1]["outcome"] == "cooperate"):
                ops += 1
                if (history[i + 2]["source_id"] == history[i]["source_id"] and
                        history[i + 2]["outcome"] == "cooperate"):
                    forgiven += 1
        return forgiven / max(ops, 1)

    def _compute_clear(self, history: list) -> float:
        if len(history) < 3:
            return 0.5
        outcomes = [1.0 if h["outcome"] == "cooperate" else 0.0 for h in history]
        mean = sum(outcomes) / len(outcomes)
        variance = sum((o - mean) ** 2 for o in outcomes) / len(outcomes)
        return max(0.0, 1.0 - variance * 4.0)

    # ═══════════════════════════════════════════
    # CHECKPOINT CREATION
    # ═══════════════════════════════════════════

    async def checkpoint(self, aggregate_type: str, aggregate_id: str) -> dict:
        """Create a checkpoint by replaying all events and persisting the state.

        Returns the checkpoint dict.
        """
        events = await self.event_store.replay_all(aggregate_type, aggregate_id)
        if not events:
            return {"aggregate_type": aggregate_type, "aggregate_id": aggregate_id,
                    "sequence_number": 0, "state": {}, "events_processed": 0}

        last_seq = events[-1]["sequence_number"]

        if aggregate_type == "trust":
            state = self._reconstruct_trust_state(events)
        elif aggregate_type == "tft":
            state = self._reconstruct_tft_state(events)
        elif aggregate_type == "stigmergy":
            state = {"events_count": len(events), "last_event": events[-1]["payload"]}
        else:
            state = {"events_count": len(events)}

        state_json = json.dumps(state, default=str)
        checksum = _checksum(state_json)

        # Upsert checkpoint (UNIQUE on type+id+sequence)
        await self.db.execute(
            """INSERT OR REPLACE INTO checkpoints
               (aggregate_type, aggregate_id, sequence_number, state, checksum, created_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (aggregate_type, aggregate_id, last_seq, state_json, checksum),
        )
        await self.db.commit()

        return {
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "sequence_number": last_seq,
            "checksum": checksum,
            "events_processed": len(events),
        }

    async def checkpoint_all(self, aggregate_type: str, force: bool = False) -> list[dict]:
        """Create checkpoints for ALL aggregates of a given type.

        If force=False, only checkpoints aggregates whose stream has grown by at
        least CHECKPOINT_INTERVAL events since the last checkpoint.
        """
        aggregates = await self.event_store.list_aggregates(aggregate_type)
        results = []

        for agg_id in aggregates:
            if not force:
                latest = await self._latest_checkpoint(aggregate_type, agg_id)
                stream_len = await self.event_store.stream_length(aggregate_type, agg_id)
                if latest and (stream_len - latest["sequence_number"] < CHECKPOINT_INTERVAL):
                    continue  # Recent enough

            result = await self.checkpoint(aggregate_type, agg_id)
            results.append(result)

        return results

    # ═══════════════════════════════════════════
    # REPLAY FROM CHECKPOINT
    # ═══════════════════════════════════════════

    async def replay(self, aggregate_type: str, aggregate_id: str) -> dict:
        """Reconstruct state from the latest checkpoint + subsequent events.

        Returns the reconstructed state dict.
        """
        checkpoint = await self._latest_checkpoint(aggregate_type, aggregate_id)

        if checkpoint:
            state = json.loads(checkpoint["state"])
            from_seq = checkpoint["sequence_number"] + 1
        else:
            state = {}
            from_seq = 1

        # Replay events after checkpoint
        events = await self.event_store.read_stream(
            aggregate_type, aggregate_id, from_sequence=from_seq
        )

        # No checkpoint: reconstruct fully from scratch
        if not checkpoint:
            if not events:
                return state
            if aggregate_type == "trust":
                return self._reconstruct_trust_state(events)
            elif aggregate_type == "tft":
                return self._reconstruct_tft_state(events)
            else:
                return {"replayed_events": len(events), "last_event": events[-1]["payload"]}

        # Have a checkpoint but no new events: return snapshot as-is
        if not events:
            return state

        # Incremental replay on top of the checkpoint
        if aggregate_type == "trust" or isinstance(state.get("interactions"), int):
            for ev in events:
                self._apply_trust_event(state, ev)
        elif aggregate_type == "tft":
            # TFT scores are window-based; recompute from a full replay
            all_events = await self.event_store.replay_all(aggregate_type, aggregate_id)
            state = self._reconstruct_tft_state(all_events)

        state["_replayed_from"] = from_seq
        state["_replayed_count"] = len(events)
        return state

    # ═══════════════════════════════════════════
    # INTERNAL
    # ═══════════════════════════════════════════

    async def _latest_checkpoint(self, aggregate_type: str, aggregate_id: str) -> Optional[dict]:
        """Get the latest checkpoint for an aggregate (None if missing/corrupt)."""
        cursor = await self.db.execute(
            "SELECT sequence_number, state, checksum, created_at "
            "FROM checkpoints WHERE aggregate_type=? AND aggregate_id=? "
            "ORDER BY sequence_number DESC LIMIT 1",
            (aggregate_type, aggregate_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        # Verify checksum against the exact stored string (matches the write path).
        expected = _checksum(row["state"])
        if expected != row["checksum"]:
            print(f"[Checkpointer] WARNING: checksum mismatch for {aggregate_type}:{aggregate_id}")
            return None  # Corrupted — force full replay

        return {
            "sequence_number": row["sequence_number"],
            "state": row["state"],
            "checksum": row["checksum"],
            "created_at": row["created_at"],
        }

    async def prune(self, aggregate_type: str, aggregate_id: str, keep_last: int = 3):
        """Delete old checkpoints, keeping only the N most recent."""
        cursor = await self.db.execute(
            "SELECT id, sequence_number FROM checkpoints "
            "WHERE aggregate_type=? AND aggregate_id=? "
            "ORDER BY sequence_number DESC",
            (aggregate_type, aggregate_id),
        )
        rows = await cursor.fetchall()
        if len(rows) <= keep_last:
            return
        to_delete = [r["id"] for r in rows[keep_last:]]
        placeholders = ",".join("?" * len(to_delete))
        await self.db.execute(
            f"DELETE FROM checkpoints WHERE id IN ({placeholders})", to_delete
        )
        await self.db.commit()
