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
