"""God Console 2.0 API — rozšírené endpointy pre admin dashboard.

Poskytuje:
  - Agent Management: NPC list s OS statmi, pause/resume/inspect
  - Byzantine Violations: live feed z LifecycleHooks
  - Agent OS Monitoring: deep dive do NPC brains, bodies, souls
  - Controller Stats: room priorities, tick timing, multiprocessing
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v2/god", tags=["god-console-2"])


async def get_db(request: Request):
    return request.app.state.db


# ═══════════════════════════════════════════
# 1. AGENT MANAGEMENT — All NPCs with OS stats
# ═══════════════════════════════════════════

@router.get("/npcs")
async def list_all_npcs(request: Request, db=Depends(get_db)):
    """List all NPCs with Agent OS stats (body, brain, soul)."""
    cursor = await db.execute("""
        SELECT
            d.npc_id, d.npc_name, d.role, d.health, d.status, d.pos_x, d.pos_y,
            b.stamina, b.hunger, b.fatigue,
            br.state_of_mind, br.current_goal, br.plan_stack,
            so.personality, so.archetype, so.emotional_state
        FROM dungeon_npcs d
        LEFT JOIN agent_body b ON b.npc_id = d.npc_id
        LEFT JOIN agent_brain br ON br.npc_id = d.npc_id
        LEFT JOIN agent_soul so ON so.npc_id = d.npc_id
        ORDER BY d.status, d.npc_name
    """)
    rows = await cursor.fetchall()
    return {"npcs": [dict(r) for r in rows], "count": len(rows)}


@router.get("/npcs/{npc_id}/detail")
async def get_npc_detail(npc_id: str, request: Request, db=Depends(get_db)):
    """Deep detail for one NPC — body, brain, soul, abilities, skills, inventory."""
    # NPC core
    cursor = await db.execute(
        "SELECT * FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
    )
    npc = await cursor.fetchone()
    if not npc:
        raise HTTPException(404, "NPC not found")

    # Body
    cursor = await db.execute(
        "SELECT * FROM agent_body WHERE npc_id=?", (npc_id,)
    )
    body = await cursor.fetchone()

    # Brain
    cursor = await db.execute(
        "SELECT * FROM agent_brain WHERE npc_id=?", (npc_id,)
    )
    brain = await cursor.fetchone()

    # Soul
    cursor = await db.execute(
        "SELECT * FROM agent_soul WHERE npc_id=?", (npc_id,)
    )
    soul = await cursor.fetchone()
    # Map soul columns to human-readable names if needed
    soul_data = dict(soul) if soul else None

    # Abilities
    cursor = await db.execute(
        "SELECT * FROM agent_abilities WHERE npc_id=?", (npc_id,)
    )
    abilities = await cursor.fetchall()

    # Skills
    cursor = await db.execute(
        "SELECT * FROM agent_skills WHERE npc_id=?", (npc_id,)
    )
    skills = await cursor.fetchall()

    # Memories (from state_store or legacy brain)
    memories = []
    if hasattr(request.app.state, "state_store") and request.app.state.state_store:
        try:
            ss = request.app.state.state_store
            brain_data = await ss.get_brain(npc_id)
            if brain_data:
                raw = brain_data.get("memory", "[]")
                if isinstance(raw, str):
                    memories = json.loads(raw)
                else:
                    memories = raw
        except Exception:
            pass

    # Inventory
    cursor = await db.execute(
        """SELECT r.name, i.quantity, i.resource_id
           FROM agent_inventory i
           JOIN resources r ON r.id = i.resource_id
           WHERE i.agent_id=?""",
        (npc_id,),
    )
    inventory = await cursor.fetchall()

    return {
        "npc": dict(npc),
        "body": dict(body) if body else None,
        "brain": dict(brain) if brain else None,
        "soul": soul_data,
        "abilities": [dict(a) for a in abilities],
        "skills": [dict(s) for s in skills],
        "memories": memories[-10:],  # last 10
        "inventory": [dict(i) for i in inventory],
    }


@router.post("/npcs/{npc_id}/pause")
async def pause_npc(npc_id: str, request: Request, db=Depends(get_db)):
    """Pause an NPC (set status to 'paused')."""
    cursor = await db.execute(
        "SELECT status FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
    )
    if not await cursor.fetchone():
        raise HTTPException(404, "NPC not found")
    await db.execute(
        "UPDATE dungeon_npcs SET status='paused' WHERE npc_id=?", (npc_id,)
    )
    await db.commit()
    return {"status": "paused", "npc_id": npc_id}


@router.post("/npcs/{npc_id}/resume")
async def resume_npc(npc_id: str, request: Request, db=Depends(get_db)):
    """Resume an NPC (set status to 'active')."""
    cursor = await db.execute(
        "SELECT status FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
    )
    if not await cursor.fetchone():
        raise HTTPException(404, "NPC not found")
    await db.execute(
        "UPDATE dungeon_npcs SET status='active' WHERE npc_id=?", (npc_id,)
    )
    await db.commit()
    return {"status": "active", "npc_id": npc_id}


# ═══════════════════════════════════════════
# 2. BYZANTINE VIOLATIONS
# ═══════════════════════════════════════════

@router.get("/violations")
async def get_byzantine_violations(request: Request, db=Depends(get_db)):
    """Get recent Byzantine violations from LifecycleHooks.

    Violations sú ukladané do DB pri každej detekcii.
    Fallback: čítame z events tabuľky.
    """
    try:
        cursor = await db.execute("""
            SELECT * FROM events
            WHERE event_type LIKE '%byzantine%' OR event_type LIKE '%violation%'
            ORDER BY created_at DESC LIMIT 100
        """)
        rows = await cursor.fetchall()
        return {"violations": [dict(r) for r in rows], "count": len(rows)}
    except Exception:
        pass

    # Fallback: in-memory violation cache
    violations = []
    hooks = getattr(request.app.state, "lifecycle_hooks", None)
    if hooks:
        violations = getattr(hooks, "_violations", [])
    return {"violations": violations[-100:], "count": len(violations)}


# ═══════════════════════════════════════════
# 3. AGENT OS MONITORING — status summary
# ═══════════════════════════════════════════

@router.get("/agent-os/summary")
async def get_agent_os_summary(request: Request, db=Depends(get_db)):
    """Summary of all Agent OS states — state_of_mind distribution, health stats."""
    cursor = await db.execute("""
        SELECT
            br.state_of_mind,
            COUNT(*) as count,
            ROUND(AVG(d.health), 1) as avg_health,
            ROUND(AVG(b.stamina), 1) as avg_stamina,
            ROUND(AVG(b.hunger), 1) as avg_hunger,
            ROUND(AVG(b.fatigue), 1) as avg_fatigue
        FROM agent_brain br
        JOIN dungeon_npcs d ON d.npc_id = br.npc_id
        LEFT JOIN agent_body b ON b.npc_id = br.npc_id
        WHERE d.status = 'active'
        GROUP BY br.state_of_mind
        ORDER BY count DESC
    """)
    rows = await cursor.fetchall()

    # Help request stats
    help_stats = {"total": 0, "completed": 0}
    try:
        cursor = await db.execute("""
            SELECT COUNT(*) as total, COUNT(CASE WHEN status='completed' THEN 1 END) as completed
            FROM help_requests
        """)
        row = await cursor.fetchone()
        if row:
            help_stats = {"total": row["total"], "completed": row["completed"]}
    except Exception:
        pass

    # Latest state changes
    cursor = await db.execute("""
        SELECT d.npc_name, br.state_of_mind, br.current_goal, d.health
        FROM agent_brain br
        JOIN dungeon_npcs d ON d.npc_id = br.npc_id
        WHERE d.status = 'active'
        ORDER BY d.npc_name
    """)
    all_npcs = await cursor.fetchall()

    return {
        "state_distribution": [dict(r) for r in rows],
        "help_requests": {
            "total": help_stats["total"] if help_stats else 0,
            "completed": help_stats["completed"] if help_stats else 0,
        },
        "all_npcs": [dict(n) for n in all_npcs],
    }


@router.get("/agent-os/help-requests")
async def get_help_requests(request: Request, db=Depends(get_db)):
    """Recent help requests."""
    try:
        cursor = await db.execute("""
            SELECT h.*, d.npc_name
            FROM help_requests h
            LEFT JOIN dungeon_npcs d ON d.npc_id = h.npc_id
            ORDER BY h.created_at DESC LIMIT 50
        """)
        rows = await cursor.fetchall()
        return {"help_requests": [dict(r) for r in rows]}
    except Exception as e:
        return {"help_requests": [], "error": str(e)}


# ═══════════════════════════════════════════
# 4. CONTROLLER STATS
# ═══════════════════════════════════════════

@router.get("/controller")
async def get_controller_stats(request: Request):
    """Current controller state — room priorities, tick info."""
    controller = getattr(request.app.state, "controller", None)
    if not controller:
        return {"error": "Controller not available"}
    return controller.get_stats()


# ═══════════════════════════════════════════
# 5. SYSTEM HEALTH
# ═══════════════════════════════════════════

@router.get("/health")
async def get_system_health(request: Request, db=Depends(get_db)):
    """Comprehensive system health check."""
    info = {
        "tick": request.app.state.tick_count if hasattr(request.app.state, "tick_count") else 0,
        "multiprocessing": False,
        "rooms": [],
        "state_of_minds": {},
        "active_npcs": 0,
        "total_agents": 0,
        "db_connected": True,
    }

    # Controller info
    controller = getattr(request.app.state, "controller", None)
    if controller:
        stats = controller.get_stats()
        info["multiprocessing"] = stats.get("multiprocessing", False)
        info["rooms"] = stats.get("rooms", [])

    # Counts
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as c FROM dungeon_npcs WHERE status='active'"
        )
        row = await cursor.fetchone()
        info["active_npcs"] = row["c"] if row else 0

        cursor = await db.execute(
            "SELECT COUNT(*) as c FROM agent_identities WHERE status='active'"
        )
        row = await cursor.fetchone()
        info["total_agents"] = row["c"] if row else 0

        # State of mind distribution
        cursor = await db.execute("""
            SELECT state_of_mind, COUNT(*) as c
            FROM agent_brain GROUP BY state_of_mind
        """)
        rows = await cursor.fetchall()
        info["state_of_minds"] = {r["state_of_mind"]: r["c"] for r in rows}
    except Exception:
        info["db_connected"] = False

    # Redis
    info["redis_connected"] = True
    try:
        from redis import asyncio as aioredis
        r = aioredis.from_url("redis://localhost:6379/0")
        await r.ping()
        await r.close()
    except Exception:
        info["redis_connected"] = False

    return info


# ═══════════════════════════════════════════════
# EVENT BUS
# ═══════════════════════════════════════════════


@router.get("/events/stats")
async def get_event_bus_stats(request: Request):
    """Get EventBus stats: subscribers, topics, recent event counts."""
    event_bus = getattr(request.app.state, "event_bus", None)
    if not event_bus:
        return {"error": "EventBus not initialized"}
    return event_bus.stats()


@router.get("/events/recent/{topic}")
async def get_recent_events(request: Request, topic: str, limit: int = 20):
    """Get recent events for a specific topic."""
    event_bus = getattr(request.app.state, "event_bus", None)
    if not event_bus:
        return {"error": "EventBus not initialized"}
    events = event_bus.get_recent(topic, limit=limit)
    return {"topic": topic, "count": len(events), "events": events}
