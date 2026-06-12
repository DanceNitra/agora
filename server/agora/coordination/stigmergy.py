"""Stigmergic coordination — agents communicate through shared trace pool.
Eliminates N^2 messaging overhead. O(N) instead of O(N^2).
Falls back to in-memory store when Redis is unavailable.
Now with DB persistence — traces survive restarts."""
import json
from collections import defaultdict
from datetime import datetime


class StigmergyPool:
    """Shared trace pool for indirect agent coordination.
    Writes to both in-memory (fast reads) and DB (persistence).
    On init, loads recent traces from DB into memory."""

    def __init__(self, redis_client=None, db=None, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.db = db
        self.ttl = ttl_seconds
        self._memory: dict[str, list[dict]] = {}

    async def load_from_db(self):
        """Load recent traces from DB into memory on startup."""
        if not self.db:
            return
        try:
            cursor = await self.db.execute(
                "SELECT agent_id, trace_type, payload, created_at FROM stigmergy_traces "
                "WHERE expires_at > datetime('now') ORDER BY created_at DESC LIMIT 500"
            )
            rows = await cursor.fetchall()
            for row in rows:
                key = f"stigmergy:{row['trace_type']}"
                if key not in self._memory:
                    self._memory[key] = []
                self._memory[key].append({
                    "agent_id": row["agent_id"],
                    "task_type": row["trace_type"],
                    "result_preview": row["payload"][:200] if row["payload"] else "",
                    "timestamp": row["created_at"],
                    "trust_delta": 0.0,
                })
            print(f"[Stigmergy] Loaded {len(rows)} traces from DB")
        except Exception as e:
            print(f"[Stigmergy] DB load error: {e}")

    async def write_trace(self, agent_id: str, task_type: str,
                          result: str, trust_delta: float = 0.0):
        trace = {"agent_id": agent_id, "task_type": task_type,
                 "result_preview": result[:200], "trust_delta": trust_delta,
                 "timestamp": datetime.utcnow().isoformat()}
        key = f"stigmergy:{task_type}"

        # In-memory (fast reads)
        if key not in self._memory:
            self._memory[key] = []
        self._memory[key].insert(0, trace)
        self._memory[key] = self._memory[key][:200]

        # Redis (if available)
        if self.redis:
            await self.redis.lpush(key, json.dumps(trace))
            await self.redis.ltrim(key, 0, 199)
            await self.redis.expire(key, self.ttl)

        # DB persistence
        if self.db:
            try:
                await self.db.execute(
                    "INSERT INTO stigmergy_traces (id, agent_id, trace_type, payload, ttl_seconds, expires_at) "
                    "VALUES (lower(hex(randomblob(16))), ?, ?, ?, ?, datetime('now', '+' || ? || ' seconds'))",
                    (agent_id, task_type, json.dumps(trace), self.ttl, self.ttl),
                )
                await self.db.commit()
            except Exception as e:
                print(f"[Stigmergy] DB write error: {e}")

        # Event sourcing integration (non-blocking, best-effort)
        if getattr(self, "event_store", None):
            try:
                await self.event_store.append(
                    aggregate_type="stigmergy",
                    aggregate_id=f"{task_type}",
                    event_type="trace_written",
                    payload={
                        "agent_id": agent_id,
                        "task_type": task_type,
                        "result_preview": result[:200],
                        "trust_delta": trust_delta,
                    },
                    metadata={"caller": "StigmergyPool.write_trace"},
                )
            except Exception:
                pass

    async def best_agent(self, task_type: str, min_traces: int = 3) -> dict | None:
        key = f"stigmergy:{task_type}"
        traces = self._memory.get(key, [])

        # If memory empty, try DB
        if not traces and self.db:
            try:
                cursor = await self.db.execute(
                    "SELECT agent_id, payload FROM stigmergy_traces "
                    "WHERE trace_type=? AND expires_at > datetime('now') ORDER BY created_at DESC LIMIT 200",
                    (task_type,),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    try:
                        p = json.loads(row["payload"])
                        traces.append(p)
                    except (json.JSONDecodeError, TypeError):
                        traces.append({
                            "agent_id": row["agent_id"],
                            "task_type": task_type,
                            "result_preview": "",
                            "trust_delta": 0.0,
                        })
            except Exception:
                pass

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

    async def get_traces_by_agent(self, agent_id: str, limit: int = 50) -> list[dict]:
        """Get all traces for a specific agent from DB."""
        if not self.db:
            return []
        try:
            cursor = await self.db.execute(
                "SELECT payload FROM stigmergy_traces "
                "WHERE agent_id=? AND expires_at > datetime('now') ORDER BY created_at DESC LIMIT ?",
                (agent_id, limit),
            )
            results = []
            for row in await cursor.fetchall():
                try:
                    results.append(json.loads(row["payload"]))
                except (json.JSONDecodeError, TypeError):
                    pass
            return results
        except Exception:
            return []

    async def get_all_trace_types(self) -> list[str]:
        """Get distinct trace types from DB."""
        if not self.db:
            return list(self._memory.keys())
        try:
            cursor = await self.db.execute(
                "SELECT DISTINCT trace_type FROM stigmergy_traces "
                "WHERE expires_at > datetime('now') ORDER BY trace_type"
            )
            return [row["trace_type"] for row in await cursor.fetchall()]
        except Exception:
            return list(self._memory.keys())
