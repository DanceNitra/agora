"""
Dungeon Persistence API — NPC state, quests, items in DB.
Save/load NPC positions, health, inventory, and quest progress.
"""

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/dungeon/persist", tags=["dungeon-persist"])

# ── Pydantic models ──

class NPCSave(BaseModel):
    npc_id: str
    npc_name: str
    role: str
    pos_x: float = 320
    pos_y: float = 240
    health: float = 100
    inventory: list[str] = []
    status: str = "active"
    objective: str = "Explore the dungeon"

class QuestDef(BaseModel):
    quest_id: str
    title: str
    description: str = ""
    quest_type: str = "exploration"
    prerequisites: list[str] = []
    rewards: dict[str, Any] = {}
    starting_npc: str | None = None

# ── NPC Endpoints ──

@router.post("/npc")
async def save_npc(body: NPCSave, request: Request):
    """Save or update NPC state to DB."""
    db = request.app.state.db
    inventory_json = json.dumps(body.inventory)
    now = datetime.utcnow().isoformat()
    
    # Canonical UUID mapping for dungeon NPCs
    CANONICAL_UUIDS = {
        "Kael":     "00000000-0000-0000-0000-000000000001",
        "Lyra":     "00000000-0000-0000-0000-000000000002",
        "Mordecai": "00000000-0000-0000-0000-000000000003",
        "Grom":     "00000000-0000-0000-0000-000000000004",
        "Zara":     "00000000-0000-0000-0000-000000000005",
        "Finn":     "00000000-0000-0000-0000-000000000006",
        "Guard":    "00000000-0000-0000-0000-000000000007",
    }

    # Check if this NPC name already exists — preserve its original npc_id
    cursor = await db.execute(
        "SELECT npc_id FROM dungeon_npcs WHERE npc_name=?", (body.npc_name,)
    )
    existing = await cursor.fetchone()
    # Force canonical UUID for known dungeon NPCs
    canonical = CANONICAL_UUIDS.get(body.npc_name)
    actual_npc_id = canonical or (existing["npc_id"] if existing else body.npc_id)

    await db.execute(
        """INSERT INTO dungeon_npcs (npc_id, npc_name, role, pos_x, pos_y, health, inventory, status, objective, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(npc_name) DO UPDATE SET
               npc_id=excluded.npc_id, pos_x=excluded.pos_x, pos_y=excluded.pos_y,
               health=excluded.health, inventory=excluded.inventory,
               status=excluded.status, objective=excluded.objective,
               updated_at=excluded.updated_at""",
        (actual_npc_id, body.npc_name, body.role, body.pos_x, body.pos_y,
         body.health, inventory_json, body.status, body.objective, now),
    )
    await db.commit()
    return {"status": "saved", "npc_id": body.npc_id}

@router.get("/npc/{npc_id}")
async def load_npc(npc_id: str, request: Request):
    """Load NPC state from DB."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT * FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return {"status": "not_found", "npc_id": npc_id}
    
    return {
        "status": "found",
        "npc": {
            "npc_id": row["npc_id"],
            "npc_name": row["npc_name"],
            "role": row["role"],
            "pos_x": row["pos_x"],
            "pos_y": row["pos_y"],
            "health": row["health"],
            "inventory": json.loads(row["inventory"]),
            "status": row["status"],
            "objective": row["objective"],
            "updated_at": row["updated_at"],
        }
    }

@router.get("/npcs")
async def list_npcs(request: Request):
    """List all persistent NPCs."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT npc_id, npc_name, role, pos_x, pos_y, status FROM dungeon_npcs ORDER BY npc_name"
    )
    rows = await cursor.fetchall()
    return {"npcs": [dict(r) for r in rows]}

# ── Quest Endpoints ──

@router.post("/quests")
async def define_quest(body: QuestDef, request: Request):
    """Define a new quest."""
    db = request.app.state.db
    prereq_json = json.dumps(body.prerequisites)
    rewards_json = json.dumps(body.rewards)
    
    await db.execute(
        """INSERT INTO dungeon_quests (quest_id, title, description, quest_type, prerequisites, rewards, starting_npc)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(quest_id) DO UPDATE SET
               title=excluded.title, description=excluded.description,
               quest_type=excluded.quest_type, prerequisites=excluded.prerequisites,
               rewards=excluded.rewards, starting_npc=excluded.starting_npc""",
        (body.quest_id, body.title, body.description, body.quest_type,
         prereq_json, rewards_json, body.starting_npc),
    )
    await db.commit()
    return {"status": "quest_defined", "quest_id": body.quest_id}

@router.get("/quests")
async def list_quests(request: Request):
    """List all defined quests."""
    db = request.app.state.db
    cursor = await db.execute("SELECT * FROM dungeon_quests ORDER BY title")
    rows = await cursor.fetchall()
    quests = []
    for r in rows:
        q = dict(r)
        q["prerequisites"] = json.loads(q["prerequisites"])
        q["rewards"] = json.loads(q["rewards"])
        quests.append(q)
    return {"quests": quests}

@router.post("/quests/{quest_id}/start/{npc_id}")
async def start_quest(quest_id: str, npc_id: str, request: Request):
    """NPC starts a quest — checks prerequisites."""
    db = request.app.state.db
    
    # Check quest exists
    cursor = await db.execute("SELECT * FROM dungeon_quests WHERE quest_id=?", (quest_id,))
    quest = await cursor.fetchone()
    if not quest:
        return {"status": "error", "error": "quest_not_found"}
    
    # Check prerequisites
    prereqs = json.loads(quest["prerequisites"])
    if prereqs:
        placeholders = ",".join("?" for _ in prereqs)
        cursor = await db.execute(
            f"SELECT quest_id, status FROM dungeon_quest_progress WHERE npc_id=? AND quest_id IN ({placeholders})",
            (npc_id, *prereqs),
        )
        completed = {r["quest_id"] for r in await cursor.fetchall() if r["status"] == "completed"}
        missing = [p for p in prereqs if p not in completed]
        if missing:
            return {"status": "error", "error": "prerequisites_not_met", "missing": missing}
    
    # Start quest
    await db.execute(
        """INSERT INTO dungeon_quest_progress (npc_id, quest_id, status, progress, started_at)
           VALUES (?, ?, 'active', '{}', datetime('now'))
           ON CONFLICT(npc_id, quest_id) DO UPDATE SET
               status='active', progress='{}', started_at=datetime('now'), completed_at=NULL""",
        (npc_id, quest_id),
    )
    await db.commit()
    return {"status": "quest_started", "quest_id": quest_id, "npc_id": npc_id}

@router.post("/quests/{quest_id}/progress/{npc_id}")
async def update_quest_progress(quest_id: str, npc_id: str, progress: dict, request: Request):
    """Update quest progress."""
    db = request.app.state.db
    progress_json = json.dumps(progress)
    
    await db.execute(
        "UPDATE dungeon_quest_progress SET progress=? WHERE npc_id=? AND quest_id=?",
        (progress_json, npc_id, quest_id),
    )
    await db.commit()
    return {"status": "progress_updated", "quest_id": quest_id, "npc_id": npc_id}

@router.post("/quests/{quest_id}/complete/{npc_id}")
async def complete_quest(quest_id: str, npc_id: str, request: Request):
    """Complete a quest — grant rewards."""
    db = request.app.state.db
    
    cursor = await db.execute(
        "SELECT * FROM dungeon_quest_progress WHERE npc_id=? AND quest_id=?",
        (npc_id, quest_id),
    )
    progress = await cursor.fetchone()
    if not progress or progress["status"] != "active":
        return {"status": "error", "error": "quest_not_active"}
    
    # Get quest rewards
    cursor = await db.execute("SELECT rewards FROM dungeon_quests WHERE quest_id=?", (quest_id,))
    quest = await cursor.fetchone()
    rewards = json.loads(quest["rewards"]) if quest else {}
    
    # Complete it
    await db.execute(
        "UPDATE dungeon_quest_progress SET status='completed', progress='{}', completed_at=datetime('now') WHERE npc_id=? AND quest_id=?",
        (npc_id, quest_id),
    )
    await db.commit()
    
    return {
        "status": "quest_completed",
        "quest_id": quest_id,
        "npc_id": npc_id,
        "rewards": rewards,
    }

@router.get("/quests/progress/{npc_id}")
async def get_npc_quests(npc_id: str, request: Request):
    """Get all quest progress for an NPC."""
    db = request.app.state.db
    cursor = await db.execute(
        """SELECT qp.*, dq.title, dq.description, dq.quest_type, dq.rewards, dq.prerequisites
           FROM dungeon_quest_progress qp
           JOIN dungeon_quests dq ON qp.quest_id = dq.quest_id
           WHERE qp.npc_id=?
           ORDER BY qp.status, dq.title""",
        (npc_id,),
    )
    rows = await cursor.fetchall()
    quests = []
    for r in rows:
        q = dict(r)
        q["rewards"] = json.loads(q["rewards"]) if isinstance(q.get("rewards"), str) else q.get("rewards", {})
        q["prerequisites"] = json.loads(q["prerequisites"]) if isinstance(q.get("prerequisites"), str) else q.get("prerequisites", [])
        q["progress"] = json.loads(q["progress"]) if isinstance(q.get("progress"), str) else q.get("progress", {})
        quests.append(q)
    return {"npcs": npc_id, "quests": quests}
