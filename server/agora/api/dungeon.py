"""
Dungeon Agent API — Phase 3: Multi-Agent with per-agent personalities and memory.
Receives game state → calls LLM → returns action decision.
"""

import json
import math
import time
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agora.execution.llm_client import call_llm

import uuid

# ── Dungeon Agent IDs (stable UUIDs for Trust Engine) ──

DUNGEON_AGENT_IDS = {
    "Kael": "00000000-0000-0000-0000-000000000001",
    "Lyra": "00000000-0000-0000-0000-000000000002",
    "Mordecai": "00000000-0000-0000-0000-000000000003",
}

DUNGEON_AGENT_ROLES = {
    "Kael": "adventurer",
    "Lyra": "scout",
    "Mordecai": "sage",
}

_DUNGEON_SEEDED = False


async def _ensure_dungeon_agents_seeded(request: Request):
    """Lazily seed dungeon agents into the database on first use."""
    global _DUNGEON_SEEDED
    if _DUNGEON_SEEDED:
        return
    db = request.app.state.db
    for name, aid in DUNGEON_AGENT_IDS.items():
        cursor = await db.execute("SELECT 1 FROM agent_identities WHERE agent_id=?", (aid,))
        exists = await cursor.fetchone()
        if not exists:
            role = DUNGEON_AGENT_ROLES.get(name, "explorer")
            genome = json.dumps({
                "role": role,
                "tools": ["move", "talk", "interact"],
                "dungeon_agent": True,
                "personality_traits": {"curiosity": 0.9, "cooperativeness": 0.8},
            })
            await db.execute(
                "INSERT INTO agent_identities (agent_id, public_key, generation, genome, trust_score, energy_balance, role, status) VALUES (?, ?, 0, ?, 0.5, 100, ?, 'active')",
                (aid, f"dungeon_{name.lower()}", genome, role),
            )
    await db.commit()
    _DUNGEON_SEEDED = True

router = APIRouter(prefix="/api/v1/dungeon", tags=["dungeon"])

# ── Dungeon Config (default: simulated LLM for fast tests) ──

_dungeon_config: dict[str, Any] = {"llm_enabled": False, "llm_tier": "cheap"}

# ── Per-Agent Memory Store ──

_memories: dict[str, list[dict[str, Any]]] = {}

# ── Message Inboxes (NPC-to-NPC communication) ──
_inboxes: dict[str, list[dict[str, Any]]] = {}


def _inbox(agent_name: str) -> list[dict[str, Any]]:
    """Get or create message inbox for an agent."""
    if agent_name not in _inboxes:
        _inboxes[agent_name] = []
    return _inboxes[agent_name]


def _mem(agent_name: str) -> list[dict[str, Any]]:
    """Get or create memory bank for a specific agent."""
    if agent_name not in _memories:
        _memories[agent_name] = []
    return _memories[agent_name]


# ── Agent Personalities ──

def _get_prompt(agent_name: str) -> str:
    agents = {
        "Kael": (
            "You are Kael, an adventurer seeking the Crystal of Eternity. "
            "You are brave, curious, and determined. You explore the dungeon to find the legendary artifact. "
            "You know Grom (blacksmith), Zara (alchemist), Finn (merchant), Lyra (scout), Mordecai (sage), and the Guard."
        ),
        "Lyra": (
            "You are Lyra, a scout and cartographer mapping the dungeon. "
            "You are swift, observant, and cautious. Your mission is to explore every corner of the dungeon, "
            "note dangers, and report back. You work alongside Kael, Mordecai, Grom, Zara, Finn, and the Guard."
        ),
        "Mordecai": (
            "You are Mordecai, a sage studying ancient artifacts and dungeon lore. "
            "You are wise, patient, and scholarly. You seek ancient knowledge, magical items, and hidden "
            "secrets. You advise Kael, Lyra, and the others with your wisdom."
        ),
    }
    personality = agents.get(agent_name, f"You are {agent_name}, an agent in a dungeon game world.")

    return (
        f"{personality}\n\n"
        f"You can see your surroundings and have a set of possible actions.\n\n"
        f"Your trust with other agents affects how they cooperate with you.\n"
        f"Higher trust means they will help you more.\n"
        f"Build trust by talking and cooperating with them.\n\n"
        f"Respond ONLY with a valid JSON object containing:\n"
        f'{{{{"action":"move|interact|talk|cooperate|wait|use|explore",'
        f'"target_x":<optional number>,"target_y":<optional number>,'
        f'"target_npc":"<optional NPC name>",'
        f'"message":"<what you say or do, 1 sentence>",'
        f'"thought":"<your internal reasoning, 1 sentence>"}}}}'
        f"\n\nActions:\n"
        f'- "move": walk to coordinates (target_x, target_y)\n'
        f'- "interact": use a workstation or object\n'
        f'- "talk": speak to an NPC (target_npc)\n'
        f'- "cooperate": work together with an NPC (target_npc)\n'
        f'- "wait": stay in place and observe\n'
        f'- "use": use an inventory item\n'
        f'- "explore": move toward unexplored area'
    )


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
    agent_name = state.agent_name
    memories = _mem(agent_name)

    # Ensure dungeon agents exist in DB for trust tracking
    await _ensure_dungeon_agents_seeded(request)

    # Build context with relevant past memories
    context = _build_context(state)
    relevant = _retrieve_relevant_memories(agent_name, context, limit=5)
    if relevant:
        mem_text = "\n".join(f"- {m['summary']}" for m in relevant)
        context += f"\n\nYour memories:\n{mem_text}"

    # Add inbox messages (from other agents talking to us)
    msgs = _inbox(agent_name)
    if msgs:
        inbox_text = "\n".join(
            f"- {m['from']} says: \"{m['message']}\""
            for m in msgs[-3:]  # last 3 messages
        )
        context += f"\n\nMessages you received:\n{inbox_text}"
        msgs.clear()  # consumed

    # Add trust scores for nearby agents
    try:
        trust_engine = request.app.state.trust
        agent_id = DUNGEON_AGENT_IDS.get(agent_name)
        if agent_id:
            trust_lines = []
            for npc in state.nearby_npcs:
                npc_name = npc.get("name", "")
                npc_id = DUNGEON_AGENT_IDS.get(npc_name)
                if npc_id:
                    trust_val = await trust_engine.get_trust(agent_id, npc_id)
                    trust_lines.append(f"{npc_name}: {trust_val:.2f}")
            if trust_lines:
                context += f"\n\nYour trust with nearby agents:\n" + "\n".join(trust_lines)
    except Exception:
        pass  # trust engine not available

    # Call LLM
    cfg = _dungeon_config
    use_llm = cfg.get("llm_enabled", False)

    if use_llm:
        raw = call_llm(
            system_prompt=_get_prompt(agent_name),
            user_prompt=context,
            tier=cfg.get("llm_tier", "cheap"),
            temperature=0.8,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
    else:
        # Simulated response for testing — vary per agent personality
        import random
        sim_actions = [
            json.dumps({"action": "move", "target_x": state.agent_x + 64,
                        "target_y": state.agent_y, "message": "I will explore this area.",
                        "thought": "I see unexplored territory ahead."}),
            json.dumps({"action": "talk", "target_npc": "Lyra",
                        "message": "Lyra, what have you discovered?",
                        "thought": "I should check in with Lyra on her findings."}),
            json.dumps({"action": "talk", "target_npc": "Mordecai",
                        "message": "Mordecai, any news on the artifacts?",
                        "thought": "The sage may have new insights."}),
        ]
        raw = random.choice(sim_actions)

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
    _store_memory(agent_name, state, decision)

    # Route messages: if "talk" with target_npc, deliver to that agent's inbox
    if decision.get("action") == "talk" and decision.get("target_npc"):
        target = decision["target_npc"]
        msg = decision.get("message", "")
        if target in ("Grom", "Zara", "Finn", "Guard", "Lyra", "Mordecai", "Kael"):
            _inbox(target).append({
                "from": agent_name,
                "message": msg,
                "timestamp": time.time(),
            })

    # Record trust interactions (talk/cooperate → trust bonus)
    try:
        trust_engine = request.app.state.trust
        source_id = DUNGEON_AGENT_IDS.get(agent_name)
        target_name = decision.get("target_npc", "")
        target_id = DUNGEON_AGENT_IDS.get(target_name)
        if source_id and target_id and decision.get("action") in ("talk", "interact", "cooperate"):
            await trust_engine.record_interaction(source_id, target_id, "cooperate")
    except Exception:
        pass  # trust engine not available for this interaction

    return decision


@router.get("/memories")
async def get_memories(agent_name: str = "Kael", limit: int = 10, min_importance: float = 1.0):
    """Retrieve agent memories, sorted by importance × recency."""
    scored = _score_all_memories(agent_name)
    filtered = [m for m in scored if m["score"] >= min_importance]
    return {"agent": agent_name, "memories": filtered[:limit]}


@router.get("/memories/search")
async def search_memories(agent_name: str = "Kael", q: str = "", limit: int = 5):
    """Search agent memories by keyword relevance."""
    memories = _mem(agent_name)
    q = q.lower().strip()
    if not q:
        scored = _score_all_memories(agent_name)
        return {"agent": agent_name, "memories": scored[:limit]}

    results = []
    for m in reversed(memories):
        text = (m.get("summary", "") + " " + m.get("state_summary", "")).lower()
        if q in text:
            results.append(m)
            if len(results) >= limit:
                break
    return {"agent": agent_name, "memories": results}


@router.get("/agents")
async def list_agents():
    """List all agents that have memories stored."""
    return {"agents": list(_memories.keys())}


@router.get("/inbox")
async def get_inbox(agent_name: str = "Kael"):
    """Get pending messages for an agent."""
    msgs = list(_inbox(agent_name))  # copy
    return {"agent": agent_name, "messages": msgs}


@router.get("/trust")
async def get_trust(agent_name: str = "Kael", request: Request = None):
    """Get trust scores between this agent and all other dungeon agents."""
    agent_id = DUNGEON_AGENT_IDS.get(agent_name)
    if not agent_id or not request:
        return {"agent": agent_name, "trust": {}}

    scores = {}
    trust_engine = request.app.state.trust
    for other_name, other_id in DUNGEON_AGENT_IDS.items():
        if other_name == agent_name:
            continue
        try:
            val = await trust_engine.get_trust(agent_id, other_id)
            scores[other_name] = round(val, 3)
        except Exception:
            scores[other_name] = 0.3  # baseline
    return {"agent": agent_name, "trust": scores}


@router.post("/memories/clear")
async def clear_memories(agent_name: str = ""):
    """Clear memories for an agent (or all if agent_name empty)."""
    if agent_name:
        _memories[agent_name] = []
    else:
        _memories.clear()
    return {"status": "cleared", "agent": agent_name or "all"}


# ── Memory Engine ──

def _store_memory(agent_name: str, state: DungeonState, decision: dict):
    """Store a memory with automatic importance scoring."""
    memories = _mem(agent_name)
    action = decision.get("action", "unknown")
    thought = decision.get("thought", "")
    message = decision.get("message", "")
    summary = thought or message or f"Performed action: {action}"

    importance = _score_importance(action, thought, state)

    memories.append({
        "timestamp": time.time(),
        "state_summary": f"At ({state.agent_x:.0f}, {state.agent_y:.0f}) HP:{state.health:.0f}",
        "decision": action,
        "summary": summary[:200],
        "importance": importance,
        "tags": _infer_tags(action, thought),
    })

    _decay_memories(agent_name)
    if len(memories) > 100:
        _prune_memories(agent_name)


def _score_importance(action: str, thought: str, state: DungeonState) -> float:
    score = 3.0
    action_weights = {"talk": 5.0, "interact": 5.0, "use": 4.0, "explore": 3.5, "move": 2.0, "wait": 1.5}
    score += action_weights.get(action, 2.0)

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

    if state.nearby_npcs and action in ("talk", "interact"):
        score += 1.5

    return min(10.0, score)


def _infer_tags(action: str, thought: str) -> list[str]:
    tags = [action]
    thought_lower = (thought or "").lower()
    if any(w in thought_lower for w in ["npc", "grom", "zara", "finn", "guard", "lyra", "mordecai", "talk"]):
        tags.append("npc_interaction")
    if any(w in thought_lower for w in ["explor", "room", "corridor", "passage", "north", "south"]):
        tags.append("exploration")
    if any(w in thought_lower for w in ["item", "key", "inventory", "use", "object"]):
        tags.append("item")
    if any(w in thought_lower for w in ["danger", "enemy", "monster", "trap", "alert"]):
        tags.append("danger")
    return tags


def _decay_memories(agent_name: str):
    now = time.time()
    for m in _mem(agent_name):
        age = (now - m["timestamp"]) / 60
        if age > 1:
            decay = 0.3 * math.log(age + 1)
            m["importance"] = max(1.0, m["importance"] - decay)


def _prune_memories(agent_name: str):
    memories = _mem(agent_name)
    scored = _score_all_memories(agent_name)
    scored.sort(key=lambda x: x["score"], reverse=True)
    keep_ids = {id(m) for m in scored[:80]}
    memories[:] = [m for m in memories if id(m) in keep_ids]


def _score_all_memories(agent_name: str) -> list[dict]:
    now = time.time()
    scored = []
    for m in reversed(_mem(agent_name)):
        age = (now - m["timestamp"]) / 60
        recency_boost = max(0.5, 1.0 - 0.1 * age)
        score = m.get("importance", 3.0) * recency_boost
        scored.append({**m, "score": round(score, 2)})
    return scored


def _retrieve_relevant_memories(agent_name: str, context: str, limit: int = 5) -> list[dict]:
    memories = _mem(agent_name)
    if not memories:
        return []

    context_lower = context.lower()
    scored = []
    for m in reversed(memories):
        text = (m.get("summary", "") + " " + m.get("state_summary", "")).lower()
        overlap = sum(1 for word in context_lower.split() if len(word) > 3 and word in text)
        relevance = m.get("importance", 3.0) + overlap * 0.5
        scored.append((relevance, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:limit]]


# ── Context Builder ──

def _build_context(state: DungeonState) -> str:
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
    _dungeon_config.update(config)
    return {"status": "config_updated", "config": _dungeon_config}
