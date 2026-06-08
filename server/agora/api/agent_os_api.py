"""Agent OS API — soul, brain, body, abilities, skills, help requests."""
from fastapi import APIRouter, Request, HTTPException

from agora.api.dungeon import DUNGEON_AGENT_IDS

# UUID → name reverse lookup
UUID_TO_NAME = {v: k for k, v in DUNGEON_AGENT_IDS.items()}

router = APIRouter(prefix="/api/v1/agent-os", tags=["agent-os"])


def get_os(request: Request):
    return request.app.state.agent_os


@router.get("/{npc_name}")
async def get_agent_os(npc_name: str, request: Request):
    """Get full OS status for an NPC by name or UUID."""
    # Resolve name to UUID
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name

    os_engine = get_os(request)
    status = await os_engine.get_full_status(npc_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"NPC {npc_name} not found")
    return status


@router.get("/{npc_name}/soul")
async def get_agent_soul(npc_name: str, request: Request):
    """Get soul status for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM agent_soul WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"NPC {npc_name} not found")
    return dict(row)


@router.get("/{npc_name}/brain")
async def get_agent_brain(npc_name: str, request: Request):
    """Get brain status for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM agent_brain WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"NPC {npc_name} not found")
    return dict(row)


@router.get("/{npc_name}/body")
async def get_agent_body(npc_name: str, request: Request):
    """Get body status for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM agent_body WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"NPC {npc_name} not found")
    return dict(row)


@router.get("/{npc_name}/abilities")
async def get_agent_abilities(npc_name: str, request: Request):
    """Get abilities for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT ability_name, description, power_level, is_passive FROM agent_abilities "
        "WHERE npc_id=? ORDER BY power_level DESC",
        (npc_id,),
    )
    abilities = [dict(r) for r in await cursor.fetchall()]
    return {"abilities": abilities, "total": len(abilities)}


@router.get("/{npc_name}/skills")
async def get_agent_skills(npc_name: str, request: Request):
    """Get skills for an NPC."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT skill_name, level, xp, xp_to_next, last_used_at FROM agent_skills "
        "WHERE npc_id=? ORDER BY level DESC",
        (npc_id,),
    )
    skills = [dict(r) for r in await cursor.fetchall()]
    return {"skills": skills, "total": len(skills)}


@router.get("/{npc_name}/help-requests")
async def get_agent_help_requests(npc_name: str, request: Request, status: str | None = None):
    """Get help requests for an NPC (as requester or helper)."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db

    where_extra = ""
    params = [npc_id, npc_id]
    if status:
        where_extra = " AND hr.status=?"
        params.append(status)

    cursor = await db.execute(
        f"SELECT hr.*, r.npc_name as requester_name, h.npc_name as helper_name "
        f"FROM agent_help_requests hr "
        f"JOIN dungeon_npcs r ON r.npc_id = hr.requester_id "
        f"JOIN dungeon_npcs h ON h.npc_id = hr.helper_id "
        f"WHERE (hr.requester_id=? OR hr.helper_id=?){where_extra} "
        f"ORDER BY hr.created_at DESC LIMIT 20",
        params,
    )
    requests = [dict(r) for r in await cursor.fetchall()]
    return {"help_requests": requests, "total": len(requests)}


@router.get("/help-matrix")
async def get_help_matrix():
    """Get the help-seeking matrix (who helps with what)."""
    from agora.agent_os.agent_os import HELP_MATRIX
    return {"matrix": HELP_MATRIX}


# ═══════════════════════════════════════════════════════════════
# Agentic OS v2 (Phase 2.0) — Brain Ecosystem observability
# Per-agent paths are 2-segment (safe from the /{npc_name} catch-all);
# global paths are namespaced under /brain/ to avoid that collision.
# ═══════════════════════════════════════════════════════════════

@router.get("/{npc_name}/memories")
async def get_memories(npc_name: str, request: Request, memory_type: str = None,
                       limit: int = 20):
    """List an agent's memories (optionally filter by type)."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    db = request.app.state.db
    q = "SELECT memory_type, content, importance, emotional_tag, source, " \
        "related_npc_id, decay_factor, created_at FROM agent_memories WHERE npc_id=?"
    params = [npc_id]
    if memory_type:
        q += " AND memory_type=?"
        params.append(memory_type)
    q += " ORDER BY importance DESC, created_at DESC LIMIT ?"
    params.append(limit)
    cursor = await db.execute(q, params)
    return {"npc": npc_name, "memories": [dict(r) for r in await cursor.fetchall()]}


@router.get("/{npc_name}/memories/recall")
async def recall_memories(npc_name: str, request: Request, q: str = "", limit: int = 5):
    """Recall the most relevant memories for a query (importance+keyword+recency)."""
    from agora.agent_os.memory_agent import MemoryAgent
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    mem = MemoryAgent(request.app.state.db, npc_id)
    return {"npc": npc_name, "query": q, "memories": await mem.recall(q, limit=limit)}


@router.get("/{npc_name}/thoughts")
async def get_thoughts(npc_name: str, request: Request, limit: int = 20):
    """Get an agent's thought journal (reasoning log)."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    cursor = await request.app.state.db.execute(
        "SELECT thought_type, content, context, importance, created_at "
        "FROM agent_thoughts WHERE npc_id=? ORDER BY created_at DESC LIMIT ?",
        (npc_id, limit))
    return {"npc": npc_name, "thoughts": [dict(r) for r in await cursor.fetchall()]}


@router.get("/brain/collective")
async def query_collective(request: Request, q: str = "", limit: int = 20):
    """Query the collective knowledge pool (the dungeon vault)."""
    db = request.app.state.db
    if q:
        os_engine = get_os(request)
        return {"query": q, "knowledge": await os_engine._query_collective(q, limit=limit)}
    cursor = await db.execute(
        "SELECT title, content, contributor_name, knowledge_type, confidence, "
        "verification_count, created_at FROM collective_knowledge "
        "ORDER BY created_at DESC LIMIT ?", (limit,))
    return {"knowledge": [dict(r) for r in await cursor.fetchall()]}


@router.post("/brain/collective")
async def add_collective(request: Request):
    """Add an entry to the collective knowledge pool."""
    body = await request.json()
    for f in ("npc", "title", "content"):
        if not body.get(f):
            raise HTTPException(400, f"Missing field: {f}")
    npc_id = DUNGEON_AGENT_IDS.get(body["npc"]) or body["npc"]
    os_engine = get_os(request)
    await os_engine._contribute_to_collective(
        npc_id, body["title"], body["content"],
        body.get("knowledge_type", "observation"))
    return {"status": "added", "title": body["title"]}


@router.get("/brain/brainstorm")
async def list_brainstorm(request: Request, limit: int = 10):
    """Recent brainstorm sessions with their top idea."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT session_id, topic, status, created_at FROM agent_brainstorm_sessions "
        "ORDER BY created_at DESC LIMIT ?", (limit,))
    sessions = []
    for s in await cursor.fetchall():
        s = dict(s)
        ic = await db.execute(
            "SELECT bi.idea_content, bi.votes, d.npc_name FROM agent_brainstorm_ideas bi "
            "LEFT JOIN dungeon_npcs d ON d.npc_id=bi.npc_id "
            "WHERE bi.session_id=? ORDER BY bi.votes DESC, bi.impact_score DESC LIMIT 1",
            (s["session_id"],))
        top = await ic.fetchone()
        s["top_idea"] = dict(top) if top else None
        sessions.append(s)
    return {"sessions": sessions}


@router.get("/brain/upgrades")
async def list_upgrades(request: Request, limit: int = 20):
    """List agent-proposed system upgrades."""
    cursor = await request.app.state.db.execute(
        "SELECT proposer_name, title, description, upgrade_type, impact_estimate, "
        "effort_estimate, status, vote_count, created_at FROM system_upgrade_proposals "
        "ORDER BY created_at DESC LIMIT ?", (limit,))
    return {"proposals": [dict(r) for r in await cursor.fetchall()]}


@router.get("/brain/emotional-state")
async def emotional_state(request: Request):
    """Mood map of all agents + their dominant emotional memory tags."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT d.npc_name, s.mood FROM dungeon_npcs d "
        "LEFT JOIN agent_soul s ON s.npc_id=d.npc_id WHERE d.status='active'")
    agents = []
    for r in await cursor.fetchall():
        r = dict(r)
        agents.append({"name": r["npc_name"],
                       "mood": round(r["mood"], 3) if r["mood"] is not None else None})
    return {"agents": agents}


@router.post("/reflect/{npc_name}")
async def reflect(npc_name: str, request: Request):
    """Trigger an agent to reflect and propose a system upgrade."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    os_engine = get_os(request)
    await os_engine._propose_upgrade(npc_id)
    return {"status": "reflected", "npc": npc_name}


@router.get("/{npc_name}/conversations")
async def get_conversations(npc_name: str, request: Request, limit: int = 20):
    """Get an agent's recent conversation turns (as speaker or target)."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    cursor = await request.app.state.db.execute(
        "SELECT session_id, speaker_name, target_name, message, intent, turn_number, created_at "
        "FROM agent_conversations WHERE speaker_id=? OR target_id=? "
        "ORDER BY created_at DESC LIMIT ?", (npc_id, npc_id, limit))
    return {"npc": npc_name, "turns": [dict(r) for r in await cursor.fetchall()]}


@router.post("/{npc_name}/converse")
async def start_converse(npc_name: str, request: Request):
    """Start a conversation from this agent to another. Body: {target, topic, intent?}."""
    body = await request.json()
    if not body.get("target") or not body.get("topic"):
        raise HTTPException(400, "Missing field: target and/or topic")
    speaker_id = DUNGEON_AGENT_IDS.get(npc_name) or npc_name
    target_id = DUNGEON_AGENT_IDS.get(body["target"]) or body["target"]
    os_engine = get_os(request)
    session_id = await os_engine._start_conversation(
        speaker_id, target_id, body["topic"], intent=body.get("intent", "chat"))
    return {"status": "started", "session_id": session_id}
