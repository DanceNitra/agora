"""Phase 4: Put the new station to work

Generated from research:
An operator uses the new station to complete a real unit of work, sandboxed first.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/put_the_new_station_to_work", tags=["put_the_new_station_to_work"])


# ── Models ──────────────────────────────────────────────

class PutTheNewStationToWorkRequest(BaseModel):
    """Request model for put the new station to work."""
    action: str
    params: dict[str, Any] = {}


class PutTheNewStationToWorkResponse(BaseModel):
    """Response model for put the new station to work."""
    status: str
    data: Optional[dict[str, Any]] = None
    message: str = ""


# ── State ──────────────────────────────────────────────

_state: dict[str, Any] = {}


@router.get("/status", response_model=PutTheNewStationToWorkResponse)
async def get_status():
    """Get current put the new station to work status."""
    return {
        "status": "ok",
        "data": {
            "active": True,
            "items": len(_state),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        },
        "message": "put the new station to work is operational",
    }


@router.post("/execute", response_model=PutTheNewStationToWorkResponse)
async def execute_action(request: PutTheNewStationToWorkRequest):
    """Execute an action in the put the new station to work subsystem."""
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
    """Initialize the put the new station to work subsystem."""
    _state.clear()
    _state["initialized_at"] = __import__("datetime").datetime.now().isoformat()
    _state["config"] = params
    return {"initialized": True, "config": params}


def _action_reset(params: dict) -> dict:
    """Reset the put the new station to work subsystem to defaults."""
    _state.clear()
    return {"reset": True}


def _action_status(params: dict) -> dict:
    """Report current state of the put the new station to work subsystem."""
    return {
        "initialized": "initialized_at" in _state,
        "state_size": len(_state),
        "state_keys": list(_state.keys()),
    }
