"""Recovery manager using event sourcing for checkpoint/rollback workflows."""

import json
import time
import uuid
from typing import Any, Optional


class RecoveryManager:
    """Event-sourced recovery manager for agent state checkpointing.

    Every state mutation is recorded as an event; checkpoints are snapshots
    of accumulated state that can be rolled back to.
    """

    def __init__(self):
        self._events: list[dict] = []
        self._checkpoints: dict[str, int] = {}  # checkpoint_id -> event index

    def create_checkpoint(
        self, label: str = "", meta: Optional[dict] = None
    ) -> str:
        """Create a checkpoint from the current event log position.

        Args:
            label: Human-readable label for the checkpoint.
            meta: Arbitrary metadata.

        Returns:
            Checkpoint ID (UUID string).
        """
        checkpoint_id = str(uuid.uuid4())
        event = {
            "type": "checkpoint",
            "checkpoint_id": checkpoint_id,
            "event_index": len(self._events),
            "label": label or f"checkpoint-{checkpoint_id[:8]}",
            "meta": meta or {},
            "timestamp": time.time(),
        }
        self._events.append(event)
        self._checkpoints[checkpoint_id] = len(self._events) - 1
        return checkpoint_id

    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """Roll the event log back to a named checkpoint.

        All events *after* the checkpoint are discarded.

        Args:
            checkpoint_id: The checkpoint to restore.

        Returns:
            True on success, False if the checkpoint does not exist.
        """
        if checkpoint_id not in self._checkpoints:
            return False

        target_idx = self._checkpoints[checkpoint_id]
        self._events = self._events[: target_idx + 1]

        # Rebuild checkpoint index after truncation
        self._checkpoints = {
            e["checkpoint_id"]: i
            for i, e in enumerate(self._events)
            if e["type"] == "checkpoint"
        }
        return True

    def list_checkpoints(self) -> list[dict]:
        """Return all checkpoint events in the log.

        Returns:
            List of checkpoint event dicts.
        """
        return [
            e
            for e in self._events
            if e["type"] == "checkpoint"
        ]

    def append_event(self, event_type: str, payload: Any) -> str:
        """Append a domain event to the log (used outside checkpointing).

        Args:
            event_type: Event type identifier.
            payload: Arbitrary event data (must be JSON-serializable).

        Returns:
            Event ID.
        """
        event_id = str(uuid.uuid4())
        event = {
            "type": event_type,
            "event_id": event_id,
            "payload": payload,
            "timestamp": time.time(),
        }
        self._events.append(event)
        return event_id

    def get_all_events(self) -> list[dict]:
        """Return the full event log (read-only view)."""
        return list(self._events)
