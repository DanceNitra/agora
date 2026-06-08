"""
Cross-Agent Learning Engine — agents learn from each other's work and improve over time.

Based on research:
  - Experience Compression Spectrum (arXiv 2604.15877): memory/skills/rules unification
  - EVOCHAMBER (arXiv 2605.11136): co-evolution at individual, team, population scales
  - Lilian Weng's framework: planning + memory + tool use as learning substrate

Learning modes:
  1. LESSON EXTRACTION — After each phase, agent writes lessons to their learning/ dir
  2. SKILL TRANSFER — Downstream agent gains XP in upstream agent's skill domain
  3. FEEDBACK ABSORPTION — Voss's QA feedback → agent updates their brain heuristics
  4. CROSS-POLLINATION — Agent reads another agent's lessons → updates own goals/knowledge

Pipeline affinities (who learns from whom):
  Kael → Mira:  research patterns → better note structure (gap awareness)
  Mira → Orin:  structured concepts → better idea grounding
  Orin → Aldric: idea specs → better feasibility estimation
  Mira → Elara:  new notes → better bridge detection
  Elara → Voss:  bridge patterns → better quality context
  Voss → ALL:    QA feedback → everyone improves
"""
import json
import os
from datetime import datetime
from typing import Optional

from .agent_directory import AgentDirectoryManager
from .agent_definitions import VAULT_ROLE_SKILLS, VAULT_SKILL_DESCRIPTIONS
# NPC_UUIDS je v agent_os.py (parent modul)
from ..agent_os import NPC_UUIDS

# ── Learning pipeline affinities ──
# (source_phase, target_agent, skill_transferred, description)
LEARNING_AFFINITIES = [
    ("research_scan", "Sage Mira", "gap_detection",
     "Shadow Kael nájde medzery, Sage Mira sa učí lepšie identifikovať čo chýba v konceptoch"),
    ("research_scan", "High Priest Orin", "frontier_scanning",
     "Shadow Kael skenuje frontiery, Orin sa učí kde hľadať inšpiráciu pre nové idey"),
    ("write_notes", "High Priest Orin", "writing",
     "Sage Mira píše štruktúrované noty, Orin sa učí lepšie formulovať svoje idey"),
    ("write_notes", "Dame Elara", "bridge_building",
     "Sage Mira vytvára nové koncepty, Elara sa učí kde hľadať prepojenia"),
    ("generate_ideas", "King Aldric", "idea_generation",
     "Orin generuje idey, Aldric sa učí lepšie chápať kontext nápadov pred buildom"),
    ("generate_ideas", "Dame Elara", "cross_domain",
     "Orin prepája domény, Elara sa učí vidieť nečakané spojenia"),
    ("build_tools", "Shadow Kael", "tool_design",
     "Aldric stavia nástroje, Kael sa učí čo je technicky možné — lepšie gap briefy"),
    ("bridge_notes", "Sage Mira", "vault_navigation",
     "Elara vytvára MOC, Mira sa učí lepšiu štruktúru notiek pre navigáciu"),
    ("quality_audit", "Shadow Kael", "quality_audit",
     "Voss kontroluje kvalitu, Kael sa učí čo očakávať — menej neformátovaných briefov"),
    ("quality_audit", "Sage Mira", "quality_audit",
     "Voss kontroluje, Mira sa učí štandardy — konzistentnejšie noty"),
    ("quality_audit", "High Priest Orin", "quality_audit",
     "Voss kontroluje, Orin sa učí formátovať idey lepšie"),
    ("quality_audit", "King Aldric", "quality_audit",
     "Voss kontroluje, Aldric sa učí QA štandardy pre tool documentation"),
    ("quality_audit", "Dame Elara", "quality_audit",
     "Voss kontroluje, Elara sa učí kvalitnejšie MOC štruktúry"),
]


class CrossAgentLearningEngine:
    """
    Orchestrates learning between vault company agents.
    
    After each night cycle, runs the learning pipeline:
      1. Extract lessons from each agent's phase output
      2. Transfer skills downstream
      3. Apply QA feedback
      4. Update agent directories with new lessons
    """
    
    def __init__(self, directory_manager: Optional[AgentDirectoryManager] = None):
        self.dm = directory_manager or AgentDirectoryManager()
    
    # ═══════════════════════════════════════════════
    # MAIN LEARNING CYCLE
    # ═══════════════════════════════════════════════
    
    async def run_learning_cycle(self, cycle_results: dict) -> dict:
        """
        Run the full cross-agent learning cycle after a night cycle.
        
        Args:
            cycle_results: The output from VaultCompanyEngine.run_night_cycle()
        
        Returns:
            Dict with learning results per agent.
        """
        phases = cycle_results.get("phases", [])
        learning_log = {
            "cycle_id": cycle_results.get("cycle_id", "unknown"),
            "lessons_extracted": 0,
            "skills_transferred": 0,
            "feedbacks_applied": 0,
            "per_agent": {},
            "started_at": datetime.now().isoformat(),
        }
        
        # 1. Extract lessons from each phase
        for phase in phases:
            agent = phase.get("agent", "")
            phase_name = phase.get("phase", "")
            output = phase.get("output", {})
            
            lesson = await self._extract_lesson(agent, phase_name, output)
            if lesson:
                await self._save_lesson(agent, lesson)
                learning_log["lessons_extracted"] += 1
                
                # Per-agent tracking
                if agent not in learning_log["per_agent"]:
                    learning_log["per_agent"][agent] = {"lessons": 0, "skills_gained": 0, "feedbacks": 0}
                learning_log["per_agent"][agent]["lessons"] += 1
        
        # 2. Transfer skills downstream
        for phase in phases:
            source_agent = phase.get("agent", "")
            phase_name = phase.get("phase", "")
            quality = phase.get("quality_score", 0.5)
            
            transfers = self._find_transfers(phase_name, source_agent)
            for transfer in transfers:
                target_agent = transfer["target"]
                skill_name = transfer["skill"]
                xp_gained = self._calculate_transfer_xp(quality)
                
                # Update target agent's skill file with XP
                await self._apply_skill_transfer(target_agent, skill_name, xp_gained, source_agent)
                
                if target_agent not in learning_log["per_agent"]:
                    learning_log["per_agent"][target_agent] = {"lessons": 0, "skills_gained": 0, "feedbacks": 0}
                learning_log["per_agent"][target_agent]["skills_gained"] += 1
                learning_log["skills_transferred"] += 1
        
        # 3. Apply QA feedback from Sergeant Voss
        voss_phase = None
        for phase in phases:
            if phase.get("agent") == "Sergeant Voss":
                voss_phase = phase
                break
        
        if voss_phase:
            feedbacks = await self._extract_feedbacks(voss_phase)
            for fb in feedbacks:
                target_agent = fb["target"]
                await self._apply_feedback_to_agent(target_agent, fb)
                
                if target_agent not in learning_log["per_agent"]:
                    learning_log["per_agent"][target_agent] = {"lessons": 0, "skills_gained": 0, "feedbacks": 0}
                learning_log["per_agent"][target_agent]["feedbacks"] += 1
                learning_log["feedbacks_applied"] += 1
        
        learning_log["finished_at"] = datetime.now().isoformat()
        return learning_log
    
    # ═══════════════════════════════════════════════
    # LESSON EXTRACTION
    # ═══════════════════════════════════════════════
    
    async def _extract_lesson(self, agent: str, phase_name: str, output: dict) -> Optional[dict]:
        """Extract a lesson from an agent's phase output."""
        if not output:
            return None
        
        # Determine lesson type based on phase
        lesson_templates = {
            "research_scan": {
                "type": "research_pattern",
                "title": "Research Scanning Insight",
                "content": output.get("summary", "No specific lesson this cycle"),
                "domain": "research_methodology",
            },
            "write_notes": {
                "type": "writing_pattern",
                "title": "Structured Writing Insight",
                "content": output.get("summary", "No specific lesson this cycle"),
                "domain": "note_structure",
            },
            "generate_ideas": {
                "type": "idea_pattern",
                "title": "Idea Generation Insight",
                "content": output.get("summary", "No specific lesson this cycle"),
                "domain": "ideation",
            },
            "bridge_notes": {
                "type": "bridge_pattern",
                "title": "Bridge Building Insight",
                "content": output.get("summary", "No specific lesson this cycle"),
                "domain": "knowledge_graph",
            },
            "build_tools": {
                "type": "tool_pattern",
                "title": "Tool Building Insight",
                "content": output.get("summary", "No specific lesson this cycle"),
                "domain": "engineering",
            },
            "quality_audit": {
                "type": "quality_pattern",
                "title": "Quality Standard Insight",
                "content": output.get("summary", "No specific lesson this cycle"),
                "domain": "quality_assurance",
            },
        }
        
        template = lesson_templates.get(phase_name, {
            "type": "general",
            "title": "General Insight",
            "content": output.get("summary", ""),
            "domain": "general",
        })
        
        return {
            "agent": agent,
            "phase": phase_name,
            "type": template["type"],
            "title": template["title"],
            "content": template["content"],
            "quality_score": output.get("quality_score", 0.5),
            "agent_thought": output.get("agent_thought", ""),
            "cycle_time": datetime.now().isoformat(),
        }
    
    async def _save_lesson(self, agent: str, lesson: dict):
        """Save a lesson to the agent's learning/ directory."""
        # Write to lessons.jsonl
        await self.dm.append_log(agent, "lessons", lesson)
        
        # Also write a readable .md lesson file
        agent_dir = os.path.join(self.dm.base_path, self.dm.name_to_dir.get(agent, agent))
        learning_dir = os.path.join(agent_dir, "learning")
        os.makedirs(learning_dir, exist_ok=True)
        
        # Count existing lessons
        lessons_file = os.path.join(learning_dir, "lessons.jsonl")
        lesson_count = 0
        if os.path.isfile(lessons_file):
            with open(lessons_file) as f:
                lesson_count = sum(1 for _ in f if _.strip())
        
        lesson_md = f"""# Lesson {lesson_count} — {lesson['type']}

**Cycle:** {lesson.get('cycle_time', 'unknown')}
**Phase:** {lesson['phase']}
**Quality:** {lesson.get('quality_score', 0):.1f}/10

{lesson.get('content', 'No content')}

## Agent's Thought
> {lesson.get('agent_thought', 'N/A')}

---

*Auto-extracted by Cross-Agent Learning Engine*
"""
        lesson_path = os.path.join(learning_dir, f"lesson_{lesson_count:04d}.md")
        with open(lesson_path, "w") as f:
            f.write(lesson_md)
    
    # ═══════════════════════════════════════════════
    # SKILL TRANSFER
    # ═══════════════════════════════════════════════
    
    def _find_transfers(self, source_phase: str, source_agent: str) -> list[dict]:
        """Find which skills should be transferred from this phase/agent."""
        transfers = []
        for affinity in LEARNING_AFFINITIES:
            phase, target, skill, desc = affinity
            if phase == source_phase:
                # Skip self-transfer
                if target == source_agent:
                    continue
                # Verify source matches (or any source for that phase)
                transfers.append({
                    "target": target,
                    "skill": skill,
                    "description": desc,
                    "source_phase": phase,
                })
        return transfers
    
    def _calculate_transfer_xp(self, quality_score: float) -> int:
        """Calculate XP gained from cross-agent observation."""
        base_xp = 3  # base XP for observing another agent's work
        quality_bonus = int(quality_score * 10)  # up to +10 for excellent work
        return base_xp + quality_bonus
    
    async def _apply_skill_transfer(self, target_agent: str, skill_name: str, xp: int, source_agent: str):
        """Apply skill XP gain from observing another agent's work."""
        # Log the transfer
        transfer_entry = {
            "skill": skill_name,
            "xp_gained": xp,
            "source": source_agent,
            "cycle_time": datetime.now().isoformat(),
            "reason": f"Observed {source_agent}'s work and learned about {skill_name}",
        }
        await self.dm.append_log(target_agent, "transfers", transfer_entry)
        
        # Update skills.yml if exists (we can read it)
        # The actual skill level update happens in the engine's _award_xp method
        # Here we just log the learning event
        
        # Also write a learning note
        agent_dir = os.path.join(self.dm.base_path, self.dm.name_to_dir.get(target_agent, target_agent))
        learning_dir = os.path.join(agent_dir, "learning")
        os.makedirs(learning_dir, exist_ok=True)
        
        skill_desc = VAULT_SKILL_DESCRIPTIONS.get(skill_name, skill_name)
        
        transfer_md = f"""# Skill Transfer: {skill_name}

**From:** {source_agent} → **To:** {target_agent}
**XP gained:** +{xp}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## What I Learned

By observing {source_agent}'s work, I improved my **{skill_desc}**.

## How This Helps Me

This helps me perform better in my own role because I now understand
{source_agent}'s perspective and can apply their patterns.

---

*Auto-generated by Cross-Agent Learning Engine*
"""
        transfer_path = os.path.join(learning_dir, f"transfer_{skill_name}_{datetime.now().strftime('%Y%m%d')}.md")
        with open(transfer_path, "w") as f:
            f.write(transfer_md)
    
    # ═══════════════════════════════════════════════
    # FEEDBACK APPLICATION
    # ═══════════════════════════════════════════════
    
    async def _extract_feedbacks(self, voss_phase: dict) -> list[dict]:
        """Extract feedback items from Sergeant Voss's quality audit."""
        output = voss_phase.get("output", {})
        audit = output.get("audit_result", {})
        
        feedbacks = []
        phase_scores = audit.get("phase_scores", [])
        for ps in phase_scores:
            target = ps.get("agent", "")
            score = ps.get("quality_score", 0)
            
            # Only generate feedback for below-threshold items
            if score < 6:
                feedbacks.append({
                    "target": target,
                    "phase": ps.get("phase", ""),
                    "score": score,
                    "feedback": f"Quality score {score:.1f}/14 — needs improvement in structure, sources, or completeness.",
                    "type": "constructive",
                    "priority": "high" if score < 4 else "medium",
                })
            else:
                feedbacks.append({
                    "target": target,
                    "phase": ps.get("phase", ""),
                    "score": score,
                    "feedback": f"Quality score {score:.1f}/14 — good work, maintain standards.",
                    "type": "affirmation",
                    "priority": "low",
                })
        
        return feedbacks
    
    async def _apply_feedback_to_agent(self, agent: str, feedback: dict):
        """Apply QA feedback to an agent's learning record."""
        feedback_entry = {
            "type": feedback["type"],
            "phase": feedback.get("phase", ""),
            "score": feedback.get("score", 0),
            "feedback": feedback.get("feedback", ""),
            "priority": feedback.get("priority", "low"),
            "cycle_time": datetime.now().isoformat(),
        }
        await self.dm.append_log(agent, "feedbacks", feedback_entry)
        
        # Write feedback as .md
        agent_dir = os.path.join(self.dm.base_path, self.dm.name_to_dir.get(agent, agent))
        learning_dir = os.path.join(agent_dir, "learning")
        os.makedirs(learning_dir, exist_ok=True)
        
        emoji = "✅" if feedback["type"] == "affirmation" else "⚠️"
        feedback_md = f"""# QA Feedback — {feedback['type'].title()}

{emoji} **Score:** {feedback.get('score', 0):.1f}/14
**Phase:** {feedback.get('phase', 'unknown')}
**Priority:** {feedback.get('priority', 'low')}

{feedback.get('feedback', 'No feedback')}

---

*From Sergeant Voss via Cross-Agent Learning Engine*
"""
        feedback_path = os.path.join(learning_dir, f"feedback_{feedback['type']}_{datetime.now().strftime('%Y%m%d_%H%M')}.md")
        with open(feedback_path, "w") as f:
            f.write(feedback_md)
    
    # ═══════════════════════════════════════════════
    # AGENT LEARNING STATUS
    # ═══════════════════════════════════════════════
    
    async def get_agent_learning_status(self, agent: str) -> dict:
        """Get the learning status for a specific agent."""
        stats = {
            "agent": agent,
            "lessons_count": 0,
            "transfers_count": 0,
            "feedbacks_count": 0,
            "recent_lessons": [],
            "recent_transfers": [],
            "recent_feedbacks": [],
        }
        
        # Count and read recent lessons
        lessons_file = f"learning/lessons.jsonl"
        lessons_content = await self.dm.read_file(agent, lessons_file)
        if lessons_content:
            lines = [l for l in lessons_content.strip().split("\n") if l.strip()]
            stats["lessons_count"] = len(lines)
            # Last 3 lessons
            for line in lines[-3:]:
                try:
                    stats["recent_lessons"].append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        
        # Read recent transfers
        transfers_file = f"log/transfers.jsonl"
        transfers_content = await self.dm.read_file(agent, transfers_file)
        if transfers_content:
            lines = [l for l in transfers_content.strip().split("\n") if l.strip()]
            stats["transfers_count"] = len(lines)
            for line in lines[-3:]:
                try:
                    stats["recent_transfers"].append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        
        # Read recent feedbacks
        feedbacks_file = f"log/feedbacks.jsonl"
        feedbacks_content = await self.dm.read_file(agent, feedbacks_file)
        if feedbacks_content:
            lines = [l for l in feedbacks_content.strip().split("\n") if l.strip()]
            stats["feedbacks_count"] = len(lines)
            for line in lines[-3:]:
                try:
                    stats["recent_feedbacks"].append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        
        return stats
    
    async def get_all_learning_status(self) -> dict:
        """Get learning status for all agents."""
        from .agent_definitions import VAULT_ROLES

        all_stats = {}
        for agent_name in VAULT_ROLES:
            all_stats[agent_name] = await self.get_agent_learning_status(agent_name)
        
        return all_stats