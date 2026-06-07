"""Dungeon OS — Quest API endpoints."""

import os

from fastapi import APIRouter, HTTPException, Request

from agora.dungeon_os.agent_worker import AgentWorker

router = APIRouter(prefix="/api/v2/dungeon-os", tags=["dungeon-os"])


def get_qe(request: Request):
    qe = getattr(request.app.state, "quest_engine", None)
    if qe is None:
        raise HTTPException(500, "Quest engine not initialized")
    return qe


def get_worker(request: Request):
    """Get or create the AgentWorker."""
    worker = getattr(request.app.state, "agent_worker", None)
    if worker is None:
        qe = get_qe(request)
        os_state = getattr(request.app.state, "os_state", None)
        db = getattr(request.app.state, "db", None)
        config = {
            "quest_engine": qe,
            "os_state": os_state,
            "log_dir": "/tmp/hermes-logs",
            "vault_path": os.path.expanduser("~/Obsidian Vault"),
            "telegram_chat_id": os.getenv("HERMES_TELEGRAM_CHAT_ID"),
            "telegram_bot_token": os.getenv("HERMES_TELEGRAM_BOT_TOKEN"),
        }
        worker = AgentWorker(qe, db, config)
        request.app.state.agent_worker = worker
    return worker


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


@router.post("/quests/create")
async def create_quest_new(request: Request):
    """Create a new quest from external stimulus (Orchestrator command)."""
    qe = get_qe(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")
    
    quest_id = body.get("id", "").strip()
    title = body.get("title", "").strip()
    goal = body.get("goal", "").strip()
    subsystem = body.get("subsystem", "").strip()
    success_criteria = body.get("success_criteria", [])
    reward = body.get("reward", 30)
    depends_on = body.get("depends_on", [])

    if not quest_id or not title or not goal or not subsystem:
        raise HTTPException(400, "Missing required fields: id, title, goal, subsystem")
    if not success_criteria or not isinstance(success_criteria, list):
        raise HTTPException(400, "success_criteria must be a non-empty list")

    result = await qe.create_quest(
        quest_id=quest_id,
        title=title,
        goal=goal,
        subsystem=subsystem,
        success_criteria=success_criteria,
        reward=reward,
        depends_on=depends_on,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


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


# ═══════════════════════════════════════════
# STIMULUS ENGINE — external event injection
# ═══════════════════════════════════════════

@router.post("/stimulus")
async def inject_stimulus(request: Request):
    """Inject an external stimulus → auto-creates a quest."""
    from agora.dungeon_os.stimulus import StimulusEngine
    qe = get_qe(request)
    os_state = getattr(request.app.state, "os_state", None)
    db = getattr(request.app.state, "db", None)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    engine = StimulusEngine(qe, os_state, db)
    result = await engine.inject_stimulus(
        stimulus_type=body.get("type", "alert"),
        source=body.get("source", "api"),
        title=body.get("title", "External stimulus"),
        description=body.get("description", ""),
        subsystem=body.get("subsystem", "knowledge"),
        priority=body.get("priority", 5),
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/stimulus/health")
async def trigger_health_check(request: Request):
    """Trigger a scheduled health check → creates maintenance quests."""
    from agora.dungeon_os.stimulus import StimulusEngine
    qe = get_qe(request)
    os_state = getattr(request.app.state, "os_state", None)
    db = getattr(request.app.state, "db", None)

    engine = StimulusEngine(qe, os_state, db)
    result = await engine.inject_health_stimulus()
    return result


@router.post("/stimulus/watch/{directory:path}")
async def watch_directory(directory: str, request: Request):
    """Set a directory to watch for new files → auto-quests."""
    from agora.dungeon_os.stimulus import StimulusEngine
    qe = get_qe(request)
    os_state = getattr(request.app.state, "os_state", None)
    db = getattr(request.app.state, "db", None)

    engine = StimulusEngine(qe, os_state, db)
    await engine.set_watch_dir(f"/{directory}")
    request.app.state.stimulus_engine = engine
    return {"status": "watching", "directory": f"/{directory}"}


@router.post("/stimulus/poll")
async def poll_watch_dir(request: Request):
    """Poll the watch directory for new files."""
    from agora.dungeon_os.stimulus import get_stimulus_engine
    engine = await get_stimulus_engine(request)
    if not engine:
        raise HTTPException(400, "No stimulus engine initialized")
    new_quests = await engine.poll_watch_dir()
    return {"new_quests": len(new_quests), "quests": new_quests}


# ═══════════════════════════════════════════
# AGENT WORKER — quest-driven NPC tick
# ═══════════════════════════════════════════

@router.post("/tick")
async def run_worker_tick(request: Request):
    """Run one agent worker tick — NPCs work on claimed quests."""
    worker = get_worker(request)
    result = await worker.tick()
    return result


@router.get("/worker/stats")
async def get_worker_stats(request: Request):
    """Get agent worker statistics."""
    worker = get_worker(request)
    return worker.get_stats()
