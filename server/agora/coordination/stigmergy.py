"""
Stigmergic coordination — agents communicate through shared trace pool.
Eliminates N² messaging overhead. O(N) instead of O(N²).
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any


class StigmergyPool:
    """
    Shared trace pool for indirect agent coordination.

    Agents write traces: {agent_id, task_type, result, trust_delta}
    Other agents read: best_agent(task_type) — who handles what best.
    """

    def __init__(self, redis_client, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl = ttl_seconds

    async def write_trace(
        self, agent_id: str, task_type: str, result: str, trust_delta: float = 0.0
    ):
        """Write a completion trace to the pool."""
        trace = {
            "agent_id": agent_id,
            "task_type": task_type,
            "result_preview": result[:200],
            "trust_delta": trust_delta,
            "timestamp": datetime.utcnow().isoformat()
        }
        key = f"stigmergy:{task_type}"
        await self.redis.lpush(key, json.dumps(trace))
        await self.redis.ltrim(key, 0, 199)  # Keep max 200 traces per type
        await self.redis.expire(key, self.ttl)

    async def best_agent(self, task_type: str, min_traces: int = 3) -> dict | None:
        """Find the best agent for a task type based on trace history."""
        key = f"stigmergy:{task_type}"
        traces = await self.redis.lrange(key, 0, -1)
        if len(traces) < min_traces:
            return None

        # Score each agent by success rate (trust_delta > 0 = success)
        agent_scores = defaultdict(lambda: {"successes": 0, "total": 0, "avg_delta": 0.0})

        for t in traces:
            trace = json.loads(t)
            aid = trace["agent_id"]
            agent_scores[aid]["total"] += 1
            agent_scores[aid]["avg_delta"] += trace["trust_delta"]
            if trace["trust_delta"] >= 0:
                agent_scores[aid]["successes"] += 1

        # Find best
        best = None
        best_score = -float("inf")
        for aid, stats in agent_scores.items():
            if stats["total"] < min_traces:
                continue
            success_rate = stats["successes"] / stats["total"]
            avg_delta = stats["avg_delta"] / stats["total"]
            score = success_rate * 0.7 + avg_delta * 0.3
            if score > best_score:
                best_score = score
                best = {"agent_id": aid, "score": round(score, 3), "total": stats["total"]}

        return best

    async def recent_alerts(self, limit: int = 10) -> list[dict]:
        """Get recent defection alerts."""
        key = "stigmergy:alert"
        traces = await self.redis.lrange(key, 0, limit - 1)
        return [json.loads(t) for t in traces]
