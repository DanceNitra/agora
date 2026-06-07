"""Dungeon OS — Quest API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

router = APIRouter(prefix="/api/v2/dungeon-os", tags=["dungeon-os"])


async def get_db(request: Request):
    return request.app.state.db


def get_quest_engine(request: Request):
    qe = getattr(request.app.state, "quest_engine", None)
    if not qe:
        raise HTTPException(500, "Quest engine not initialized")
    return qe


# ═══════════════════════════════════════════
# QUESTS
# ═══════════════════════════════════════════


@router.get("/quests")
async def list_quests(request: Request, status: str = None, db=Depends(get_db)):
    """List all quests, optionally filtered by status."""
    qe = get_quest_engine(request)
    if status:
        return {"quests": await qe.list_quests(status)}
    return {"quests": await qe.list_quests()}


@router.get("/quests/available")
async def get_available_quests(request: Request, db=Depends(get_db)):
    """Get quests whose dependencies are met."""
    qe = get_quest_engine(request)
    return {"quests": await qe.get_available_quests()}


@router.get("/quests/{quest_id}")
async def get_quest(quest_id: str, request: Request, db=Depends(get_db)):
    """Get a single quest by ID."""
    qe = get_quest_engine(request)
    quest = await qe.get_quest(quest_id)
    if not quest:
        raise HTTPException(404, f"Quest '{quest_id}' not found")
    return quest


@router.post("/quests/{quest_id}/assign")
async def assign_quest(quest_id: str, request: Request, body: dict, db=Depends(get_db)):
    """Assign an open quest to an agent."""
    qe = get_quest_engine(request)
    agent = body.get("agent", "")
    if not agent:
        raise HTTPException(400, "Missing 'agent' in body")
    result = await qe.assign_quest(quest_id, agent)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/submit")
async def submit_for_review(
    quest_id: str, request: Request, body: dict, db=Depends(get_db)
):
    """Submit a claimed quest for Warden verification."""
    qe = get_quest_engine(request)
    agent = body.get("agent", "")
    if not agent:
        raise HTTPException(400, "Missing 'agent' in body")
    result = await qe.submit_for_review(quest_id, agent)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/verify")
async def verify_quest(
    quest_id: str, request: Request, body: dict = None, db=Depends(get_db)
):
    """Warden verifies a quest — marks done, raises osState."""
    qe = get_quest_engine(request)
    runs = (body or {}).get("runs", 3)
    result = await qe.verify_quest(quest_id, runs=runs)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/deny")
async def deny_quest(
    quest_id: str, request: Request, body: dict, db=Depends(get_db)
):
    """Warden denies a quest review."""
    qe = get_quest_engine(request)
    reason = body.get("reason", "Criteria not met")
    fix = body.get("fix")
    result = await qe.deny_quest(quest_id, reason, fix)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/block")
async def block_quest(
    quest_id: str, request: Request, body: dict, db=Depends(get_db)
):
    """Block a quest (dependency, resource, etc.)."""
    qe = get_quest_engine(request)
    reason = body.get("reason", "")
    result = await qe.block_quest(quest_id, reason)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/unblock")
async def unblock_quest(quest_id: str, request: Request, db=Depends(get_db)):
    """Unblock a quest."""
    qe = get_quest_engine(request)
    result = await qe.unblock_quest(quest_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ═══════════════════════════════════════════
# AGENT-RELATED QUERIES
# ═══════════════════════════════════════════


@router.get("/agents/{agent_name}/quests")
async def get_agent_quests(
    agent_name: str, request: Request, db=Depends(get_db)
):
    """Get all quests assigned to a specific agent."""
    qe = get_quest_engine(request)
    return {"quests": await qe.get_agent_quests(agent_name)}


@router.get("/stats")
async def get_dungeon_os_stats(request: Request, db=Depends(get_db)):
    """Get Dungeon OS statistics — quest completions, osState, boot status."""
    qe = get_quest_engine(request)
    os_state = getattr(request.app.state, "os_state", None)

    return {
        "quests": {
            "total": len(await qe.list_quests()),
            "open": len(await qe.list_quests("open")),
            "claimed": len(await qe.list_quests("claimed")),
            "review": len(await qe.list_quests("review")),
            "done": len(await qe.list_quests("done")),
            "blocked": len(await qe.list_quests("blocked")),
            "impact": await qe.get_os_impact_summary(),
        },
        "os_state": os_state.get_stats() if os_state else None,
    }
