"""
EventBus — Redis pub/sub with in-process fallback for topic-based events.

Architecture:
  - Topics: agent:{id}, room:{name}, system, epoch, byzantine, economy,
            csd, stigmergy, all
  - Real Redis via aioredis (pub/sub channels prefixed "agora:event:")
  - In-process fallback via in-memory subscriber dict (no Redis needed)
  - Recent events buffer (capped per topic) for replay on connect
  - Each WebSocket connection maintains a set of subscribed topics

Usage:
  event_bus = EventBus(app)
  await event_bus.start()
  await event_bus.publish("agent:abc", "agent_thought", {...})
  await event_bus.subscribe(websocket, ["system", "agent:abc"])
  await event_bus.replay(websocket, ["system"])
"""

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

# Max recent events stored per topic
RECENT_MAX = 100


class EventBus:
    """Topic-based pub/sub with Redis (real or fallback) + in-process delivery."""

    def __init__(self, app):
        self.app = app
        # In-process subscription: websocket -> set[topic]
        self._subscriptions: dict[Any, set[str]] = {}
        # In-process reverse map: topic -> set[websocket]
        self._topic_subscribers: dict[str, set[Any]] = defaultdict(set)
        # Recent events buffer: topic -> list[dict]
        self._recent: dict[str, list[dict]] = defaultdict(list)
        # Redis
        self._redis = None
        self._pubsub = None
        self._redis_task: Optional[asyncio.Task] = None
        self._use_redis = False
        # Lock for subscriber bookkeeping
        self._lock = asyncio.Lock()

    # ── Lifecycle ──────────────────────────────────────────────

    async def start(self):
        """Initialise Redis connection (try real, fall back to in-process)."""
        from agora.config import settings

        # Try real Redis
        try:
            import redis.asyncio as aioredis

            redis_url = settings.redis_url or "redis://localhost:6379/0"
            self._redis = aioredis.from_url(
                redis_url, decode_responses=True, socket_connect_timeout=2
            )
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            self._use_redis = True
            print(f"[EventBus] Redis connected ({redis_url})")
        except Exception as e:
            self._redis = None
            self._pubsub = None
            self._use_redis = False
            print(f"[EventBus] Redis unavailable, using in-process: {e}")

        # Start Redis listener task if available
        if self._use_redis and self._pubsub:
            await self._pubsub.subscribe("agora:event:*")
            self._redis_task = asyncio.create_task(self._redis_listener())

    async def stop(self):
        """Shut down Redis listener and connections."""
        if self._redis_task:
            self._redis_task.cancel()
            try:
                await self._redis_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
        if self._redis:
            await self._redis.close()

    # ── Publish ────────────────────────────────────────────────

    async def publish(
        self, topic: str, event_type: str, payload: dict
    ) -> dict:
        """Publish an event to a topic.

        Stores in recent buffer, pushes to Redis (if available),
        and delivers to all in-process subscribers of this topic
        plus subscribers of 'all'.
        """
        event = {
            "id": str(uuid.uuid4())[:8],
            "topic": topic,
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # ── Recent buffer ──
        buf = self._recent[topic]
        buf.append(event)
        if len(buf) > RECENT_MAX:
            buf.pop(0)

        # ── Redis publish ──
        if self._use_redis and self._redis:
            try:
                channel = f"agora:event:{topic}"
                await self._redis.publish(channel, json.dumps(event))
            except Exception:
                pass  # Redis hiccup — don't break the event

        # ── In-process delivery ──
        await self._deliver_in_process(event)

        return event

    async def _deliver_in_process(self, event: dict):
        """Send event to all in-process WebSocket subscribers."""
        topic = event["topic"]
        targets: set[Any] = set()

        async with self._lock:
            # Subscribers of this specific topic
            if topic in self._topic_subscribers:
                targets.update(self._topic_subscribers[topic])
            # Subscribers of 'all' (catch-all)
            if "all" in self._topic_subscribers:
                targets.update(self._topic_subscribers["all"])

        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:
                # Clean up stale connection
                await self._remove_websocket(ws)

    # ── Subscribe / Unsubscribe ────────────────────────────────

    async def subscribe(self, websocket, topics: list[str]):
        """Subscribe a WebSocket connection to one or more topics."""
        async with self._lock:
            if websocket not in self._subscriptions:
                self._subscriptions[websocket] = set()
            subs = self._subscriptions[websocket]
            for t in topics:
                if t not in subs:
                    subs.add(t)
                    self._topic_subscribers[t].add(websocket)

    async def unsubscribe(self, websocket, topics: list[str]):
        """Unsubscribe a WebSocket from one or more topics."""
        async with self._lock:
            subs = self._subscriptions.get(websocket)
            if not subs:
                return
            for t in topics:
                if t in subs:
                    subs.discard(t)
                    self._topic_subscribers[t].discard(websocket)
                    if not self._topic_subscribers[t]:
                        del self._topic_subscribers[t]

    async def _remove_websocket(self, websocket):
        """Fully remove a WebSocket from all subscriptions."""
        async with self._lock:
            subs = self._subscriptions.pop(websocket, set())
            for t in subs:
                self._topic_subscribers[t].discard(websocket)
                if not self._topic_subscribers[t]:
                    self._topic_subscribers.pop(t, None)

    # ── Replay ─────────────────────────────────────────────────

    async def replay(
        self, websocket, topics: list[str], limit: int = 20
    ):
        """Send recent events for the given topics to a WebSocket."""
        sent = 0
        for topic in topics:
            events = list(self._recent.get(topic, []))
            for ev in events[-limit:]:
                try:
                    await websocket.send_json(ev)
                    sent += 1
                except Exception:
                    await self._remove_websocket(websocket)
                    return
        return sent

    # ── Redis listener (cross-process events) ──

    async def _redis_listener(self):
        """Listen for Redis pub/sub messages and re-deliver locally."""
        if not self._pubsub:
            return
        try:
            async for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                    # Re-deliver to local subscribers (avoids loop via
                    # _deliver_in_process which doesn't re-publish to Redis)
                    await self._deliver_in_process(event)
                except (json.JSONDecodeError, KeyError):
                    pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[EventBus] Redis listener error: {e}")

    # ── Stats ──────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return current EventBus stats."""
        return {
            "use_redis": self._use_redis,
            "subscribers": len(self._subscriptions),
            "topics": dict(
                (t, len(ws)) for t, ws in self._topic_subscribers.items()
            ),
            "recent_events": dict(
                (t, len(ev)) for t, ev in self._recent.items()
            ),
        }

    def get_recent(self, topic: str, limit: int = 20) -> list[dict]:
        """Get recent events for a topic (for API queries)."""
        return list(self._recent.get(topic, []))[-limit:]
