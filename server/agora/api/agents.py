"""Agents API router for Agora server."""

from fastapi import APIRouter, Depends, HTTPException, Request
import json
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(tags=["agents"])


# ---------- Schemas ----------

class AgentCreate(BaseModel):
    name: str
    role: str
    model: str = "default"
    system_prompt: Optional[str] = None


class AgentResponse(BaseModel):
    agent_id: str
    role: str
    trust_score: float
    energy_balance: float
    status: str
    genome: dict
    created_at: str


class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int


# ---------- Dependency ----------

async def get_db(request: Request):
    return request.app.state.db


# ---------- Routes ----------

@router.get("/", response_model=AgentListResponse)
async def list_agents(db=Depends(get_db)):
    """List all active agents."""
    cursor = await db.execute(
        "SELECT agent_id, role, trust_score, energy_balance, status, genome, created_at "
        "FROM agent_identities WHERE status='active' ORDER BY created_at ASC"
    )
    rows = await cursor.fetchall()
    agents = []
    for row in rows:
        try:
            genome = json.loads(row["genome"])
        except (json.JSONDecodeError, TypeError):
            genome = {}
        agents.append(AgentResponse(
            agent_id=row["agent_id"],
            role=row["role"],
            trust_score=row["trust_score"],
            energy_balance=row["energy_balance"],
            status=row["status"],
            genome=genome,
            created_at=row["created_at"],
        ))
    return AgentListResponse(agents=agents, total=len(agents))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db=Depends(get_db)):
    """Get a single agent by ID."""
    cursor = await db.execute(
        "SELECT agent_id, role, trust_score, energy_balance, status, genome, created_at "
        "FROM agent_identities WHERE agent_id=?",
        (agent_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        genome = json.loads(row["genome"])
    except (json.JSONDecodeError, TypeError):
        genome = {}
    return AgentResponse(
        agent_id=row["agent_id"],
        role=row["role"],
        trust_score=row["trust_score"],
        energy_balance=row["energy_balance"],
        status=row["status"],
        genome=genome,
        created_at=row["created_at"],
    )


@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: str, db=Depends(get_db)):
    """Pause an agent."""
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
    """Resume a paused agent."""
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
    """Apply a positive reward to an agent."""
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
    """Apply a punishment to an agent."""
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
