"""
Dungeon Agent API — Phase 2: One Real Agent with LLM.
Receives game state → calls LLM → returns action decision.
Memory system with importance scoring, decay, and relevance retrieval.
"""

import json
import math
import time
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agora.execution.llm_client import call_llm

router = APIRouter(prefix="/api/v1/dungeon", tags=["dungeon"])

# ── Memory Store ──

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

    # Add relevant past memories (retrieved by relevance, not just recent)
    relevant = _retrieve_relevant_memories(context, limit=5)
    if relevant:
        mem_text = "\n".join(f"- {m['summary']}" for m in relevant)
        context += f"\n\nYour memories:\n{mem_text}"

    # Call LLM
    cfg = getattr(request.app.state, 'dungeon_config', {})
    use_llm = cfg.get("llm_enabled", True)

    if use_llm:
        raw = call_llm(
            system_prompt=DUNGEON_SYSTEM_PROMPT,
            user_prompt=context,
            tier=cfg.get("llm_tier", "cheap"),
            temperature=0.8,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
    else:
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

    # Store memory with importance scoring
    _store_memory(
        state=state,
        decision=decision,
    )

    return decision


@router.get("/memories")
async def get_memories(limit: int = 10, min_importance: float = 1.0):
    """Retrieve agent memories, sorted by importance × recency."""
    scored = _score_all_memories()
    filtered = [m for m in scored if m["score"] >= min_importance]
    return {"memories": filtered[:limit]}


@router.get("/memories/search")
async def search_memories(q: str = "", limit: int = 5):
    """Search memories by keyword relevance."""
    q = q.lower().strip()
    if not q:
        return {"memories": _score_all_memories()[:limit]}

    results = []
    for m in reversed(_memories):
        text = (m.get("summary", "") + " " + m.get("state_summary", "")).lower()
        if q in text:
            results.append(m)
            if len(results) >= limit:
                break
    return {"memories": results}


@router.post("/memories/clear")
async def clear_memories():
    """Clear all memories (new session)."""
    _memories.clear()
    return {"status": "cleared"}


# ── Memory Engine ──

def _store_memory(state: DungeonState, decision: dict):
    """Store a memory with automatic importance scoring."""
    action = decision.get("action", "unknown")
    thought = decision.get("thought", "")
    message = decision.get("message", "")
    summary = thought or message or f"Performed action: {action}"

    # Score importance based on action type and context
    importance = _score_importance(action, thought, state)

    _memories.append({
        "timestamp": time.time(),
        "state_summary": f"At ({state.agent_x:.0f}, {state.agent_y:.0f}) HP:{state.health:.0f}",
        "decision": action,
        "summary": summary[:200],
        "importance": importance,
        "tags": _infer_tags(action, thought),
    })

    # Decay old memories
    _decay_memories()

    # Prune if over limit
    if len(_memories) > 100:
        _prune_memories()


def _score_importance(action: str, thought: str, state: DungeonState) -> float:
    """Score memory importance 1-10 based on content."""
    score = 3.0  # baseline

    # Action-based boosts
    action_weights = {
        "talk": 5.0,
        "interact": 5.0,
        "use": 4.0,
        "explore": 3.5,
        "move": 2.0,
        "wait": 1.5,
    }
    score += action_weights.get(action, 2.0)

    # Thought content boosts
    thought_lower = (thought or "").lower()
    important_keywords = [
        "crystal", "eternity", "discover", "found", "secret", "treasure",
        "danger", "enemy", "monster", "key", "door", "portal", "quest",
        "artifact", "ancient", "boss", "puzzle", "trap", "reward",
        "ally", "friend", "betray", "important",
    ]
    for kw in important_keywords:
        if kw in thought_lower:
            score += 1.0

    # NPC interaction boost
    if state.nearby_npcs and action in ("talk", "interact"):
        score += 1.5

    return min(10.0, score)


def _infer_tags(action: str, thought: str) -> list[str]:
    """Infer memory tags from content."""
    tags = [action]
    thought_lower = (thought or "").lower()

    if any(w in thought_lower for w in ["npc", "grom", "zara", "finn", "guard", "talk"]):
        tags.append("npc_interaction")
    if any(w in thought_lower for w in ["explor", "room", "corridor", "passage", "north", "south"]):
        tags.append("exploration")
    if any(w in thought_lower for w in ["item", "key", "inventory", "use", "object"]):
        tags.append("item")
    if any(w in thought_lower for w in ["danger", "enemy", "monster", "trap", "alert"]):
        tags.append("danger")

    return tags


def _decay_memories():
    """Reduce importance of old memories over time."""
    now = time.time()
    for m in _memories:
        age = (now - m["timestamp"]) / 60  # minutes
        if age > 1:
            decay = 0.3 * math.log(age + 1)
            m["importance"] = max(1.0, m["importance"] - decay)


def _prune_memories():
    """Keep only the most valuable memories."""
    scored = _score_all_memories()
    scored.sort(key=lambda x: x["score"], reverse=True)
    keep_ids = {id(m) for m in scored[:80]}
    _memories[:] = [m for m in _memories if id(m) in keep_ids]


def _score_all_memories() -> list[dict]:
    """Score all memories by importance × recency factor."""
    now = time.time()
    scored = []
    for m in reversed(_memories):
        age = (now - m["timestamp"]) / 60  # minutes
        recency_boost = max(0.5, 1.0 - 0.1 * age)
        score = m.get("importance", 3.0) * recency_boost
        scored.append({**m, "score": round(score, 2)})
    return scored


def _retrieve_relevant_memories(context: str, limit: int = 5) -> list[dict]:
    """Retrieve memories relevant to current context using keyword overlap."""
    if not _memories:
        return []

    # Extract context keywords
    context_lower = context.lower()
    # Score each memory by keyword overlap
    scored = []
    for m in reversed(_memories):
        text = (m.get("summary", "") + " " + m.get("state_summary", "")).lower()
        # Simple overlap score
        overlap = 0
        for word in context_lower.split():
            if len(word) > 3 and word in text:
                overlap += 1
        relevance = m.get("importance", 3.0) + overlap * 0.5
        scored.append((relevance, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:limit]]


# ── Context Builder ──

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
        npc_list = [
            f"{n.get('name', '?')} ({n.get('role', '?')}) at ({n.get('x', 0):.0f}, {n.get('y', 0):.0f})"
            for n in state.nearby_npcs
        ]
        parts.append(f"Nearby NPCs: {', '.join(npc_list)}")
    else:
        parts.append("Nearby NPCs: none")

    if state.nearby_objects:
        obj_list = [
            f"{o.get('name', '?')} at ({o.get('x', 0):.0f}, {o.get('y', 0):.0f})"
            for o in state.nearby_objects
        ]
        parts.append(f"Nearby objects: {', '.join(obj_list)}")

    return "\n".join(parts)


@router.post("/config")
async def set_config(config: dict):
    """Set dungeon agent config (LLM tier, enabled flag)."""
    return {"status": "config_updated"}
