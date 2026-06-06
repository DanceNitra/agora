"""Agora server — main FastAPI application.

Sets up lifespan (DB, Redis, subsystems, seed agents), WebSocket /ws endpoint,
tick_loop background task, and global AgoraState.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from agora.api import agents, tasks, timeline, god

logger = logging.getLogger("agora")


# ---------- Global State ----------

@dataclass
class AgoraState:
    """Holds all top-level subsystem references for the running server."""

    db: Optional[object] = None
    redis: Optional[object] = None
    agent_manager: Optional[object] = None
    task_manager: Optional[object] = None
    timeline_service: Optional[object] = None
    god_engine: Optional[object] = None
    websocket_connections: list = field(default_factory=list)
    tick_interval: float = 1.0  # seconds


# Singleton state instance
state = AgoraState()


# ---------- Lifespan ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle.

    On startup:
      - Connect to database
      - Connect to Redis
      - Initialize subsystems (agent manager, task manager, timeline, god)
      - Create seed agents
      - Start background tick loop

    On shutdown:
      - Stop tick loop
      - Tear down subsystems
      - Close Redis / DB connections
    """
    logger.info("Agora server starting up...")

    # ---- Startup ----

    # 1. Database connection (placeholder)
    # state.db = await create_async_engine("postgresql+asyncpg://...")
    logger.info("Database connection established (placeholder)")

    # 2. Redis connection (placeholder)
    # state.redis = await aioredis.from_url("redis://localhost:6379")
    logger.info("Redis connection established (placeholder)")

    # 3. Initialize subsystems (placeholder)
    # state.agent_manager = AgentManager(db=state.db, redis=state.redis)
    # state.task_manager = TaskManager(db=state.db)
    # state.timeline_service = TimelineService()
    # state.god_engine = GodEngine(...)
    logger.info("Subsystems initialized (placeholder)")

    # 4. Create seed agents (placeholder)
    # await state.agent_manager.spawn("helper", "A general-purpose helper", name="Athena")
    # await state.agent_manager.spawn("critic", "Reviews and critiques output", name="Socrates")
    logger.info("Seed agents created (placeholder)")

    # 5. Start background tick loop
    tick_task = asyncio.create_task(tick_loop())

    yield  # Application runs here

    # ---- Shutdown ----

    logger.info("Agora server shutting down...")

    tick_task.cancel()
    try:
        await tick_task
    except asyncio.CancelledError:
        pass

    # Tear down subsystems
    # await state.agent_manager.shutdown()
    # await state.task_manager.shutdown()
    # await state.timeline_service.shutdown()

    # Close connections
    # if state.redis:
    #     await state.redis.close()
    # if state.db:
    #     await state.db.dispose()

    logger.info("Agora server shutdown complete.")


# ---------- Background Tick Loop ----------

async def tick_loop():
    """Periodic background task that drives the agent simulation loop."""
    while True:
        try:
            # 1. Process queued agent actions
            # 2. Check for timed-out tasks
            # 3. Emit heartbeats to WebSocket clients
            # 4. Persist state snapshots

            # Broadcast tick to connected WebSocket clients
            payload = json.dumps({"type": "tick", "ts": asyncio.get_event_loop().time()})
            dead_connections = []
            for ws in state.websocket_connections:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead_connections.append(ws)

            for ws in dead_connections:
                state.websocket_connections.remove(ws)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception("Error in tick_loop: %s", exc)

        await asyncio.sleep(state.tick_interval)


# ---------- WebSocket Endpoint ----------

async def handle_websocket(websocket: WebSocket):
    """Handle an individual WebSocket connection lifecycle."""
    await websocket.accept()
    state.websocket_connections.append(websocket)
    logger.info("WebSocket client connected (%d total)", len(state.websocket_connections))

    try:
        while True:
            data = await websocket.receive_text()
            # Process incoming messages (e.g. agent commands, chat)
            try:
                msg = json.loads(data)
                # Handle message dispatch...
                # e.g. if msg.get("type") == "command":
                #     await state.god_engine.handle(msg["command"])
                response = {"type": "ack", "original": msg}
                await websocket.send_text(json.dumps(response))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "detail": "Invalid JSON"}))
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.exception("WebSocket error: %s", exc)
    finally:
        if websocket in state.websocket_connections:
            state.websocket_connections.remove(websocket)


# ---------- FastAPI Application ----------

def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Agora Server",
        description="Multi-agent orchestration server",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(agents.router)
    app.include_router(tasks.router)
    app.include_router(timeline.router)
    app.include_router(god.router)

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await handle_websocket(websocket)

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "agents_online": len(state.websocket_connections)}

    return app


# Instantiate the app
app = create_app()
