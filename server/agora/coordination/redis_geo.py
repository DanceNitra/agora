"""RedisGeo — NPC spatial tracking cez Redis (upravené pre pixelové súradnice).

Používa Redis dátové štruktúry:
  - HASH `npc:rooms` — NPC_name → room_name
  - ZSET `npc:positions` — NPC_name → pixel score (linearizovaná pozícia)
  - SET `npc:room:{room_name}` — členovia roomy pre rýchle query

Pixel → score: score = x + y * 10000 (linearizácia 2D do 1D pre ZSET)
"""

import json
import math
from typing import Any, Optional

from agora.config import settings

# Linearizácia pixel position pre Redis ZSET
# score = x + y * MAP_WIDTH (1280 by default, use 10000 for safety)
MAP_WIDTH = 10000

# Attempt real Redis; fall back to fakeredis
_redis_client = None

try:
    import fakeredis
    _fallback = fakeredis.FakeStrictRedis()
except ImportError:
    _fallback = None

try:
    import redis.asyncio as aioredis
    _redis_available = True
except ImportError:
    _redis_available = False


def _pos_to_score(x: float, y: float) -> float:
    """Linearize pixel (x, y) into a single Redis ZSET score."""
    return x + y * MAP_WIDTH


def _score_to_pos(score: float) -> tuple[float, float]:
    """Reverse linearization: score → (x, y)."""
    y = int(score // MAP_WIDTH)
    x = score - y * MAP_WIDTH
    return x, y


def get_redis_client():
    """Get Redis client (real async or fakeredis fallback)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if _redis_available:
        redis_url = getattr(settings, 'redis_url', None) or "redis://localhost:6379/0"
        try:
            _redis_client = aioredis.from_url(redis_url, decode_responses=True)
            return _redis_client
        except Exception:
            pass

    _redis_client = _fallback
    return _redis_client


# ═══════════════════════════════════════════
# KEYS
# ═══════════════════════════════════════════

KEY_ROOMS = "npc:rooms"           # HASH: name → room
KEY_POSITIONS = "npc:positions"   # ZSET: name → score (linearizovaný pixel)
KEY_ROOM_PREFIX = "npc:room:"     # SET: npc:room:{room} → [name, ...]


def _room_set(room: str) -> str:
    return f"{KEY_ROOM_PREFIX}{room}"


# ═══════════════════════════════════════════
# NPC POSITION TRACKING
# ═══════════════════════════════════════════

async def update_npc_position(npc_name: str, x: float, y: float, room: str = ""):
    """Update NPC position in Redis."""
    r = get_redis_client()
    try:
        score = _pos_to_score(x, y)
        await r.zadd(KEY_POSITIONS, {npc_name: score})

        old_room = await r.hget(KEY_ROOMS, npc_name)
        if room:
            await r.hset(KEY_ROOMS, npc_name, room)
            # Remove from old room set, add to new
            if old_room and old_room != room:
                await r.srem(_room_set(old_room), npc_name)
            await r.sadd(_room_set(room), npc_name)
    except Exception as e:
        print(f"[RedisGeo] Position error: {e}")


async def get_npc_position(npc_name: str) -> Optional[dict]:
    """Get NPC position from Redis ZSET."""
    r = get_redis_client()
    try:
        score = await r.zscore(KEY_POSITIONS, npc_name)
        if score is not None:
            x, y = _score_to_pos(score)
            return {"x": x, "y": y}
    except Exception:
        pass
    return None


async def get_npcs_in_room(room_name: str) -> list[str]:
    """Get all NPC names in a room."""
    r = get_redis_client()
    try:
        members = await r.smembers(_room_set(room_name))
        return list(members) if members else []
    except Exception:
        return []


async def get_all_npc_rooms() -> dict[str, str]:
    """Get {npc_name: room_name} mapping."""
    r = get_redis_client()
    try:
        return await r.hgetall(KEY_ROOMS) or {}
    except Exception:
        return {}


async def get_nearby_npcs(npc_name: str, radius_px: float = 200) -> list[dict]:
    """Find NPCs within pixel radius using ZSET range query.

    Uses linearized score: nearby means score ± radius.
    """
    r = get_redis_client()
    try:
        score = await r.zscore(KEY_POSITIONS, npc_name)
        if score is None:
            return []

        x, y = _score_to_pos(score)
        nearby = []

        # Get all NPCs and filter by distance
        all_scores = await r.zrange(KEY_POSITIONS, 0, -1, withscores=True)
        for name, other_score in all_scores:
            if name == npc_name:
                continue
            ox, oy = _score_to_pos(other_score)
            dist = math.sqrt((x - ox) ** 2 + (y - oy) ** 2)
            if dist <= radius_px:
                nearby.append({"name": name, "distance": round(dist, 1)})

        return sorted(nearby, key=lambda n: n["distance"])
    except Exception:
        return []


async def remove_npc(npc_name: str):
    """Remove NPC from Redis tracking."""
    r = get_redis_client()
    try:
        old_room = await r.hget(KEY_ROOMS, npc_name)
        await r.zrem(KEY_POSITIONS, npc_name)
        await r.hdel(KEY_ROOMS, npc_name)
        if old_room:
            await r.srem(_room_set(old_room), npc_name)
    except Exception:
        pass


# ═══════════════════════════════════════════
# BULK SYNC
# ═══════════════════════════════════════════

async def sync_all_npcs_to_redis(db):
    """Bulk-sync all active NPCs from DB to Redis."""
    try:
        cursor = await db.execute(
            "SELECT npc_name, pos_x, pos_y FROM dungeon_npcs WHERE status='active'"
        )
        npcs = await cursor.fetchall()
        r = get_redis_client()

        # Clear old data
        await r.delete(KEY_POSITIONS, KEY_ROOMS)
        room_keys = await r.keys(f"{KEY_ROOM_PREFIX}*")
        if room_keys:
            await r.delete(*room_keys)

        for npc in npcs:
            try:
                from agora.agent_os.dungeon_map import get_room_at
                room = get_room_at(npc["pos_x"], npc["pos_y"]) or "main_hall"
                await update_npc_position(npc["npc_name"], npc["pos_x"], npc["pos_y"], room)
            except Exception as e:
                # Fallback: use default room
                await update_npc_position(npc["npc_name"], npc["pos_x"], npc["pos_y"], "main_hall")
                print(f"[RedisGeo] Sync skip {npc['npc_name']}: {e}")

        print(f"[RedisGeo] Synced {len(npcs)} NPCs to Redis")
    except Exception as e:
        print(f"[RedisGeo] Sync error: {e}")
