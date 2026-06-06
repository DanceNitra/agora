"""Timeline API router for Agora server.

Provides a list of recent events and a Server-Sent Events (SSE) streaming
endpoint for real-time timeline updates.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


# ---------- Schemas ----------

class TimelineEvent(BaseModel):
    id: str
    type: str  # e.g. agent_spawned, task_created, agent_rewarded, etc.
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    message: str
    timestamp: datetime
    metadata: Optional[dict] = None


class TimelineListResponse(BaseModel):
    events: List[TimelineEvent]
    total: int


# ---------- In-memory event store (placeholder) ----------

_events: List[TimelineEvent] = []
_event_queue: asyncio.Queue = asyncio.Queue()
_MAX_EVENTS = 1000


def push_event(event: TimelineEvent):
    """Push an event into the in-memory store and notify SSE subscribers."""
    _events.append(event)
    if len(_events) > _MAX_EVENTS:
        _events.pop(0)
    _event_queue.put_nowait(event)


# ---------- Dependency ----------

def get_db():
    yield None


# ---------- Routes ----------

@router.get("/", response_model=TimelineListResponse)
async def list_recent_events(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    db=Depends(get_db),
):
    """List recent timeline events, newest first."""
    filtered = _events
    if event_type:
        filtered = [e for e in filtered if e.type == event_type]

    total = len(filtered)
    # Reverse so newest first
    reversed_events = list(reversed(filtered))
    page = reversed_events[offset : offset + limit]

    return TimelineListResponse(events=page, total=total)


@router.get("/stream")
async def stream_events(request: Request):
    """SSE endpoint that streams timeline events in real time."""

    async def event_generator():
        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                break

            try:
                # Wait for a new event (timeout periodically to check disconnect)
                event = await asyncio.wait_for(_event_queue.get(), timeout=30.0)
                data = json.dumps(event.model_dump(), default=str)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                # Send a keepalive comment to maintain the connection
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
