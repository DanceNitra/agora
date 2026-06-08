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


# ═══════════════════════════════════════════════════════════════
# AGENT DIRECTORY ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/agent/{agent_name}/directory")
async def list_agent_directory(agent_name: str, request: "Request"):
    """List all files in an agent's directory."""
    from agora.agent_os.vault_company import AgentDirectoryManager
    
    mgr = AgentDirectoryManager()
    files = await mgr.list_files(agent_name)
    return {"status": "ok", "agent": agent_name, "files": files, "count": len(files)}


@router.get("/agent/{agent_name}/directory/{file_path:path}")
async def read_agent_file(agent_name: str, file_path: str, request: "Request"):
    """Read a specific file from an agent's directory."""
    from agora.agent_os.vault_company import AgentDirectoryManager
    
    mgr = AgentDirectoryManager()
    content = await mgr.read_file(agent_name, file_path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found for agent '{agent_name}'")
    return {"status": "ok", "agent": agent_name, "file": file_path, "content": content, "size": len(content)}


@router.get("/agent/{agent_name}/summary")
async def get_agent_directory_summary(agent_name: str, request: "Request"):
    """Get summary of an agent from their directory files."""
    from agora.agent_os.vault_company import AgentDirectoryManager
    
    mgr = AgentDirectoryManager()
    summary = await mgr.get_agent_summary(agent_name)
    return {"status": "ok", "agent": summary}


class LogActionRequest(BaseModel):
    agent_name: str
    log_type: str  # "actions" or "decisions" or "episodic"
    entry: dict


@router.post("/agent/{agent_name}/log")
async def log_agent_action(agent_name: str, req: LogActionRequest, request: "Request"):
    """Append an entry to an agent's log."""
    from agora.agent_os.vault_company import AgentDirectoryManager
    
    mgr = AgentDirectoryManager()
    success = await mgr.append_log(agent_name, req.log_type, req.entry)
    if not success:
        raise HTTPException(status_code=400, detail=f"Invalid log_type: {req.log_type}. Use: actions, decisions, or episodic.")
    return {"status": "ok", "agent": agent_name, "log_type": req.log_type, "logged": True}


class ThinkRequest(BaseModel):
    agent_name: str
    phase: str = "research_scan"
    context: str = ""
    tier: str = "cheap"


@router.post("/think")
async def agent_think_llm(req: ThinkRequest, request: "Request"):
    """Have a vault company agent 'think' using real LLM with their personality."""
    from agora.agent_os.vault_company.vault_company_think import vault_company_think
    
    result = await vault_company_think(
        agent_name=req.agent_name,
        phase_name=req.phase,
        context=req.context,
        tier=req.tier,
    )
    return {"status": "ok", "agent": req.agent_name, "phase": req.phase, "result": result}


@router.get("/think/{agent_name}/{phase}")
async def agent_think_get(agent_name: str, phase: str = "research_scan", request: "Request" = None, context: str = ""):
    """Quick GET endpoint to have an agent think (for testing)."""
    from agora.agent_os.vault_company.vault_company_think import vault_company_think
    
    result = await vault_company_think(
        agent_name=agent_name,
        phase_name=phase,
        context=context,
        tier="cheap",
    )
    return {"status": "ok", "agent": agent_name, "phase": phase, "result": result}