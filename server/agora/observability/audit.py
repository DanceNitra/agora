"""Append-only audit logger for agent and system events."""

import json
import time
import uuid
from typing import Any, Callable, Optional


class AuditLogger:
    """Append-only audit log for recording and replaying system events.

    Every event is assigned a monotonic sequence number, a UUID, and a
    timestamp. Events cannot be deleted or modified — only appended.
    """

    def __init__(self):
        self._events: list[dict] = []
        self._seq = 0

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str = "",
        detail: Optional[dict] = None,
        meta: Optional[dict] = None,
    ) -> str:
        """Record a new audit event.

        Args:
            event_type: Category of the event (e.g. "identity", "execution").
            actor: Who/what performed the action.
            action: What was done (e.g. "create", "deactivate").
            resource: The resource affected (optional).
            detail: Structured detail about the event.
            meta: Arbitrary metadata.

        Returns:
            The event ID string.
        """
        event_id = str(uuid.uuid4())
        self._seq += 1
        event = {
            "id": event_id,
            "seq": self._seq,
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "resource": resource,
            "detail": detail or {},
            "meta": meta or {},
            "timestamp": time.time(),
        }
        self._events.append(event)
        return event_id

    def get_events(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Query events with optional filters.

        Args:
            event_type: Filter by event type.
            actor: Filter by actor.
            action: Filter by action.
            limit: Maximum number of results (default 100).
            offset: Skip N results for pagination.

        Returns:
            List of matching event dicts, newest first.
        """
        results = list(self._events)  # copy

        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        if actor:
            results = [e for e in results if e["actor"] == actor]
        if action:
            results = [e for e in results if e["action"] == action]

        # Newest first
        results.reverse()
        return results[offset : offset + limit]

    def replay_events(
        self,
        handler: Callable[[dict], Any],
        event_type: Optional[str] = None,
        start_seq: int = 1,
    ) -> int:
        """Replay events through a handler function.

        Useful for rebuilding state or applying side-effects from the
        event log.

        Args:
            handler: A callable that receives each event dict.
            event_type: Optional filter to replay only matching events.
            start_seq: Start replaying from this sequence number (1-indexed).

        Returns:
            Number of events replayed.
        """
        count = 0
        for event in self._events:
            if event["seq"] < start_seq:
                continue
            if event_type and event["event_type"] != event_type:
                continue
            handler(event)
            count += 1
        return count

    def get_event_count(self) -> int:
        """Return the total number of events in the log."""
        return len(self._events)

    def clear(self) -> None:
        """Clear all events (testing utility — violates append-only in prod)."""
        self._events.clear()
        self._seq = 0
