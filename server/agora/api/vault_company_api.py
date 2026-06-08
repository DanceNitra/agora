"""Vault Company API endpoints."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/vault-company", tags=["vault-company"])


class RunNightCycleRequest(BaseModel):
    force: bool = False


class AgentReportRequest(BaseModel):
    agent_name: str


@router.post("/night-cycle")
async def run_night_cycle(req: RunNightCycleRequest, request: "Request"):
    """Run the full autonomous vault company night cycle."""
    app = request.app
    engine = getattr(app.state, "vault_company_engine", None)
    if not engine:
        raise HTTPException(status_code=503, detail="VaultCompanyEngine not initialized")
    
    result = await engine.run_night_cycle(force=req.force)
    return {
        "status": "ok",
        "cycle_id": result.get("cycle_id"),
        "phases": len(result.get("phases", [])),
        "orchestrator_report": result.get("orchestrator_report"),
    }


@router.get("/report/{agent_name}")
async def get_agent_report(agent_name: str, request: "Request"):
    """Get report card for a specific vault company agent."""
    app = request.app
    engine = getattr(app.state, "vault_company_engine", None)
    if not engine:
        raise HTTPException(status_code=503, detail="VaultCompanyEngine not initialized")
    
    result = await engine.get_agent_report(agent_name)
    return {"status": "ok", "agent": result}


@router.get("/org-chart")
async def get_org_chart(request: "Request"):
    """Get the vault company organizational chart."""
    from agora.agent_os.vault_company.agent_definitions import (
        VAULT_COMPANY_ORG_CHART, VAULT_ROLES,
    )
    
    agents = []
    for name, role in VAULT_ROLES.items():
        agents.append({
            "name": name,
            "title": role.get("title"),
            "department": role.get("department"),
            "vault_role": role.get("vault_role"),
            "night_cycle": role.get("night_cycle"),
        })
    
    return {
        "status": "ok",
        "company": VAULT_COMPANY_ORG_CHART,
        "agents": agents,
    }


@router.get("/agent/{agent_name}/definition")
async def get_agent_definition(agent_name: str, request: "Request"):
    """Get full definition (role, soul, skills, tools) for an agent."""
    from agora.agent_os.vault_company.agent_definitions import (
        AGENT_VAULT_DEFS, VAULT_SKILL_DESCRIPTIONS,
    )
    
    defs = AGENT_VAULT_DEFS.get(agent_name)
    if not defs:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    # Enrich skills with descriptions
    enriched = defs.copy()
    all_skills = []
    for s in defs.get("skills", {}).get("primary", []):
        sk = {"name": s[0], "level": s[1], "xp": s[2]}
        sk["description"] = VAULT_SKILL_DESCRIPTIONS.get(s[0], "")
        all_skills.append(sk)
    for s in defs.get("skills", {}).get("secondary", []):
        sk = {"name": s[0], "level": s[1], "xp": s[2]}
        sk["description"] = VAULT_SKILL_DESCRIPTIONS.get(s[0], "")
        all_skills.append(sk)
    enriched["skills_enriched"] = all_skills
    
    return {"status": "ok", "agent": agent_name, "definition": enriched}


@router.get("/cycles")
async def get_cycle_history(request: "Request"):
    """Get recent night cycle results."""
    engine = getattr(request.app.state, "vault_company_engine", None)
    if not engine:
        raise HTTPException(status_code=503, detail="VaultCompanyEngine not initialized")
    
    cycle = getattr(engine, "cycle_results", {})
    if not cycle:
        return {"status": "ok", "cycles": [], "message": "No cycles yet"}
    
    return {
        "status": "ok",
        "last_cycle": {
            "cycle_id": cycle.get("cycle_id"),
            "status": cycle.get("status"),
            "phases_completed": sum(1 for p in cycle.get("phases", [])
                                    if p.get("status") == "completed"),
            "phases_total": len(cycle.get("phases", [])),
            "duration_seconds": cycle.get("duration_seconds", 0),
            "report": cycle.get("orchestrator_report"),
        },
    }