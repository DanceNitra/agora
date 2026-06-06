"""Stigmergic coordination — agents communicate through shared trace pool.
Eliminates N^2 messaging overhead. O(N) instead of O(N^2).
Falls back to in-memory store when Redis is unavailable."""

import json
from collections import defaultdict
from datetime import datetime


class StigmergyPool:
    """Shared trace pool for indirect agent coordination.
    Falls back to in-memory dict when Redis is unavailable."""

    def __init__(self, redis_client=None, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self._memory: dict[str, list[dict]] = {}

    async def write_trace(self, agent_id: str, task_type: str,
                          result: str, trust_delta: float = 0.0):
        trace = {"agent_id": agent_id, "task_type": task_type,
                 "result_preview": result[:200], "trust_delta": trust_delta,
                 "timestamp": datetime.utcnow().isoformat()}
        key = f"stigmergy:{task_type}"
        if self.redis:
            await self.redis.lpush(key, json.dumps(trace))
            await self.redis.ltrim(key, 0, 199)
            await self.redis.expire(key, self.ttl)
        else:
            if key not in self._memory:
                self._memory[key] = []
            self._memory[key].insert(0, trace)
            self._memory[key] = self._memory[key][:200]

    async def best_agent(self, task_type: str, min_traces: int = 3) -> dict | None:
        key = f"stigmergy:{task_type}"
        if self.redis:
            traces = await self.redis.lrange(key, 0, -1)
            traces = [json.loads(t) for t in traces]
        else:
            traces = self._memory.get(key, [])

        if len(traces) < min_traces:
            return None

        agent_scores = defaultdict(lambda: {"successes": 0, "total": 0, "avg_delta": 0.0})
        for t in traces:
            aid = t["agent_id"]
            agent_scores[aid]["total"] += 1
            agent_scores[aid]["avg_delta"] += t.get("trust_delta", 0)
            if t.get("trust_delta", 0) >= 0:
                agent_scores[aid]["successes"] += 1

        best, best_score = None, -float("inf")
        for aid, stats in agent_scores.items():
            if stats["total"] < min_traces:
                continue
            score = (stats["successes"] / stats["total"]) * 0.7 + (
                stats["avg_delta"] / stats["total"]) * 0.3
            if score > best_score:
                best_score, best = score, {"agent_id": aid, "score": round(score, 3),
                                           "total": stats["total"]}
        return best

    async def recent_alerts(self, limit: int = 10) -> list[dict]:
        key = "stigmergy:alert"
        if self.redis:
            return [json.loads(t) for t in await self.redis.lrange(key, 0, limit - 1)]
        return self._memory.get(key, [])[:limit]

    async def alert(self, message: str):
        await self.write_trace("system", "alert", message, -0.3)
