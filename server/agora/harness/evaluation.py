"""Evaluation Interface — epoch metrics a per-agent scoring (V v ETCSLV harnesse).

Merané metriky na konci každej epochy:
  - Per-agent:
      * Skill growth (Δ level + Δ XP)
      * Energy efficiency (actions / energy spent)
      * Help success rate (completed / total help requests)
      * Trust delta
      * Stuck incidents
      * Tool usage distribution
  - Global:
      * Agent count (active/dead/culled)
      * Total artifacts created
      * Economy health (total energy, trades)
      * Byzantine violations
      * Library queries
"""

import json
from datetime import datetime
from typing import Any, Optional


class EpochEvaluator:
    """Collects and computes agent/epoch metrics for the Evaluation Interface."""

    def __init__(self, state_store, db, lifecycle_hooks=None):
        self.state_store = state_store
        self.db = db
        self.lifecycle_hooks = lifecycle_hooks
        # Cumulative metrics across all epochs
        self._epoch_metrics: dict[int, dict] = {}

    # ═══════════════════════════════════════════
    # PER-AGENT METRICS
    # ═══════════════════════════════════════════

    async def compute_agent_metrics(self, agent_id: str, snapshot_start: dict = None,
                                     snapshot_end: dict = None) -> dict:
        """Compute evaluation metrics for a single agent during one epoch."""
        metrics = {
            "agent_id": agent_id[:8],
            "name": "unknown",
            "role": "unknown",
            "skill_growth": 0,
            "skill_xp_gained": 0.0,
            "energy_efficiency": 0.0,
            "help_requests_sent": 0,
            "help_completed": 0,
            "help_success_rate": 0.0,
            "trust_delta": 0.0,
            "stuck_incidents": 0,
            "avg_health": 0.0,
            "actions_taken": 0,
        }

        if not self.state_store:
            return metrics

        # ── Identity ──
        npc = await self.state_store.get_npc(agent_id)
        if not npc:
            agent = await self.state_store.get_agent(agent_id)
            if not agent:
                return metrics
            metrics["name"] = agent.get("role", agent_id[:8])
            metrics["role"] = agent.get("role", "unknown")
        else:
            metrics["name"] = npc.get("npc_name", agent_id[:8])
            metrics["role"] = npc.get("role", "unknown")

        # ── Skill growth ──
        try:
            skills = await self.state_store.get_all_skills(agent_id)
            total_level = sum(s["level"] for s in skills)
            total_xp = sum(s["xp"] for s in skills)
            metrics["skill_growth"] = total_level
            metrics["skill_xp_gained"] = round(total_xp, 1)
        except Exception:
            pass

        # ── Help requests ──
        try:
            cursor = await self.db.execute(
                "SELECT COUNT(*) as c FROM agent_help_requests WHERE requester_id=?",
                (agent_id,),
            )
            row = await cursor.fetchone()
            metrics["help_requests_sent"] = row["c"] if row else 0

            cursor = await self.db.execute(
                "SELECT COUNT(*) as c FROM agent_help_requests "
                "WHERE (requester_id=? OR helper_id=?) AND status='completed'",
                (agent_id, agent_id),
            )
            row = await cursor.fetchone()
            metrics["help_completed"] = row["c"] if row else 0

            if metrics["help_requests_sent"] > 0:
                metrics["help_success_rate"] = round(
                    metrics["help_completed"] / metrics["help_requests_sent"], 2
                )
        except Exception:
            pass

        # ── Energy efficiency ──
        if snapshot_start and snapshot_end:
            energy_start = snapshot_start.get("energy", 100)
            energy_end = snapshot_end.get("energy", 100)
            energy_spent = max(0, energy_start - energy_end)

            if snapshot_start and snapshot_end:
                actions_start = snapshot_start.get("actions_taken", 0)
                actions_end = snapshot_end.get("actions_taken", 0)
                metrics["actions_taken"] = max(0, actions_end - actions_start)
                if energy_spent > 0:
                    metrics["energy_efficiency"] = round(
                        metrics["actions_taken"] / energy_spent, 2
                    )

            trust_start = snapshot_start.get("trust", 0.5)
            trust_end = snapshot_end.get("trust", 0.5)
            metrics["trust_delta"] = round(trust_end - trust_start, 3)

        # ── Stuck incidents (from lifecycle hooks) ──
        if self.lifecycle_hooks:
            violations = self.lifecycle_hooks.get_violations_log(limit=200)
            stuck = [v for v in violations if v.get("type") == "stuck"
                     and v.get("npc_id") == agent_id]
            metrics["stuck_incidents"] = len(stuck)

        # ── Health ──
        if npc:
            metrics["avg_health"] = round(npc.get("health", 100), 1)

        return metrics

    # ═══════════════════════════════════════════
    # GLOBAL EPOCH METRICS
    # ═══════════════════════════════════════════

    async def compute_epoch_summary(self, epoch_number: int) -> dict:
        """Compute global epoch-level evaluation summary."""
        summary = {
            "epoch": epoch_number,
            "timestamp": datetime.utcnow().isoformat(),
            "agents": {"active": 0, "dead": 0, "culled": 0, "total": 0},
            "economy": {"total_energy": 0.0, "trades": 0, "resources": 0},
            "activity": {
                "artifacts_created": 0,
                "tasks_completed": 0,
                "help_requests": 0,
                "help_completed": 0,
                "library_queries": 0,
                "byzantine_violations": 0,
            },
            "top_agents": [],
        }

        try:
            # ── Agent counts ──
            cursor = await self.db.execute(
                "SELECT status, COUNT(*) as c FROM agent_identities GROUP BY status"
            )
            for row in await cursor.fetchall():
                summary["agents"][row["status"]] = row["c"]
            summary["agents"]["total"] = sum(summary["agents"].values())

            # ── Economy ──
            cursor = await self.db.execute(
                "SELECT COALESCE(SUM(energy_balance), 0) as total FROM agent_identities WHERE status='active'"
            )
            row = await cursor.fetchone()
            if row:
                summary["economy"]["total_energy"] = round(row["total"], 1)

            cursor = await self.db.execute("SELECT COUNT(*) as c FROM trade_history")
            row = await cursor.fetchone()
            if row:
                summary["economy"]["trades"] = row["c"]

            cursor = await self.db.execute("SELECT COUNT(*) as c FROM resources")
            row = await cursor.fetchone()
            if row:
                summary["economy"]["resources"] = row["c"]

            # ── Activity ──
            for table, metric in [
                ("artifacts", "artifacts_created"),
                ("tasks WHERE status='completed'", "tasks_completed"),
                ("agent_help_requests", "help_requests"),
                ("agent_help_requests WHERE status='completed'", "help_completed"),
            ]:
                cursor = await self.db.execute(f"SELECT COUNT(*) as c FROM {table}")
                row = await cursor.fetchone()
                if row:
                    summary["activity"][metric] = row["c"]

            # Library queries are stored as artifacts with type 'knowledge'
            cursor = await self.db.execute(
                "SELECT COUNT(*) as c FROM artifacts WHERE artifact_type='knowledge'"
            )
            row = await cursor.fetchone()
            if row:
                summary["activity"]["library_queries"] = row["c"]

            # ── Byzantine violations ──
            cursor = await self.db.execute(
                "SELECT COUNT(*) as c FROM events WHERE event_type='byzantine_violation'"
            )
            row = await cursor.fetchone()
            if row:
                summary["activity"]["byzantine_violations"] = row["c"]

            # ── Top agents (highest trust) ──
            cursor = await self.db.execute(
                "SELECT agent_id, role, trust_score, energy_balance, generation "
                "FROM agent_identities WHERE status='active' "
                "ORDER BY trust_score DESC LIMIT 5"
            )
            for agent in await cursor.fetchall():
                summary["top_agents"].append({
                    "id": agent["agent_id"][:8],
                    "role": agent["role"],
                    "trust": round(agent["trust_score"], 3),
                    "energy": round(agent["energy_balance"], 1),
                    "gen": agent["generation"],
                })

        except Exception as e:
            print(f"[EpochEvaluator] Summary error: {e}")

        return summary

    # ═══════════════════════════════════════════
    # AGENT SCORING
    # ═══════════════════════════════════════════

    async def compute_agent_score(self, agent_id: str) -> dict:
        """Compute an overall performance score for an agent.

        Score = weighted combination of:
          - Trust (0.30)
          - Skill level (0.25)
          - Help success rate (0.15)
          - Energy efficiency (0.15)
          - Survival (generations) (0.15)
        """
        metrics = await self.compute_agent_metrics(agent_id)

        trust_weight = 0.30
        skill_weight = 0.25
        help_weight = 0.15
        energy_weight = 0.15
        survival_weight = 0.15

        # Normalize each metric to 0-1
        trust_score = 0.0
        try:
            agent = await self.state_store.get_agent(agent_id) if self.state_store else None
            if agent:
                trust_score = agent.get("trust_score", 0.5)
            else:
                npc = await self.state_store.get_npc(agent_id) if self.state_store else None
                trust_score = npc.get("trust_score", 0.5) if npc else 0.5
        except Exception:
            trust_score = 0.5

        skill_score = min(1.0, metrics["skill_growth"] / 50.0) if metrics["skill_growth"] else 0.3
        help_score = metrics["help_success_rate"]
        energy_score = min(1.0, metrics["energy_efficiency"] * 2) if metrics["energy_efficiency"] else 0.5

        # Survival: generations (from agent_identities)
        survival_score = 0.5
        try:
            cursor = await self.db.execute(
                "SELECT generation FROM agent_identities WHERE agent_id=?",
                (agent_id,),
            )
            row = await cursor.fetchone()
            if row:
                survival_score = min(1.0, row["generation"] / 10.0)
        except Exception:
            pass

        total = (
            trust_weight * trust_score
            + skill_weight * skill_score
            + help_weight * help_score
            + energy_weight * energy_score
            + survival_weight * survival_score
        )

        return {
            "agent_id": agent_id[:8],
            "name": metrics["name"],
            "role": metrics["role"],
            "score": round(total, 3),
            "components": {
                "trust": round(trust_score, 3),
                "skill": round(skill_score, 3),
                "help_success": round(help_score, 3),
                "energy_eff": round(energy_score, 3),
                "survival": round(survival_score, 3),
            },
            "weights": {
                "trust": trust_weight,
                "skill": skill_weight,
                "help": help_weight,
                "energy": energy_weight,
                "survival": survival_weight,
            },
        }

    # ═══════════════════════════════════════════
    # EPOCH INTEGRATION
    # ═══════════════════════════════════════════

    async def build_epoch_report(self, epoch_number: int) -> dict:
        """Full epoch report: summary + per-agent metrics + rankings."""
        summary = await self.compute_epoch_summary(epoch_number)

        # Per-agent metrics
        agents = []
        try:
            cursor = await self.db.execute(
                "SELECT agent_id FROM agent_identities ORDER BY trust_score DESC"
            )
            for row in await cursor.fetchall():
                agent_metrics = await self.compute_agent_metrics(row["agent_id"])
                score = await self.compute_agent_score(row["agent_id"])
                agents.append({
                    **agent_metrics,
                    "score": score["score"],
                    "score_components": score["components"],
                })
        except Exception as e:
            print(f"[EpochEvaluator] Agent metrics error: {e}")

        summary["agents_detail"] = sorted(agents, key=lambda a: a.get("score", 0), reverse=True)
        summary["total_agents_evaluated"] = len(agents)

        # Store in DB
        try:
            epoch_report = json.dumps(summary)
            cursor = await self.db.execute(
                "SELECT id FROM epochs WHERE epoch_number=? ORDER BY id DESC LIMIT 1",
                (epoch_number,),
            )
            row = await cursor.fetchone()
            if row:
                await self.db.execute(
                    "UPDATE epochs SET summary=? WHERE id=?",
                    (epoch_report, row["id"]),
                )
            else:
                await self.db.execute(
                    "INSERT INTO epochs (epoch_number, status, summary) VALUES (?, 'completed', ?)",
                    (epoch_number, epoch_report),
                )
            await self.db.commit()
        except Exception as e:
            print(f"[EpochEvaluator] DB store error: {e}")

        self._epoch_metrics[epoch_number] = summary
        return summary

    async def finalize_epoch(self, epoch_number: int) -> dict:
        """Finalize and return epoch evaluation report.

        Called by EpochEngine._finalize_epoch() at the end of each epoch.
        """
        report = await self.build_epoch_report(epoch_number)

        # Print summary
        print(f"[EpochEvaluator] 📊 Epoch {epoch_number} complete:")
        print(f"  Agents: {report['agents']['active']} active / {report['agents']['dead']} dead / {report['agents']['culled']} culled")
        print(f"  Activity: {report['activity']['tasks_completed']} tasks, {report['activity']['help_completed']}/{report['activity']['help_requests']} helps")
        print(f"  Economy: {report['economy']['total_energy']}⚡ energy, {report['economy']['trades']} trades")
        if report["top_agents"]:
            top = report["top_agents"][0]
            print(f"  Top agent: {top['role']}({top['id']}) trust={top['trust']}")

        return report

    # ═══════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════

    def get_epoch_metrics(self, epoch_number: int = None) -> dict:
        """Get cached epoch metrics."""
        if epoch_number is not None:
            return self._epoch_metrics.get(epoch_number, {})
        return self._epoch_metrics

    async def get_epoch_report_from_db(self, epoch_number: int) -> Optional[dict]:
        """Get epoch report from DB."""
        try:
            cursor = await self.db.execute(
                "SELECT summary FROM epochs WHERE epoch_number=? ORDER BY id DESC LIMIT 1",
                (epoch_number,),
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row["summary"])
        except Exception:
            pass
        return None
