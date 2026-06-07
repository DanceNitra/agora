"""Phase 4: Build the first tool station

Generated from research:
A new, composable station exists and passes verification.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/build_the_first_tool_station", tags=["build_the_first_tool_station"])


# ── Models ──────────────────────────────────────────────

class BuildTheFirstToolStationRequest(BaseModel):
    """Request model for build the first tool station."""
    action: str
    params: dict[str, Any] = {}


class BuildTheFirstToolStationResponse(BaseModel):
    """Response model for build the first tool station."""
    status: str
    data: Optional[dict[str, Any]] = None
    message: str = ""


# ── State ──────────────────────────────────────────────

_state: dict[str, Any] = {}


@router.get("/status", response_model=BuildTheFirstToolStationResponse)
async def get_status():
    """Get current build the first tool station status."""
    return {
        "status": "ok",
        "data": {
            "active": True,
            "items": len(_state),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        },
        "message": "build the first tool station is operational",
    }


@router.post("/execute", response_model=BuildTheFirstToolStationResponse)
async def execute_action(request: BuildTheFirstToolStationRequest):
    """Execute an action in the build the first tool station subsystem."""
    try:
        result = _handle_action(request.action, request.params)
        logger.info(f"Executed {request.action}: {result}")
        return {
            "status": "ok",
            "data": result,
            "message": f"Action '{request.action}' completed",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Action failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _handle_action(action: str, params: dict) -> dict:
    """Route an action to its handler."""
    handlers = {
        "init": _action_init,
        "reset": _action_reset,
        "status": _action_status,
    }
    handler = handlers.get(action)
    if not handler:
        raise ValueError(f"Unknown action: {action}")
    return handler(params)


def _action_init(params: dict) -> dict:
    """Initialize the build the first tool station subsystem."""
    _state.clear()
    _state["initialized_at"] = __import__("datetime").datetime.now().isoformat()
    _state["config"] = params
    return {"initialized": True, "config": params}


def _action_reset(params: dict) -> dict:
    """Reset the build the first tool station subsystem to defaults."""
    _state.clear()
    return {"reset": True}


def _action_status(params: dict) -> dict:
    """Report current state of the build the first tool station subsystem."""
    return {
        "initialized": "initialized_at" in _state,
        "state_size": len(_state),
        "state_keys": list(_state.keys()),
    }
