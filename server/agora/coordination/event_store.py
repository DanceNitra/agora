"""
EventStore — Append-only event log with stream replay.

Architecture:
  - Events are grouped by (aggregate_type, aggregate_id) into streams.
  - Each event in a stream has a monotonic sequence_number.
  - Streams can be replayed from any point to reconstruct state.
  - The EventStore is write-only for operational code;
    state reconstruction happens in the reading layer (checkpointing).

Usage:
  store = EventStore(db)
  await store.append('trust', 'agent:alice:agent:bob', 'trust_updated',
                     {'score': 0.7, 'outcome': 'cooperate'})
  stream = await store.read_stream('trust', 'agent:alice:agent:bob')
  # stream[0] = {..., sequence_number: 1, ...}
  # stream[1] = {..., sequence_number: 2, ...}

  # Replay from sequence 3 onwards:
  stream = await store.read_stream('trust', 'agent:alice:agent:bob', from_sequence=3)

  # Count events in a stream:
  count = await store.stream_length('trust', 'agent:alice:agent:bob')

  # List all aggregate IDs for a type (for dashboard/recovery):
  aggregates = await store.list_aggregates('trust')
"""

import json
from datetime import datetime, timezone
from typing import Optional


class EventStore:
    """Append-only event log with stream replay."""

    def __init__(self, db):
        self.db = db

    async def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict,
        metadata: dict | None = None,
    ) -> dict:
        """Append an event to a stream. Returns the stored event dict."""
        # Get next sequence number
        cursor = await self.db.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_seq "
            "FROM event_store WHERE aggregate_type=? AND aggregate_id=?",
            (aggregate_type, aggregate_id),
        )
        row = await cursor.fetchone()
        next_seq = row["next_seq"] if row else 1

        event = {
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "sequence_number": next_seq,
            "event_type": event_type,
            "payload": json.dumps(payload),
            "metadata": json.dumps(metadata or {}),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        await self.db.execute(
            """INSERT INTO event_store
               (aggregate_type, aggregate_id, sequence_number, event_type, payload, metadata, occurred_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event["aggregate_type"],
                event["aggregate_id"],
                event["sequence_number"],
                event["event_type"],
                event["payload"],
                event["metadata"],
                event["occurred_at"],
            ),
        )
        await self.db.commit()

        return event

    async def read_stream(
        self,
        aggregate_type: str,
        aggregate_id: str,
        from_sequence: int = 1,
        limit: int = 1000,
    ) -> list[dict]:
        """Read events from a stream, ordered by sequence_number."""
        cursor = await self.db.execute(
            """SELECT id, aggregate_type, aggregate_id, sequence_number,
                      event_type, payload, metadata, occurred_at
               FROM event_store
               WHERE aggregate_type=? AND aggregate_id=? AND sequence_number >= ?
               ORDER BY sequence_number ASC
               LIMIT ?""",
            (aggregate_type, aggregate_id, from_sequence, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "aggregate_type": r["aggregate_type"],
                "aggregate_id": r["aggregate_id"],
                "sequence_number": r["sequence_number"],
                "event_type": r["event_type"],
                "payload": json.loads(r["payload"]),
                "metadata": json.loads(r["metadata"]),
                "occurred_at": r["occurred_at"],
            }
            for r in rows
        ]

    async def stream_length(self, aggregate_type: str, aggregate_id: str) -> int:
        """Return the number of events in a stream."""
        cursor = await self.db.execute(
            "SELECT COUNT(*) AS cnt FROM event_store WHERE aggregate_type=? AND aggregate_id=?",
            (aggregate_type, aggregate_id),
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    async def list_aggregates(self, aggregate_type: str) -> list[str]:
        """List all aggregate IDs for a given type (for recovery/dashboard)."""
        cursor = await self.db.execute(
            "SELECT DISTINCT aggregate_id FROM event_store WHERE aggregate_type=? ORDER BY aggregate_id",
            (aggregate_type,),
        )
        rows = await cursor.fetchall()
        return [r["aggregate_id"] for r in rows]

    async def replay_all(self, aggregate_type: str, aggregate_id: str) -> list[dict]:
        """Full stream replay (convenience, uses read_stream internally)."""
        return await self.read_stream(aggregate_type, aggregate_id, from_sequence=1, limit=100000)

    async def latest_event(self, aggregate_type: str, aggregate_id: str) -> dict | None:
        """Get the most recent event in a stream."""
        cursor = await self.db.execute(
            """SELECT id, aggregate_type, aggregate_id, sequence_number,
                      event_type, payload, metadata, occurred_at
               FROM event_store
               WHERE aggregate_type=? AND aggregate_id=?
               ORDER BY sequence_number DESC LIMIT 1""",
            (aggregate_type, aggregate_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "aggregate_type": row["aggregate_type"],
            "aggregate_id": row["aggregate_id"],
            "sequence_number": row["sequence_number"],
            "event_type": row["event_type"],
            "payload": json.loads(row["payload"]),
            "metadata": json.loads(row["metadata"]),
            "occurred_at": row["occurred_at"],
        }

    async def delete_stream(self, aggregate_type: str, aggregate_id: str) -> int:
        """Delete all events for a stream (for testing/tidy-up). Returns count deleted."""
        cursor = await self.db.execute(
            "DELETE FROM event_store WHERE aggregate_type=? AND aggregate_id=?",
            (aggregate_type, aggregate_id),
        )
        await self.db.commit()
        return cursor.rowcount
