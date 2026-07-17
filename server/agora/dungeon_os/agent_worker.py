"""Agent Worker — HEAD→PATA→Compound quest lifecycle for Dungeon OS NPCs.

PHASE 3: Recursive Self-Improvement Loop.
  - Corporation memory: lessons modify agent prompts recursively
  - MetaScanner: system creates meta-quests to improve itself
  - QualityTracker: every evaluation scored and trended

Each 15-min tick:
  1. SCOUT scans GitHub for opportunities
  2. MetaScanner (every 20 ticks) — creates self-improvement quests
  3. HEAD research (3x parallel)
  4. BRAINMASTER synthesizes → vault
  5. CEO/CTO evaluates (with PromptEngine memory injection)
  6. PATA execution
  7. COMPOUND: lessons → corporation_memory → improves future prompts
  8. Quality trends recorded
  9. Telegram report
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from agora.dungeon_os.actions.registry import get_registry

# ═══════════════════════════════════════════
# STEP MAP
# ═══════════════════════════════════════════

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
    """Autonomous Corporation worker — runs the full HEAD→PATA→Compound cycle.

    Phase 3 additions:
      - corporation_memory / PromptEngine for recursive prompt improvement
      - MetaScanner for self-analysis meta-quests
      - QualityTracker for evaluation quality trending
    """

    def __init__(self, quest_engine, db=None, config: Optional[dict] = None):
        self.qe = quest_engine
        self.db = db
        self.config = config or {}
        self.registry = get_registry()

        # ── Phase 3 modules (lazy-init) ──
        self._memory = None
        self._prompt_engine = None
        self._meta_scanner = None
        self._quality_tracker = None
        self._phase3_initialized = False

        self._stats = {
            "ticks": 0,
            "scout_runs": 0,
            "head_completed": 0,
            "pata_completed": 0,
            "lessons_extracted": 0,
            "meta_quests_created": 0,
            "quality_records": 0,
        }

    # ═══════════════════════════════════════════
    # Phase 3 lazy init
    # ═══════════════════════════════════════════

    async def _ensure_phase3(self):
        """Initialize Phase 3 modules on first use."""
        if self._phase3_initialized or not self.db:
            return

        from agora.dungeon_os.corporation_memory import CorporationMemory, PromptEngine
        from agora.dungeon_os.meta_scanner import MetaScanner
        from agora.dungeon_os.quality_scoring import QualityTracker

        self._memory = CorporationMemory(self.db)
        await self._memory.ensure_tables()

        self._prompt_engine = PromptEngine(self._memory)
        self._meta_scanner = MetaScanner(self.db, self.qe, self._memory)
        self._quality_tracker = QualityTracker(self.db)
        await self._quality_tracker.ensure_tables()

        self._phase3_initialized = True
        print("[Phase3] Corporation Memory, MetaScanner, QualityTracker initialized")

    # ═══════════════════════════════════════════
    # MAIN TICK
    # ═══════════════════════════════════════════

    async def tick(self, tick_count: int = 0) -> dict:
        """Run one full corporation tick.

        Args:
            tick_count: Current global tick count (for MetaScanner interval)

        Returns dict with all step results.
        """
        await self._ensure_phase3()

        self._stats["ticks"] += 1
        tick_start = datetime.now()
        results = []

        # ── STEP 0: META SCANNER (every 20 ticks) ──
        if self._meta_scanner:
            meta_results = await self._meta_scanner.scan_and_act(tick_count)
            for mr in meta_results:
                results.append({"stage": "meta", **mr})
                if "quest_id" in mr:
                    self._stats["meta_quests_created"] += 1

        # ── STEP 1: SCOUT ──
        scout_result = await self._run_scout()
        if scout_result:
            results.append(scout_result)

        # ── STEP 1.5: RESEARCH-FRONTIER SEEDER ──
        # Feed the board with hard, original research questions from real vault gaps
        # (flywheel falsifiers / contradictions / structural holes) when it runs low.
        if len(await self._get_quests_by_phase("head")) < 2:
            seeded = await self._seed_research_frontier()
            if seeded:
                results.append(seeded)

        # ── STEP 2: HEAD research ──
        head_quests = await self._get_quests_by_phase("head")
        for quest in head_quests:
            head_result = await self._process_head(quest)
            results.append(head_result)

        # ── STEP 3: SYNTHESIS (Brainmaster) ──
        syn_quests = await self._get_quests_with_pending_synthesis()
        for quest in syn_quests:
            syn_result = await self._process_synthesis(quest)
            results.append(syn_result)

        # ── STEP 4: EVALUATION (CEO/CTO with PromptEngine) ──
        eval_quests = await self._get_quests_awaiting_evaluation()
        for quest in eval_quests:
            eval_result = await self._process_evaluation(quest)
            results.append(eval_result)

            # Phase 3: record quality
            if eval_result and self._quality_tracker:
                await self._quality_tracker.record_evaluation(
                    quest_id=eval_result.get("quest_id", ""),
                    evaluator_role="ceo",
                    approved=eval_result.get("ceo_approved", False),
                    score=eval_result.get("ceo_score", 50),
                )
                await self._quality_tracker.record_evaluation(
                    quest_id=eval_result.get("quest_id", ""),
                    evaluator_role="cto",
                    approved=eval_result.get("cto_approved", False),
                    score=eval_result.get("cto_score", 50),
                )
                # Update findings quality
                if eval_result.get("approved"):
                    await self._quality_tracker.update_finding_quality(
                        quest_id=eval_result.get("quest_id", ""),
                        quality_score=max(
                            eval_result.get("cto_score", 50),
                            eval_result.get("ceo_score", 50),
                        ) / 100.0,
                        feedback=f"CTO: {eval_result.get('cto_rationale', '')[:100]}\nCEO: {eval_result.get('ceo_rationale', '')[:100]}",
                    )
                self._stats["quality_records"] += 2

            # Corp researched an idea and its CEO/CTO approved it → file it to Claude
            # as a shippable proposal. Claude ships the ones with merit, skips the thin.
            if eval_result and eval_result.get("approved"):
                self._file_ship_review(quest, eval_result)
                await self._mark_handed_off(quest.get("id", ""))
            # REPOINT (owner 2026-06-26): a board NEAR-MISS (not ship-approved but with a decent
            # score and real research) still carries lead value — surface it to Claude as a research
            # DOSSIER instead of letting it die in HEAD. The score is a priority hint, not a kill
            # switch; Claude develops the ambitious ones and archives the rest (RAISED BAR).
            elif eval_result and not eval_result.get("approved"):
                _score = max(eval_result.get("cto_score", 0) or 0, eval_result.get("ceo_score", 0) or 0)
                _has_research = bool(quest.get("research_summary") or quest.get("findings_path"))
                if _score >= 55 and _has_research:
                    self._file_research_dossier(quest, eval_result)
                    await self._mark_handed_off(quest.get("id", ""))

        # ── STEP 5: PATA execution ──
        pata_quests = await self._get_quests_by_phase("pata")
        for quest in pata_quests:
            pata_result = await self._process_pata(quest)
            results.append(pata_result)

        # ── STEP 6: COMPOUND → CORPORATION MEMORY ──
        compound_result = await self._run_compound()
        if compound_result:
            results.append(compound_result)

            # Phase 3: also record quality trend periodically
            if self._quality_tracker and tick_count % 10 == 0:
                summary = await self._quality_tracker.compute_quality_summary(tick_count)
                results.append({"stage": "quality_trend", "data": summary})
                self._stats["quality_records"] += 1

        # Clean up
        results = [r for r in results if r]
        elapsed = (datetime.now() - tick_start).total_seconds()

        summary = self._build_summary(results)
        # Only ping Telegram when the tick actually SHIPPED something — a real
        # commit, an approved deliverable, new findings, or a new quest. The
        # per-tick "system healthy / QA flagged" report was pure noise to the owner.
        if self._is_noteworthy(results):
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
        """Run the Scout — find an EXTERNAL research lead.

        PRIMARY source (the corp redesign): a REAL paper with a quantitative, simulable claim
        (pick_paper_target — arXiv/OpenAlex, already proven feeding Rooke's replications). This is
        the corp's 'view from outside': it scans the literature while the rest of the OS scans
        itself, and an approved lead becomes a Crucible candidate for Claude. The old GitHub
        horizon scan (which had degraded into junk digest-repos) remains only as a fallback."""
        self._stats["scout_runs"] += 1

        # ── PRIMARY: a real quantitative paper claim ──
        try:
            import asyncio as _aio
            from agora.execution.replication import pick_paper_target
            paper = await _aio.to_thread(pick_paper_target)
        except Exception as e:
            print(f"[Scout] paper target failed: {e}")
            paper = None
        if paper and paper.get("claim"):
            # dedup: one lead per claim per 3 days
            try:
                cur = await self.db.execute(
                    "SELECT COUNT(*) FROM quests WHERE goal LIKE ? AND created_at >= datetime('now','-3 day')",
                    (f"%{paper['claim'][:80]}%",))
                if (await cur.fetchone())[0] > 0:
                    paper = None
            except Exception:
                pass
        if paper and paper.get("claim"):
            quest_id = f"lead-paper-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            quest_title = f"Paper lead: {paper.get('title', paper['claim'])[:150]}"
            quest_goal = (
                f"CLAIM (verbatim, from a real paper): {paper['claim']}\n"
                f"PAPER: {paper.get('source', '')}\n"
                f"URL: {paper.get('url', '')}\n\n"
                f"Research this claim: what does the paper actually show, is the claim quantitative "
                f"and mechanistically testable in a minimal simulation, and is it interesting enough "
                f"(famous, contested, or board-priority) to deserve the Crucible bench? An approved "
                f"lead becomes a Crucible candidate for Claude to replicate or refute."
            )
            create_result = await self.qe.create_quest(
                quest_id=quest_id, title=quest_title, goal=quest_goal, subsystem="knowledge",
                success_criteria=["Ground the claim in the actual paper",
                                  "Judge testability (simulable mechanism + a number)",
                                  "Submit for CEO/CTO evaluation"],
                # non-http label ON PURPOSE: an http research_source routes deep_research down the
                # URL-FETCH path, which on an arXiv page yields 'Analyzed 1 lines' garbage and the
                # board (correctly) rejects it. The label forces the _topic_research route, which
                # researches the verbatim CLAIM in the goal with real OpenAlex/arXiv grounding.
                reward=25, phase="head", research_source=f"paper:{paper.get('url', '')}",
            )
            if "error" not in create_result:
                await self.qe.assign_quest(quest_id, "scout")
                return {"stage": "scout", "status": "new_quest", "quest_id": quest_id,
                        "title": quest_title, "finding": paper}

        # ── FALLBACK: the old GitHub horizon scan ──
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

        await self.qe.assign_quest(quest_id, "scout")

        # Phase 3: also store this finding as a memory
        if self._memory:
            await self._memory.store_lesson(
                lesson=f"Scout discovered: {top['title']} (relevance {top.get('score', 50)})",
                source_quest=quest_id,
                source_phase="scout",
                role_target="scout",
                category="general",
                impact_score=min(1.0, top.get("score", 50) / 100),
            )

        return {
            "stage": "scout",
            "status": "new_quest",
            "quest_id": quest_id,
            "title": quest_title,
            "finding": top,
        }

    async def _source_standing(self) -> dict:
        """Tah 5 — EARNED RESEARCH STANDING per source-KIND. Sources whose leads survive to approval / a
        measured receipt earn more seeding throughput; sources that produce shallow rejects get throttled.
        Standing = (approved + 1) / (rejected + 1), read live from the quests ledger (smoothed so no source
        starves). This is the bench-slot weighting: the generation layer's earned throughput."""
        standing = {}
        try:
            cur = await self.db.execute(
                "SELECT research_source, proposal_status, phase FROM quests WHERE research_source LIKE 'frontier:%'")
            rows = await cur.fetchall()
            agg = {}
            for src, status, phase in rows:
                kind = (src or "").split(":", 1)[-1]
                d = agg.setdefault(kind, {"good": 0, "bad": 0})
                if status == "approved" or phase == "pata":
                    d["good"] += 1
                elif status == "rejected":
                    d["bad"] += 1
            for kind, d in agg.items():
                standing[kind] = (d["good"] + 1.0) / (d["bad"] + 1.0)
        except Exception as e:
            print(f"[seed] standing read failed: {e}")
        return standing

    async def _escalate_lead(self, kind: str, short: str, prompt: str):
        """Tah 3 — the 'raise it twice' escalation: take a raw candidate lead and return the AMBITIOUS version
        of the SAME underlying question (the one that would matter 10x more, bridges two domains, or contradicts
        a common assumption) — still OPEN (not a known-result re-derivation) and MEASURABLE with a small model.
        Returns (question, falsifier) or (None, None) on failure (caller falls back to the raw candidate)."""
        try:
            import asyncio
            from agora.execution.llm_client import call_llm
            esc_prompt = (
                "You are a Frontier Scout for an autonomous research organization. Here is a raw research lead:\n"
                f"KIND: {kind}\nQUESTION: {prompt}\n\n"
                "Treat it as the SHALLOW first draft. Produce the AMBITIOUS version of the SAME underlying "
                "question: the version that would matter 10x more if answered, and/or bridges two domains that "
                "rarely meet, and/or contradicts an assumption most people hold. HARD CONSTRAINTS: it must stay "
                "genuinely OPEN (NOT a re-derivation of a known named result — regression to the mean, collider "
                "bias, survivorship, ripple effects, majority-vote are textbook), and it must be MEASURABLE with "
                "a small model (a number, threshold, exponent, or rate) via a NON-circular measurement. Bar: "
                "could this stand as serious science?\n\n"
                "Reply with exactly two lines:\nQUESTION: <one sharp sentence>\nFALSIFIER: <the single result that would kill it>"
            )
            raw = await asyncio.to_thread(call_llm, system_prompt="", user_prompt=esc_prompt,
                                          tier="medium", temperature=0.5, max_tokens=400)
            q = f = ""
            for line in (raw or "").splitlines():
                u = line.strip()
                if u.upper().startswith("QUESTION:"):
                    q = u.split(":", 1)[1].strip()
                elif u.upper().startswith("FALSIFIER:"):
                    f = u.split(":", 1)[1].strip()
            return (q, f) if q else (None, None)
        except Exception as e:
            print(f"[seed] escalation failed: {e}")
            return (None, None)

    async def _lead_is_textbook(self, question: str) -> bool:
        """Novelty gate for Crucible leads: is this research question an already-established, textbook /
        named-law result a specialist would recognize as settled? True => do not seed it. Fail-open
        (return False) on any error, so the gate never silently starves the board."""
        try:
            import asyncio
            from agora.execution.llm_client import call_llm
            raw = await asyncio.to_thread(
                call_llm,
                system_prompt=("You are a strict domain expert screening research questions for an "
                               "autonomous lab. Is the QUESTION already settled by an established, textbook / "
                               "named-law result (self-organized criticality, power-law tails, tipping/critical "
                               "fraction, phase transition, regression to the mean, majority-vote — all known)? "
                               "Reply ONLY JSON: {\"known\":true|false}."),
                user_prompt=f"QUESTION: {question}", tier="cheap", temperature=0.0, max_tokens=60)
            import json as _json
            import re as _re
            m = _re.search(r"\{.*\}", raw or "", _re.DOTALL)
            return bool(_json.loads(m.group(0)).get("known")) if m else False
        except Exception:
            return False

    async def _seed_research_frontier(self) -> Optional[dict]:
        """Seed the QuestBoard with a HARD, ORIGINAL research question drawn from REAL
        vault gaps — open flywheel falsifiers, belief contradictions, and structural
        holes / thin domains — not scraped news. This is what makes the board surface
        ideas worth dissecting, aligned to the owner's raised bar (rigorous original work)."""
        try:
            import re as _re
            from agora.execution import frontier as _frontier
            from agora.execution import flywheel as _flywheel
            from agora.execution import contradictions as _contra
            vault = self.config.get("vault_path") or "C:/Users/Danculus/my-second-brain"

            def _clean(s: str) -> str:
                # vault note ids look like 'ARI_2026-05-21_Why_AI_Systems_' — make them human
                s = _re.sub(r"^ARI_\d{4}-\d{2}-\d{2}_", "", s or "")
                s = s.replace("_", " ").replace("-", " ").strip()
                return _re.sub(r"\s+", " ", s)

            # Gather candidate leads from ALL sources, then pick the first FRESH one (not seeded in
            # the last day). The flywheel/contradiction sources keep returning the same unresolved
            # item until it's closed, so picking only one source churned the SAME research question
            # for hours/days. Trying all sources guarantees variety while any source has fresh content.
            candidates = []  # list of (kind, short, prompt, seedkey)
            oq = _flywheel.open_questions(3) or []
            for q in oq:
                txt = q.get("question")
                if txt:
                    candidates.append(("flywheel", txt[:150],
                                       f"Close this OPEN question with a MEASURED answer: {txt}", None))
            oc = _contra.open_contradictions(2) or []
            for cc in oc:
                a = _clean(cc.get("a_title") or cc.get("a") or "")
                b = _clean(cc.get("b_title") or cc.get("b") or "")
                if a and b:
                    candidates.append(("contradiction", f"{a[:70]} vs {b[:70]}",
                                       f"Two of our beliefs are in tension: '{a}' vs '{b}'. Investigate "
                                       f"which holds (or the distinction that reconciles them) with evidence.", None))
            ft = _frontier.frontier_target(vault)
            if ft:
                candidates.append((ft.get("kind", "frontier"), (ft.get("target") or "")[:150],
                                   ft.get("prompt", ""), ft.get("target")))
            if not candidates:
                return None
            # EARNED THROUGHPUT (Tah 5): order candidates by their source-kind's earned standing — sources
            # whose leads reach approval/receipts are tried first — with a 1-in-4 rotation for exploration so
            # no source starves. The freshness check below still prevents repeating the same question.
            standing = await self._source_standing()
            candidates.sort(key=lambda c: standing.get(c[0], 1.0), reverse=True)
            if self._stats["ticks"] % 4 == 0 and len(candidates) > 1:
                candidates = candidates[1:] + candidates[:1]

            async def _recently_seeded(title: str) -> bool:
                try:
                    cur = await self.db.execute(
                        "SELECT COUNT(*) FROM quests WHERE title=? AND created_at >= datetime('now','-1 day')",
                        (title,))
                    return (await cur.fetchone())[0] > 0
                except Exception:
                    return False

            lead = None
            for c in candidates:
                if not await _recently_seeded(f"Research question: {c[1]}"):
                    lead = c
                    break
            if lead is None:
                return None                       # everything fresh-worthy already on the board
            kind, short, prompt, seedkey = lead

            # Tah 3 — "raise it twice": escalate the raw candidate to its hardest honest, still-measurable
            # version before it hits the board, so the generator never hands off the shallow first framing.
            esc_q, esc_f = await self._escalate_lead(kind, short, prompt)
            if esc_q:
                short = esc_q[:150]
                prompt = esc_q + (f"\nFalsifier to target: {esc_f}" if esc_f else "")

            # NOVELTY GATE (owner RAISED BAR 2026-07-16, flag AGORA_NOVELTY_GATE default ON): the escalation
            # ASKS for open-not-textbook but does not VERIFY it — which is how the flywheel / power-law /
            # self-organized-criticality / critical-fraction flood got seeded. Verify: if the final question
            # is an already-established textbook result, DO NOT seed it (quality over quantity). Reversible.
            if os.getenv("AGORA_NOVELTY_GATE", "1") != "0" and await self._lead_is_textbook(short):
                return None

            quest_id = f"frontier-{kind}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            title = f"Research question: {short}"
            goal = (
                f"{prompt}\n\nBAR (owner): serious, RIGOROUS, ORIGINAL research — not a textbook "
                f"restatement. Aim for a measured result with a falsifier (Lab simulation or real "
                f"data; formal model where useful). If it has genuine merit, it becomes a Ship-review "
                f"for Claude to develop into rigorous shipped work."
            )
            res = await self.qe.create_quest(
                quest_id=quest_id, title=title, goal=goal, subsystem="knowledge",
                success_criteria=["Frame a sharp, testable question",
                                  "Produce a measured finding + falsifier",
                                  "Submit for CEO/CTO evaluation"],
                reward=25, phase="head", research_source=f"frontier:{kind}",
            )
            if "error" in res:
                return None
            await self.qe.assign_quest(quest_id, "scout")
            if seedkey:
                _frontier.record_seeded(seedkey, kind)
            self._stats["frontier_seeded"] = self._stats.get("frontier_seeded", 0) + 1
            print(f"[Frontier] seeded research question: {title[:60]}")
            return {"stage": "scout", "status": "new_quest", "quest_id": quest_id, "title": title}
        except Exception as e:
            print(f"[Frontier] seed error: {e}")
            return None

    # ═══════════════════════════════════════════
    # STEP 2: HEAD — Research phase
    # ═══════════════════════════════════════════

    async def _process_head(self, quest: dict) -> Optional[dict]:
        """Process a HEAD quest: run 3 parallel researchers."""
        quest_id = quest.get("id", "")
        quest_goal = quest.get("goal", "")
        url = quest.get("research_source", "")
        title = quest.get("title", "")

        # A frontier-seeded quest carries a LABEL (e.g. 'frontier:contradiction'), not a fetchable
        # URL. Treating it as a URL made the researcher fetch a bad target → 0 findings → the quest
        # stuck at 'claimed' forever. Non-http sources mean "research the TOPIC", so clear the url.
        if url and not url.startswith(("http://", "https://")):
            url = ""
        if not url:
            for line in quest_goal.split("\n"):
                if line.startswith("Source: "):
                    url = line.replace("Source: ", "").strip()
                    break

        # ══ Phase 3: build enriched researcher prompts with corporation memory ══
        research_results = []
        for res_type in ["repo", "docs", "best-practices"]:
            # Inject memory-enriched context if available
            enriched_params = {
                "url": url,
                "researcher_type": res_type,
            }
            if self._prompt_engine:
                enriched_prompt = await self._prompt_engine.build_prompt(
                    "researcher",
                    extra_context=f"Research target: {title}\nURL: {url}\nType: {res_type}",
                )
                enriched_params["enriched_prompt"] = enriched_prompt

            res_result = await self.registry.execute(
                npc_name="researcher",
                skill_name="deep_research",
                config=self.config,
                quest=quest,
                params=enriched_params,
            )
            research_results.append({"type": res_type, "result": res_result})

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

        if all_findings:
            # Populate research_summary with the ACTUAL findings so CEO/CTO evaluate the research,
            # not an empty field/the bare question. (Empty summaries were why ~100% got rejected.)
            summary_text = " | ".join(
                f"[{f['researcher']}] {f['summary']}" for f in all_findings if f.get("summary"))[:1500]
            if summary_text:
                try:
                    await self.qe.db.execute(
                        "UPDATE quests SET research_summary=? WHERE id=?", (summary_text, quest_id))
                    await self.qe.db.commit()
                except Exception as e:
                    print(f"[Head] research_summary store error: {e}")
            await self.qe.submit_for_review(quest_id, "scout")
        else:
            # ZERO findings: this quest used to stay open in 'head' and get re-researched every
            # tick FOREVER (oldest-first ordering meant dead topics clogged the 5-quest window —
            # the "agents are stuck in HEAD" alert). Count the attempt via verification_runs;
            # after the 2nd dry run, close it as a dead-end so the pipeline moves on.
            try:
                cur = await self.qe.db.execute(
                    "SELECT COALESCE(verification_runs,0) FROM quests WHERE id=?", (quest_id,))
                row = await cur.fetchone()
                runs = (row[0] if row else 0) + 1
                if runs >= 2:
                    await self.qe.db.execute(
                        "UPDATE quests SET status='done', proposal_status='rejected', "
                        "denial_reason='dead-end: research returned 0 findings on 2 attempts', "
                        "verification_runs=?, completed_at=datetime('now') WHERE id=?",
                        (runs, quest_id))
                    print(f"[Head] closed dead-end quest {quest_id} (0 findings x{runs})")
                else:
                    await self.qe.db.execute(
                        "UPDATE quests SET verification_runs=? WHERE id=?", (runs, quest_id))
                await self.qe.db.commit()
            except Exception as e:
                print(f"[Head] dead-end bookkeeping error: {e}")

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
    # STEP 4: EVALUATION — CEO/CTO with PromptEngine
    # ═══════════════════════════════════════════

    async def _process_evaluation(self, quest: dict) -> Optional[dict]:
        """CEO and CTO evaluate the research proposal.

        Phase 3: enriched prompts with corporation memory injection.
        """
        quest_id = quest.get("id", "")
        title = quest.get("title", "")

        # ══ Phase 3: inject memory-enriched prompts into params ══
        cto_params = {}
        ceo_params = {}

        if self._prompt_engine:
            # Build enriched contexts with relevant past lessons
            cto_context = await self._prompt_engine.build_prompt(
                "cto",
                extra_context=f"Evaluating proposal: {title}\nSummary: {quest.get('research_summary', '')[:200]}",
            )
            ceo_context = await self._prompt_engine.build_prompt(
                "ceo",
                extra_context=f"Evaluating proposal: {title}\nSummary: {quest.get('research_summary', '')[:200]}",
            )
            cto_params["enriched_prompt"] = cto_context
            ceo_params["enriched_prompt"] = ceo_context

        cto_result = await self.registry.execute(
            npc_name="cto",
            skill_name="evaluate_proposal",
            config=self.config,
            quest=quest,
            params=cto_params,
        )

        ceo_result = await self.registry.execute(
            npc_name="ceo",
            skill_name="evaluate_proposal",
            config=self.config,
            quest=quest,
            params=ceo_params,
        )

        cto_approved = cto_result.get("approved", False)
        ceo_approved = ceo_result.get("approved", False)
        cto_score = cto_result.get("cto", {}).get("score", 50) if isinstance(cto_result.get("cto"), dict) else 50
        ceo_score = ceo_result.get("ceo", {}).get("score", 50) if isinstance(ceo_result.get("ceo"), dict) else 50

        # FIX B — softened gate. The corp's job is to surface promising LEADS; Claude is the real
        # quality filter (a Ship-review tells Claude to develop the good ones and skip the thin).
        # So pass if EITHER exec approves, or the better score clears a modest bar — instead of the
        # old AND-of-both that rejected ~100% and choked the pipeline.
        approved = cto_approved or ceo_approved or max(cto_score, ceo_score) >= 60

        # PERSIST the verdict — without this the quest stayed status='review' / proposal='pending'
        # and was re-evaluated every tick forever (never advancing). Now it reaches a terminal state:
        # approved research → done (and the tick files a Ship-review to Claude); rejected → done/rejected.
        if self.db and quest_id:
            try:
                await self.db.execute(
                    "UPDATE quests SET status='done', proposal_status=?, completed_at=datetime('now') WHERE id=?",
                    ("approved" if approved else "rejected", quest_id),
                )
                await self.db.commit()
            except Exception as e:
                print(f"[Eval] persist verdict error: {e}")

        return {
            "stage": "evaluation",
            "quest_id": quest_id,
            "title": title,
            "cto_approved": cto_approved,
            "ceo_approved": ceo_approved,
            "approved": approved,
            "priority": cto_result.get("priority", "low"),
            "cto_rationale": cto_result.get("cto", {}).get("rationale", "") if isinstance(cto_result.get("cto"), dict) else cto_result.get("output", ""),
            "ceo_rationale": ceo_result.get("ceo", {}).get("rationale", "") if isinstance(ceo_result.get("ceo"), dict) else ceo_result.get("output", ""),
            "cto_score": cto_score,
            "ceo_score": ceo_score,
        }
    async def _process_pata(self, quest: dict) -> Optional[dict]:
        """Process a PATA quest: execute real implementation via Designer → Developer → QA.

        Phase 4: Instead of logging a plan file, this produces real artifacts:
          1. Designer generates ADR + design spec + code outline
          2. Developer generates actual code files → writes to repo
          3. QA verifies output (syntax check, criteria match)
          4. Quest completes only if QA passes

        Args:
            quest: The quest dict with research_summary, success_criteria, etc.

        Returns:
            dict with stage results and file paths
        """
        quest_id = quest.get("id", "")
        title = quest.get("title", "")
        research_summary = quest.get("research_summary") or ""
        criteria = quest.get("success_criteria", [])

        log_dir = self.config.get("log_dir", "/tmp/hermes-logs")
        os.makedirs(log_dir, exist_ok=True)

        # ══ STEP 1: DESIGNER — generate ADR + design spec ══
        design_result = await self.registry.execute(
            npc_name="designer",
            skill_name="design",
            config=self.config,
            quest=quest,
            params={
                "title": title,
                "research_summary": research_summary,
                "success_criteria": criteria,
            },
        )
        design_files = design_result.get("files", [])
        design_ok = design_result.get("status") == "ok"

        # ══ STEP 2: DEVELOPER — generate code from design ══
        impl_result = await self.registry.execute(
            npc_name="developer",
            skill_name="implement",
            config=self.config,
            quest=quest,
            params={
                "title": title,
                "research_summary": research_summary,
                "design_files": design_files,
                "success_criteria": criteria,
            },
        )
        code_files = impl_result.get("files_created", [])
        impl_ok = impl_result.get("status") == "ok"
        syntax_check = impl_result.get("syntax_check", {})

        # ══ STEP 3: QA — verify everything ══
        qa_result = await self.registry.execute(
            npc_name="qa",
            skill_name="verify",
            config=self.config,
            quest=quest,
            params={
                "files_to_check": code_files,
                "design_files": design_files,
                "success_criteria": criteria,
            },
        )
        qa_ok = qa_result.get("status") == "passed"

        # ══ Step 4: Auto-commit to git if QA passed ══
        commit_result = {}
        if qa_ok:
            # Stage and commit the new files
            commit_result = self._git_commit(quest_id, title, code_files + design_files)
            
            await self.qe.submit_for_review(quest_id, "developer")
            verify_result = await self.qe.verify_quest(quest_id, runs=1)
            quest_status = verify_result.get("status", "done")
        else:
            # QA flagged — still progress, but log the issues
            quest_status = "flagged"
            print(f"[PATA] QA flagged {quest_id}: {qa_result.get('output', '')}")

        self._stats["pata_completed"] += 1

        # Build summary
        summary_parts = []
        if design_ok:
            summary_parts.append(f"🎨 Design: {len(design_files)} files")
        if impl_ok:
            summary_parts.append(f"💻 Code: {len(code_files)} files (syntax: {syntax_check.get('passed', 0)}/{syntax_check.get('total', 0)})")
        summary_parts.append(f"🛡️ QA: {'PASSED' if qa_ok else 'FLAGGED'}")

        return {
            "stage": "pata",
            "quest_id": quest_id,
            "title": title,
            "status": quest_status,
            "design": {
                "ok": design_ok,
                "files": design_files,
            },
            "implementation": {
                "ok": impl_ok,
                "files": code_files,
                "syntax": syntax_check,
            },
            "qa": {
                "passed": qa_ok,
                "report": qa_result.get("report_file", ""),
                "output": qa_result.get("output", ""),
            },
            "git_commit": commit_result,
            "summary": " | ".join(summary_parts),
        }

    # ═══════════════════════════════════════════
    # STEP 6: COMPOUND → Corporation Memory
    # ═══════════════════════════════════════════

    async def _run_compound(self) -> Optional[dict]:
        """Extract lessons from recently completed quests.

        Phase 3: lessons go to corporation_memory AND update agent prompts.
        """
        cursor = await self.db.execute(
            "SELECT * FROM quests WHERE status='done' AND (compound_lessons IS NULL OR compound_lessons = '') ORDER BY completed_at DESC LIMIT 3"
        )
        done_quests = await cursor.fetchall()

        if not done_quests:
            return None

        results = []
        for quest in done_quests:
            quest_dict = self._quest_to_dict(quest)

            # ── Run compound action ──
            result = await self.registry.execute(
                npc_name="warden",
                skill_name="compound",
                config=self.config,
                quest=quest_dict,
                params={},
            )
            lessons = result.get("lessons", [])

            # ══ Phase 3: store lessons in corporation_memory ══
            if self._memory and lessons:
                for lesson in lessons:
                    # Determine which role this lesson applies to
                    role_target = "general"
                    lesson_lower = lesson.lower()
                    if "research" in lesson_lower or "findings" in lesson_lower or "knowledge" in lesson_lower:
                        role_target = "researcher"
                    elif "technical" in lesson_lower or "code" in lesson_lower or "implement" in lesson_lower:
                        role_target = "developer"
                    elif "design" in lesson_lower or "visual" in lesson_lower or "ui" in lesson_lower:
                        role_target = "designer"
                    elif "approve" in lesson_lower or "evaluate" in lesson_lower or "strategic" in lesson_lower:
                        role_target = "ceo"
                    elif "architect" in lesson_lower or "performance" in lesson_lower:
                        role_target = "cto"
                    elif "scout" in lesson_lower or "discover" in lesson_lower:
                        role_target = "scout"

                    await self._memory.store_lesson(
                        lesson=lesson,
                        source_quest=quest_dict.get("id", ""),
                        source_phase=quest_dict.get("phase", ""),
                        role_target=role_target,
                        category="general",
                        impact_score=0.5,
                    )

            # ══ Phase 3: build enriched prompts with new lessons ══
            if self._prompt_engine and lessons:
                for role in ["scout", "researcher", "ceo", "cto", "developer", "designer"]:
                    await self._prompt_engine.build_prompt(role)

            results.append({
                "quest_id": quest_dict.get("id"),
                "lessons": lessons,
                "memories_stored": len(lessons) if self._memory else 0,
            })

        self._stats["lessons_extracted"] += len(results)
        return {
            "stage": "compound",
            "quests_processed": len(results),
            "details": results,
        }

    # ═══════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════

    async def _mark_handed_off(self, quest_id: str) -> None:
        """The corp's lifecycle ENDS at the hand-off to Claude (research → package → file to inbox).
        SHIPPING is Claude's job — it develops the worthy ones into rigorous, Lab-tested work and records
        the verdict in the Crucible; the corp cannot observe that and must not gate on it. Marking the quest
        done HERE is the fix for the perpetual '0 shipped' + 'stuck in HEAD' alerts: the legacy PATA build
        chain (Designer→Developer→QA→git, _process_pata) stranded every approved quest in 'open'/'pata'
        forever, so throughput never registered and the pile-up kept re-firing the meta-scanner alert.
        Reversible: revert this call to restore the legacy self-build path."""
        if not (self.qe and getattr(self.qe, "db", None) and quest_id):
            return
        try:
            await self.qe.db.execute(
                "UPDATE quests SET status='done', proposal_status='handed_to_claude', "
                "completed_at=datetime('now') WHERE id=?",
                (quest_id,),
            )
            await self.qe.db.commit()
            self._stats["handed_to_claude"] = self._stats.get("handed_to_claude", 0) + 1
        except Exception as e:
            print(f"[Corp] hand-off completion error: {e}")

    async def _get_quests_by_phase(self, phase: str) -> list[dict]:
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
        if not self.db:
            return []
        try:
            cursor = await self.db.execute(
                "SELECT * FROM quests WHERE phase='head' AND status='review' AND (research_summary IS NULL OR research_summary = '') ORDER BY created_at ASC LIMIT 3",
            )
            rows = await cursor.fetchall()
            return [self._quest_to_dict(r) for r in rows]
        except Exception:
            return []

    async def _get_quests_awaiting_evaluation(self) -> list[dict]:
        if not self.db:
            return []
        try:
            cursor = await self.db.execute(
                "SELECT * FROM quests WHERE phase='head' AND research_summary IS NOT NULL AND research_summary != '' AND proposal_status='pending' ORDER BY created_at ASC LIMIT 3",
            )
            rows = await cursor.fetchall()
            return [self._quest_to_dict(r) for r in rows]
        except Exception:
            return []

    def _quest_to_dict(self, row) -> dict:
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


    @staticmethod
    def _lead_saturated(title: str, summary: str) -> str:
        """Root-cause guard for the daily inbox flood: a lead is refused at FILING time if (a) it matches a
        theme Claude editorially skipped via the gatekeeper (the generators kept re-offering 'memory-capacity
        threshold' variants 20x/day), or (b) its title+summary is a near-duplicate of a recently filed task.
        Returns the refusal reason, or '' if the lead is fresh. Checks the LEAD text only (not the shared
        instruction boilerplate, which inflates whole-task Jaccard past the inbox's 0.82 gate)."""
        import re as _re
        try:
            from agora.execution.gatekeeper import skipped_themes
            from agora.execution.claude_inbox import recent_texts
        except Exception:
            return ""
        stop = {"the", "a", "an", "of", "in", "on", "for", "and", "or", "to", "at", "is", "are", "does",
                "with", "that", "this", "which", "from", "into", "their", "its", "vs", "via"}
        def words(t):
            return {w for w in _re.findall(r"[a-z][a-z-]{2,}", (t or "").lower()) if w not in stop}
        lead = words(title) | words(summary)
        if not lead:
            return ""
        for theme in skipped_themes():
            tw = words(theme)
            if tw and len(tw & lead) / len(tw) >= 0.6:
                return f"gatekeeper-skipped theme: {theme[:60]}"
        for txt in recent_texts():
            core = txt.split("||")[0] + " " + (txt.split("RESEARCH:")[1][:300] if "RESEARCH:" in txt else "")
            ow = words(core)
            if ow and len(lead & ow) / max(1, len(lead | ow)) >= 0.45:
                return f"near-duplicate of a recent task: {txt[:60]}"
        return ""

    def _file_ship_review(self, quest: dict, ev: dict) -> None:
        """An idea the corp RESEARCHED and its CEO/CTO approved → file it to Claude's
        inbox as a 'Ship-review' proposal. Claude develops the promising ones into
        rigorous, scientifically-tested work and ships them; thin ones get skipped.
        The corp does the legwork; Claude is the bar for rigour and ambition."""
        try:
            from agora.execution.claude_inbox import add_task
            title = (quest.get("title") or "untitled idea")[:90]
            summary = (quest.get("research_summary") or quest.get("goal") or "")[:600]
            why_refused = self._lead_saturated(title, summary)
            if why_refused:
                print(f"[Corp->Claude] dossier REFUSED ({why_refused}): {title[:50]}")
                return
            why_refused = self._lead_saturated(title, summary)
            if why_refused:
                print(f"[Corp→Claude] ship-review REFUSED ({why_refused}): {title[:50]}")
                return
            src = quest.get("research_source") or quest.get("findings_path") or ""
            why = (ev.get("ceo_rationale") or ev.get("cto_rationale") or "")[:200]
            text = (
                f"Crucible candidate: {title} || CORP-RESEARCHED, CEO/CTO approved "
                f"(CEO {ev.get('ceo_score', 0):.0f}/CTO {ev.get('cto_score', 0):.0f}). "
                f"RESEARCH: {summary} WHY: {why} SOURCE: {src} "
                f"|| Claude: judge HONESTLY whether this claim deserves the Crucible bench. If yes, "
                f"REPLICATE it: build the smallest computational model of its mechanism via "
                f"/brain/lab/run, record REPRODUCED|FAILED|NOT_COMPUTABLE via /brain/replication-record, "
                f"add curation + re-render the Crucible. A potential FAILED of a famous claim is the "
                f"highest-value outcome. If the claim is thin/unmeasurable, skip with reason."
            )
            tid = add_task(text)
            self._stats["ship_reviews_filed"] = self._stats.get("ship_reviews_filed", 0) + 1
            print(f"[Corp→Claude] filed ship-review {tid}: {title[:50]}")
        except Exception as e:
            print(f"[Corp→Claude] ship-review file error: {e}")

    def _file_research_dossier(self, quest: dict, ev: dict) -> None:
        """REPOINT (owner 2026-06-26): a near-miss the corp RESEARCHED but the board did not
        ship-approve still carries real research value. Rather than let it die in HEAD, file it to
        Claude's inbox as a RESEARCH DOSSIER — packaged findings for Claude to DEVELOP into rigorous,
        Lab-tested work OR honestly ARCHIVE. The board score is a priority hint, not a kill switch;
        Claude is the bar for rigour/ambition (RAISED BAR: develop the ambitious ones, archive thin)."""
        try:
            from agora.execution.claude_inbox import add_task
            title = (quest.get("title") or "untitled idea")[:90]
            summary = (quest.get("research_summary") or quest.get("goal") or "")[:600]
            src = quest.get("research_source") or quest.get("findings_path") or ""
            why = (ev.get("cto_rationale") or ev.get("ceo_rationale") or "")[:200]
            text = (
                f"Research dossier: {title} || CORP-RESEARCHED, board near-miss "
                f"(CEO {ev.get('ceo_score', 0):.0f}/CTO {ev.get('cto_score', 0):.0f} — not ship-approved, "
                f"surfaced as a lead). RESEARCH: {summary} BOARD NOTE: {why} SOURCE: {src} "
                f"|| Claude: judge HONESTLY against the RAISED BAR. If it is a hard, original, testable "
                f"question, DEVELOP it into rigorous work (Lab + falsifier, real data where possible); "
                f"otherwise ARCHIVE with a one-line reason. Do NOT manufacture a small note from a thin lead."
            )
            tid = add_task(text)
            self._stats["ship_reviews_filed"] = self._stats.get("ship_reviews_filed", 0) + 1
            print(f"[Corp→Claude] filed research dossier {tid}: {title[:50]}")
        except Exception as e:
            print(f"[Corp→Claude] dossier file error: {e}")

    def _is_noteworthy(self, results: list[dict]) -> bool:
        """Fire the owner's briefing on REAL signals — he wants visibility into health and why agents
        stall. That includes the MetaScanner's self-diagnostics (agents stuck, too many rejections),
        completed research, approvals, and shipped commits. Repetition is held down upstream by the
        MetaScanner's one-live-quest-per-title dedup, so the same alert no longer repeats every tick."""
        for r in results:
            stage = r.get("stage", "")
            if stage == "meta" and r.get("quest_id"):        # a NEW health/diagnostic alert
                return True
            if stage == "pata" and r.get("git_commit", {}).get("sha"):
                return True
            if stage == "evaluation":                        # approved OR rejected — both are signal
                return True
            if stage == "head" and r.get("findings_count", 0) > 0:
                return True
            if stage == "scout" and r.get("status") == "new_quest":
                return True
        return False

    def _build_summary(self, results: list[dict]) -> str:
        """Owner-readable tick report: what happened, what it means, what (if anything)
        needs attention — grouped, deduped, plain language. No internal codes."""
        alerts, researched, verdicts, shipped, seeds = [], [], [], [], []
        for r in results:
            stage = r.get("stage", "")
            if stage == "meta" and r.get("quest_id"):
                alerts.append(r.get("title", "")[:80])
            elif stage == "scout" and r.get("status") == "new_quest":
                seeds.append(r.get("title", "").replace("Research question: ", "")[:70])
            elif stage == "head":
                n = r.get("findings_count", 0)
                t = r.get("title", "").replace("Research question: ", "")[:60]
                researched.append(
                    f"“{t}” — {n} finding{'s' if n != 1 else ''}"
                    + (" → to CEO/CTO review" if n else " → dead-end check"))
            elif stage == "evaluation":
                t = r.get("title", "").replace("Research question: ", "")[:55]
                cto, ceo = r.get("cto_score", 0), r.get("ceo_score", 0)
                why = (r.get("cto_rationale") or r.get("ceo_rationale") or "")[:90]
                if r.get("approved"):
                    verdicts.append(f"✅ approved “{t}” (CTO {cto:.0f} · CEO {ceo:.0f}) → sent to Claude for ship-review")
                else:
                    verdicts.append(f"❌ rejected “{t}” (CTO {cto:.0f} · CEO {ceo:.0f})"
                                    + (f" — {why}" if why else ""))
            elif stage == "pata":
                commit = r.get("git_commit", {}).get("sha", "")
                shipped.append(f"“{r.get('title', '')[:45]}”" + (f" [{commit}]" if commit else ""))

        parts = [f"🏢 Corporation — tick #{self._stats['ticks']}"]
        if alerts:
            parts.append("")
            parts.append(f"⚠️ Health alerts ({len(alerts)}):")
            parts += [f"  • {a}" for a in alerts]
        if seeds:
            parts.append("")
            parts.append("🌱 New research quests:")
            parts += [f"  • {s}" for s in seeds]
        if researched:
            parts.append("")
            parts.append("🔬 Researched this tick:")
            parts += [f"  • {x}" for x in researched]
        if verdicts:
            parts.append("")
            parts.append("👔 Board verdicts:")
            parts += [f"  • {v}" for v in verdicts]
        if shipped:
            parts.append("")
            parts.append("🛠️ Shipped:")
            parts += [f"  • {s}" for s in shipped]
        if len(parts) == 1:
            parts.append("Quiet tick — nothing noteworthy.")

        s = self._stats
        parts += [
            "",
            f"Lifetime: {s['head_completed']} researched · "
            f"{s.get('handed_to_claude', s.get('ship_reviews_filed', 0))} handed to Claude "
            f"(shipping tracked in the Crucible) · {s['lessons_extracted']} lessons",
        ]
        return "\n".join(parts)

    async def _send_report(self, message: str):
        """Send the tick summary via Telegram."""
        from agora.dungeon_os.actions.hermes import action_send_message
        await action_send_message(
            self.config,
            {"id": f"tick-{self._stats['ticks']}", "title": "Corporation Report", "goal": message, "subsystem": "comms"},
            {"message": message, "title": "🏢 Corporation Report", "channel": "telegram"},
        )

    def _git_commit(self, quest_id: str, title: str, files: list) -> dict:
        """Auto-commit Phase 4 output files to git.

        Stages the generated files and creates a commit
        with the quest title as message.
        """
        import subprocess
        repo_path = self.config.get("repo_path") or os.path.expanduser("/home/vboxuser/agora")

        if not files:
            return {"committed": False, "reason": "No files to commit"}

        try:
            # Stage files (only those that exist)
            for f in files:
                if os.path.exists(f):
                    # Get relative path from repo root
                    rel = os.path.relpath(f, repo_path)
                    subprocess.run(
                        ["git", "add", rel],
                        cwd=repo_path, capture_output=True, text=True, timeout=10,
                    )

            # Commit
            commit_msg = f"🤖 Phase 4: {title[:60]}\n\nAuto-generated by Dungeon OS Agent Worker\nQuest: {quest_id}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=repo_path, capture_output=True, text=True, timeout=15,
            )

            sha = ""
            for line in result.stdout.split("\n"):
                if "commit" in line:
                    sha = line.strip()
                    break

            committed = result.returncode == 0
            if committed:
                print(f"[Git] Committed {len(files)} files: {sha[:20]}")
            else:
                print(f"[Git] Commit skipped: {result.stdout[:100]}")

            return {
                "committed": committed,
                "sha": sha[:20] if sha else "",
                "files_staged": len(files),
                "message": result.stdout[:100] if not committed else sha[:20],
            }
        except Exception as e:
            print(f"[Git] Commit error: {e}")
            return {"committed": False, "error": str(e)}

    def get_stats(self) -> dict:
        return dict(self._stats)

    async def get_phase3_stats(self) -> dict:
        """Get additional Phase 3 statistics."""
        if not self._memory:
            return {"phase3_initialized": False}
        memory_stats = await self._memory.get_stats()
        meta_stats = self._meta_scanner.get_stats() if self._meta_scanner else {}
        quality_stats = {}
        if self._quality_tracker:
            quality_stats["approval"] = await self._quality_tracker.get_approval_rate()
            quality_stats["avg_quality"] = await self._quality_tracker.get_average_quality()
            quality_stats["trends"] = await self._quality_tracker.get_trends(limit=5)

        return {
            "phase3_initialized": self._phase3_initialized,
            "memory": memory_stats,
            "meta_scanner": meta_stats,
            "quality": quality_stats,
        }
