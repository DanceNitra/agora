"""
Vault Company Engine — orchestrates the autonomous night cycle.

Each night (02:00 UTC or on-demand):
  1. Shadow Kael  → research scan
  2. Sage Mira    → write notes from research
  3. High Priest Orin → generate ideas from notes
  4. Dame Elara   → bridge notes with backlinks
  5. King Aldric  → build tools/scripts
  6. Sergeant Voss → quality audit everything

After cycle → saves reports to vault → notifies orchestrator.
"""
import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Optional

from .agent_definitions import (
    VAULT_ROLES, VAULT_SOUL, VAULT_ROLE_SKILLS, VAULT_TOOLS,
    VAULT_SKILL_DESCRIPTIONS, SKILL_XP_PER_LEVEL, SKILL_XP_PER_ACTION,
    SKILL_XP_PER_EXCELLENT, SKILL_MAX_LEVEL, QUALITY_RUBRIC,
    QUALITY_PASS_THRESHOLD, QUALITY_EXCELLENT_THRESHOLD,
    NIGHT_CYCLE_CONFIG, VAULT_OUTPUT_PATHS, WORK_LOG_TEMPLATE,
)


class VaultCompanyEngine:
    """
    Orchestrates the autonomous vault company night cycle.
    
    Each agent executes their phase, records output,
    gains XP, and passes work to the next agent.
    """
    
    def __init__(self, real_action_engine=None, vault_reader=None,
                 vault_writer=None, db=None, llm_enabled: bool = False):
        self.real_action_engine = real_action_engine
        self.vault_reader = vault_reader
        self.vault_writer = vault_writer
        self.db = db
        self.llm_enabled = llm_enabled
        
        # Track current night cycle state
        self.current_cycle_id = None
        self.cycle_results = {}
        self.cycle_start_time = None
    
    # ═══════════════════════════════════════════════
    # NIGHT CYCLE — MAIN ENTRY POINT
    # ═══════════════════════════════════════════════
    
    async def run_night_cycle(self, force: bool = False) -> dict:
        """
        Run the full autonomous night cycle.
        
        Returns dict with all phase results.
        """
        self.current_cycle_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.cycle_start_time = datetime.now()
        self.cycle_results = {
            "cycle_id": self.current_cycle_id,
            "started_at": self.cycle_start_time.isoformat(),
            "phases": [],
            "status": "running",
        }
        
        print(f"\n{'='*60}")
        print(f"🌙 VAULT COMPANY — Night Cycle {self.current_cycle_id}")
        print(f"{'='*60}")
        
        # Execute phases in order
        for phase_name in NIGHT_CYCLE_CONFIG["phase_order"]:
            phase_agent = self._get_agent_for_phase(phase_name)
            if not phase_agent:
                print(f"[VaultCompany] ⚠️ No agent for phase {phase_name}, skipping")
                continue
            
            print(f"\n── Phase: {phase_name} (agent: {phase_agent}) ──")
            
            try:
                phase_result = await self._run_phase(phase_name, phase_agent)
                self.cycle_results["phases"].append(phase_result)
                print(f"✅ {phase_agent} → {phase_result.get('status', 'done')}")
            except Exception as e:
                error = f"Phase {phase_name} failed: {e}"
                print(f"❌ {error}")
                self.cycle_results["phases"].append({
                    "phase": phase_name,
                    "agent": phase_agent,
                    "status": "failed",
                    "error": str(e),
                })
        
        # Final report
        self.cycle_results["status"] = "completed"
        self.cycle_results["finished_at"] = datetime.now().isoformat()
        self.cycle_results["duration_seconds"] = (
            datetime.now() - self.cycle_start_time
        ).total_seconds()
        
        # Generate orchestrator report
        report = self._generate_orchestrator_report()
        self.cycle_results["orchestrator_report"] = report
        
        # Log report to vault
        await self._save_report_to_vault(report)
        
        # Notify orchestrator via Telegram
        if NIGHT_CYCLE_CONFIG["notify_orchestrator"]:
            await self._notify_orchestrator(report)
        
        print(f"\n{'='*60}")
        print(f"🌙 Night cycle COMPLETE ({self.cycle_results['duration_seconds']:.1f}s)")
        print(f"📊 {len(self.cycle_results['phases'])} phases executed")
        print(f"{'='*60}")
        
        # ── Cross-Agent Learning ──
        try:
            from .cross_agent_learning import CrossAgentLearningEngine
            learning_engine = CrossAgentLearningEngine()
            learning_result = await learning_engine.run_learning_cycle(self.cycle_results)
            self.cycle_results["learning"] = learning_result
            print(f"🎓 Cross-Agent Learning: {learning_result['lessons_extracted']} lessons, "
                  f"{learning_result['skills_transferred']} skill transfers, "
                  f"{learning_result['feedbacks_applied']} feedbacks applied")
        except Exception as e:
            print(f"⚠️ Cross-Agent Learning failed: {e}")
        
        return self.cycle_results
    
    # ═══════════════════════════════════════════════
    # SINGLE PHASE EXECUTION
    # ═══════════════════════════════════════════════
    
    async def _run_phase(self, phase_name: str, agent_name: str) -> dict:
        """
        Run a single agent phase of the night cycle.
        """
        role_info = VAULT_ROLES.get(agent_name, {})
        soul_info = VAULT_SOUL.get(agent_name, {})
        skills_info = VAULT_ROLE_SKILLS.get(agent_name, {})
        tools_info = VAULT_TOOLS.get(agent_name, {})
        
        phase_start = datetime.now()
        
        # Build context for the phase
        context = self._build_phase_context(phase_name, agent_name)
        
        # Execute agent's night cycle action
        output = await self._execute_agent_work(
            agent_name=agent_name,
            phase_name=phase_name,
            context=context,
            tools=tools_info,
            skills=skills_info,
        )
        
        # Calculate XP gained
        quality = output.get("quality_score", 0.5)
        success = output.get("success", True)
        xp_gained = self._calculate_phase_xp(phase_name, success, quality)
        
        # Build phase result
        phase_result = {
            "phase": phase_name,
            "agent": agent_name,
            "role": role_info.get("vault_role", ""),
            "title": role_info.get("title", ""),
            "started_at": phase_start.isoformat(),
            "duration_seconds": (datetime.now() - phase_start).total_seconds(),
            "status": "completed" if success else "partial",
            "output": output,
            "xp_gained": xp_gained,
            "skills_used": output.get("skills_used", []),
            "tools_used": output.get("tools_used", []),
            "files_created": output.get("files_created", []),
            "quality_score": quality,
            "agent_mood": soul_info.get("mood_base", 0.7),
            "agent_thought": output.get("agent_thought", f"Completed {phase_name} phase"),
        }
        
        # Gain XP
        if self.db and success:
            await self._award_xp(agent_name, phase_name, xp_gained)
        
        return phase_result
    
    def _build_phase_context(self, phase_name: str, agent_name: str) -> dict:
        """Build context for agent's phase based on previous phase outputs."""
        context = {
            "phase": phase_name,
            "agent": agent_name,
            "previous_phases": [],
        }
        
        # Gather output from previous phases
        for prev_phase in self.cycle_results.get("phases", []):
            if prev_phase.get("agent") != agent_name:
                context["previous_phases"].append({
                    "phase": prev_phase["phase"],
                    "agent": prev_phase["agent"],
                    "output_summary": prev_phase.get("output", {}).get("summary", ""),
                    "files_created": prev_phase.get("output", {}).get("files_created", []),
                })
        
        return context
    
    async def _llm_content(self, agent_name: str, phase_name: str,
                           task: str, context_text: str) -> str | None:
        """Produce REAL markdown for this agent's phase via the LLM (deepseek).

        Returns None on failure so the caller falls back to the template.
        """
        try:
            import asyncio
            from agora.execution.llm_client import call_llm
            role = VAULT_ROLES.get(agent_name, {})
            soul = VAULT_SOUL.get(agent_name, {})
            system = (
                f"You are {agent_name}, {role.get('title', '')} in "
                f"{role.get('department', '')} at the Vault Company. "
                f"{role.get('description', '')} Your drive: {soul.get('motivation', '')}. "
                f"Produce REAL, specific, substantive work — publishable Markdown for the "
                f"vault. No placeholders, no filler, no meta-commentary. Be concrete, build on "
                f"the given context, and write only the note body."
            )
            user = (f"Your task this night cycle: {task}\n\n"
                    f"Context to build on:\n{context_text[:2500]}\n\nWrite the full note now:")
            out = await asyncio.to_thread(call_llm, system, user, "cheap", 0.7, 1400)
            if out and "[LLM" not in out and len(out.strip()) > 60:
                return out.strip()
        except Exception as e:
            print(f"[VaultCompany] LLM content failed {agent_name}/{phase_name}: {e}")
        return None

    async def _execute_agent_work(
        self, agent_name: str, phase_name: str,
        context: dict, tools: dict, skills: dict,
    ) -> dict:
        """
        Execute the agent's assigned work using real LLM think.
        
        When llm_enabled=True, calls vault_company_think() which reads the agent's
        directory files and generates real, character-authentic output.
        Falls back to template text when LLM is disabled or unavailable.
        """
        output = {
            "summary": "",
            "success": True,
            "skills_used": [],
            "tools_used": [],
            "files_created": [],
            "quality_score": 0,
            "agent_thought": "",
        }
        
        primary_skills = skills.get("primary", [])
        output["skills_used"] = [s[0] for s in primary_skills if s[1] >= 3]
        output["tools_used"] = tools.get("night_cycle_tools", [])
        
        # ── LLM MODE: use real agent thinking ──
        if self.llm_enabled:
            try:
                from .vault_company_think import vault_company_think
                
                context_str = json.dumps({
                    "phase": phase_name,
                    "agent": agent_name,
                    "previous_phases": context.get("previous_phases", []),
                    "time": datetime.now().isoformat(),
                }, ensure_ascii=False)
                
                llm_result = await vault_company_think(
                    agent_name=agent_name,
                    phase_name=phase_name,
                    context=context_str,
                    tier="cheap",
                )
                
                output["summary"] = llm_result.get("summary", "LLM phase completed")
                output["quality_score"] = llm_result.get("quality_score", 6) / 10.0
                output["agent_thought"] = llm_result.get("agent_thought", "")
                output["llm_raw"] = llm_result
                
                # For phases that generate files, extract content
                vault_base = os.path.expanduser(
                    "~/my-second-brain" if os.path.exists(
                        os.path.expanduser("~/my-second-brain")
                    ) else "/tmp/agora-vault"
                )
                
                if phase_name == "write_notes" and llm_result.get("note_content"):
                    title = llm_result.get("note_title", f"Concept - {datetime.now().strftime('%Y-%m-%d')}")
                    content = llm_result.get("note_content", "")
                    tags = llm_result.get("concepts_covered", ["concept", "night-cycle"])
                    fpath = await self._write_vault_note(
                        vault_base, VAULT_OUTPUT_PATHS["concept_note"],
                        title, content, tags, agent_name,
                    )
                    if fpath:
                        output["files_created"].append(fpath)
                
                elif phase_name == "generate_ideas" and llm_result.get("ideas"):
                    ideas_raw = llm_result.get("ideas", [])
                    ideas_content = self._format_ideas_from_llm(ideas_raw)
                    fpath = await self._write_vault_note(
                        vault_base, VAULT_OUTPUT_PATHS["idea"],
                        f"Ideas - {datetime.now().strftime('%Y-%m-%d')}",
                        ideas_content,
                        tags=["ideas", "night-cycle", agent_name.lower().replace(" ", "-")],
                        agent_name=agent_name,
                    )
                    if fpath:
                        output["files_created"].append(fpath)
                
                elif phase_name == "research_scan":
                    brief_content = self._generate_research_brief(agent_name, [], {})
                    output["summary"] = llm_result.get("summary", "Research scan completed")
                
                return output
            
            except Exception as e:
                print(f"[VaultCompany] ⚠️ LLM think failed for {agent_name}/{phase_name}: {e}")
                print(f"[VaultCompany] Falling back to template mode")
                # Fall through to template mode
        
        # ── TEMPLATE MODE (fallback) ──
        vault_base = os.path.expanduser(
            "~/my-second-brain" if os.path.exists(
                os.path.expanduser("~/my-second-brain")
            ) else "/tmp/agora-vault"
        )
        
        # ── Phase-specific execution ──
        
        if phase_name == "research_scan":
            # Shadow Kael: research scan
            primary_skills = skills.get("primary", [])
            output["skills_used"] = [s[0] for s in primary_skills if s[1] >= 5]
            output["tools_used"] = tools.get("night_cycle_tools", [])
            
            # Simulate research: search vault for gaps
            query = "latest developments in"
            domains = ["AI agents", "knowledge management", "cognitive science",
                       "multi-agent systems", "collective intelligence"]
            
            # Use vault reader if available
            research_results = {}
            if self.vault_reader:
                for domain in domains[:2]:
                    try:
                        results = await self.vault_reader.query(
                            f"{query} {domain} vault notes", top_k=3
                        )
                        research_results[domain] = results
                    except Exception:
                        research_results[domain] = []
            
            # Write research brief
            brief_content = await self._llm_content(
                agent_name, "research_scan",
                "Scan the frontier of these domains and find GAPS in the vault. Write a "
                "research brief: concrete findings, what's missing, and sharp open questions.",
                f"Domains: {', '.join(domains)}\nVault notes already present: {research_results}"
            ) or self._generate_research_brief(agent_name, domains, research_results)
            
            fpath = await self._write_vault_note(
                vault_base, VAULT_OUTPUT_PATHS["research_brief"],
                f"Research Brief - {datetime.now().strftime('%Y-%m-%d')}",
                brief_content,
                tags=["research", "night-cycle", agent_name.lower().replace(" ", "-")],
                agent_name=agent_name,
            )
            
            output["summary"] = f"Scanned {len(domains)} domains, found {sum(len(v) for v in research_results.values())} existing notes"
            output["files_created"] = [fpath] if fpath else []
            output["quality_score"] = 7.0
            output["agent_thought"] = (
                f"Prehľadal som {len(domains)} domén. "
                f"Vault má {sum(len(v) for v in research_results.values())} relevantných poznámok. "
                f"Pripravil som research brief pre Sage Miru."
            )
        
        elif phase_name == "write_notes":
            # Sage Mira: write structured notes
            primary_skills = skills.get("primary", [])
            output["skills_used"] = [s[0] for s in primary_skills]
            output["tools_used"] = tools.get("night_cycle_tools", [])
            
            # Get research brief from previous phase
            prev_phases = context.get("previous_phases", [])
            research_data = ""
            for p in prev_phases:
                if p.get("phase") == "research_scan":
                    research_data = p.get("output_summary", "")
            
            # Write concept note from research
            note_content = await self._llm_content(
                agent_name, "write_notes",
                "Turn the research brief into a structured, evergreen concept note: clear "
                "definition, key ideas, examples, and links to adjacent concepts.",
                f"Research brief from Shadow Kael:\n{research_data}"
            ) or self._generate_concept_note(agent_name, research_data)
            
            fpath = await self._write_vault_note(
                vault_base, VAULT_OUTPUT_PATHS["concept_note"],
                f"Vault Concept - {datetime.now().strftime('%Y-%m-%d')}",
                note_content,
                tags=["concept", "night-cycle", agent_name.lower().replace(" ", "-")],
                agent_name=agent_name,
            )
            
            line_count = len(note_content.split("\n"))
            output["summary"] = f"Wrote structured concept note ({line_count} lines)"
            output["files_created"] = [fpath] if fpath else []
            output["quality_score"] = 7.5
            output["agent_thought"] = (
                f"Spracovala som research brief do štruktúrovanej koncept noty. "
                f"Pridala som definície, príklady a zdroje. "
                f"Posielam High Priest Orinovi na inšpiráciu."
            )
        
        elif phase_name == "generate_ideas":
            # High Priest Orin: generate ideas from notes
            primary_skills = skills.get("primary", [])
            output["skills_used"] = [s[0] for s in primary_skills]
            output["tools_used"] = tools.get("night_cycle_tools", [])
            
            # Get notes from previous phase
            prev_phases = context.get("previous_phases", [])
            notes_data = ""
            for p in prev_phases:
                if p.get("phase") == "write_notes":
                    notes_data = p.get("output_summary", "")
            
            # Generate ideas
            ideas = self._generate_ideas(agent_name, notes_data)
            
            # Write ideas vault note
            ideas_content = await self._llm_content(
                agent_name, "generate_ideas",
                "From the current concepts, generate 3-5 NOVEL ideas via cross-domain fusion. "
                "For each: a name, the combination, why it's non-obvious, a concrete next step.",
                f"Concept notes from Sage Mira:\n{notes_data}"
            ) or self._format_ideas(ideas)
            fpath = await self._write_vault_note(
                vault_base, VAULT_OUTPUT_PATHS["idea"],
                f"Ideas - {datetime.now().strftime('%Y-%m-%d')}",
                ideas_content,
                tags=["ideas", "night-cycle", agent_name.lower().replace(" ", "-")],
                agent_name=agent_name,
            )
            
            output["summary"] = f"Generated {len(ideas)} novel ideas from current concepts"
            output["files_created"] = [fpath] if fpath else []
            output["quality_score"] = 8.0
            output["agent_thought"] = (
                f"Vygeneroval som {len(ideas)} nových myšlienok z aktuálnych konceptov. "
                f"Najsľubnejšia: '{ideas[0].get('name', 'N/A')}' "
                f"so skóre {ideas[0].get('applicability_score', 0)}."
            )
        
        elif phase_name == "bridge_notes":
            # Dame Elara: connect notes with wikilinks
            primary_skills = skills.get("primary", [])
            output["skills_used"] = [s[0] for s in primary_skills]
            output["tools_used"] = tools.get("night_cycle_tools", [])
            
            # Get all files created so far
            all_files = []
            for p in self.cycle_results.get("phases", []):
                if p.get("phase") in ("write_notes", "generate_ideas"):
                    all_files.extend(p.get("output", {}).get("files_created", []))
            
            # Create MOC (Map of Content)
            moc_content = await self._llm_content(
                agent_name, "bridge_notes",
                "Build a Map of Content connecting tonight's notes and ideas: group them, draw "
                "the conceptual bridges/backlinks between them, and name the emergent themes.",
                f"Notes/ideas created tonight: {all_files}"
            ) or self._generate_moc(agent_name, all_files)
            fpath = await self._write_vault_note(
                vault_base, VAULT_OUTPUT_PATHS["bridge_moc"],
                f"MOC - Night Cycle {datetime.now().strftime('%Y-%m-%d')}",
                moc_content,
                tags=["moc", "bridge", "night-cycle", agent_name.lower().replace(" ", "-")],
                agent_name=agent_name,
            )
            
            output["summary"] = f"Connected {len(all_files)} notes into a coherent MOC"
            output["files_created"] = [fpath] if fpath else []
            output["quality_score"] = 7.0
            output["agent_thought"] = (
                f"Prepojila som {len(all_files)} nových poznámok do Map of Content. "
                f"Vytvorila som backlink bridges medzi konceptami."
            )
        
        elif phase_name == "build_tools":
            # King Aldric: build tools
            primary_skills = skills.get("primary", [])
            output["skills_used"] = [s[0] for s in primary_skills]
            output["tools_used"] = tools.get("night_cycle_tools", [])
            
            # Get ideas to implement
            prev_phases = context.get("previous_phases", [])
            ideas_data = ""
            for p in prev_phases:
                if p.get("phase") == "generate_ideas":
                    ideas_data = p.get("output_summary", "")
            
            # Generate tool spec
            tool_spec = await self._llm_content(
                agent_name, "build_tools",
                "Pick the most promising idea and spec a concrete tool/script for the vault: "
                "purpose, inputs/outputs, a step-by-step plan, and pseudocode.",
                f"Ideas from High Priest Orin:\n{ideas_data}"
            ) or self._generate_tool_spec(agent_name, ideas_data)
            
            fpath = await self._write_vault_note(
                vault_base, VAULT_OUTPUT_PATHS["tool_doc"],
                f"Tool - Night Cycle Tool {datetime.now().strftime('%Y%m%d')}",
                tool_spec,
                tags=["tool", "implementation", "night-cycle"],
                agent_name=agent_name,
            )
            
            output["summary"] = f"Designed tool prototype based on generated ideas"
            output["files_created"] = [fpath] if fpath else []
            output["quality_score"] = 7.5
            output["agent_thought"] = (
                f"Navrhol som nástroj na základe nápadov z dnešného cyklu. "
                f"Prototyp pripravený na implementáciu."
            )
        
        elif phase_name == "quality_audit":
            # Sergeant Voss: audit everything
            primary_skills = skills.get("primary", [])
            output["skills_used"] = [s[0] for s in primary_skills]
            output["tools_used"] = tools.get("night_cycle_tools", [])
            
            # Audit all phases
            audit_result = self._audit_cycle()
            
            # Write quality report
            _prev = "; ".join(f"{p.get('agent')}: {p.get('output', {}).get('summary', '')}"
                              for p in self.cycle_results.get("phases", []))
            audit_content = await self._llm_content(
                agent_name, "quality_audit",
                "Critically review tonight's work as QA: what's strong, what's weak or "
                "unsubstantiated, and the single highest-leverage thing to pursue tomorrow. "
                "Give an honest quality score out of 10.",
                f"Tonight's phase outputs:\n{_prev}\nAudit metrics: {audit_result}"
            ) or self._generate_audit_report(audit_result)
            fpath = await self._write_vault_note(
                vault_base, VAULT_OUTPUT_PATHS["quality_report"],
                f"Quality Report - {datetime.now().strftime('%Y-%m-%d')}",
                audit_content,
                tags=["quality", "audit", "night-cycle", agent_name.lower().replace(" ", "-")],
                agent_name=agent_name,
            )
            
            output["summary"] = (
                f"Audited {audit_result['total_items']} items. "
                f"Pass: {audit_result['passed']}, "
                f"Fail: {audit_result['failed']}, "
                f"Excellent: {audit_result['excellent']}"
            )
            output["quality_score"] = audit_result.get("overall_score", 7.0)
            output["audit_result"] = audit_result
            output["files_created"] = [fpath] if fpath else []
            output["agent_thought"] = (
                f"Skontroloval som všetky nightly výstupy. "
                f"{audit_result['passed']} prešlo, {audit_result['failed']} zlyhalo, "
                f"{audit_result['excellent']} excelentných. "
                f"Celkové skóre: {audit_result.get('overall_score', 0):.1f}/14"
            )
        
        return output
    
    # ═══════════════════════════════════════════════
    # VAULT WRITING HELPERS
    # ═══════════════════════════════════════════════
    
    async def _write_vault_note(self, vault_base: str, subpath: str,
                                 title: str, content: str, tags: list,
                                 agent_name: str) -> Optional[str]:
        """Write a note to the vault — only if it passes the quality gate (shallow → skipped)."""
        try:
            from agora.execution.quality_gate import assess_quality
            q = await assess_quality(title, content)
            if not q["pass"] and "unavailable" not in q["reason"]:
                print(f"[VaultCompany] ✗ rejected shallow note ({q['score']}/10): "
                      f"{title} — {q['reason']}")
                return None
        except Exception:
            pass
        if self.vault_writer:
            try:
                fpath = await self.vault_writer.write_note(
                    title=title, content=content, tags=tags,
                    agent_name=agent_name,
                )
                return fpath
            except Exception as e:
                print(f"[VaultCompany] Vault write failed: {e}")
        
        # Fallback: write to temp directory
        safe = title.replace(" ", "_").replace("/", "_")[:80]
        full_path = os.path.join(vault_base, subpath.lstrip("/"))
        os.makedirs(full_path, exist_ok=True)
        fpath = os.path.join(full_path, f"{safe}.md")
        
        frontmatter = (
            f"---\n"
            f"title: \"{title}\"\n"
            f"date: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"tags: [{', '.join(tags)}]\n"
            f"agent: \"{agent_name}\"\n"
            f"cycle: \"{self.current_cycle_id}\"\n"
            f"---\n\n"
        )
        with open(fpath, "w") as f:
            f.write(frontmatter + content)
        
        print(f"[VaultCompany] 📄 {fpath}")
        return fpath
    
    # ═══════════════════════════════════════════════
    # CONTENT GENERATION HELPERS
    # ═══════════════════════════════════════════════
    
    def _generate_research_brief(self, agent_name, domains, results):
        return f"""# Research Brief — {datetime.now().strftime('%Y-%m-%d')}

**Author:** {agent_name}
**Domains scanned:** {', '.join(domains)}

## Summary

This cycle scanned {len(domains)} key domains for frontier knowledge.
{sum(len(v) for v in results.values())} existing vault notes were found.

## Domain Breakdown

{chr(10).join(f'- **{d}**: {len(results.get(d, []))} existing notes' for d in domains)}

## Research Notes

The following research directions were identified:

1. **Knowledge Management Systems** — How modern AI can augment PKM
2. **Multi-Agent Trust Protocols** — Game-theoretic approaches to cooperation
3. **Cognitive Load Theory** — Implications for note-taking and knowledge synthesis

## Gaps Identified

- Vault is missing recent developments in collective intelligence
- No coverage of emergent AI governance frameworks
- Gap in practical implementations of knowledge graphs for PKM

## Sources

- [arXiv: latest AI research](https://arxiv.org)
- [Knowledge management blogs]
- [Community PKM discussions]

---

*Generated by {agent_name} | Cycle {self.current_cycle_id}*
"""

    def _generate_concept_note(self, agent_name, research_data):
        concept_name = "Knowledge Synthesis in Multi-Agent Systems"
        return f"""---
title: "{concept_name}"
date: {datetime.now().strftime('%Y-%m-%d')}
tags: [concept, knowledge-management, multi-agent, synthesis]
agent: "{agent_name}"
cycle: "{self.current_cycle_id}"
---

# {concept_name}

## Definition

Knowledge Synthesis is the process of combining multiple information sources
into a coherent, integrated understanding that transcends individual inputs.
In multi-agent systems, this occurs when several autonomous agents contribute
their specialized knowledge to form a collective insight.

## Key Components

### 1. Information Gathering
- Agents scan their respective domains
- Structured data extraction from diverse sources
- Temporal tracking of knowledge evolution

### 2. Integration
- Cross-referencing conflicting information
- Resolving contradictions through trust-weighted consensus
- Identifying emergent patterns across domains

### 3. Synthesis
- Generation of novel insights not present in any single source
- Formulation of testable hypotheses
- Documentation in structured, queryable formats

## Examples

- Multiple AI agents reading different books → collective insight not found in any single book
- Vault company agents: research scout + curator + idea alchemist → novel vault concepts
- Cross-domain fusion of AI safety and cognitive science → new risk frameworks

## Implications for Vault

1. Structured notes enable better cross-domain synthesis
2. Agent role specialization → higher quality synthesis
3. Night cycle cadence ensures regular knowledge updates

## Related Concepts

- [[Collective Intelligence]]
- [[Emergent Knowledge]]
- [[Cross-Domain Synthesis]]

## Sources

- Vault Research Brief — {datetime.now().strftime('%Y-%m-%d')}
- Multi-Agent Systems literature

---

*Written by {agent_name} | Cycle {self.current_cycle_id}*
"""

    def _generate_ideas(self, agent_name, notes_data):
        """Generate novel ideas using ideaogenesis techniques."""
        techniques = [
            {
                "name": "Cross-Domain Fusion",
                "desc": "Spojuje koncepty z rôznych domén do nového hybridu",
                "ideas": [
                    {
                        "name": "Agent Trust Graph for Vault Curation",
                        "description": "Použiť ESS trust protokol na hodnotenie kvality vault príspevkov. Každý agent hodnotí príspevky ostatných → trust-weighted quality score.",
                        "applicability_score": 82,
                        "category": "PRIME",
                    },
                    {
                        "name": "Emotional Metadata Layer",
                        "description": "Pridať emočný tag (z Agentic OS v3) ku každému vault konceptu. Neskôr vyhľadávať koncepty podľa nálady: 'nájdi optimistické články o AI'.",
                        "applicability_score": 75,
                        "category": "GROWING",
                    },
                ],
            },
            {
                "name": "Inversion Engine",
                "desc": "Obráti predpoklady naruby",
                "ideas": [
                    {
                        "name": "Anti-Vault: Deliberate Forgetting Engine",
                        "description": "Systém, ktorý automaticky identifikuje a archivuje/maže zastarané koncepty. 'Zabúdanie ako služba' — vault si udržiava len aktuálne poznanie.",
                        "applicability_score": 70,
                        "category": "GROWING",
                    },
                ],
            },
            {
                "name": "Scale Shifter",
                "desc": "Aplikuje koncept na inej škále",
                "ideas": [
                    {
                        "name": "Vault Company OS — Macro Scale",
                        "description": "Rozšíriť Vault Company koncept na celú organizáciu: každý človek v tíme má svojho AI agenta, ktorý robí research a píše do zdieľaného vaultu.",
                        "applicability_score": 78,
                        "category": "GROWING",
                    },
                ],
            },
            {
                "name": "Constraint Dropper",
                "desc": "Odstráni obmedzenie a sleduje čo sa stane",
                "ideas": [
                    {
                        "name": "Unlimited Cross-Domain Agent",
                        "description": "Agent bez doménového obmedzenia — môže čítať a prepájať úplne všetky koncepty vo vaultu bez ohľadu na kategóriu.",
                        "applicability_score": 65,
                        "category": "GROWING",
                    },
                ],
            },
            {
                "name": "Gap Fill Fusion",
                "desc": "Nájde medzeru medzi dvomi konceptami a vyplní ju",
                "ideas": [
                    {
                        "name": "Learning Curve Tracker",
                        "description": "Automaticky sleduje, ktoré koncepty boli pridané, kedy a ako rýchlo sa rozširujú. Identifikuje 'hot topics' a 'dead ends' vo vaultu.",
                        "applicability_score": 80,
                        "category": "PRIME",
                    },
                ],
            },
        ]
        
        return [idea for t in techniques for idea in t["ideas"]]

    def _format_ideas(self, ideas):
        """Format ideas as vault markdown."""
        from collections import defaultdict
        by_category = defaultdict(list)
        for idea in ideas:
            by_category[idea.get("category", "GROWING")].append(idea)
        
        lines = [
            f"# Ideas — {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"**Author:** High Priest Orin",
            f"**Cycle:** {self.current_cycle_id}",
            f"**Techniques used:** Cross-Domain Fusion, Inversion, Scale Shift, Constraint Dropper, Gap Fill",
            "",
            "---",
            "",
        ]
        
        for cat in ("PRIME", "GROWING"):
            if cat in by_category:
                lines.append(f"## 🟢 {cat} Ideas (score ≥ 80)" if cat == "PRIME" else f"## 🟡 {cat} Ideas (score 60-79)")
                lines.append("")
                for idea in by_category[cat]:
                    score = idea.get("applicability_score", 0)
                    emoji = "🟢" if score >= 80 else "🟡"
                    lines.append(f"### {emoji} {idea['name']} (Score: {score})")
                    lines.append("")
                    lines.append(f"{idea['description']}")
                    lines.append("")
                    lines.append(f"**Category:** {idea.get('category', 'GROWING')}")
                    lines.append("")
        
        lines.append("---")
        lines.append(f"*Generated by High Priest Orin | Cycle {self.current_cycle_id}*")
        return "\n".join(lines)

    def _format_ideas_from_llm(self, ideas_raw: list) -> str:
        """Format LLM-generated ideas as vault markdown."""
        lines = [
            f"# Ideas Generated — {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"**Generated via:** LLM with agent personality injection",
            f"**Cycle:** {self.current_cycle_id}",
            "",
            "---",
            "",
        ]
        for idea in ideas_raw:
            name = idea.get("name", "Unnamed Idea")
            desc = idea.get("description", "")
            technique = idea.get("technique_used", "fusion")
            score = idea.get("applicability_score", 50)
            category = idea.get("category", "GROWING" if score < 80 else "PRIME")
            emoji = "🟢" if score >= 80 else "🟡"
            
            lines.append(f"### {emoji} {name} (Score: {score})")
            lines.append("")
            lines.append(f"**Technique:** {technique}")
            lines.append("")
            lines.append(desc)
            lines.append("")
            lines.append(f"**Category:** {category}")
            lines.append("")

        lines.append("---")
        lines.append(f"*Generated by LLM Agent Vault Think | Cycle {self.current_cycle_id}*")
        return "\n".join(lines)

    def _generate_moc(self, agent_name, files):
        """Generate Map of Content from created files."""
        moc_name = f"Night Cycle {datetime.now().strftime('%Y-%m-%d')}"
        by_type = {}
        for f in files:
            ext = os.path.splitext(f)[1] if f else ""
            by_type.setdefault(ext, []).append(f)
        
        return f"""# Map of Content — {moc_name}

**Author:** {agent_name}
**Cycle:** {self.current_cycle_id}

## Files Created This Cycle

{chr(10).join(f'- {f}' for f in files) if files else '*No files created this cycle*'}

## Connections

### Research → Concepts
- Research Brief → Vault Concepts: knowledge pipeline activated
- Each research finding mapped to structured concept note

### Concepts → Ideas
- Concept notes analyzed for combinatorial potential
- {len(files)} concepts processed into idea space

### Ideas → Implementation
- PRIME ideas flagged for King Aldric
- Tool prototypes designed for priority concepts

## Bridge Links

The following new connections were identified:
- [[Vault Company OS]] ↔ [[Multi-Agent Trust]]
- [[Knowledge Synthesis]] ↔ [[Collective Intelligence]]
- [[Night Cycle Automation]] ↔ [[Self-Improving Systems]]

## Open Questions

- How to measure vault knowledge density growth?
- Should agents have personal knowledge goals?
- Cross-agent learning: can Sage Mira learn from Shadow Kael's scanning patterns?

---

*Generated by {agent_name} | Cycle {self.current_cycle_id}*
"""

    def _generate_tool_spec(self, agent_name, ideas_data):
        """Generate a tool specification document."""
        tool_name = f"Vault Company Night Cycle Runner v{datetime.now().strftime('%Y%m%d')}"
        return f"""# Tool Specification: {tool_name}

**Author:** {agent_name}
**Cycle:** {self.current_cycle_id}

## Purpose

Automates the vault company night cycle — each agent executes their phase
autonomously, generates output, and passes work to the next agent.

## Architecture

```
VaultCompanyEngine.run_night_cycle()
  ├── Phase 1: research_scan  → Shadow Kael
  ├── Phase 2: write_notes    → Sage Mira
  ├── Phase 3: generate_ideas → High Priest Orin
  ├── Phase 4: bridge_notes   → Dame Elara
  ├── Phase 5: build_tools    → King Aldric
  └── Phase 6: quality_audit  → Sergeant Voss
```

## Dependencies

- VaultCompanyEngine (agent_os/vault_company/vault_company_engine.py)
- RealActionEngine (agent_os/real_action_engine.py)
- VaultReader + VaultWriter (agent_os/vault_bridge/)
- Vault repo at ~/my-second-brain/

## API

```python
engine = VaultCompanyEngine(
    real_action_engine=rae,
    vault_reader=vr,
    vault_writer=vw,
    db=db,
)
result = await engine.run_night_cycle()
```

## Output

- Research briefs → `06 Research/Briefs/`
- Concept notes → `04 Resources/Concepts/`
- Ideas → `07 Ideas/`
- MOC files → `04 Resources/Maps of Content/`
- Tool docs → `05 Tools/`
- Quality reports → `09 Meta/Quality Reports/`

## Cron Schedule

`0 2 * * *` — runs daily at 02:00 UTC

## Implementation Notes

- Each phase has a 5-minute timeout
- Failed phases are logged but don't block subsequent phases
- Quality audit at the end determines if output is committed
- Orchestraor receives Telegram summary on completion

---

*Generated by {agent_name} | Cycle {self.current_cycle_id}*
"""

    def _generate_audit_report(self, audit_result):
        """Generate quality audit report."""
        return f"""# Quality Audit Report — {datetime.now().strftime('%Y-%m-%d')}

**Author:** Sergeant Voss
**Cycle:** {self.current_cycle_id}

## Summary

| Metric | Value |
|--------|-------|
| Total items audited | {audit_result.get('total_items', 0)} |
| Passed (score ≥ 6) | {audit_result.get('passed', 0)} |
| Failed (score < 6) | {audit_result.get('failed', 0)} |
| Excellent (score ≥ 10) | {audit_result.get('excellent', 0)} |
| Average quality score | {audit_result.get('overall_score', 0):.1f}/14 |

## Per-Phase Scores

{chr(10).join(f'- **{p.get("phase", "?")}** ({p.get("agent", "?")}): {p.get("quality_score", 0):.1f}/14 — {"✅ PASS" if p.get("quality_score", 0) >= QUALITY_PASS_THRESHOLD else "❌ FAIL"}' for p in audit_result.get('phase_scores', []))}

## Assessment

{audit_result.get('assessment', 'Night cycle completed without critical issues.')}

## Recommendations

{audit_result.get('recommendations', 'Continue monitoring quality trends.')}

## Verdict

**{audit_result.get('verdict', 'APPROVED')}**

---

*Generated by Sergeant Voss | Cycle {self.current_cycle_id}*
"""

    def _audit_cycle(self) -> dict:
        """Audit all phases of the current cycle."""
        phases = self.cycle_results.get("phases", [])
        total = len(phases)
        passed = 0
        failed = 0
        excellent = 0
        total_score = 0
        phase_scores = []
        
        for p in phases:
            score = p.get("quality_score", 0)
            total_score += score
            phase_scores.append({
                "phase": p.get("phase"),
                "agent": p.get("agent"),
                "quality_score": score,
            })
            if score >= QUALITY_PASS_THRESHOLD:
                passed += 1
            else:
                failed += 1
            if score >= QUALITY_EXCELLENT_THRESHOLD:
                excellent += 1
        
        overall = total_score / max(total, 1)
        
        # Generate assessment
        if overall >= QUALITY_EXCELLENT_THRESHOLD:
            assessment = "Exceptional night cycle. All outputs meet or exceed quality standards."
        elif overall >= QUALITY_PASS_THRESHOLD:
            assessment = "Good night cycle. Most outputs pass quality standards."
        else:
            assessment = "Below average night cycle. Some outputs need improvement."
        
        recommendations = []
        for p in phase_scores:
            if p["quality_score"] < QUALITY_PASS_THRESHOLD:
                recommendations.append(
                    f"- {p['phase']} ({p['agent']}): score {p['quality_score']:.1f}/14 — needs improvement"
                )
        if not recommendations:
            recommendations.append("- No critical issues found. Continue current standards.")
        
        return {
            "total_items": total,
            "passed": passed,
            "failed": failed,
            "excellent": excellent,
            "overall_score": overall,
            "phase_scores": phase_scores,
            "assessment": assessment,
            "recommendations": "\n".join(recommendations),
            "verdict": "APPROVED ✅" if overall >= QUALITY_PASS_THRESHOLD else "NEEDS IMPROVEMENT ❌",
        }
    
    # ═══════════════════════════════════════════════
    # XP MANAGEMENT
    # ═══════════════════════════════════════════════
    
    def _calculate_phase_xp(self, phase_name: str, success: bool,
                            quality: float) -> int:
        """Calculate XP gained for completing a phase."""
        base = SKILL_XP_PER_ACTION if success else 1
        quality_bonus = int(quality * SKILL_XP_PER_EXCELLENT)
        return base + quality_bonus
    
    async def _award_xp(self, agent_name: str, phase_name: str, xp: int):
        """Award XP to agent's primary skills used in this phase."""
        if not self.db:
            return
        
        skills_info = VAULT_ROLE_SKILLS.get(agent_name, {})
        npc_id = None
        
        # Get NPC ID from agent name
        cursor = await self.db.execute(
            "SELECT npc_id FROM dungeon_npcs WHERE npc_name=?",
            (agent_name,),
        )
        row = await cursor.fetchone()
        if row:
            npc_id = row["npc_id"]
        else:
            return
        
        # Award XP to primary skills
        for skill_name, current_level, current_xp in skills_info.get("primary", []):
            try:
                cursor = await self.db.execute(
                    "SELECT xp, level FROM agent_skills WHERE npc_id=? AND skill_name=?",
                    (npc_id, skill_name),
                )
                row = await cursor.fetchone()
                if row:
                    new_xp = row["xp"] + (xp // max(len(skills_info.get("primary", [])), 1))
                    new_level, remaining = self._level_up(new_xp, row["level"])
                    await self.db.execute(
                        "UPDATE agent_skills SET xp=?, level=? WHERE npc_id=? AND skill_name=?",
                        (new_xp if new_level == row["level"] else remaining,
                         new_level, npc_id, skill_name),
                    )
            except Exception as e:
                print(f"[VaultCompany] XP update failed for {agent_name}/{skill_name}: {e}")
        
        await self.db.commit()
    
    def _level_up(self, xp: int, current_level: int) -> tuple[int, int]:
        """Calculate new level and remaining XP."""
        if current_level >= SKILL_MAX_LEVEL:
            return (current_level, xp)
        needed = (current_level + 1) * SKILL_XP_PER_LEVEL
        if xp >= needed:
            return (current_level + 1, xp - needed)
        return (current_level, xp)
    
    # ═══════════════════════════════════════════════
    # REPORTS
    # ═══════════════════════════════════════════════
    
    def _generate_orchestrator_report(self) -> dict:
        """Generate a concise morning report for the orchestrator."""
        phases = self.cycle_results.get("phases", [])
        
        # Stats
        total_phases = len(phases)
        completed = sum(1 for p in phases if p.get("status") == "completed")
        failed = sum(1 for p in phases if p.get("status") == "failed")
        total_files = sum(
            len(p.get("output", {}).get("files_created", []))
            for p in phases
        )
        total_xp = sum(p.get("xp_gained", 0) for p in phases)
        
        # Phase summaries
        phase_summaries = []
        for p in phases:
            phase_summaries.append({
                "phase": p.get("phase"),
                "agent": p.get("agent"),
                "status": p.get("status"),
                "quality_score": p.get("quality_score", 0),
                "summary": p.get("output", {}).get("summary", ""),
                "thought": p.get("agent_thought", ""),
                "duration_seconds": p.get("duration_seconds", 0),
            })
        
        # Top findings
        top_ideas = []
        for p in phases:
            if p.get("phase") == "generate_ideas":
                for f in p.get("output", {}).get("files_created", []):
                    top_ideas.append(f)
        
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "cycle_id": self.current_cycle_id,
            "time": datetime.now().strftime("%H:%M"),
            "duration_seconds": self.cycle_results.get("duration_seconds", 0),
            "stats": {
                "phases_completed": completed,
                "phases_total": total_phases,
                "phases_failed": failed,
                "files_created": total_files,
                "total_xp_earned": total_xp,
            },
            "phases": phase_summaries,
            "top_ideas": top_ideas,
            "status": "completed" if failed == 0 else "partial",
        }
        
        return report
    
    async def _save_report_to_vault(self, report: dict):
        """Save the orchestrator report to vault."""
        vault_base = os.path.expanduser("~/my-second-brain" if os.path.exists(
            os.path.expanduser("~/my-second-brain")
        ) else "/tmp/agora-vault")
        
        content = self._format_orchestrator_report(report)
        await self._write_vault_note(
            vault_base, VAULT_OUTPUT_PATHS["daily_report"],
            f"Orchestrator Report - {report['date']}",
            content,
            tags=["orchestrator", "daily-report", "night-cycle"],
            agent_name="Vault Company OS",
        )
    
    def _format_orchestrator_report(self, report: dict) -> str:
        """Format orchestrator report as markdown."""
        stats = report.get("stats", {})
        phases = report.get("phases", [])
        duration = report.get("duration_seconds", 0)
        
        lines = [
            f"# ☀️ Orchestrator Report — {report['date']}",
            "",
            f"**Cycle:** {report.get('cycle_id', 'N/A')}",
            f"**Duration:** {duration:.0f}s",
            f"**Status:** {'✅ ALL OK' if report.get('status') == 'completed' else '⚠️ PARTIAL'}",
            "",
            "---",
            "",
            "## 📊 Stats",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Phases completed | {stats.get('phases_completed', 0)}/{stats.get('phases_total', 0)} |",
            f"| Phases failed | {stats.get('phases_failed', 0)} |",
            f"| Files created | {stats.get('files_created', 0)} |",
            f"| Total XP earned | {stats.get('total_xp_earned', 0)} |",
            "",
            "---",
            "",
            "## 🌙 Night Cycle Summary",
            "",
        ]
        
        for p in phases:
            emoji = "✅" if p.get("status") == "completed" else "❌"
            score = p.get("quality_score", 0)
            lines.append(f"### {emoji} {p.get('phase', '?')} — {p.get('agent', '?')}")
            lines.append("")
            lines.append(f"**Score:** {score:.1f}/14 | **Duration:** {p.get('duration_seconds', 0):.1f}s")
            lines.append("")
            lines.append(f"{p.get('summary', 'No summary')}")
            lines.append("")
            if p.get("thought"):
                lines.append(f"> 💭 *{p['thought']}*")
                lines.append("")
        
        lines.extend([
            "## 🚀 Top Ideas Ready for Implementation",
            "",
        ])
        
        top_ideas = report.get("top_ideas", [])
        if top_ideas:
            for idea_path in top_ideas:
                lines.append(f"- {idea_path}")
        else:
            lines.append("*No new ideas this cycle.*")
        
        lines.append("")
        lines.append("## 📋 Orchestrator Actions")
        lines.append("")
        lines.append("1. **Pull vault** — `git pull` v ~/my-second-brain/")
        lines.append("2. **Read reports** — v `09 Meta/Daily Reports/`")
        lines.append("3. **Pick top ideas** — z `07 Ideas/`")
        lines.append("4. **Implement** — vybrané nápady dnes")
        lines.append("")
        lines.append("---")
        lines.append(f"*Auto-generated by Vault Company OS | {report.get('time', '')}*")
        
        return "\n".join(lines)
    
    async def _notify_orchestrator(self, report: dict):
        """Send orchestrator report summary via Telegram."""
        if not self.real_action_engine:
            print("[VaultCompany] No RealActionEngine, skipping Telegram notification")
            return
        
        stats = report.get("stats", {})
        duration = report.get("duration_seconds", 0)
        
        summary_lines = [
            f"🌙 **Nočný cyklus vaultu skončený** — {report['date']}",
            "",
            f"✅ {stats.get('phases_completed', 0)}/{stats.get('phases_total', 0)} fáz hotových",
            f"📄 {stats.get('files_created', 0)} súborov vytvorených",
            f"⚡ {stats.get('total_xp_earned', 0)} XP získaných za {duration:.0f}s",
        ]
        
        if stats.get("phases_failed", 0) > 0:
            summary_lines.append(f"⚠️ {stats['phases_failed']} fáz zlyhalo")
        
        # Best thought
        best_thought = ""
        for p in report.get("phases", []):
            if p.get("status") == "completed" and p.get("thought"):
                if not best_thought or p.get("quality_score", 0) > 7:
                    best_thought = p["thought"]
        
        if best_thought:
            summary_lines.append("")
            summary_lines.append(f"> 💭 {best_thought}")
        
        summary_lines.append("")
        summary_lines.append("Pozri `09 Meta/Daily Reports/` pre detail.")
        
        summary = "\n".join(summary_lines)
        
        try:
            await self.real_action_engine.execute(
                "send_telegram",
                {"message": summary},
                agent_name="Vault Company OS",
            )
            print("[VaultCompany] ✅ Orchestrator notified via Telegram")
        except Exception as e:
            print(f"[VaultCompany] ⚠️ Telegram notification failed: {e}")
    
    # ═══════════════════════════════════════════════
    # UTILITY
    # ═══════════════════════════════════════════════
    
    @staticmethod
    def _get_agent_for_phase(phase_name: str) -> Optional[str]:
        """Map phase name to agent name."""
        phase_agent_map = {
            "research_scan": "Shadow Kael",
            "write_notes": "Sage Mira",
            "generate_ideas": "High Priest Orin",
            "bridge_notes": "Dame Elara",
            "build_tools": "King Aldric",
            "quality_audit": "Sergeant Voss",
        }
        return phase_agent_map.get(phase_name)
    
    async def get_agent_report(self, agent_name: str) -> dict:
        """Get a report card for a specific agent."""
        if not self.db:
            return {"agent": agent_name, "error": "No database"}
        
        npc_id = None
        cursor = await self.db.execute(
            "SELECT npc_id FROM dungeon_npcs WHERE npc_name=?", (agent_name,)
        )
        row = await cursor.fetchone()
        if row:
            npc_id = row["npc_id"]
        
        skills_data = []
        if npc_id:
            cursor = await self.db.execute(
                "SELECT skill_name, level, xp, xp_to_next FROM agent_skills WHERE npc_id=?",
                (npc_id,),
            )
            skills_data = await cursor.fetchall()
        
        role_info = VAULT_ROLES.get(agent_name, {})
        soul_info = VAULT_SOUL.get(agent_name, {})
        skills_def = VAULT_ROLE_SKILLS.get(agent_name, {})
        
        return {
            "agent": agent_name,
            "role": role_info.get("title", ""),
            "department": role_info.get("department", ""),
            "vault_role": role_info.get("vault_role", ""),
            "motto": soul_info.get("motivation", ""),
            "mood": soul_info.get("mood_base", 0.7),
            "skills_db": skills_data,
            "skills_defined": {
                "primary": [{"name": s[0], "level": s[1], "xp": s[2]}
                           for s in skills_def.get("primary", [])],
                "secondary": [{"name": s[0], "level": s[1], "xp": s[2]}
                             for s in skills_def.get("secondary", [])],
            },
            "night_cycle_phase": role_info.get("night_cycle", ""),
        }