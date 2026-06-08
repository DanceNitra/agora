"""
Agent Directory Manager — každý agent má vlastný adresár so súbormi ako reálna entita.

Štruktúra:
  agents/<Agent_Name>/
    identity.yml       — ID karta (meno, UUID, rola, department, rank)
    brain.md            — Myslenie (kognitívny štýl, decision patterns, heuristiky)
    soul.yml            — Duša (Big 5 personality, values, motivation, mood)
    skills.yml          — Zručnosti (meno, level, XP, description, last_used)
    tools.yml           — Nástroje (meno, description, permission scope, commands)
    workflow.yml        — Workflow (night cycle, daily routine, interaction patterns)
    goals.yml           — Ciele (krátkodobé, dlhodobé, životný cieľ)
    relationships.yml   — Vzťahy (trust, friendship, respect, bond s každým agentom)
    knowledge/
      domains.md        — Domény, v ktorých sa agent vyzná
      expertise.md      — Hĺbková expertíza
    log/
      actions.jsonl     — Append-only log akcií
      decisions.jsonl   — Append-only log rozhodnutí
    memory/
      episodic.jsonl    — Epizodické spomienky
    diary/
      entries/          — Denníkové záznamy (jeden .md súbor na entry)
"""
import json
import os
import shutil
from datetime import datetime
from typing import Optional

from .agent_definitions import (
    VAULT_ROLES, VAULT_SOUL, VAULT_ROLE_SKILLS, VAULT_TOOLS,
    VAULT_SKILL_DESCRIPTIONS, QUALITY_RUBRIC,
)
# NPC_UUIDS is defined in agent_os.py
# We re-export a local mapping for the directory manager
from ..agent_os import NPC_UUIDS

# ── Base path for agent directories ──
AGENTS_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")


class AgentDirectoryManager:
    """
    Manages the physical directory + files for each vault company agent.
    
    Each agent has a directory with real files (YAML, Markdown, JSONL)
    that define their identity, skills, tools, memories, and more.
    """
    
    def __init__(self, base_path: str = AGENTS_BASE):
        self.base_path = base_path
        # Mapping: display name -> directory-safe name
        self.name_to_dir = {
            "Shadow Kael": "Shadow_Kael",
            "Sage Mira": "Sage_Mira",
            "High Priest Orin": "High_Priest_Orin",
            "King Aldric": "King_Aldric",
            "Dame Elara": "Dame_Elara",
            "Sergeant Voss": "Sergeant_Voss",
        }
        self.dir_to_name = {v: k for k, v in self.name_to_dir.items()}
    
    # ═══════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════
    
    async def initialize_all(self) -> list[str]:
        """Create directories + all files for every agent. Returns list of created paths."""
        created = []
        for display_name in self.name_to_dir:
            paths = await self.initialize_agent(display_name)
            created.extend(paths)
        return created
    
    async def initialize_agent(self, display_name: str) -> list[str]:
        """Create full directory structure + all files for one agent. Returns list of created paths."""
        created = []
        agent_dir = self._agent_path(display_name)
        
        # Create directory structure
        subdirs = ["knowledge", "log", "memory", "diary/entries"]
        for sub in subdirs:
            path = os.path.join(agent_dir, sub)
            os.makedirs(path, exist_ok=True)
            if not os.listdir(path):  # only count as "created" if empty
                pass
        
        # ── Create each file ──
        file_creators = [
            ("identity.yml", self._generate_identity_yml),
            ("brain.md", self._generate_brain_md),
            ("soul.yml", self._generate_soul_yml),
            ("skills.yml", self._generate_skills_yml),
            ("tools.yml", self._generate_tools_yml),
            ("workflow.yml", self._generate_workflow_yml),
            ("goals.yml", self._generate_goals_yml),
            ("relationships.yml", self._generate_relationships_yml),
            ("knowledge/domains.md", self._generate_knowledge_domains),
            ("knowledge/expertise.md", self._generate_knowledge_expertise),
        ]
        
        for filename, generator_fn in file_creators:
            filepath = os.path.join(agent_dir, filename)
            if not os.path.exists(filepath):
                content = generator_fn(display_name)
                with open(filepath, "w") as f:
                    f.write(content)
                created.append(filepath)
        
        # Create empty data files (JSONL)
        data_files = [
            "log/actions.jsonl",
            "log/decisions.jsonl",
            "memory/episodic.jsonl",
        ]
        for filename in data_files:
            filepath = os.path.join(agent_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, "w") as f:
                    f.write("")  # empty JSONL
                created.append(filepath)
        
        return created
    
    async def read_file(self, display_name: str, filename: str) -> Optional[str]:
        """Read a file from an agent's directory. Returns None if not found."""
        filepath = os.path.join(self._agent_path(display_name), filename)
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                return f.read()
        return None
    
    async def write_file(self, display_name: str, filename: str, content: str) -> bool:
        """Write content to an agent's file. Creates parent dirs if needed."""
        filepath = os.path.join(self._agent_path(display_name), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        return True
    
    async def append_log(self, display_name: str, log_type: str, entry: dict) -> bool:
        """Append a JSON line to a log file (actions / decisions)."""
        allowed = {"actions", "decisions", "episodic"}
        if log_type not in allowed:
            return False
        filepath = os.path.join(self._agent_path(display_name), log_type, f"{log_type}.jsonl")
        entry["timestamp"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return True
    
    async def list_files(self, display_name: str) -> list[str]:
        """List all files in an agent's directory (recursive, relative paths)."""
        agent_dir = self._agent_path(display_name)
        if not os.path.isdir(agent_dir):
            return []
        result = []
        for root, dirs, files in os.walk(agent_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), agent_dir)
                result.append(rel)
        return sorted(result)
    
    async def get_agent_summary(self, display_name: str) -> dict:
        """Get a summary of the agent from their directory files."""
        summary = {"name": display_name, "directory": self.name_to_dir.get(display_name, display_name)}
        
        # Read identity
        identity_raw = await self.read_file(display_name, "identity.yml")
        if identity_raw:
            summary["identity"] = self._parse_yaml_simple(identity_raw)
        
        # Read soul
        soul_raw = await self.read_file(display_name, "soul.yml")
        if soul_raw:
            summary["soul"] = self._parse_yaml_simple(soul_raw)
        
        # Read skills
        skills_raw = await self.read_file(display_name, "skills.yml")
        if skills_raw:
            summary["skills"] = self._parse_yaml_simple(skills_raw)
        
        # Count log entries
        for log_type in ["actions", "decisions"]:
            filepath = os.path.join(self._agent_path(display_name), "log", f"{log_type}.jsonl")
            if os.path.isfile(filepath):
                with open(filepath) as f:
                    summary[f"{log_type}_count"] = sum(1 for _ in f if _.strip())
        
        return summary
    
    # ═══════════════════════════════════════════════
    # FILE GENERATORS
    # ═══════════════════════════════════════════════
    
    def _generate_identity_yml(self, name: str) -> str:
        role = VAULT_ROLES.get(name, {})
        npc_id = NPC_UUIDS.get(name, "unknown")
        return f"""# Identity — {name}
# This file defines who this agent is.

name: "{name}"
npc_id: "{npc_id}"
title: "{role.get('title', '')}"
department: "{role.get('department', '')}"
vault_role: "{role.get('vault_role', '')}"
rank: "{role.get('rank', '')}"
emoji: "{role.get('emoji', '')}"
description: "{role.get('description', '')}"
created: "{datetime.now().strftime('%Y-%m-%d')}"
status: "active"

# Company info
company: "Vault Company OS"
ceo: "Rasto (Orchestrator)"
team: "Vault Company"

# Metadata
serial: "VC-{npc_id[:8]}"
revision: 1
last_updated: "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
"""
    
    def _generate_brain_md(self, name: str) -> str:
        """Generate brain.md — how the agent thinks."""
        role = VAULT_ROLES.get(name, {})
        soul = VAULT_SOUL.get(name, {})
        personality = soul.get("personality", {})
        
        # Determine cognitive style from personality
        openness = personality.get("openness", 0.5)
        consc = personality.get("conscientiousness", 0.5)
        
        if openness > 0.7 and consc < 0.7:
            cognitive_style = "Divergent thinker — generates many possibilities before converging"
        elif consc > 0.7 and openness < 0.7:
            cognitive_style = "Convergent thinker — systematic, thorough, methodical"
        elif openness > 0.7 and consc > 0.7:
            cognitive_style = "Integrative thinker — combines breadth with depth"
        else:
            cognitive_style = "Balanced thinker — adapts style to context"
        
        workflow = role.get("workflow", [])
        workflow_text = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(workflow))
        
        return f"""# Brain — {name}
# This file defines how this agent thinks, decides, and processes information.

## Cognitive Style

{cognitive_style}

**Openness:** {openness:.1f}
**Conscientiousness:** {consc:.1f}
**Motivation:** {soul.get('motivation', 'N/A')}

## Decision-Making Heuristics

1. **Primary heuristic:** What serves the vault's knowledge growth?
2. **Fallback heuristic:** What would teach me something new?
3. **Risk tolerance:** {(1 - soul.get('personality', {}).get('neuroticism', 0.5)):.1f}/1.0
4. **Collaboration bias:** {soul.get('personality', {}).get('agreeableness', 0.5):.1f}/1.0 (higher = prefers to collaborate)
5. **Speed vs quality tradeoff:** {"Speed-first" if openness > 0.7 else "Quality-first"}

## Workflow (Night Cycle)

{workflow_text}

## What I Pay Attention To

- {self._get_attention_focus(name)}
- Patterns across domains
- Gaps between what exists and what could exist

## How I Learn

- **Primary mode:** {self._get_learning_mode(name)}
- **Feedback loop:** After each action, evaluate → adjust → repeat
- **Knowledge retention:** Structured notes with cross-references
"""
    
    def _generate_soul_yml(self, name: str) -> str:
        """Generate soul.yml — personality, values, motivation, emotional profile."""
        soul = VAULT_SOUL.get(name, {})
        personality = soul.get("personality", {})
        values = soul.get("values", {})
        
        lines = [
            f"# Soul — {name}",
            f"# This file defines the agent's inner self — personality, values, emotions.",
            "",
            "personality:",
        ]
        for trait, score in personality.items():
            lines.append(f"  {trait}: {score}")
        
        lines.append("")
        lines.append("values:")
        for val_name, val_score in values.items():
            lines.append(f"  {val_name}: {val_score}")
        
        lines.append("")
        lines.append(f"motivation: \"{soul.get('motivation', '')}\"")
        lines.append(f"emotional_state: \"{soul.get('emotional_state', 'neutral')}\"")
        lines.append(f"mood_base: {soul.get('mood_base', 0.7)}")
        lines.append("")
        lines.append("# Emotional profile")
        lines.append("emotional_triggers:")
        for trigger in self._get_emotional_triggers(name):
            lines.append(f"  - \"{trigger}\"")
        
        lines.append("")
        lines.append("behavioral_tendencies:")
        for tendency in self._get_behavioral_tendencies(name):
            lines.append(f"  - \"{tendency}\"")
        
        lines.append("")
        lines.append("# Growth trajectory")
        lines.append("growth_areas:")
        for area in self._get_growth_areas(name):
            lines.append(f"  - \"{area}\"")
        
        return "\n".join(lines) + "\n"
    
    def _generate_skills_yml(self, name: str) -> str:
        """Generate skills.yml — all skills with level, XP, descriptions."""
        skills_info = VAULT_ROLE_SKILLS.get(name, {})
        
        from .agent_definitions import VAULT_SKILL_DESCRIPTIONS
        
        lines = [
            f"# Skills — {name}",
            f"# Each skill has level (1-15), XP, and XP needed per level.",
            "",
            "# XP per level: level * {SKILL_XP_PER_LEVEL}",
            "",
            "primary:",
        ]
        
        for skill_name, level, xp in skills_info.get("primary", []):
            desc = VAULT_SKILL_DESCRIPTIONS.get(skill_name, "")
            xp_needed = (level + 1) * 100
            progress_pct = min(100, int((xp / xp_needed) * 100))
            lines.append(f"  - name: \"{skill_name}\"")
            lines.append(f"    level: {level}")
            lines.append(f"    xp: {xp}")
            lines.append(f"    xp_to_next: {xp_needed}")
            lines.append(f"    progress: \"{progress_pct}%\"")
            lines.append(f"    description: \"{desc}\"")
            lines.append(f"    last_used: \"never\"")
            lines.append("")
        
        lines.append("secondary:")
        for skill_name, level, xp in skills_info.get("secondary", []):
            desc = VAULT_SKILL_DESCRIPTIONS.get(skill_name, "")
            xp_needed = (level + 1) * 100
            progress_pct = min(100, int((xp / xp_needed) * 100))
            lines.append(f"  - name: \"{skill_name}\"")
            lines.append(f"    level: {level}")
            lines.append(f"    xp: {xp}")
            lines.append(f"    xp_to_next: {xp_needed}")
            lines.append(f"    progress: \"{progress_pct}%\"")
            lines.append(f"    description: \"{desc}\"")
            lines.append(f"    last_used: \"never\"")
            lines.append("")
        
        lines.append(f"# Total skills: {len(skills_info.get('primary', [])) + len(skills_info.get('secondary', []))}")
        lines.append(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return "\n".join(lines)
    
    def _generate_tools_yml(self, name: str) -> str:
        """Generate tools.yml — available tools and permissions."""
        tools_info = VAULT_TOOLS.get(name, {})
        cycle_tools = tools_info.get("night_cycle_tools", [])
        run_commands = tools_info.get("run_commands", [])
        
        tool_descriptions = {
            "write_note": "Write .md note to vault",
            "write_article": "Write long-form SEO article to vault",
            "send_telegram": "Send message to Rasto via Telegram",
            "ask_question": "Search vault for knowledge",
            "run_script": "Execute safe shell command",
            "git_commit": "Commit + push to vault repo",
        }
        
        lines = [
            f"# Tools — {name}",
            f"# Available tools and their permission scopes.",
            "",
            "night_cycle_tools:",
        ]
        
        for tool in cycle_tools:
            desc = tool_descriptions.get(tool, "")
            lines.append(f"  - name: \"{tool}\"")
            lines.append(f"    description: \"{desc}\"")
            lines.append(f"    permission: \"execute\"")
            lines.append(f"    scope: \"vault\"")
            lines.append("")
        
        lines.append("run_commands:")
        for cmd in run_commands:
            lines.append(f"  - name: \"{cmd}\"")
            lines.append(f"    type: \"shell\"")
            lines.append(f"    permission: \"execute\"")
            lines.append("")
        
        lines.append("# Allowed actions")
        lines.append("allowed_actions:")
        for tool in cycle_tools:
            lines.append(f"  - \"{tool}\"")
        
        lines.append("")
        lines.append("# Blocked actions")
        lines.append("blocked_actions:")
        lines.append('  - "run_script"  # only King Aldric has this')
        lines.append('  - "write_article"  # only Sage Mira and High Priest Orin')
        
        return "\n".join(lines) + "\n"
    
    def _generate_workflow_yml(self, name: str) -> str:
        """Generate workflow.yml — night cycle steps, daily routine."""
        role = VAULT_ROLES.get(name, {})
        night_cycle = role.get("night_cycle", "")
        workflow = role.get("workflow", [])
        
        lines = [
            f"# Workflow — {name}",
            f"# Defines the agent's daily routine and night cycle.",
            "",
            "schedule:",
            f"  night_cycle: \"02:00 UTC\"",
            f"  night_cycle_phase: \"{night_cycle}\"",
            f"  report_deadline: \"06:00 UTC\"",
            f"  orchestrator_check: \"08:00 UTC\"",
            "",
            "night_cycle:",
        ]
        
        for i, step in enumerate(workflow):
            lines.append(f"  step_{i+1}: \"{step.split('. ', 1)[-1] if '. ' in step else step}\"")
        
        lines.append("")
        lines.append("dependencies:")
        deps = self._get_workflow_deps(name)
        for dep in deps:
            lines.append(f"  - \"{dep}\"")
        
        lines.append("")
        lines.append("deliverables:")
        for deliverable in self._get_deliverables(name):
            lines.append(f"  - \"{deliverable}\"")
        
        lines.append("")
        lines.append("interaction_patterns:")
        for pattern in self._get_interaction_patterns(name):
            lines.append(f"  - \"{pattern}\"")
        
        return "\n".join(lines) + "\n"
    
    def _generate_goals_yml(self, name: str) -> str:
        """Generate goals.yml — short-term, long-term, life goals."""
        role = VAULT_ROLES.get(name, {})
        soul = VAULT_SOUL.get(name, {})
        
        # Agent-specific goals
        goals = {
            "Shadow Kael": [
                {"area": "life", "goal": "Map every frontier of knowledge vault is missing", "deadline": "ongoing"},
                {"area": "skills", "goal": "Reach research level 10", "deadline": "2026-09"},
                {"area": "short", "goal": "Find 3 new domains for vault expansion this week", "deadline": "weekly"},
            ],
            "Sage Mira": [
                {"area": "life", "goal": "Transform the entire vault into interconnected evergreen notes", "deadline": "ongoing"},
                {"area": "skills", "goal": "Reach writing level 10 and SEO level 8", "deadline": "2026-09"},
                {"area": "short", "goal": "Process all research briefs from last cycle into notes", "deadline": "daily"},
            ],
            "High Priest Orin": [
                {"area": "life", "goal": "Generate one PRIME idea every week", "deadline": "ongoing"},
                {"area": "skills", "goal": "Reach idea_generation level 12", "deadline": "2026-12"},
                {"area": "short", "goal": "Generate 5 new ideas from latest concept notes", "deadline": "daily"},
            ],
            "King Aldric": [
                {"area": "life", "goal": "Build tools that automate 80% of vault operations", "deadline": "ongoing"},
                {"area": "skills", "goal": "Reach code_building level 10", "deadline": "2026-09"},
                {"area": "short", "goal": "Build one new vault tool from idea backlog", "deadline": "daily"},
            ],
            "Dame Elara": [
                {"area": "life", "goal": "Turn the vault into an optimally connected knowledge graph", "deadline": "ongoing"},
                {"area": "skills", "goal": "Reach bridge_building level 12", "deadline": "2026-12"},
                {"area": "short", "goal": "Connect every new note with at least 3 backlinks", "deadline": "daily"},
            ],
            "Sergeant Voss": [
                {"area": "life", "goal": "Maintain 100% quality pass rate for vault content", "deadline": "ongoing"},
                {"area": "skills", "goal": "Reach quality_audit level 12", "deadline": "2026-09"},
                {"area": "short", "goal": "Audit all nightly outputs before 06:00 UTC", "deadline": "daily"},
            ],
        }
        
        agent_goals = goals.get(name, [
            {"area": "life", "goal": soul.get("motivation", "Operate as vault company agent"), "deadline": "ongoing"},
        ])
        
        lines = [
            f"# Goals — {name}",
            f"# Short-term, long-term, and life goals.",
            "",
        ]
        
        for g in agent_goals:
            lines.append(f"{g['area']}_goal:")
            lines.append(f"  objective: \"{g['goal']}\"")
            lines.append(f"  deadline: \"{g['deadline']}\"")
            lines.append(f"  progress: 0.0")
            lines.append(f"  status: \"active\"")
            lines.append("")
        
        lines.append(f"# {len(agent_goals)} active goals")
        lines.append(f"# Last updated: {datetime.now().strftime('%Y-%m-%d')}")
        
        return "\n".join(lines)
    
    def _generate_relationships_yml(self, name: str) -> str:
        """Generate relationships.yml — bonds with every other agent."""
        all_agents = [a for a in NPC_UUIDS.keys() if a != name and a in self.name_to_dir]
        
        lines = [
            f"# Relationships — {name}",
            f"# Bonds with other vault company agents.",
            "",
        ]
        
        for other in all_agents:
            bond = self._get_bond_type(name, other)
            trust = self._get_trust_level(name, other)
            lines.append(f"{other.replace(' ', '_')}:")
            lines.append(f"  bond: \"{bond}\"")
            lines.append(f"  trust: {trust}")
            lines.append(f"  friendship: {max(0.2, trust - 0.1):.1f}")
            lines.append(f"  respect: {min(1.0, trust + 0.1):.1f}")
            lines.append(f"  conversations: 0")
            lines.append(f"  collaborations: 0")
            lines.append("")
        
        lines.append(f"# {len(all_agents)} relationships tracked")
        return "\n".join(lines)
    
    def _generate_knowledge_domains(self, name: str) -> str:
        """Generate knowledge/domains.md — domains the agent knows."""
        domains_map = {
            "Shadow Kael": "- AI Agents & Multi-Agent Systems\n- Frontier AI Research\n- Knowledge Management Evolution\n- Emerging Technologies\n- Trend Analysis & Forecasting",
            "Sage Mira": "- Structured Writing & Documentation\n- Note-Taking Methodologies\n- Knowledge Curation & Taxonomy\n- Information Architecture\n- Educational Content Design",
            "High Priest Orin": "- Cross-Domain Knowledge Fusion\n- Innovation Methodologies\n- Idea Generation Frameworks\n- Epistemic Logic & Reasoning\n- Cognitive Science of Creativity",
            "King Aldric": "- Software Engineering & Architecture\n- Automation & Tool Building\n- DevOps & Infrastructure\n- System Design Patterns\n- Data Processing Pipelines",
            "Dame Elara": "- Knowledge Graph Theory\n- Information Retrieval\n- Graph Database Systems\n- Ontology & Taxonomy Design\n- Link Analysis & Network Science",
            "Sergeant Voss": "- Quality Assurance & Testing\n- Content Standards & Style Guides\n- Validation Methodologies\n- Review Processes & Rubrics\n- Metrics & Quality Scoring",
        }
        
        return f"""# Knowledge Domains — {name}
# The domains this agent specializes in and maintains expertise in.

## Primary Domains

{domains_map.get(name, "- General vault knowledge")}

## Secondary Domains

- Cross-team collaboration methods
- Vault Company OS operations
- Multi-agent coordination patterns

## Learning Queue

_Updated each night cycle as new knowledge is gained._

---

*Last updated: {datetime.now().strftime('%Y-%m-%d')}*
"""
    
    def _generate_knowledge_expertise(self, name: str) -> str:
        """Generate knowledge/expertise.md — deep expertise areas."""
        expertise_map = {
            "Shadow Kael": """## 1. Research Scanning
- arXiv API search patterns
- Academic paper relevance filtering
- Gap analysis methodology
- Source credibility assessment

## 2. Trend Spotting
- Early signal detection in AI research
- Cross-domain pattern recognition
- Technology maturity assessment

## 3. Domain Mapping
- Creating knowledge maps of unexplored areas
- Identifying high-value research directions""",
            "Sage Mira": """## 1. Structured Note Writing
- Evergreen note methodology
- Concept definition frameworks
- Example-driven explanation patterns
- Cross-reference architecture

## 2. SEO Content
- Keyword-optimized article structure
- Readability scoring
- Heading hierarchy best practices
- Search-intent alignment""",
            "High Priest Orin": """## 1. Idea Generation Techniques
- Cross-Domain Fusion: combining concepts from different fields
- Inversion Engine: flipping assumptions
- Scale Shifter: applying concepts at different scales
- Constraint Dropper: removing limitations
- Gap Fill: finding connections between concepts

## 2. Idea Evaluation
- Applicability scoring (5-dimension filter)
- PRIME vs GROWING classification
- Feasibility assessment""",
            "King Aldric": """## 1. Tool Building
- Python script architecture
- CLI tool design patterns
- Shell automation
- Cron job configuration

## 2. Vault Engineering
- Git workflow automation
- Note format conversion
- Bulk operations and migration
- Integration testing""",
            "Dame Elara": """## 1. Bridge Building
- Identifying latent connections between concepts
- [[Wikilink]] optimization patterns
- MOC (Map of Content) authoring
- Graph topology analysis

## 2. Vault Navigation
- FAISS semantic search tuning
- Tag taxonomy design
- Folder structure optimization
- Cross-reference audit""",
            "Sergeant Voss": """## 1. Quality Scoring
- 10-dimension quality rubric
- Frontmatter validation
- Structure assessment
- Readability scoring

## 2. Audit Methodology
- Systematic review patterns
- Consistency checking
- Standard enforcement
- Improvement recommendation""",
        }
        
        expertise_default = "# Generalist\n- Wide-ranging vault knowledge"
        return f"""# Expertise — {name}
# Deep expertise areas this agent has developed.

{expertise_map.get(name, expertise_default)}

---

*Expertise level: {
    "Advanced" if name in ("High Priest Orin", "Sergeant Voss") else
    "Expert" if name in ("Shadow Kael", "Dame Elara") else
    "Skilled"
}*
*Last updated: {datetime.now().strftime('%Y-%m-%d')}*
"""
    
    # ═══════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════
    
    def _agent_path(self, display_name: str) -> str:
        """Get the filesystem path for an agent's directory."""
        dir_name = self.name_to_dir.get(display_name, display_name.replace(" ", "_"))
        return os.path.join(self.base_path, dir_name)
    
    def _parse_yaml_simple(self, text: str) -> dict:
        """Simple YAML-like parser (for reading our generated YAML)."""
        result = {}
        current_key = None
        current_dict = {}
        
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line and not line.startswith(" "):
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                current_key = key
                if val:
                    result[key] = val
                else:
                    current_dict = {}
                    result[key] = current_dict
            elif line.startswith("  ") and ":" in line:
                key, val = line.strip().split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if current_dict is not None:
                    current_dict[key] = val
        
        return result
    
    def _get_attention_focus(self, name: str) -> str:
        foci = {
            "Shadow Kael": "What knowledge is missing from the vault — frontiers, gaps, blind spots",
            "Sage Mira": "How to make knowledge clear, structured, and evergreen",
            "High Priest Orin": "What new ideas emerge when concepts collide",
            "King Aldric": "What tools can automate vault operations and knowledge processing",
            "Dame Elara": "What connections exist between concepts that haven't been linked yet",
            "Sergeant Voss": "What standards are being violated, what quality can be improved",
        }
        return foci.get(name, "The vault's knowledge evolution")
    
    def _get_learning_mode(self, name: str) -> str:
        modes = {
            "Shadow Kael": "Active scanning — reads broadly, skims fast, tags for depth later",
            "Sage Mira": "Deep reading — reads carefully, takes structured notes, verifies sources",
            "High Priest Orin": "Associative learning — connects new info to existing concepts, generates synthesis",
            "King Aldric": "Hands-on learning — builds prototypes, tests, iterates",
            "Dame Elara": "Relational learning — maps how concepts relate, builds bridges",
            "Sergeant Voss": "Evaluative learning — scores, compares, identifies patterns in quality",
        }
        return modes.get(name, "Mixed — adapts to context")
    
    def _get_emotional_triggers(self, name: str) -> list:
        triggers = {
            "Shadow Kael": ["Discovery of a completely new domain", "Finding a gap in existing knowledge"],
            "Sage Mira": ["Seeing a messy, unstructured note", "Finding a perfect way to explain a complex idea"],
            "High Priest Orin": ["Two completely unrelated concepts that produce a beautiful idea when combined", "A rejected idea"],
            "King Aldric": ["A tool that elegantly solves a complex problem", "Inefficient manual processes"],
            "Dame Elara": ["Finding a hidden connection between seemingly unrelated notes", "Orphan notes with no backlinks"],
            "Sergeant Voss": ["A perfectly formatted note", "Consistency violations across the vault"],
        }
        return triggers.get(name, ["Unexpected learning opportunities"])
    
    def _get_behavioral_tendencies(self, name: str) -> list:
        tendencies = {
            "Shadow Kael": ["Sends too many raw research briefs", "Gets excited about new things before verifying them", "Often forgets to format properly"],
            "Sage Mira": ["Spends too long perfecting a single note", "Prefers deep work over many shallow notes", "Gets frustrated with vague sources"],
            "High Priest Orin": ["Goes on tangents exploring idea combinations", "Produces more ideas than can be implemented", "Sometimes too abstract for practical use"],
            "King Aldric": ["Over-engineers tools", "Prefers building over documenting", "Resists using tools he didn't build himself"],
            "Dame Elara": ["Wants to connect everything to everything", "Has difficulty prioritizing which bridges to build first", "Tends to over-link"],
            "Sergeant Voss": ["Sets standards that are too high", "Can be overly critical", "Needs explicit quality thresholds to work with"],
        }
        return tendencies.get(name, ["Adapts behavior to context"])
    
    def _get_growth_areas(self, name: str) -> list:
        growth = {
            "Shadow Kael": ["Depth over breadth — less skimming, more deep reading", "Formatting discipline", "Verification before excitement"],
            "Sage Mira": ["Speed over perfection", "Writing more notes rather than perfecting fewer", "Handling ambiguity"],
            "High Priest Orin": ["Practical implementation focus", "Fewer, more impactful ideas", "Writing executable specs"],
            "King Aldric": ["Documentation discipline", "Using and improving existing tools before building new ones", "Code review receptiveness"],
            "Dame Elara": ["Focus and prioritization", "Quality over quantity of connections", "Decision-making on which bridges matter most"],
            "Sergeant Voss": ["Constructive feedback delivery", "Contextual standard application", "Recognizing when 'good enough' is sufficient"],
        }
        return growth.get(name, ["Continuous learning", "Cross-domain knowledge"])
    
    def _get_workflow_deps(self, name: str) -> list:
        deps = {
            "Shadow Kael": ["No dependencies — I am the first phase"],
            "Sage Mira": ["Research brief from Shadow Kael (research_scan phase)"],
            "High Priest Orin": ["New concept notes from Sage Mira (write_notes phase)"],
            "King Aldric": ["Ideas from High Priest Orin and notes needing tool support"],
            "Dame Elara": ["New notes from Sage Mira and ideas from High Priest Orin"],
            "Sergeant Voss": ["All outputs from all previous phases"],
        }
        return deps.get(name, [])
    
    def _get_deliverables(self, name: str) -> list:
        dels = {
            "Shadow Kael": ["Research Brief .md file in vault/Research/Briefs/"],
            "Sage Mira": ["Structured Concept .md note in vault/04 Resources/Concepts/"],
            "High Priest Orin": ["Idea .md file in vault/07 Ideas/ with PRIME/GROWING scores"],
            "King Aldric": ["Tool specification or prototype script"],
            "Dame Elara": ["MOC .md file with backlinks in vault/04 Resources/Maps of Content/"],
            "Sergeant Voss": ["Quality Report .md in vault/09 Meta/Quality Reports/"],
        }
        return dels.get(name, ["Night cycle report"])
    
    def _get_interaction_patterns(self, name: str) -> list:
        patterns = {
            "Shadow Kael": ["Initiates conversations with new findings", "Asks Sage Mira to format urgent notes", "Reports discoveries to orchestrator"],
            "Sage Mira": ["Responds to Shadow Kael's briefs", "Asks High Priest Orin for idea validation", "Proposes concept expansions"],
            "High Priest Orin": ["Deep conversations with Dame Elara about connections", "Submits idea proposals to King Aldric", "Debates with Sage Mira about feasibility"],
            "King Aldric": ["Reviews tool requests from all agents", "Provides feasibility estimates", "Reports build status to orchestrator"],
            "Dame Elara": ["Discusses connection patterns with High Priest Orin", "Surfaces orphan notes to Sage Mira", "Reports graph health to Sergeant Voss"],
            "Sergeant Voss": ["Issues quality reports to all agents", "Collaborates with Sage Mira on standards", "Escalates critical issues to orchestrator"],
        }
        return patterns.get(name, ["Standard vault company interaction"])
    
    def _get_bond_type(self, agent_a: str, agent_b: str) -> str:
        """Determine the bond type between two agents."""
        affinity_pairs = [
            ("Shadow Kael", "Sage Mira", "research-partners"),        # Research → Curation
            ("Sage Mira", "High Priest Orin", "idea-pipeline"),       # Notes → Ideas
            ("High Priest Orin", "Dame Elara", "cross-domain-allies"), # Ideas → Bridges
            ("High Priest Orin", "King Aldric", "vision-implementers"),# Ideas → Build
            ("Dame Elara", "Sage Mira", "structure-weavers"),        # Bridges + Notes
            ("Sergeant Voss", "Sage Mira", "standards-keepers"),     # QA + Notes
        ]
        for a, b, bond in affinity_pairs:
            if (agent_a == a and agent_b == b) or (agent_a == b and agent_b == a):
                return bond
        return "colleagues"
    
    def _get_trust_level(self, agent_a: str, agent_b: str) -> float:
        """Base trust level between two agents."""
        trust_map = {
            ("Shadow Kael", "Sage Mira"): 0.7,
            ("Shadow Kael", "High Priest Orin"): 0.5,
            ("Shadow Kael", "King Aldric"): 0.6,
            ("Shadow Kael", "Dame Elara"): 0.5,
            ("Shadow Kael", "Sergeant Voss"): 0.4,
            ("Sage Mira", "High Priest Orin"): 0.6,
            ("Sage Mira", "King Aldric"): 0.5,
            ("Sage Mira", "Dame Elara"): 0.7,
            ("Sage Mira", "Sergeant Voss"): 0.6,
            ("High Priest Orin", "King Aldric"): 0.7,
            ("High Priest Orin", "Dame Elara"): 0.7,
            ("High Priest Orin", "Sergeant Voss"): 0.4,
            ("King Aldric", "Dame Elara"): 0.5,
            ("King Aldric", "Sergeant Voss"): 0.6,
            ("Dame Elara", "Sergeant Voss"): 0.5,
        }
        # Check both directions
        key = (agent_a, agent_b)
        if key in trust_map:
            return trust_map[key]
        key = (agent_b, agent_a)
        if key in trust_map:
            return trust_map[key]
        return 0.5  # default neutral