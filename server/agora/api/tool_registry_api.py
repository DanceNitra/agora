"""Tool Registry API — discover agent capabilities and validate tool calls."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


class ToolCallRequest(BaseModel):
    tool_id: str
    agent_id: str
    parameters: dict = {}


@router.get("")
async def list_all_tools(request: Request):
    """List all registered tools in the system."""
    registry = request.app.state.tool_registry
    tools = registry.list_all_tools()
    return {
        "count": len(tools),
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description[:80],
                "category": t.category.value,
                "parameters": [p.model_dump() for p in t.parameters],
            }
            for t in tools
        ],
    }


@router.get("/categories/{category}")
async def list_tools_by_category(request: Request, category: str):
    """List tools filtered by skill category."""
    from agora.harness.tool_registry import SkillCategory
    try:
        cat = SkillCategory(category)
    except ValueError:
        return {"error": f"Invalid category: {category}", "valid": [c.value for c in SkillCategory]}
    registry = request.app.state.tool_registry
    tools = registry.list_tools_by_category(cat)
    return {
        "category": category,
        "count": len(tools),
        "tools": [{"id": t.id, "name": t.name, "description": t.description[:80]} for t in tools],
    }


@router.get("/agent/{agent_id}")
async def get_agent_tools(request: Request, agent_id: str):
    """Discover all tools available to a specific NPC/agent."""
    registry = request.app.state.tool_registry
    tools = await registry.get_tools_for_agent(agent_id)
    return {
        "agent_id": agent_id[:8],
        "count": len(tools),
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description[:80],
                "category": t.category.value,
                "energy_cost": t.energy_cost,
                "min_skill_level": t.min_skill_level,
                "parameters": [p.model_dump() for p in t.parameters],
            }
            for t in tools
        ],
    }


@router.post("/validate")
async def validate_tool_call(request: Request, call: ToolCallRequest):
    """Validate a tool call without executing it."""
    from agora.harness.tool_registry import ToolCall
    registry = request.app.state.tool_registry
    tool_call = ToolCall(tool_id=call.tool_id, agent_id=call.agent_id, parameters=call.parameters)
    error = registry.validate_call(tool_call)
    if error:
        return {"valid": False, "error": error}
    can_use, msg = await registry.can_agent_use_tool(call.agent_id, call.tool_id)
    return {"valid": can_use, "message": msg if not can_use else "Valid and authorized"}
