"""Agents API router for Agora server."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ---------- Schemas ----------

class AgentCreate(BaseModel):
    name: str
    role: str
    model: str = "default"
    system_prompt: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    model: str
    status: str  # active, paused, archived
    system_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    reward_score: float = 0.0


class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int


# ---------- Dependency: database session ----------

def get_db():
    """Placeholder: yields a database session."""
    # In production, replace with actual sessionmaker yield.
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()
    yield None


# ---------- Route Helpers ----------

def _agent_to_response(agent_row) -> AgentResponse:
    """Convert a database agent row to an AgentResponse."""
    return AgentResponse(
        id=agent_row.id,
        name=agent_row.name,
        role=agent_row.role,
        model=agent_row.model,
        status=agent_row.status,
        system_prompt=getattr(agent_row, "system_prompt", None),
        created_at=agent_row.created_at,
        updated_at=agent_row.updated_at,
        reward_score=getattr(agent_row, "reward_score", 0.0),
    )


# ---------- Routes ----------

@router.get("/", response_model=AgentListResponse)
async def list_agents(db=Depends(get_db)):
    """List all agents."""
    # agents = db.query(AgentModel).all()
    agents = []  # placeholder
    return AgentListResponse(
        agents=[_agent_to_response(a) for a in agents],
        total=len(agents),
    )


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(body: AgentCreate, db=Depends(get_db)):
    """Create a new agent."""
    # agent = AgentModel(name=body.name, role=body.role, ...)
    # db.add(agent)
    # db.commit()
    # db.refresh(agent)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db=Depends(get_db)):
    """Get a single agent by ID."""
    # agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    # if not agent:
    #     raise HTTPException(status_code=404, detail="Agent not found")
    # return _agent_to_response(agent)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")


@router.post("/{agent_id}/pause", response_model=AgentResponse)
async def pause_agent(agent_id: str, db=Depends(get_db)):
    """Pause an agent."""
    # agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    # if not agent:
    #     raise HTTPException(status_code=404, detail="Agent not found")
    # agent.status = "paused"
    # agent.updated_at = datetime.utcnow()
    # db.commit()
    # db.refresh(agent)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")


@router.post("/{agent_id}/resume", response_model=AgentResponse)
async def resume_agent(agent_id: str, db=Depends(get_db)):
    """Resume a paused agent."""
    # agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    # if not agent:
    #     raise HTTPException(status_code=404, detail="Agent not found")
    # agent.status = "active"
    # agent.updated_at = datetime.utcnow()
    # db.commit()
    # db.refresh(agent)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")


@router.post("/{agent_id}/reward", response_model=AgentResponse)
async def reward_agent(agent_id: str, amount: float = 1.0, db=Depends(get_db)):
    """Apply a positive reward to an agent."""
    # agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    # if not agent:
    #     raise HTTPException(status_code=404, detail="Agent not found")
    # agent.reward_score = (agent.reward_score or 0) + amount
    # agent.updated_at = datetime.utcnow()
    # db.commit()
    # db.refresh(agent)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")


@router.post("/{agent_id}/punish", response_model=AgentResponse)
async def punish_agent(agent_id: str, amount: float = 1.0, db=Depends(get_db)):
    """Apply a punishment (negative reward) to an agent."""
    # agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    # if not agent:
    #     raise HTTPException(status_code=404, detail="Agent not found")
    # agent.reward_score = (agent.reward_score or 0) - amount
    # agent.updated_at = datetime.utcnow()
    # db.commit()
    # db.refresh(agent)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")
