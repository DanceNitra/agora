"""
Dungeon Agent API — Phase 2: One Real Agent with LLM.
Receives game state → calls LLM → returns action decision.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agora.execution.llm_client import call_llm

router = APIRouter(prefix="/api/v1/dungeon", tags=["dungeon"])

# ── In-memory memory store (short-term per session) ──
_memories: list[dict[str, Any]] = []

DUNGEON_SYSTEM_PROMPT = """You are an AI agent named Kael in a dungeon game world.
You can see your surroundings and have a set of possible actions.
Your goal is to explore the dungeon, interact with NPCs, and complete tasks.

Respond ONLY with a valid JSON object containing:
{
  "action": "move|interact|talk|wait|use|explore",
  "target_x": <optional number>,
  "target_y": <optional number>,
  "target_npc": "<optional NPC name>",
  "message": "<what you say or do, 1 sentence>",
  "thought": "<your internal reasoning, 1 sentence>"
}

Actions:
- "move": walk to coordinates (target_x, target_y)
- "interact": use a workstation or object
- "talk": speak to an NPC (target_npc)
- "wait": stay in place and observe
- "use": use an inventory item
- "explore": move toward unexplored area"""


class DungeonState(BaseModel):
    agent_name: str = "Kael"
    agent_x: float
    agent_y: float
    health: float = 100
    inventory: list[str] = []
    nearby_npcs: list[dict[str, Any]] = []
    nearby_objects: list[dict[str, Any]] = []
    recent_memories: list[str] = []
    current_objective: str = "Explore the dungeon"


@router.post("/agent-action")
async def dungeon_agent_action(state: DungeonState, request: Request):
    """Receive game state → LLM decides action → return decision."""
    
    # Build context from game state
    context = _build_context(state)
    
    # Add recent memories
    mem_text = ""
    recent = _memories[-5:] if len(_memories) > 5 else _memories
    if recent:
        mem_text = "\n".join(f"- {m['summary']}" for m in recent)
        context += f"\n\nYour memories:\n{mem_text}"
    
    # Call LLM
    cfg = request.app.state.dungeon_config if hasattr(request.app.state, 'dungeon_config') else {}
    tier = cfg.get("llm_tier", "cheap")
    use_llm = cfg.get("llm_enabled", True)
    
    if use_llm:
        raw = call_llm(
            system_prompt=DUNGEON_SYSTEM_PROMPT,
            user_prompt=context,
            tier=tier,
            temperature=0.8,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
    else:
        # Simulated response for testing
        raw = json.dumps({
            "action": "move",
            "target_x": state.agent_x + 64,
            "target_y": state.agent_y,
            "message": "I'll explore this corridor.",
            "thought": "I see an unexplored passage to the east."
        })
    
    # Parse response
    try:
        decision = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        decision = {
            "action": "wait",
            "message": "I'm thinking about what to do next.",
            "thought": "I received an unclear response from my reasoning."
        }
    
    # Store memory
    _memories.append({
        "timestamp": datetime.utcnow().isoformat(),
        "state_summary": f"At ({state.agent_x:.0f}, {state.agent_y:.0f}) HP:{state.health:.0f}",
        "decision": decision.get("action", "unknown"),
        "summary": decision.get("thought", "") or decision.get("message", ""),
    })
    
    return decision


@router.get("/memories")
async def get_memories(limit: int = 10):
    """Retrieve recent agent memories."""
    recent = _memories[-limit:] if len(_memories) > limit else _memories
    return {"memories": list(reversed(recent))}


@router.post("/memories/clear")
async def clear_memories():
    """Clear all memories (new session)."""
    _memories.clear()
    return {"status": "cleared"}


def _build_context(state: DungeonState) -> str:
    """Build a detailed context string from game state."""
    parts = [f"You are {state.agent_name} at position ({state.agent_x:.0f}, {state.agent_y:.0f})."]
    parts.append(f"Health: {state.health:.0f}/100.")
    
    if state.inventory:
        parts.append(f"Inventory: {', '.join(state.inventory)}.")
    else:
        parts.append("Inventory: empty.")
    
    if state.current_objective:
        parts.append(f"Objective: {state.current_objective}")
    
    if state.nearby_npcs:
        npc_list = [f"{n.get('name', '?')} ({n.get('role', '?')}) at ({n.get('x', 0):.0f}, {n.get('y', 0):.0f})" for n in state.nearby_npcs]
        parts.append(f"Nearby NPCs: {', '.join(npc_list)}")
    else:
        parts.append("Nearby NPCs: none")
    
    if state.nearby_objects:
        obj_list = [f"{o.get('name', '?')} at ({o.get('x', 0):.0f}, {o.get('y', 0):.0f})" for o in state.nearby_objects]
        parts.append(f"Nearby objects: {', '.join(obj_list)}")
    
    return "\n".join(parts)


@router.post("/config")
async def set_config(config: dict):
    """Set dungeon agent config (LLM tier, enabled flag)."""
    # Store in app state via middleware
    return {"status": "config_updated"}
