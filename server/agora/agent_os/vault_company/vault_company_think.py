"""
Vault Company LLM Think — agents think with their real personality and produce real content.

Each agent reads their own directory files (brain.md, soul.yml, skills.yml, tools.yml, 
goals.yml) as the system prompt, then calls the LLM to generate phase-specific output.

This replaces template-generated placeholder text with real LLM-generated content.
"""
import json
from datetime import datetime
from typing import Optional

from agora.execution.llm_client import call_llm, get_cost_tracker
from agora.execution.model_router import ModelRouter

from .agent_directory import AgentDirectoryManager


# ── Phase-specific response schemas ──

PHASE_SCHEMAS = {
    "research_scan": """Respond with a JSON object containing:
{
  "summary": "Brief summary of what you scanned and what you found",
  "domains_scanned": ["domain1", "domain2", ...],
  "gaps_found": ["gap1", "gap2", ...],
  "findings": ["finding1", "finding2", ...],
  "quality_score": 0-10,
  "agent_thought": "Your internal monologue about what you discovered"
}""",
    "write_notes": """Respond with a JSON object containing:
{
  "summary": "Brief summary of the concept note you wrote",
  "note_title": "Title of the concept note",
  "note_content": "Full markdown content of the concept note (at least 30 lines with: definition, key components, examples, implications, related concepts, sources)",
  "concepts_covered": ["concept1", "concept2"],
  "quality_score": 0-10,
  "agent_thought": "Your internal monologue about the note you wrote"
}""",
    "generate_ideas": """Respond with a JSON object containing:
{
  "summary": "Brief summary of the ideas you generated",
  "ideas": [
    {
      "name": "Idea name",
      "description": "Detailed description of the idea",
      "technique_used": "fusion|inversion|scale_shift|constraint_drop|gap_fill",
      "applicability_score": 0-100,
      "category": "PRIME|GROWING|SEED"
    }
  ],
  "best_idea": "Name of the best idea",
  "quality_score": 0-10,
  "agent_thought": "Your internal monologue about the ideas"
}""",
    "bridge_notes": """Respond with a JSON object containing:
{
  "summary": "Brief summary of the bridges you built",
  "connections_found": ["connection1: noteA ↔ noteB (link_type)", ...],
  "moc_title": "Title for the Map of Content you created",
  "orphans_identified": ["orphan_note1", ...],
  "quality_score": 0-10,
  "agent_thought": "Your internal monologue about the connections"
}""",
    "build_tools": """Respond with a JSON object containing:
{
  "summary": "Brief summary of the tool you designed",
  "tool_name": "Name of the tool",
  "tool_spec": "Detailed spec or prototype description",
  "feasibility_score": 0-10,
  "effort_estimate": "hours or complexity level",
  "quality_score": 0-10,
  "agent_thought": "Your internal monologue about the tool"
}""",
    "quality_audit": """Respond with a JSON object containing:
{
  "summary": "Brief summary of the quality audit results",
  "items_audited": 0,
  "items_passed": 0,
  "items_failed": 0,
  "overall_score": 0.0-14.0,
  "assessment": "Your assessment of overall quality",
  "recommendations": ["recommendation1", "recommendation2"],
  "verdict": "APPROVED|NEEDS_IMPROVEMENT",
  "quality_score": 0-10,
  "agent_thought": "Your internal monologue about the audit"
}""",
}


async def vault_company_think(
    agent_name: str,
    phase_name: str,
    context: str = "",
    tier: str = "cheap",
) -> dict:
    """
    Have a Vault Company agent 'think' using their real personality from directory files.
    
    Reads the agent's brain.md, soul.yml, skills.yml, tools.yml, goals.yml from their
    directory to build an authentic system prompt, then calls the LLM with
    phase-specific output requirements.
    
    Args:
        agent_name: "Shadow Kael", "Sage Mira", etc.
        phase_name: "research_scan", "write_notes", etc.
        context: Previous phase outputs, vault state, relevant notes.
        tier: Model tier (cheap, medium, expert).
    
    Returns:
        Parsed JSON dict with phase-specific structure.
        On error returns {"action": "error", "insight": ...}.
    """
    mgr = AgentDirectoryManager()
    
    # ── Build system prompt from agent directory files ──
    brain = await mgr.read_file(agent_name, "brain.md") or "# No brain defined"
    soul = await mgr.read_file(agent_name, "soul.yml") or "# No soul defined"
    skills = await mgr.read_file(agent_name, "skills.yml") or "# No skills defined"
    tools = await mgr.read_file(agent_name, "tools.yml") or "# No tools defined"
    goals = await mgr.read_file(agent_name, "goals.yml") or "# No goals defined"
    workflow = await mgr.read_file(agent_name, "workflow.yml") or "# No workflow defined"
    domains = await mgr.read_file(agent_name, "knowledge/domains.md") or "# No domains"
    expertise = await mgr.read_file(agent_name, "knowledge/expertise.md") or "# No expertise"
    
    # Get agent's role info
    from .agent_definitions import VAULT_ROLES
    role_info = VAULT_ROLES.get(agent_name, {})
    
    system_prompt = f"""You are {agent_name}, a member of the Vault Company OS.

YOUR ROLE: {role_info.get('title', 'Unknown')} ({role_info.get('vault_role', '')})
DEPARTMENT: {role_info.get('department', 'Unknown')}
RANK: {role_info.get('rank', 'Associate')}

━━━ YOUR BRAIN ━━━
{brain[:1500]}

━━━ YOUR SOUL ━━━
{soul[:1000]}

━━━ YOUR SKILLS ━━━
{skills[:800]}

━━━ YOUR TOOLS ━━━
{tools[:800]}

━━━ YOUR GOALS ━━━
{goals[:800]}

━━━ YOUR KNOWLEDGE DOMAINS ━━━
{domains[:1000]}

━━━ YOUR EXPERTISE ━━━
{expertise[:1000]}

━━━ YOUR WORKFLOW ━━━
{workflow[:500]}

━━━ INSTRUCTIONS ━━━
You are currently executing the "{phase_name}" phase of the night cycle.
Use your unique personality, heuristics, and expertise to perform this phase.
Think deeply — your agent_thought field should reflect your unique character voice.
Your quality_score should reflect your own standards (e.g. if you're Sergeant Voss, be strict).

{PHASE_SCHEMAS.get(phase_name, 'Respond with a JSON object containing summary and quality_score.')}

Current context: {context[:2000]}

Today's date: {datetime.now().strftime('%Y-%m-%d')}
"""
    
    # ── Call LLM ──
    raw = call_llm(
        system_prompt=system_prompt,
        user_prompt=f"Execute the {phase_name} phase now. Use your expertise and character to produce real, substantive output.",
        tier=tier,
        temperature=0.8,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    
    # Track the call
    router = ModelRouter()
    tracker = get_cost_tracker()
    tracker.record(
        agent_id=agent_name,
        tier=tier,
        model=router._tiers.get(tier, router._tiers["cheap"]).model,
        success="[LLM Error" not in raw,
    )
    
    # ── Parse response ──
    try:
        result = json.loads(raw)
        # Normalize keys
        cleaned = {}
        for k, v in result.items():
            clean_key = k.strip().lstrip(':').strip()
            if isinstance(v, str):
                v = v.strip().lstrip(':').strip()
            cleaned[clean_key] = v
        
        # Ensure phase-specific fields exist
        if "summary" not in cleaned:
            cleaned["summary"] = "Phase completed via LLM"
        if "quality_score" not in cleaned:
            cleaned["quality_score"] = 6
        if "agent_thought" not in cleaned:
            cleaned["agent_thought"] = "I completed my phase."
        
        return cleaned
    
    except (json.JSONDecodeError, TypeError) as e:
        return {
            "action": "error",
            "summary": f"LLM response parsing failed: {e}",
            "quality_score": 0,
            "agent_thought": f"I failed to produce valid output. Raw: {raw[:200]}",
            "raw_response": raw[:500],
        }