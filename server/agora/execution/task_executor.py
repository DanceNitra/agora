"""
Task Execution Pipeline — runs inside the tick loop.

Flow (Contract Net):
  1. Post new task → status='bidding'
  2. Agents bid (via dungeon API or LLM)
  3. Resolve: pick highest bidder → status='assigned'
  4. Track execution across ticks (metadata.target_ticks)
  5. Complete: reward agent + create artifact + broadcast

This is the bridge between the bidding API and actual task completion.
"""
import json
import random
import time
from typing import Any, Optional

# ── Task types the system auto-generates ──

AUTO_TASKS = [
    {"title": "Analyze recent trace patterns", "description": "Review the latest agent traces and identify emergent behavior patterns.",
     "task_type": "analysis", "difficulty": 2, "reward_energy": 12, "target_ticks": 3},
    {"title": "Draft exploration report", "description": "Compile findings from recent exploration into a structured report.",
     "task_type": "writing", "difficulty": 1, "reward_energy": 8, "target_ticks": 2},
    {"title": "Audit trust distribution", "description": "Verify trust scores across all agents are within expected ranges.",
     "task_type": "review", "difficulty": 3, "reward_energy": 15, "target_ticks": 4},
    {"title": "Research market trends", "description": "Analyze resource market prices and identify trading opportunities.",
     "task_type": "research", "difficulty": 2, "reward_energy": 10, "target_ticks": 3},
    {"title": "Synthesize knowledge graph", "description": "Merge recent findings into the collective knowledge graph.",
     "task_type": "analysis", "difficulty": 3, "reward_energy": 14, "target_ticks": 4},
    {"title": "Resolve coordination deadlock", "description": "Identify agents with conflicting goals and propose resolution.",
     "task_type": "review", "difficulty": 4, "reward_energy": 20, "target_ticks": 5},
    {"title": "Explore new resource vein", "description": "Dispatch explorers to locate and catalogue new resource deposits.",
     "task_type": "exploration", "difficulty": 2, "reward_energy": 10, "target_ticks": 3},
    {"title": "Optimize energy allocation", "description": "Review agent energy levels and redistribute surplus.",
     "task_type": "analysis", "difficulty": 2, "reward_energy": 10, "target_ticks": 3},
    {"title": "Generate system health report", "description": "Produce a comprehensive health report with KPIs and anomalies.",
     "task_type": "writing", "difficulty": 1, "reward_energy": 8, "target_ticks": 2},
    {"title": "Peer review recent artifacts", "description": "Cross-check recently created artifacts for quality and accuracy.",
     "task_type": "review", "difficulty": 2, "reward_energy": 10, "target_ticks": 3},
]

RESOURCE_REWARDS_BY_TYPE = {
    "analysis": 1,    # crystal_shards
    "writing": 2,     # herbs
    "review": 4,      # scroll_fragment
    "research": 4,    # scroll_fragment
    "exploration": 0, # gold_ore
}


class TaskExecutor:
    """Runs inside the tick loop: post → resolve → track → complete → reward."""

    def __init__(self, db):
        self.db = db
        self._running_tasks: dict[int, int] = {}  # task_id → remaining_ticks
        self._posted_count: int = 0
        self._task_index: int = 0

    async def tick(self, app) -> list[dict]:
        """Run one tick of the task pipeline. Returns list of events to broadcast."""
        events = []
        db = self.db

        # 1. POST a new task periodically (every 3 ticks average)
        if self._posted_count == 0 or random.random() < 0.33:
            task = await self._post_new_task(db)
            if task:
                self._posted_count += 1
                events.append({
                    "type": "task_posted",
                    "payload": {
                        "task_id": task["id"],
                        "title": task["title"],
                        "task_type": task.get("task_type", "unknown"),
                        "difficulty": task.get("difficulty", 1),
                    }
                })

        # 2. RESOLVE bidding tasks (pick highest bidder)
        resolved_before = len(self._running_tasks)
        resolved = await self._resolve_bidding(db, app)
        for r in resolved:
            events.append({
                "type": "task_assigned",
                "payload": r,
            })
            self._running_tasks[r["task_id"]] = r["target_ticks"]
        if resolved:
            print(f"[Tasks] Assigned {len(resolved)} tasks (running: {len(self._running_tasks)})")

        # 3. EXECUTE: decrement running tasks
        completed_ids = []
        for task_id in list(self._running_tasks.keys()):
            self._running_tasks[task_id] -= 1
            if self._running_tasks[task_id] <= 0:
                completed_ids.append(task_id)

        # 4. COMPLETE tasks that are done
        for task_id in completed_ids:
            result = await self._complete_task(task_id, db, app)
            if result:
                events.append({
                    "type": "task_completed",
                    "payload": result,
                })
            else:
                print(f"[Tasks] _complete_task returned None for #{task_id}")
            del self._running_tasks[task_id]

        return events

    async def _post_new_task(self, db) -> Optional[dict]:
        """Post one new auto-task to the market (status='bidding')."""
        tpl = AUTO_TASKS[self._task_index % len(AUTO_TASKS)]
        self._task_index += 1

        # Vary difficulty/reward slightly
        difficulty = max(1, tpl["difficulty"] + random.choice([-1, 0, 0, 1]))
        reward = tpl["reward_energy"] + random.randint(-2, 4)

        metadata = json.dumps({
            "difficulty": difficulty,
            "reward_energy": reward,
            "task_type": tpl["task_type"],
            "target_ticks": tpl["target_ticks"],
            "announced_by": "system",
            "auto": True,
        })

        cursor = await db.execute(
            "INSERT INTO tasks (title, description, status, priority, metadata) "
            "VALUES (?, ?, 'bidding', ?, ?)",
            (tpl["title"], tpl["description"], difficulty, metadata),
        )
        await db.commit()
        return {
            "id": cursor.lastrowid,
            "title": tpl["title"],
            "description": tpl["description"],
            "task_type": tpl["task_type"],
            "difficulty": difficulty,
            "reward_energy": reward,
            "target_ticks": tpl["target_ticks"],
        }

    async def _resolve_bidding(self, db, app) -> list[dict]:
        """Find tasks in 'bidding' state, assign to highest bidder or fallback random agent."""
        resolved = []

        # Pass 1: tasks WITH bids — pick highest bidder
        cursor = await db.execute(
            "SELECT id, title, metadata FROM tasks WHERE status='bidding' AND "
            "id IN (SELECT DISTINCT task_id FROM task_bids WHERE status='pending')"
            " ORDER BY priority DESC LIMIT 2"
        )
        tasks_with_bids = await cursor.fetchall()
        resolved += await self._resolve_and_assign(tasks_with_bids, db, require_bids=True)

        # Pass 2: tasks WITHOUT bids — auto-assign to random agent
        cursor = await db.execute(
            "SELECT id, title, metadata FROM tasks WHERE status='bidding' AND "
            "id NOT IN (SELECT DISTINCT task_id FROM task_bids WHERE status='pending')"
            " ORDER BY priority DESC LIMIT 1"
        )
        stale_tasks = await cursor.fetchall()
        resolved += await self._resolve_and_assign(stale_tasks, db, require_bids=False)

        return resolved

    async def _resolve_and_assign(self, tasks, db, require_bids: bool = True) -> list[dict]:
        """Assign each task to best bidder or random fallback."""
        resolved = []

        for task in tasks:
            task_id = task["id"]
            meta = json.loads(task["metadata"] or "{}")
            target_ticks = meta.get("target_ticks", 3)

            if require_bids:
                # Find highest bid
                cursor = await db.execute(
                    "SELECT tb.agent_id, tb.bid_amount, ai.role "
                    "FROM task_bids tb "
                    "JOIN agent_identities ai ON tb.agent_id = ai.agent_id "
                    "WHERE tb.task_id=? AND tb.status='pending' "
                    "ORDER BY tb.bid_amount DESC LIMIT 1",
                    (task_id,),
                )
                best = await cursor.fetchone()
                if best:
                    agent_id = best["agent_id"]
                    role = best["role"]
                    bid_amount = best["bid_amount"]
                    bid_reason = "highest bidder"
                else:
                    # No bids (edge case) — skip for this pass
                    continue
            else:
                # Auto-assign to random active agent
                cursor = await db.execute(
                    "SELECT agent_id, role FROM agent_identities WHERE status='active' "
                    "ORDER BY RANDOM() LIMIT 1"
                )
                random_agent = await cursor.fetchone()
                if not random_agent:
                    continue
                agent_id = random_agent["agent_id"]
                role = random_agent["role"]
                bid_amount = 0.5
                bid_reason = "auto-assigned (no bids)"

            # Accept bid / assign task
            await db.execute(
                "UPDATE task_bids SET status='accepted' WHERE task_id=? AND agent_id=?",
                (task_id, agent_id),
            )
            await db.execute(
                "UPDATE task_bids SET status='rejected' WHERE task_id=? AND agent_id!=?",
                (task_id, agent_id),
            )
            await db.execute(
                "UPDATE tasks SET status='assigned', assignee_id=?, updated_at=datetime('now') WHERE id=?",
                (agent_id, task_id),
            )
            await db.commit()

            resolved.append({
                "task_id": task_id,
                "title": task["title"],
                "agent_id": agent_id[:8],
                "role": role,
                "bid_amount": bid_amount,
                "bid_reason": bid_reason,
                "target_ticks": target_ticks,
            })

        return resolved

    async def _complete_task(self, task_id: int, db, app) -> Optional[dict]:
        """Mark a task as completed, reward the agent, create an artifact."""
        cursor = await db.execute(
            "SELECT t.id, t.title, t.assignee_id, t.metadata, "
            "COALESCE(ai.role, 'agent') as role "
            "FROM tasks t "
            "LEFT JOIN agent_identities ai ON t.assignee_id = ai.agent_id "
            "WHERE t.id=? AND t.status='assigned'",
            (task_id,),
        )
        task = await cursor.fetchone()
        if not task or not task["assignee_id"]:
            return None

        agent_id = task["assignee_id"]
        role = task["role"]
        meta = json.loads(task["metadata"] or "{}")
        task_type = meta.get("task_type", "general")
        reward_energy = meta.get("reward_energy", 10)
        difficulty = meta.get("difficulty", 1)

        # Reward: trust + energy
        trust_boost = 0.05 + (difficulty * 0.02)
        await db.execute(
            "UPDATE agent_identities SET trust_score=MIN(trust_score+?, 1.0), "
            "energy_balance=MIN(energy_balance+?, 100.0), updated_at=datetime('now') "
            "WHERE agent_id=?",
            (trust_boost, reward_energy, agent_id),
        )

        # Reward: random resource
        economy = getattr(app.state, "economy", None)
        resource_rewarded = None
        if economy:
            resources = await economy.get_all_resources()
            resource_idx = RESOURCE_REWARDS_BY_TYPE.get(task_type, 0)
            if resource_idx < len(resources):
                res = resources[resource_idx]
                qty = round(1.0 + difficulty * 0.5, 1)
                await economy.add_to_inventory(agent_id, res["id"], qty)
                resource_rewarded = {"name": res["name"], "quantity": qty}
            elif resources:
                res = random.choice(resources)
                qty = round(random.uniform(0.5, 1.5), 1)
                await economy.add_to_inventory(agent_id, res["id"], qty)
                resource_rewarded = {"name": res["name"], "quantity": qty}

        # Create artifact with generated content
        content = self._generate_artifact_content(task["title"], task_type, task["title"],
                                                   agent_id, role, difficulty)
        await db.execute(
            "INSERT INTO artifacts (agent_id, title, artifact_type, storage_path, "
            "mime_type, size_bytes, content, metadata) "
            "VALUES (?, ?, ?, ?, 'text/markdown', ?, ?, ?)",
            (
                agent_id,
                task["title"],
                task_type,
                f"tasks/task-{task_id}",
                len(content.encode("utf-8")),
                content,
                json.dumps({"task_id": task_id, "task_type": task_type, "difficulty": difficulty}),
            ),
        )

        # Mark task complete
        await db.execute(
            "UPDATE tasks SET status='completed', updated_at=datetime('now') WHERE id=?",
            (task_id,),
        )
        await db.commit()

        # Broadcast via inlined websocket push
        try:
            import json as _json
            from datetime import datetime as _dt
            event = {
                "type": "task_completed",
                "payload": {
                    "task_id": task_id,
                    "title": task["title"],
                    "agent_id": agent_id[:8],
                    "reward_energy": reward_energy,
                    "trust_boost": round(trust_boost, 3),
                    "resource_rewarded": resource_rewarded,
                    "task_type": task_type,
                },
                "timestamp": _dt.utcnow().isoformat(),
            }
            for ws in list(getattr(app.state, "active_connections", [])):
                try:
                    await ws.send_json(event)
                except Exception:
                    pass
        except Exception:
            pass  # broadcast not available

        return {
            "task_id": task_id,
            "title": task["title"],
            "agent_id": agent_id[:8],
            "reward_energy": reward_energy,
            "trust_boost": round(trust_boost, 3),
            "resource_rewarded": resource_rewarded,
        }

    @staticmethod
    def _generate_artifact_content(title: str, task_type: str, description: str,
                                    agent_id: str, role: str, difficulty: int) -> str:
        """Generate realistic markdown content for a completed task artifact."""
        now = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        template = f"""# {title}

## Metadata
- **Produced by:** {role} agent (`{agent_id[:8]}`)
- **Type:** {task_type}
- **Difficulty:** {difficulty}/5
- **Timestamp:** {now}

## Summary

"""
        body_templates = {
            "analysis": f"""This analysis examines the current state of the Agora agent ecosystem.

Key findings:
1. Agent trust distribution shows {"healthy diversity" if difficulty < 3 else "concentration issues"} across roles.
2. Task completion rate correlates positively with agent energy reserves.
3. Resource market dynamics indicate {"stable" if difficulty < 3 else "volatile"} supply patterns.
4. Coordination efficiency metrics suggest {"routine operations are normal" if difficulty < 3 else "emergent bottlenecks in peer-to-peer routing"}.

## Recommendations
- Monitor low-trust agents for potential failure cascades.
- Increase task posting frequency during high-energy periods.
- Review resource pricing for {"crystal_shards" if difficulty > 2 else "herbs and basic materials"}.
""",
            "writing": f"""## Report

This document summarizes findings from recent agent activities within the Agora ecosystem.

### Activity Overview
- Total agents active: {"all operational" if difficulty < 3 else "some agents approaching energy depletion"}
- Task pipeline throughput: {"nominal" if difficulty < 3 else "near capacity"}
- Artifact production rate: {"consistent" if difficulty < 3 else "variable, requiring optimization"}

### Highlights
{description or "Standard operational reporting period with no major anomalies."}

*Report generated by {role} agent.*
""",
            "review": f"""## Audit Report

**Scope:** {title}

### Criteria Evaluated
1. Data completeness
2. Processing accuracy
3. Timing and recency
4. Cross-agent consistency

### Findings
- **Overall quality score:** {"8/10 — Good" if difficulty < 3 else "6/10 — Needs improvement"}
- **Anomalies detected:** {"None" if difficulty < 2 else "Minor inconsistencies in trust score distribution"}
- **Recommendation:** {"Continue current operations" if difficulty < 3 else "Initiate corrective measures for low-performing agents"}

### Verdict
{"PASS" if difficulty < 4 else "REVIEW REQUIRED"} — Signed by {role} agent.
""",
            "research": f"""## Research Note

### Topic
{title}

### Context
{description or "Systematic investigation of current Agora operational parameters."}

### Preliminary Findings
1. Agent genome diversity {"is improving with each generation" if difficulty > 2 else "remains stable" }
2. Trust network density shows {"positive correlation with task throughput" if difficulty > 2 else "expected baseline values"}
3. Resource discovery rates {"are sufficient for current demand" if difficulty < 3 else "may require targeted exploration missions"}

### Next Steps
- {"Deep-dive analysis of trust network topology" if difficulty > 2 else "Routine data collection continues"}
- Monitor for emerging coordination patterns
""",
            "exploration": f"""## Exploration Log

### Mission
{title}

### Discoveries
- Surveyed {"multiple sectors" if difficulty > 2 else "designated area"} of the operational landscape
- {"New resource deposits identified" if difficulty > 2 else "Existing resources catalogued and verified"}
- {"Unusual agent coordination patterns observed near high-energy zones" if difficulty > 3 else "Standard exploration parameters maintained"}

### Resources Collected
- Primary findings catalogued for analysis
- Raw data stored for further processing

### Status
Exploration {"complete with valuable findings" if difficulty > 2 else "routine — no anomalies"}.
""",
            "general": f"""## Artifact: {title}

**Agent:** {role} (`{agent_id[:8]}`)
**Difficulty:** {difficulty}/5

{description or "Standard operational artifact produced during routine agent activity."}

---
*Auto-generated by Agora task execution pipeline.*
""",
        }

        body = body_templates.get(task_type, body_templates["general"])
        return template + body + f"\n\n---\n_Agora Engine · {now}_\n"

    async def get_stats(self) -> dict:
        """Return current executor stats."""
        return {
            "running_tasks": len(self._running_tasks),
            "active_task_ids": list(self._running_tasks.keys()),
            "total_tasks_posted": self._posted_count,
        }
