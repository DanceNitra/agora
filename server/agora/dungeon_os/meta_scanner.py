"""MetaScanner — system self-analysis and meta-quest generation.

Phase 3: Recursive Self-Improvement Loop.

The MetaScanner periodically analyzes the corporation's own health metrics
and generates meta-quests to improve the system itself.

What it looks at:
  - Agent pool health (count, trust distribution, energy levels)
  - Quest pipeline (completion rate, phase transition speed, pass rate)
  - Research quality (CEO/CTO approval rate, compound lesson value)
  - Knowledge gap density (which subsystems are under-researched)
  - Prompt staleness (how many Ticks since prompt last changed)
"""

import json
from datetime import datetime
from typing import Optional

from agora.dungeon_os.corporation_memory import CorporationMemory


# Meta-quest templates — self-improvement opportunity templates
META_QUEST_TEMPLATES = {
    "low_agent_trust": {
        "title": "Investigate and fix agent trust deflation",
        "goal": (
            "System trust scores are abnormally low ({metric_value:.0%} avg). "
            "This indicates either: (a) genuinely poor agent behavior, "
            "(b) misconfigured trust thresholds, or (c) a trust scoring bug. "
            "Investigate the root cause and propose a fix."
        ),
        "subsystem": "safety",
        "criteria": [
            "Diagnose why trust is low (is it the agents or the scoring?)",
            "Propose specific threshold or algorithm adjustments",
            "Run a simulation to verify the fix",
        ],
        "reward": 40,
    },
    "slow_quest_completion": {
        "title": "Optimize quest lifecycle — agents are stuck in HEAD phase",
        "goal": (
            "Quests are completing slowly. Phase transitions are taking "
            "long ({metric_value:.1f} avg ticks per completed quest). "
            "Analyze the bottleneck and propose a pipeline optimization."
        ),
        "subsystem": "tooling",
        "criteria": [
            "Identify the bottleneck phase (HEAD vs PATA vs COMPOUND)",
            "Propose a change to acceleration (parallelism, timeout reduction)",
            "If possible, implement the fix",
        ],
        "reward": 50,
    },
    "low_ceo_approval": {
        "title": "Improve research quality — CEO/CTO rejecting too many proposals",
        "goal": (
            "CEO/CTO is rejecting {metric_value:.0%} of proposals. "
            "Either the Scout is finding bad leads or the researchers "
            "are producing low-quality summaries. Investigate and improve."
        ),
        "subsystem": "knowledge",
        "criteria": [
            "Analyze the last 5 rejected proposals — what pattern do they share?",
            "Identify whether the issue is Scout (bad leads) or Researcher (poor synthesis)",
            "Propose a filter improvement for the culprit",
        ],
        "reward": 35,
    },
    "energy_crisis": {
        "title": "Balance agent energy — risk of mass starvation",
        "goal": (
            "Average agent energy is critically low at {metric_value:.1f}. "
            "Agents may start dying soon. Investigate the economy imbalance "
            "and propose a resource injection or production boost."
        ),
        "subsystem": "economy",
        "criteria": [
            "Check production vs consumption rates per role",
            "Identify which resources are scarce",
            "Propose an energy injection or production tweak",
        ],
        "reward": 60,
    },
    "prompt_stale": {
        "title": "Refresh agent prompts with corporation memory",
        "goal": (
            "Agent prompts haven't been updated in {metric_value} cycles. "
            "Corporation memory contains accumulated lessons that could "
            "improve agent reasoning. Apply relevant lessons to each role's prompt."
        ),
        "subsystem": "knowledge",
        "criteria": [
            "Review latest 10 corporation memory entries",
            "Map lessons to affected agent roles",
            "Generate updated prompts incorporating the lessons",
        ],
        "reward": 30,
    },
    "low_research_findings": {
        "title": "Explore new research directions — no quests created recently",
        "goal": (
            "No research quests have been created in {metric_value} ticks. "
            "The corporation is stagnating. Either the Scout is failing "
            "or there's nothing interesting on the horizon."
        ),
        "subsystem": "knowledge",
        "criteria": [
            "Check if Scout is functional (GitHub API check)",
            "Broaden search scope to find new opportunities",
            "Create at least one new research quest",
        ],
        "reward": 25,
    },
}


class MetaScanner:
    """Scans corporation health and generates meta-quests for improvement.

    Each tick (or every N ticks), this analyzes:
      - Agent stats (trust, energy, count)
      - Quest stats (completion rate, phase distribution)
      - Research quality (approval rate, findings quality)
      - Memory richness (how many lessons, impact trends)
      - Prompt staleness (tick count since last prompt update)
    """

    def __init__(self, db, quest_engine=None, memory: Optional[CorporationMemory] = None):
        self.db = db
        self.qe = quest_engine
        self.memory = memory
        self._meta_quest_count = 0
        self._last_scan_tick = 0
        self._scan_interval = 20  # Every 20 ticks (~100s at 5s/tick)

    async def scan_and_act(self, tick_count: int) -> list[dict]:
        """Run a meta-scan if enough ticks have passed.

        Returns:
            list of meta-quest creation results (or empty list if skipped)
        """
        if tick_count - self._last_scan_tick < self._scan_interval:
            return []

        self._last_scan_tick = tick_count
        return await self._run_scan()

    async def _run_scan(self) -> list[dict]:
        """Analyze system health and create meta-quests for improvement."""
        print(f"[MetaScanner] Running scan at tick...")
        results = []

        # Gather metrics
        metrics = await self._gather_metrics()

        # Evaluate each template against current metrics
        triggered_quests = []
        for template_key, template in META_QUEST_TEMPLATES.items():
            trigger = self._evaluate_trigger(template_key, metrics)
            if trigger:
                triggered_quests.append((template, trigger))

        # Create meta-quests for triggered templates (max 2 per scan)
        for template, trigger in triggered_quests[:2]:
            result = await self._create_meta_quest(template, trigger)
            if result:
                results.append(result)

        if not results:
            print(f"[MetaScanner] No meta-quests triggered — system healthy")
            results.append({"status": "healthy", "metrics": metrics})

        return results

    async def _gather_metrics(self) -> dict:
        """Collect system health metrics."""
        metrics = {}

        # Agent metrics
        try:
            cursor = await self.db.execute(
                "SELECT COUNT(*) as cnt, AVG(trust_score) as avg_trust, "
                "AVG(energy_balance) as avg_energy, "
                "SUM(CASE WHEN energy_balance < 10 THEN 1 ELSE 0 END) as starving "
                "FROM agent_identities WHERE status='active'"
            )
            row = await cursor.fetchone()
            if row:
                metrics["agent_count"] = row["cnt"] or 0
                metrics["avg_trust"] = row["avg_trust"] or 0.5
                metrics["avg_energy"] = row["avg_energy"] or 50.0
                metrics["starving_agents"] = row["starving"] or 0
        except Exception as e:
            print(f"[MetaScanner] Agent metrics error: {e}")

        # Quest metrics
        try:
            cursor = await self.db.execute("SELECT COUNT(*) as cnt, status FROM quests GROUP BY status")
            quest_rows = await cursor.fetchall()
            metrics["quest_counts"] = {r["status"]: r["cnt"] for r in quest_rows}

            # Average time to complete
            cursor = await self.db.execute(
                "SELECT AVG(CAST(julianday(completed_at) - julianday(created_at) AS REAL) * 24 * 60) as avg_minutes "
                "FROM quests WHERE status='done' AND completed_at IS NOT NULL"
            )
            row = await cursor.fetchone()
            metrics["avg_completion_minutes"] = row[0] if row and row[0] else None

            # Phase distribution
            cursor = await self.db.execute(
                "SELECT phase, COUNT(*) as cnt FROM quests GROUP BY phase"
            )
            metrics["phase_distribution"] = {r["phase"]: r["cnt"] for r in await cursor.fetchall()}
        except Exception as e:
            print(f"[MetaScanner] Quest metrics error: {e}")

        # CEO/CTO approval rate
        try:
            cursor = await self.db.execute(
                "SELECT proposal_status, COUNT(*) as cnt FROM quests "
                "WHERE proposal_status IS NOT NULL AND proposal_status != 'pending' "
                "GROUP BY proposal_status"
            )
            metrics["proposal_statuses"] = {r["proposal_status"]: r["cnt"] for r in await cursor.fetchall()}
        except Exception as e:
            print(f"[MetaScanner] Proposal metrics error: {e}")

        # Corporation memory stats
        if self.memory:
            try:
                metrics["memory_stats"] = await self.memory.get_stats()
            except Exception as e:
                print(f"[MetaScanner] Memory stats error: {e}")

        # Research findings count
        try:
            cursor = await self.db.execute("SELECT COUNT(*) as cnt FROM research_findings")
            row = await cursor.fetchone()
            metrics["research_findings_count"] = row[0] if row else 0
        except Exception:
            pass

        return metrics

    def _evaluate_trigger(self, template_key: str, metrics: dict) -> Optional[dict]:
        """Check if a metric condition triggers a meta-quest template.

        Returns the trigger values dict or None if not triggered.
        """
        avg_trust = metrics.get("avg_trust", 0.5)
        avg_energy = metrics.get("avg_energy", 50.0)
        quest_counts = metrics.get("quest_counts", {})
        done_quests = quest_counts.get("done", 0)
        proposal_statuses = metrics.get("proposal_statuses", {})
        approved = proposal_statuses.get("approved", 0)
        rejected = proposal_statuses.get("rejected", 0)
        total_proposals = approved + rejected

        if template_key == "low_agent_trust":
            if avg_trust < 0.3:
                return {"metric_value": avg_trust}
            return None

        elif template_key == "slow_quest_completion":
            avg_min = metrics.get("avg_completion_minutes")
            if avg_min and avg_min > 30:  # Takes >30 min to complete a quest
                return {"metric_value": avg_min}
            # Fallback: check if many quests are stuck in open/claimed
            open_count = quest_counts.get("open", 0) + quest_counts.get("claimed", 0)
            if done_quests > 0 and open_count > done_quests * 2:
                return {"metric_value": float(open_count)}
            return None

        elif template_key == "low_ceo_approval":
            if total_proposals >= 3:
                rejection_rate = rejected / total_proposals
                if rejection_rate > 0.6:
                    return {"metric_value": rejection_rate}
            return None

        elif template_key == "energy_crisis":
            if avg_energy < 15 and metrics.get("starving_agents", 0) > 2:
                return {"metric_value": avg_energy}
            return None

        elif template_key == "prompt_stale":
            # Always consider if we have memories but haven't applied them
            memory_stats = metrics.get("memory_stats", {})
            if memory_stats.get("total", 0) >= 3:
                return {"metric_value": memory_stats["total"]}
            return None

        elif template_key == "low_research_findings":
            findings_count = metrics.get("research_findings_count", 0)
            done_q = quest_counts.get("done", 0)
            if done_q == 0 and findings_count == 0:
                return {"metric_value": 50}
            return None

        return None

    async def _create_meta_quest(self, template: dict, trigger: dict) -> Optional[dict]:
        """Create a meta-quest from a triggered template."""
        if not self.qe:
            return None

        quest_id = f"meta-{template['subsystem']}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        title = template["title"]
        goal = template["goal"].format(**trigger)

        try:
            result = await self.qe.create_quest(
                quest_id=quest_id,
                title=title,
                goal=goal,
                subsystem=template["subsystem"],
                success_criteria=template["criteria"],
                reward=template["reward"],
                phase="head",
            )
            if "error" in result:
                print(f"[MetaScanner] Quest creation failed: {result['error']}")
                return None

            await self.qe.assign_quest(quest_id, "meta-scanner")
            self._meta_quest_count += 1
            print(f"[MetaScanner] Created meta-quest: {quest_id} — {title}")

            # Also store the trigger as a corporation lesson
            if self.memory:
                await self.memory.store_lesson(
                    lesson=f"MetaScanner triggered: {title} (metrics: {json.dumps(trigger)})",
                    source_quest=quest_id,
                    source_phase="meta",
                    role_target="scout",
                    category="process",
                    impact_score=0.7,
                )

            return {
                "quest_id": quest_id,
                "title": title,
                "goal": goal[:100],
                "subsystem": template["subsystem"],
            }
        except Exception as e:
            import traceback
            print(f"[MetaScanner] Error creating meta-quest: {e}\n{traceback.format_exc()[:300]}")
            return None

    def get_stats(self) -> dict:
        return {
            "meta_quests_created": self._meta_quest_count,
            "last_scan_tick": self._last_scan_tick,
        }
