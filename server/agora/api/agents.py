"""Agents API router for Agora server."""
from fastapi import APIRouter, Depends, HTTPException, Request
import json
from typing import Optional
from pydantic import BaseModel

# Reverse map: UUID → NPC name (imported from dungeon API)
from agora.api.dungeon import DUNGEON_AGENT_IDS, DUNGEON_AGENT_ROLES

# Build reverse lookup: UUID → name
UUID_TO_NAME = {v: k for k, v in DUNGEON_AGENT_IDS.items()}

router = APIRouter(tags=["agents"])


# ---------- Schemas ----------

class AgentCreate(BaseModel):
    name: str
    role: str
    model: str = "default"
    system_prompt: Optional[str] = None


class AgentResponse(BaseModel):
    agent_id: str
    name: str = ""
    role: str
    trust_score: float = 0.5
    energy_balance: float = 0.0
    status: str = "active"
    genome: dict = {}
    created_at: str = ""
    objective: str = ""
    health: float = 100.0
    inventory: list[str] = []
    pos_x: float = 0.0
    pos_y: float = 0.0
    current_task: str = ""


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


# ---------- Dependency ----------

async def get_db(request: Request):
    return request.app.state.db


def _safe_parse_json(val, default=None):
    """Parse a JSON string or return the value as-is if already a list/dict."""
    import json
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
    return default or ([] if isinstance(default, list) else {})


def _merge_dungeon_data(row, agent_only: dict | None = None) -> dict:
    """Merge agent_identities row with dungeon NPC name mapping."""
    agent = dict(row)
    agent_id = agent.get("agent_id") or ""
    agent["agent_id"] = agent_id  # ensure it's always a string

    # Parse JSON fields that come as strings from DB
    inv = agent.get("inventory")
    agent["inventory"] = _safe_parse_json(inv, [])
    genome_val = agent.get("genome")
    agent["genome"] = _safe_parse_json(genome_val, {})
    # Ensure scalar fields are never None
    for key in ("objective", "created_at"):
        if agent.get(key) is None:
            agent[key] = ""
    for key in ("health", "pos_x", "pos_y"):
        if agent.get(key) is None:
            agent[key] = 0.0
    for key in ("trust_score", "energy_balance"):
        if agent.get(key) is None:
            agent[key] = 0.0

    # First try UUID-to-name mapping
    name_from_uuid = UUID_TO_NAME.get(agent_id, "")

    # Check if this row has dungeon NPC data from LEFT JOIN
    try:
        npc_name = row["npc_name"] if "npc_name" in row and row["npc_name"] else None
    except (KeyError, IndexError, TypeError):
        npc_name = None

    actual_name = npc_name or name_from_uuid
    if not actual_name:
        actual_name = agent_id[:8] if agent_id else "unknown"
    agent["name"] = actual_name

    if npc_name or name_from_uuid:
        agent["objective"] = agent.get("objective") or f"Operating as {actual_name}"
        if not agent.get("health"):
            agent["health"] = 100
        if not agent.get("pos_x"):
            agent["pos_x"] = 0
        if not agent.get("pos_y"):
            agent["pos_y"] = 0
    return agent


# ---------- Routes ----------

@router.get("/", response_model=AgentListResponse)
async def list_agents(db=Depends(get_db)):
    """List all active agents with dungeon NPC data merged."""
    cursor = await db.execute(
        "SELECT a.agent_id, a.role, a.trust_score, a.energy_balance, a.status, a.genome, a.created_at, "
        "d.npc_name, d.objective, d.health, d.pos_x, d.pos_y, d.inventory "
        "FROM agent_identities a "
        "LEFT JOIN dungeon_npcs d ON a.agent_id = d.npc_id "
        "WHERE a.status='active' ORDER BY a.created_at ASC"
    )
    rows = await cursor.fetchall()
    agents = []
    for row in rows:
        merged = _merge_dungeon_data(row, row)
        genome = merged.get("genome", {})
        agents.append(AgentResponse(
            agent_id=merged["agent_id"],
            name=merged.get("name", "") or "",
            role=merged["role"] or "unknown",
            trust_score=merged.get("trust_score") or 0.5,
            energy_balance=merged.get("energy_balance") or 0.0,
            status=merged.get("status") or "active",
            genome=genome or {},
            created_at=merged.get("created_at") or "",
            objective=merged.get("objective") or "",
            health=merged.get("health") or 100.0,
            inventory=merged.get("inventory") or [],
            pos_x=merged.get("pos_x") or 0.0,
            pos_y=merged.get("pos_y") or 0.0,
            current_task=merged.get("objective") or "",
        ))
    return AgentListResponse(agents=agents, total=len(agents))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db=Depends(get_db)):
    """Get a single agent by ID (UUID or name)."""
    # Try by agent_id (UUID) first, then by npc_name
    cursor = await db.execute(
        "SELECT a.agent_id, a.role, a.trust_score, a.energy_balance, a.status, a.genome, a.created_at, "
        "d.npc_name, d.objective, d.health, d.pos_x, d.pos_y, d.inventory "
        "FROM agent_identities a "
        "LEFT JOIN dungeon_npcs d ON a.agent_id = d.npc_id "
        "WHERE a.agent_id=?",
        (agent_id,),
    )
    row = await cursor.fetchone()
    if not row:
        # Try by name — lookup npc_id from dungeon_npcs
        cursor = await db.execute(
            "SELECT d.*, a.agent_id, a.role, a.trust_score, a.energy_balance, a.status, a.genome, a.created_at "
            "FROM dungeon_npcs d "
            "LEFT JOIN agent_identities a ON d.npc_id = a.agent_id "
            "WHERE LOWER(d.npc_name)=LOWER(?)",
            (agent_id,),
        )
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    merged = _merge_dungeon_data(row, row)
    genome = merged.get("genome", {})
    return AgentResponse(
        agent_id=merged["agent_id"],
        name=merged.get("name", "") or "",
        role=merged["role"] or "unknown",
        trust_score=merged.get("trust_score") or 0.5,
        energy_balance=merged.get("energy_balance") or 0.0,
        status=merged.get("status") or "active",
        genome=genome or {},
        created_at=merged.get("created_at") or "",
        objective=merged.get("objective") or "",
        health=merged.get("health") or 100.0,
        inventory=merged.get("inventory") or [],
        pos_x=merged.get("pos_x") or 0.0,
        pos_y=merged.get("pos_y") or 0.0,
        current_task=merged.get("objective") or "",
    )


@router.get("/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str, db=Depends(get_db)):
    """Get tasks assigned to an agent."""
    cursor = await db.execute(
        "SELECT t.* FROM tasks t "
        "LEFT JOIN dungeon_npcs d ON (t.assigned_to = d.npc_name OR t.assigned_to = d.npc_id) "
        "WHERE d.npc_id=? OR d.npc_name=? "
        "ORDER BY t.created_at DESC LIMIT 20",
        (agent_id, agent_id),
    )
    rows = await cursor.fetchall()
    tasks = []
    for row in rows:
        r = dict(row)
        tasks.append({
            "id": r["id"],
            "title": r.get("title", ""),
            "description": r.get("description", ""),
            "status": r.get("status", "pending"),
            "difficulty": r.get("difficulty", 1),
            "reward": r.get("reward", 0),
            "created_at": r.get("created_at", ""),
        })
    return {"tasks": tasks, "total": len(tasks)}


@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: str, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT status FROM agent_identities WHERE agent_id=?", (agent_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    if row["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Agent is {row['status']}, cannot pause")
    await db.execute(
        "UPDATE agent_identities SET status='paused', updated_at=datetime('now') WHERE agent_id=?",
        (agent_id,),
    )
    await db.commit()
    return {"status": "paused", "agent_id": agent_id}


@router.post("/{agent_id}/resume")
async def resume_agent(agent_id: str, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT status FROM agent_identities WHERE agent_id=?", (agent_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    if row["status"] != "paused":
        raise HTTPException(status_code=400, detail=f"Agent is {row['status']}, cannot resume")
    await db.execute(
        "UPDATE agent_identities SET status='active', updated_at=datetime('now') WHERE agent_id=?",
        (agent_id,),
    )
    await db.commit()
    return {"status": "active", "agent_id": agent_id}


@router.post("/{agent_id}/reward")
async def reward_agent(agent_id: str, amount: float = 1.0, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT trust_score FROM agent_identities WHERE agent_id=?", (agent_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    new_score = min(1.0, row["trust_score"] + amount * 0.1)
    await db.execute(
        "UPDATE agent_identities SET trust_score=?, updated_at=datetime('now') WHERE agent_id=?",
        (new_score, agent_id),
    )
    await db.commit()
    return {"agent_id": agent_id, "trust_score": new_score}


@router.post("/{agent_id}/punish")
async def punish_agent(agent_id: str, amount: float = 1.0, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT trust_score FROM agent_identities WHERE agent_id=?", (agent_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    new_score = max(0.0, row["trust_score"] - amount * 0.1)
    await db.execute(
        "UPDATE agent_identities SET trust_score=?, updated_at=datetime('now') WHERE agent_id=?",
        (new_score, agent_id),
    )
    await db.commit()
    return {"agent_id": agent_id, "trust_score": new_score}
