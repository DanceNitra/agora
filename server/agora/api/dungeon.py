"""
Dungeon Agent API — Phase 3: Multi-Agent with per-agent personalities and memory.
Receives game state → calls LLM → returns action decision.
"""

import asyncio
import json
import math
import time
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agora.execution.llm_client import call_llm
from agora.execution import quest_manager

import uuid

# ── Dungeon Agent IDs (stable UUIDs for Trust Engine) ──

DUNGEON_AGENT_IDS = {
    "Kael": "00000000-0000-0000-0000-000000000001",
    "Lyra": "00000000-0000-0000-0000-000000000002",
    "Mordecai": "00000000-0000-0000-0000-000000000003",
    "Grom": "00000000-0000-0000-0000-000000000004",
    "Zara": "00000000-0000-0000-0000-000000000005",
    "Finn": "00000000-0000-0000-0000-000000000006",
    "Guard": "00000000-0000-0000-0000-000000000007",
}

DUNGEON_AGENT_ROLES = {
    "Kael": "adventurer",
    "Lyra": "scout",
    "Mordecai": "sage",
    "Grom": "blacksmith",
    "Zara": "alchemist",
    "Finn": "merchant",
    "Guard": "guard",
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

_dungeon_config: dict[str, Any] = {"llm_enabled": True, "llm_tier": "cheap"}
_announced_tasks: list[int] = []  # task IDs announced in this session

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
        f"When there are OPEN TASKS available, you can bid on them using the 'bid' action.\n"
        f"A higher bid_amount (0.0–1.0) means you want the task more.\n"
        f"If you win the bid, you will be assigned to complete the task.\n"
        f"Bid on tasks that match your skills and personality.\n\n"
        f"Respond ONLY with a valid JSON object containing:\n"
        f'{{{{"action":"move|interact|talk|cooperate|wait|use|explore|bid",'
        f'"target_x":<optional number>,"target_y":<optional number>,'
        f'"target_npc":"<optional NPC name>",'
        f'"task_id":<optional task number>,'
        f'"bid_amount":<optional 0.0-1.0>,'
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
    agent_name: str
    agent_x: float
    agent_y: float
    health: float = 100
    inventory: list[str] = []
    nearby_npcs: list[dict[str, Any]] = []
    nearby_objects: list[dict[str, Any]] = []
    recent_memories: list[str] = []
    current_objective: str = "Explore the dungeon"


class InteractRequest(BaseModel):
    player_x: int
    player_y: int
    object_name: str
    description: str = ""


@router.post("/interact")
async def dungeon_interact(req: InteractRequest, request: Request):
    """Log a workstation interaction from the game."""
    db = request.app.state.db
    await db.execute(
        "INSERT INTO logs (kind, data, created_at) VALUES (?, ?, ?)",
        ("interact", json.dumps({
            "object": req.object_name,
            "player_x": req.player_x,
            "player_y": req.player_y,
            "description": req.description,
        }), time.time())
    )
    await db.commit()
    return {"status": "ok", "object": req.object_name}


@router.post("/agent-action")
async def dungeon_agent_action(state: DungeonState, request: Request):
    """Receive game state → LLM decides action → return decision."""
    agent_name = state.agent_name
    memories = _mem(agent_name)
    db = request.app.state.db

    # Ensure dungeon agents exist in DB for trust tracking
    await _ensure_dungeon_agents_seeded(request)

    # Auto-assign quests if not yet assigned
    await quest_manager.auto_assign_quests(db)

    # Build context with relevant past memories
    context = _build_context(state)
    relevant = _retrieve_relevant_memories(agent_name, context, limit=5)
    if relevant:
        mem_text = "\n".join(f"- {m['summary']}" for m in relevant)
        context += f"\n\nYour memories:\n{mem_text}"

    # Inject quest context (active quest info drives NPC behavior)
    context, active_quest = await quest_manager.inject_quest_context(db, agent_name, context)

    # ── Inject system events as "Dungeon Rumors" ──
    try:
        cursor = await db.execute(
            "SELECT event_type, source_id, payload, occurred_at FROM events "
            "ORDER BY id DESC LIMIT 5"
        )
        recent_events = await cursor.fetchall()
        if recent_events:
            rumor_lines = ["\n\n══ Dungeon Rumors (recent system activity) ══"]
            for ev in recent_events:
                try:
                    p = json.loads(ev["payload"])
                except (json.JSONDecodeError, TypeError):
                    p = {}
                event_type = ev["event_type"]
                src = ev["source_id"][:8] if ev["source_id"] else "?"
                if event_type == "agent_died":
                    rumor_lines.append(f"  💀 Rumor: An agent ({p.get('role','?')}) was lost in the depths.")
                elif event_type == "agent_reborn":
                    rumor_lines.append(f"  ✨ Rumor: A fallen agent ({p.get('role','?')}) has returned, changed.")
                elif event_type == "agent_culled":
                    rumor_lines.append(f"  ⚠️ Rumor: A low-trust agent ({p.get('role','?')}) was banished.")
                elif event_type == "epoch_advanced":
                    rumor_lines.append(f"  📯 Rumor: A new age (epoch {p.get('epoch')}) has begun in the dungeon.")
                elif event_type == "epoch_end":
                    rumor_lines.append(f"  📜 Rumor: An age ended — {p.get('tasks_completed',0)} tasks done, {p.get('artifacts_created',0)} artifacts found.")
                elif event_type == "task_completed":
                    rumor_lines.append(f"  ✅ Rumor: Someone completed \"{p.get('title','?')}\" and was rewarded.")
                else:
                    rumor_lines.append(f"  📡 Rumor: {event_type} — {src}")
            context += "\n".join(rumor_lines)
    except Exception:
        pass  # events not available

    # ── Inject recent artifact discoveries ──
    try:
        cursor = await db.execute(
            "SELECT title, artifact_type, substr(content,1,80) as snippet "
            "FROM artifacts WHERE content IS NOT NULL AND content != '' "
            "ORDER BY id DESC LIMIT 3"
        )
        recent_arts = await cursor.fetchall()
        if recent_arts:
            art_lines = ["\n══ Recent Discoveries (artifacts found) ══"]
            for art in recent_arts:
                snippet = (art["snippet"] or "").strip()[:60]
                art_lines.append(f"  📄 \"{art['title']}\" — {snippet}..." if snippet else f"  📄 \"{art['title']}\"")
            context += "\n".join(art_lines)
    except Exception:
        pass  # artifacts table not available

    # ── Inject system agent activity summary ──
    try:
        cursor = await db.execute(
            "SELECT role, COUNT(*) as cnt, ROUND(AVG(trust_score),2) as avg_trust, "
            "ROUND(AVG(energy_balance),0) as avg_energy "
            "FROM agent_identities WHERE status='active' AND agent_id NOT LIKE '00000000%' "
            "GROUP BY role"
        )
        sys_agents = await cursor.fetchall()
        if sys_agents:
            sys_lines = ["\n══ System Activity (beyond the dungeon) ══"]
            for sa in sys_agents:
                sys_lines.append(f"  🏛️ The {sa['role']}s ({sa['cnt']}) — trust {sa['avg_trust']}, energy {sa['avg_energy']}")
            context += "\n".join(sys_lines)
    except Exception:
        pass

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

    # Add open tasks (Contract Net bidding) — highlight NPC-specific tasks
    try:
        db = request.app.state.db
        cursor = await db.execute(
            "SELECT id, title, description, priority, metadata "
            "FROM tasks WHERE status='bidding' ORDER BY priority DESC LIMIT 5"
        )
        open_tasks = await cursor.fetchall()
        if open_tasks:
            task_lines = ["\n══ OPEN TASKS available for bidding ══"]
            for t in open_tasks:
                meta = json.loads(t["metadata"] or "{}")
                assigned_npc = meta.get("assigned_npc", "")
                # Highlight tasks meant for this NPC
                is_for_me = assigned_npc == agent_name
                prefix = "  ▶ " if is_for_me else "  • "
                npc_tag = f" [for {assigned_npc}]" if assigned_npc else ""
                task_lines.append(
                    f"{prefix}#{t['id']}: \"{t['title']}\" "
                    f"(dif={meta.get('difficulty', 1)}, "
                    f"reward={meta.get('reward_energy', 10)} energy){npc_tag}"
                )
                if is_for_me:
                    task_lines.append(f"     ← This task is meant for you, {agent_name}!")
            task_lines.append(
                "\nTo bid, respond with: {\"action\": \"bid\", \"task_id\": <#>, "
                "\"bid_amount\": <0.0-1.0>, \"message\": \"I want this task!\"}"
            )
            context += "\n" + "\n".join(task_lines)
    except Exception:
        pass  # tasks not available

    # Call LLM
    cfg = _dungeon_config
    use_llm = cfg.get("llm_enabled", False)

    if use_llm:
        raw = await asyncio.to_thread(
            call_llm,
            system_prompt=_get_prompt(agent_name),
            user_prompt=context,
            tier=cfg.get("llm_tier", "cheap"),
            temperature=0.8,
            max_tokens=1000,
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

    # Handle bid action (Contract Net)
    if decision.get("action") == "bid":
        task_id = decision.get("task_id")
        bid_amount = decision.get("bid_amount", 0.5)
        if task_id:
            try:
                bid_body = BidSubmission(
                    agent_name=agent_name,
                    task_id=int(task_id),
                    bid_amount=float(max(0.0, min(1.0, bid_amount))),
                    bid_reason=str(decision.get("message", "I want this task!")),
                )
                await submit_bid(bid_body, request)
                decision["message"] = f"I bid {bid_amount:.1f} on task #{task_id}."
            except Exception:
                pass  # bid failed silently

    # Check quest progress (did this action complete a quest step?)
    # First: override decision if NPC isn't progressing their quest
    decision, overridden = await quest_manager.override_decision_for_quest(
        db, agent_name, decision, (state.agent_x, state.agent_y)
    )
    
    npc_positions = {a: (0, 0) for a in ("Kael", "Lyra", "Mordecai")}
    npc_positions[agent_name] = (state.agent_x, state.agent_y)
    quest_update = await quest_manager.check_quest_progress(db, agent_name, decision, npc_positions)
    if quest_update:
        decision["_quest"] = quest_update
        # Add quest completion message to speech
        msg = quest_update.get("message", "")
        if msg:
            decision["message"] = f"{decision.get('message', '')} | {msg}"
            next_q = quest_update.get("next_quest")
            if next_q:
                decision["message"] += f" | Next: {next_q.replace('_', ' ').title()}"

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


# ── Contract Net (Q3.4) ──


class TaskAnnouncement(BaseModel):
    title: str
    description: str = ""
    difficulty: int = 1
    reward_energy: int = 10
    task_type: str = "exploration"
    announced_by: str = "orchestrator"


class BidSubmission(BaseModel):
    agent_name: str
    task_id: int
    bid_amount: float = 0.5  # 0.0–1.0
    bid_reason: str = ""


@router.post("/announce-task")
async def announce_task(body: TaskAnnouncement, request: Request):
    """Announce a new task for dungeon agents to bid on (Contract Net)."""
    db = request.app.state.db
    metadata = json.dumps({
        "difficulty": body.difficulty,
        "reward_energy": body.reward_energy,
        "task_type": body.task_type,
        "announced_by": body.announced_by,
    })
    cursor = await db.execute(
        "INSERT INTO tasks (title, description, status, priority, metadata, assignee_id) "
        "VALUES (?, ?, 'bidding', ?, ?, NULL)",
        (body.title, body.description, body.difficulty, metadata),
    )
    await db.commit()
    task_id = cursor.lastrowid
    _announced_tasks.append(task_id)
    return {
        "status": "task_announced",
        "task_id": task_id,
        "title": body.title,
        "description": body.description,
        "difficulty": body.difficulty,
        "reward_energy": body.reward_energy,
        "task_type": body.task_type,
        "bidding_open": True,
    }


@router.post("/bid")
async def submit_bid(body: BidSubmission, request: Request):
    """Submit a bid from a dungeon agent on an open task."""
    db = request.app.state.db

    # Check task exists and is in bidding state
    cursor = await db.execute(
        "SELECT id, status, assignee_id FROM tasks WHERE id=?", (body.task_id,)
    )
    task = await cursor.fetchone()
    if not task:
        return {"status": "error", "error": "task_not_found"}
    if task["status"] != "bidding":
        return {"status": "error", "error": f"task_not_bidding (status={task['status']})"}

    # Look up agent_id from name
    agent_id = DUNGEON_AGENT_IDS.get(body.agent_name)
    if not agent_id:
        return {"status": "error", "error": "unknown_agent"}

    # Upsert bid
    try:
        cursor = await db.execute(
            "INSERT INTO task_bids (task_id, agent_id, bid_amount, bid_reason) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(task_id, agent_id) DO UPDATE SET "
            "bid_amount=excluded.bid_amount, bid_reason=excluded.bid_reason, status='pending'",
            (body.task_id, agent_id, max(0.0, min(1.0, body.bid_amount)), body.bid_reason),
        )
        await db.commit()
    except Exception as e:
        return {"status": "error", "error": str(e)}

    return {
        "status": "bid_recorded",
        "agent_name": body.agent_name,
        "task_id": body.task_id,
        "bid_amount": body.bid_amount,
        "bid_reason": body.bid_reason,
    }


@router.post("/assign-best/{task_id}")
async def assign_task_best_bidder(task_id: int, request: Request):
    """Assign a task to the agent with the highest bid (lowest = best if competitive)."""
    db = request.app.state.db

    # Check task
    cursor = await db.execute(
        "SELECT id, status, assignee_id FROM tasks WHERE id=?", (task_id,)
    )
    task = await cursor.fetchone()
    if not task:
        return {"status": "error", "error": "task_not_found"}
    if task["status"] != "bidding":
        return {"status": "error", "error": f"task_not_bidding (status={task['status']})"}

    # Find best bid (highest bid_amount)
    cursor = await db.execute(
        "SELECT tb.id, tb.agent_id, tb.bid_amount, tb.bid_reason, ai.role "
        "FROM task_bids tb "
        "JOIN agent_identities ai ON tb.agent_id = ai.agent_id "
        "WHERE tb.task_id=? AND tb.status='pending' "
        "ORDER BY tb.bid_amount DESC LIMIT 1",
        (task_id,),
    )
    best_bid = await cursor.fetchone()
    if not best_bid:
        return {"status": "error", "error": "no_bids"}

    # Accept this bid, reject others
    await db.execute(
        "UPDATE task_bids SET status='accepted' WHERE task_id=? AND agent_id=?",
        (task_id, best_bid["agent_id"]),
    )
    await db.execute(
        "UPDATE task_bids SET status='rejected' WHERE task_id=? AND agent_id!=?",
        (task_id, best_bid["agent_id"]),
    )
    # Assign task
    await db.execute(
        "UPDATE tasks SET status='assigned', assignee_id=?, updated_at=datetime('now') WHERE id=?",
        (best_bid["agent_id"], task_id),
    )
    await db.commit()

    # Map agent_id back to name
    winner_name = "unknown"
    for name, aid in DUNGEON_AGENT_IDS.items():
        if aid == best_bid["agent_id"]:
            winner_name = name
            break

    return {
        "status": "task_assigned",
        "task_id": task_id,
        "winner": winner_name,
        "winner_role": best_bid["role"],
        "bid_amount": best_bid["bid_amount"],
        "bid_reason": best_bid["bid_reason"],
    }


@router.get("/tasks")
async def list_dungeon_tasks(request: Request):
    """List open tasks visible to dungeon agents, with bids."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT id, title, description, status, priority, assignee_id, metadata, created_at "
        "FROM tasks WHERE status IN ('bidding', 'assigned') "
        "ORDER BY priority DESC, created_at ASC"
    )
    rows = await cursor.fetchall()

    tasks = []
    for row in rows:
        task_id = row["id"]
        meta = json.loads(row["metadata"] or "{}")
        task_info = {
            "id": task_id,
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "difficulty": meta.get("difficulty", 1),
            "reward_energy": meta.get("reward_energy", 10),
            "task_type": meta.get("task_type", "exploration"),
        }

        # Get bids for this task
        bid_cursor = await db.execute(
            "SELECT tb.bid_amount, tb.bid_reason, ai.agent_id "
            "FROM task_bids tb "
            "JOIN agent_identities ai ON tb.agent_id = ai.agent_id "
            "WHERE tb.task_id=? AND tb.status='pending'",
            (task_id,),
        )
        bids = await bid_cursor.fetchall()
        task_info["bids"] = [
            {
                "agent_name": next((n for n, a in DUNGEON_AGENT_IDS.items() if a == b["agent_id"]), b["agent_id"]),
                "bid_amount": b["bid_amount"],
                "bid_reason": b["bid_reason"],
            }
            for b in bids
        ]

        # If assigned, show assignee
        if row["status"] == "assigned" and row["assignee_id"]:
            task_info["assignee"] = next(
                (n for n, a in DUNGEON_AGENT_IDS.items() if a == row["assignee_id"]),
                row["assignee_id"],
            )

        tasks.append(task_info)

    return {"tasks": tasks, "total": len(tasks)}


@router.post("/tasks")
async def create_dungeon_task(body: TaskAnnouncement, request: Request):
    """Convenience: announce + return task info visible to dungeon agents."""
    result = await announce_task(body, request)
    if result.get("status") != "task_announced":
        return result
    return await list_dungeon_tasks(request)


# ── God Console Endpoints (Q3.5) ──


class SpawnRequest(BaseModel):
    agent_name: str
    role: str = "explorer"
    agent_x: float = 10
    agent_y: float = 10


@router.post("/spawn-agent")
async def spawn_agent(body: SpawnRequest, request: Request):
    """Dynamically spawn a new dungeon agent (from God Console !spawn)."""
    await _ensure_dungeon_agents_seeded(request)

    # Generate stable UUID for this new agent
    agent_id = str(uuid.uuid4())
    name = body.agent_name

    # Add to dungeon agent tracking
    DUNGEON_AGENT_IDS[name] = agent_id
    DUNGEON_AGENT_ROLES[name] = body.role

    # Create in DB
    db = request.app.state.db
    genome = json.dumps({
        "role": body.role,
        "tools": ["move", "talk", "interact"],
        "dungeon_agent": True,
        "spawned_via": "god_console",
        "personality_traits": {"curiosity": 0.7, "cooperativeness": 0.6},
    })
    await db.execute(
        "INSERT INTO agent_identities (agent_id, public_key, generation, genome, trust_score, energy_balance, role, status) "
        "VALUES (?, ?, 0, ?, 0.5, 100, ?, 'active')",
        (agent_id, f"dungeon_{name.lower()}", genome, body.role),
    )
    await db.commit()

    # Color based on role
    color_map = {
        "warrior": 0xff4444, "explorer": 0xffaa44, "mage": 0xaa44ff,
        "healer": 0x44ffaa, "rogue": 0x888888, "ranger": 0x44dd44,
    }
    color = color_map.get(body.role, 0xaaaaaa)

    return {
        "status": "spawned",
        "agent_name": name,
        "agent_id": agent_id,
        "role": body.role,
        "position": {"x": body.agent_x, "y": body.agent_y},
        "color": color,
        "energy_balance": 100,
        "trust_score": 0.5,
    }


class RewardRequest(BaseModel):
    agent_name: str
    amount: float = 10


@router.post("/reward-agent")
async def reward_agent(body: RewardRequest, request: Request):
    """Reward an agent with energy (from God Console !reward)."""
    agent_id = DUNGEON_AGENT_IDS.get(body.agent_name)
    if not agent_id:
        return {"status": "error", "error": "unknown_agent"}

    db = request.app.state.db
    await db.execute(
        "UPDATE agent_identities SET energy_balance = energy_balance + ?, updated_at = datetime('now') "
        "WHERE agent_id=?",
        (body.amount, agent_id),
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT energy_balance, trust_score FROM agent_identities WHERE agent_id=?",
        (agent_id,),
    )
    row = await cursor.fetchone()
    return {
        "status": "rewarded",
        "agent_name": body.agent_name,
        "reward_amount": body.amount,
        "new_energy_balance": row["energy_balance"] if row else "?",
        "trust_score": row["trust_score"] if row else "?",
    }
