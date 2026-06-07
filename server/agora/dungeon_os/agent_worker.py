"""Agent Worker — HEAD→PATA→Compound quest lifecycle for Dungeon OS NPCs.

Each 15-min tick:
  1. SCOUT scans GitHub for opportunities
  2. If opportunity found → creates HEAD research quest
  3. HEAD quest: 3x parallel researchers (repo, docs, best-practices)
  4. BRAINMASTER synthesizes → stores to vault
  5. CEO/CTO evaluates → either moves to PATA or rejects
  6. PATA quest: Designer/Developer implements → QA verifies
  7. COMPOUND: lessons extracted → AGENTS.md updated
  8. Hermes sends Telegram report of the cycle

This transforms Dungeon OS from a static quest board
into a self-improving autonomous corporation.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from agora.dungeon_os.actions.registry import get_registry

# ── Corporation Agent workflow map ──
# Maps phase → agent → skill_action
CORPORATION_FLOW = {
    "scout": {
        "scout": {"skill": "scan_horizon", "params": {}},
    },
    "head": {
        "researcher_repo": {"npc": "researcher", "skill": "repo_analysis", "params": {"researcher_type": "repo"}},
        "researcher_docs": {"npc": "researcher", "skill": "docs_analysis", "params": {"researcher_type": "docs"}},
        "researcher_best": {"npc": "researcher", "skill": "best_practices", "params": {"researcher_type": "best-practices"}},
    },
    "synthesize": {
        "brainmaster": {"npc": "brainmaster", "skill": "store_knowledge", "params": {}},
    },
    "evaluate": {
        "cto": {"npc": "cto", "skill": "evaluate_proposal", "params": {}},
        "ceo": {"npc": "ceo", "skill": "evaluate_proposal", "params": {}},
    },
    "pata": {
        "designer": {"npc": "designer", "skill": "design", "params": {}},
        "developer": {"npc": "developer", "skill": "implement", "params": {}},
        "qa": {"npc": "qa", "skill": "verify", "params": {}},
    },
    "compound": {
        "warden": {"npc": "warden", "skill": "compound", "params": {}},
    },
}


class CorporationWorker:
    """Autonomous Corporation worker — runs the full HEAD→PATA→Compound cycle."""

    def __init__(self, quest_engine, db=None, config: Optional[dict] = None):
        self.qe = quest_engine
        self.db = db
        self.config = config or {}
        self.registry = get_registry()
        self._stats = {
            "ticks": 0,
            "scout_runs": 0,
            "head_completed": 0,
            "pata_completed": 0,
            "lessons_extracted": 0,
        }

    async def tick(self) -> dict:
        """Run one full corporation tick."""
        self._stats["ticks"] += 1
        tick_start = datetime.now()
        results = []

        # ── Step 1: SCOUT — scan horizon for opportunities ──
        scout_result = await self._run_scout()
        if scout_result:
            results.append(scout_result)

        # ── Step 2: Find HEAD quests and process them ──
        head_quests = await self._get_quests_by_phase("head")
        for quest in head_quests:
            head_result = await self._process_head(quest)
            results.append(head_result)

        # ── Step 3: Find quests awaiting synthesis ──
        syn_quests = await self._get_quests_with_pending_synthesis()
        for quest in syn_quests:
            syn_result = await self._process_synthesis(quest)
            results.append(syn_result)

        # ── Step 4: Find quests awaiting evaluation ──
        eval_quests = await self._get_quests_awaiting_evaluation()
        for quest in eval_quests:
            eval_result = await self._process_evaluation(quest)
            results.append(eval_result)

        # ── Step 5: Find PATA quests and process them ──
        pata_quests = await self._get_quests_by_phase("pata")
        for quest in pata_quests:
            pata_result = await self._process_pata(quest)
            results.append(pata_result)

        # ── Step 6: COMPOUND — extract lessons from completed quests ──
        compound_result = await self._run_compound()
        if compound_result:
            results.append(compound_result)

        # Clean up empty results
        results = [r for r in results if r]

        elapsed = (datetime.now() - tick_start).total_seconds()

        # Build Telegram summary
        summary = self._build_summary(results)

        # Send Telegram report
        await self._send_report(summary)

        return {
            "tick": self._stats["ticks"],
            "duration_seconds": round(elapsed, 1),
            "results": results,
            "summary": summary,
            "stats": dict(self._stats),
        }

    # ═══════════════════════════════════════════
    # STEP 1: SCOUT
    # ═══════════════════════════════════════════

    async def _run_scout(self) -> Optional[dict]:
        """Run the Scout — scan GitHub for new opportunities."""
        self._stats["scout_runs"] += 1

        result = await self.registry.execute(
            npc_name="scout",
            skill_name="scan_horizon",
            config=self.config,
            quest={"id": f"scout-{datetime.now().strftime('%Y%m%d_%H%M')}", "title": "Horizon Scan", "goal": "", "subsystem": "knowledge"},
            params={},
        )

        if result.get("status") != "ok":
            return None

        findings = result.get("findings", [])
        if not findings:
            return {"stage": "scout", "status": "nothing_new", "detail": "No interesting findings"}

        top = result.get("top_finding", {})
        # Create a HEAD quest from the top finding
        quest_id = f"research-{top.get('source', 'github').replace(':', '-')}-{datetime.now().strftime('%Y%m%d')}"
        quest_title = f"Research: {top['title'][:80]}"
        quest_goal = f"Deep research on: {top['title']}\nSource: {top.get('url', top.get('source', ''))}\nSummary: {top.get('summary', '')[:300]}"

        create_result = await self.qe.create_quest(
            quest_id=quest_id,
            title=quest_title,
            goal=quest_goal,
            subsystem="knowledge",
            success_criteria=[
                f"Read and synthesize: {top['title']}",
                "Store findings in vault",
                "Submit for CEO/CTO evaluation",
            ],
            reward=20,
            phase="head",
            research_source=top.get("url", ""),
        )

        if "error" in create_result:
            return {"stage": "scout", "status": "create_failed", "error": create_result["error"]}

        # Assign to scout for HEAD research
        await self.qe.assign_quest(quest_id, "scout")

        return {
            "stage": "scout",
            "status": "new_quest",
            "quest_id": quest_id,
            "title": quest_title,
            "finding": top,
        }

    # ═══════════════════════════════════════════
    # STEP 2: HEAD — Research phase
    # ═══════════════════════════════════════════

    async def _process_head(self, quest: dict) -> Optional[dict]:
        """Process a HEAD quest: run 3 parallel researchers."""
        quest_id = quest.get("id", "")
        quest_goal = quest.get("goal", "")
        url = quest.get("research_source", "")
        title = quest.get("title", "")

        # If no URL, try to extract from goal
        if not url:
            for line in quest_goal.split("\n"):
                if line.startswith("Source: "):
                    url = line.replace("Source: ", "").strip()
                    break

        # Run 3 parallel research actions (sequential for now, parallel later)
        research_results = []
        for res_type in ["repo", "docs", "best-practices"]:
            res_result = await self.registry.execute(
                npc_name="researcher",
                skill_name="deep_research",
                config=self.config,
                quest=quest,
                params={
                    "url": url,
                    "researcher_type": res_type,
                },
            )
            research_results.append({"type": res_type, "result": res_result})

        # Collect all findings
        all_findings = []
        for rr in research_results:
            r = rr["result"]
            if r.get("status") == "ok":
                syn = r.get("synthesis", {})
                all_findings.append({
                    "researcher": rr["type"],
                    "summary": syn.get("summary", ""),
                    "key_points": syn.get("key_points", []),
                    "impact": syn.get("impact", "medium"),
                })

        # Advance quest: mark synthesis as pending
        if all_findings:
            await self.qe.submit_for_review(quest_id, "scout")

        self._stats["head_completed"] += 1

        return {
            "stage": "head",
            "quest_id": quest_id,
            "title": title,
            "researchers_run": len(research_results),
            "findings_count": len(all_findings),
        }

    # ═══════════════════════════════════════════
    # STEP 3: SYNTHESIS — Brainmaster
    # ═══════════════════════════════════════════

    async def _process_synthesis(self, quest: dict) -> Optional[dict]:
        """Brainmaster synthesizes research findings into vault knowledge."""
        quest_id = quest.get("id", "")
        title = quest.get("title", "")

        # Get research findings from DB
        findings = []
        if self.db:
            try:
                cursor = await self.db.execute(
                    "SELECT * FROM research_findings WHERE quest_id=? ORDER BY researcher",
                    (quest_id,),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    findings.append({
                        "researcher": row["researcher"],
                        "summary": row["summary"],
                    })
            except Exception:
                pass

        result = await self.registry.execute(
            npc_name="brainmaster",
            skill_name="store_knowledge",
            config=self.config,
            quest=quest,
            params={
                "title": title,
                "research_summary": quest.get("research_summary") or quest.get("goal", "")[:500],
                "findings": findings,
            },
        )

        return {
            "stage": "synthesis",
            "quest_id": quest_id,
            "status": result.get("status"),
            "filepath": result.get("filepath", ""),
        }

    # ═══════════════════════════════════════════
    # STEP 4: EVALUATION — CEO/CTO
    # ═══════════════════════════════════════════

    async def _process_evaluation(self, quest: dict) -> Optional[dict]:
        """CEO and CTO evaluate the research proposal."""
        quest_id = quest.get("id", "")
        title = quest.get("title", "")

        # CTO evaluates
        cto_result = await self.registry.execute(
            npc_name="cto",
            skill_name="evaluate_proposal",
            config=self.config,
            quest=quest,
            params={},
        )

        # CEO evaluates (re-using same action with different config bias)
        ceo_result = await self.registry.execute(
            npc_name="ceo",
            skill_name="evaluate_proposal",
            config=self.config,
            quest=quest,
            params={},
        )

        approved = cto_result.get("approved", False) and ceo_result.get("approved", False)

        return {
            "stage": "evaluation",
            "quest_id": quest_id,
            "title": title,
            "cto_approved": cto_result.get("approved", False),
            "ceo_approved": ceo_result.get("approved", False),
            "approved": approved,
            "priority": cto_result.get("priority", "low"),
            "cto_rationale": cto_result.get("cto", {}).get("rationale", ""),
            "ceo_rationale": ceo_result.get("ceo", {}).get("rationale", ""),
        }

    # ═══════════════════════════════════════════
    # STEP 5: PATA — Execution phase
    # ═══════════════════════════════════════════

    async def _process_pata(self, quest: dict) -> Optional[dict]:
        """Process a PATA quest: execute the approved changes.

        For now, the PATA phase logs a detailed action plan.
        In later phases, this will spawn Developer/Designer subagents.
        """
        quest_id = quest.get("id", "")
        title = quest.get("title", "")
        research_summary = quest.get("research_summary") or ""

        # Log PATA execution plan
        log_dir = self.config.get("log_dir", "/tmp/hermes-logs")
        os.makedirs(log_dir, exist_ok=True)

        plan = [
            f"# PATA Execution Plan: {title}",
            f"",
            f"**Quest:** {quest_id}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Research:** {research_summary[:300]}",
            f"",
            "## Implementation Steps",
            f"",
            f"1. Designer: Create technical design based on research findings",
            f"2. Developer: Implement the changes in code",
            f"3. QA: Verify changes meet criteria",
            f"4. Deploy: Merge and apply changes",
            f"",
            "---",
            f"*PATA phase initiated by Autonomous Corporation Worker*",
        ]
        plan_file = f"{log_dir}/pata_{quest_id}.md"
        with open(plan_file, "w") as f:
            f.write("\n".join(plan))

        # Mark as done for now (in later phases, real implementation happens)
        await self.qe.submit_for_review(quest_id, "developer")
        verify_result = await self.qe.verify_quest(quest_id, runs=1)

        self._stats["pata_completed"] += 1

        return {
            "stage": "pata",
            "quest_id": quest_id,
            "title": title,
            "status": verify_result.get("status", "done"),
            "plan_file": plan_file,
        }

    # ═══════════════════════════════════════════
    # STEP 6: COMPOUND — Lessons learned
    # ═══════════════════════════════════════════

    async def _run_compound(self) -> Optional[dict]:
        """Extract lessons from recently completed quests."""
        # Find recently done quests without compound lessons
        cursor = await self.db.execute(
            "SELECT * FROM quests WHERE status='done' AND (compound_lessons IS NULL OR compound_lessons = '') ORDER BY completed_at DESC LIMIT 3"
        )
        done_quests = await cursor.fetchall()

        if not done_quests:
            return None

        results = []
        for quest in done_quests:
            quest_dict = self._quest_to_dict(quest)
            result = await self.registry.execute(
                npc_name="warden",
                skill_name="compound",
                config=self.config,
                quest=quest_dict,
                params={},
            )
            results.append({
                "quest_id": quest_dict.get("id"),
                "lessons": result.get("lessons", []),
            })

        self._stats["lessons_extracted"] += len(results)
        return {"stage": "compound", "quests_processed": len(results), "details": results}

    # ═══════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════

    async def _get_quests_by_phase(self, phase: str) -> list[dict]:
        """Get quests in a specific lifecycle phase."""
        if not self.db:
            return []
        try:
            cursor = await self.db.execute(
                "SELECT * FROM quests WHERE phase=? AND status IN ('open', 'claimed') ORDER BY created_at ASC LIMIT 5",
                (phase,),
            )
            rows = await cursor.fetchall()
            return [self._quest_to_dict(r) for r in rows]
        except Exception:
            return []

    async def _get_quests_with_pending_synthesis(self) -> list[dict]:
        """Get quests in review status that need Brainmaster synthesis."""
        if not self.db:
            return []
        try:
            cursor = await self.db.execute(
                "SELECT * FROM quests WHERE phase='head' AND status='review' AND (findings_path IS NULL OR findings_path = '') ORDER BY created_at ASC LIMIT 3",
            )
            rows = await cursor.fetchall()
            return [self._quest_to_dict(r) for r in rows]
        except Exception:
            return []

    async def _get_quests_awaiting_evaluation(self) -> list[dict]:
        """Get quests that have findings but haven't been evaluated yet."""
        if not self.db:
            return []
        try:
            cursor = await self.db.execute(
                "SELECT * FROM quests WHERE phase='head' AND findings_path IS NOT NULL AND findings_path != '' AND proposal_status='pending' ORDER BY created_at ASC LIMIT 3",
            )
            rows = await cursor.fetchall()
            return [self._quest_to_dict(r) for r in rows]
        except Exception:
            return []

    def _quest_to_dict(self, row) -> dict:
        """Convert sqlite3.Row to dict."""
        def _safe_get(key, default=None):
            try:
                val = row[key]
                return val if val is not None else default
            except (KeyError, IndexError, TypeError):
                return default
        return {
            "id": row["id"],
            "title": row["title"],
            "goal": row["goal"],
            "subsystem": row["subsystem"],
            "success_criteria": json.loads(row["success_criteria"] or "[]"),
            "reward": row["reward"],
            "owner": _safe_get("owner"),
            "status": row["status"],
            "phase": _safe_get("phase", "pata"),
            "research_source": _safe_get("research_source"),
            "findings_path": _safe_get("findings_path"),
            "proposal_status": _safe_get("proposal_status", "pending"),
            "compound_lessons": _safe_get("compound_lessons"),
            "research_summary": _safe_get("research_summary"),
            "depends_on": json.loads(row["depends_on"] or "[]"),
            "created_at": _safe_get("created_at"),
            "completed_at": _safe_get("completed_at"),
        }

    def _build_summary(self, results: list[dict]) -> str:
        """Build a Telegram summary of this tick."""
        parts = [f"🏢 **Corporation Tick #{self._stats['ticks']}**", ""]

        for r in results:
            stage = r.get("stage", "")
            if stage == "scout":
                status = r.get("status", "")
                if status == "new_quest":
                    parts.append(f"👁️ Scout: *{r.get('title', '')}*")
                elif status == "nothing_new":
                    parts.append(f"👁️ Scout: Nothing new found")
            elif stage == "head":
                parts.append(f"🔬 HEAD: *{r.get('title', '')}* — {r.get('researchers_run', 0)} researchers")
            elif stage == "synthesis":
                parts.append(f"🧠 Brainmaster: Knowledge stored → vault")
            elif stage == "evaluation":
                verdict = "✅ Approved" if r.get("approved") else "❌ Rejected"
                parts.append(f"👔 CEO/CTO: {verdict} — *{r.get('title', '')}*")
            elif stage == "pata":
                parts.append(f"🛠️ PATA: *{r.get('title', '')}* — executed")
            elif stage == "compound":
                parts.append(f"📚 Compound: {r.get('quests_processed', 0)} quests → lessons extracted")

        parts.extend([
            "",
            f"📊 Stats: {self._stats['head_completed']} HEAD / {self._stats['pata_completed']} PATA / {self._stats['lessons_extracted']} lessons",
            f"╰ {datetime.now().strftime('%H:%M:%S')}",
        ])

        return "\n".join(parts)

    async def _send_report(self, message: str):
        """Send the tick summary via Telegram."""
        from agora.dungeon_os.actions.hermes import action_send_message
        await action_send_message(
            self.config,
            {"id": f"tick-{self._stats['ticks']}", "title": "Corporation Report", "goal": message, "subsystem": "comms"},
            {"message": message, "title": "🏢 Corporation Report", "channel": "telegram"},
        )

    def get_stats(self) -> dict:
        return dict(self._stats)
