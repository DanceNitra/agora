"""Dungeon OS — Quest API endpoints."""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/v2/dungeon-os", tags=["dungeon-os"])


def get_qe(request: Request):
    qe = getattr(request.app.state, "quest_engine", None)
    if qe is None:
        raise HTTPException(500, "Quest engine not initialized")
    return qe


@router.get("/quests")
async def list_quests(request: Request, status: str = None):
    qe = get_qe(request)
    if status:
        return {"quests": await qe.list_quests(status)}
    return {"quests": await qe.list_quests()}


@router.get("/quests/available")
async def get_available_quests(request: Request):
    qe = get_qe(request)
    return {"quests": await qe.get_available_quests()}


@router.get("/quests/{quest_id}")
async def get_quest(quest_id: str, request: Request):
    qe = get_qe(request)
    quest = await qe.get_quest(quest_id)
    if not quest:
        raise HTTPException(404, f"Quest '{quest_id}' not found")
    return quest


@router.post("/quests/{quest_id}/assign")
async def assign_quest(quest_id: str, request: Request):
    qe = get_qe(request)
    body = await request.json()
    agent = body.get("agent", "")
    if not agent:
        raise HTTPException(400, "Missing 'agent' in body")
    result = await qe.assign_quest(quest_id, agent)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/submit")
async def submit_for_review(quest_id: str, request: Request):
    qe = get_qe(request)
    body = await request.json()
    agent = body.get("agent", "")
    if not agent:
        raise HTTPException(400, "Missing 'agent' in body")
    result = await qe.submit_for_review(quest_id, agent)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/verify")
async def verify_quest(quest_id: str, request: Request):
    qe = get_qe(request)
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    runs = body.get("runs", 3) if isinstance(body, dict) else 3
    result = await qe.verify_quest(quest_id, runs=runs)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/deny")
async def deny_quest(quest_id: str, request: Request):
    qe = get_qe(request)
    body = await request.json()
    reason = body.get("reason", "Criteria not met")
    fix = body.get("fix")
    result = await qe.deny_quest(quest_id, reason, fix)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/block")
async def block_quest(quest_id: str, request: Request):
    qe = get_qe(request)
    body = await request.json()
    reason = body.get("reason", "")
    result = await qe.block_quest(quest_id, reason)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/quests/{quest_id}/unblock")
async def unblock_quest(quest_id: str, request: Request):
    qe = get_qe(request)
    result = await qe.unblock_quest(quest_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/agents/{agent_name}/quests")
async def get_agent_quests(agent_name: str, request: Request):
    qe = get_qe(request)
    return {"quests": await qe.get_agent_quests(agent_name)}


@router.get("/stats")
async def get_dungeon_os_stats(request: Request):
    qe = get_qe(request)
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


@router.get("/verification-log/{quest_id}")
async def get_verification_log(quest_id: str, request: Request):
    """Get all Warden verification runs for a quest."""
    qe = get_qe(request)
    log = await qe.get_verification_log(quest_id)
    return {"quest_id": quest_id, "runs": log}


@router.get("/verification-stats")
async def get_verification_stats(request: Request):
    """Get aggregate Warden verification statistics."""
    qe = get_qe(request)
    return await qe.get_verification_stats()
