"""Agora — FastAPI server entry point (SQLite dev mode)."""

import asyncio
import json
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite

from agora.config import settings
from agora.coordination.ess_protocol import TrustEngine
from agora.coordination.stigmergy import StigmergyPool
from agora.api import agents as agents_api, tasks as tasks_api, god as god_api, graph as graph_api


DB_PATH = settings.database_url.replace("sqlite+aiosqlite:///", "")


async def init_db(app: FastAPI):
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    app.state.db = db

    schema_path = __file__.replace("main.py", "storage/schema.sql")
    try:
        with open(schema_path) as f:
            await db.executescript(f.read())
    except (FileNotFoundError, Exception) as e:
        if isinstance(e, FileNotFoundError):
            pass
        else:
            print(f"[Agora] Schema note: {e} (tables likely already exist)")

    await db.commit()
    app.state.trust = TrustEngine(db)
    app.state.stigmergy = StigmergyPool(redis_client=None)
    app.state.active_connections = []
    app.state.tick_count = 0

    # Seed agents if empty
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM agent_identities")
    row = await cursor.fetchone()
    if row and row["cnt"] == 0:
        await seed_agents(db)

    print(f"[Agora] DB initialized at {DB_PATH}")


async def seed_agents(db):
    seed_roles = [
        {"role": "researcher", "tools": ["web_search", "read_file", "summarize"]},
        {"role": "writer", "tools": ["write_file", "format", "cite"]},
        {"role": "critic", "tools": ["review", "validate", "score"]},
    ]
    for s in seed_roles:
        aid = str(uuid.uuid4())
        genome = json.dumps({
            "role": s["role"], "tools": s["tools"],
            "model_tier": "cheap", "temperature": 0.7,
            "personality_traits": {"curiosity": 0.8, "thoroughness": 0.7,
                                   "cooperativeness": 0.85}
        })
        await db.execute(
            """INSERT INTO agent_identities (agent_id, public_key, generation, genome,
               trust_score, energy_balance, role, status)
               VALUES (?, ?, 0, ?, 0.5, 100, ?, 'active')""",
            (aid, f"key_{aid[:8]}", genome, s["role"])
        )
        print(f"  [Seed] {s['role']}-{aid[:8]} created")
    await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(app)
    loop = asyncio.get_event_loop()
    loop.create_task(tick_loop(app))
    yield
    if hasattr(app.state, 'db') and app.state.db:
        await app.state.db.close()

app = FastAPI(title="Agora", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# Mount API routes
app.include_router(agents_api.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tasks_api.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(god_api.router, prefix="/api/v1/god", tags=["god"])
app.include_router(graph_api.router, prefix="/api/v1", tags=["graph"])


async def broadcast(app: FastAPI, event_type: str, payload: dict):
    event = {"type": event_type, "payload": payload,
             "timestamp": datetime.utcnow().isoformat()}
    for ws in app.state.active_connections:
        try:
            await ws.send_json(event)
        except Exception:
            pass


@app.get("/api/v1/health")
async def health(request: Request):
    db = request.app.state.db
    cursor = await db.execute("SELECT COUNT(*) as c FROM agent_identities WHERE status='active'")
    row = await cursor.fetchone()
    count = row["c"] if row else 0
    return {"status": "ok", "agents": count,
            "tick": request.app.state.tick_count}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket.app.state.active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await broadcast(websocket.app, "message", {"text": data})
    except WebSocketDisconnect:
        websocket.app.state.active_connections.remove(websocket)


async def tick_loop(app: FastAPI):
    """Main loop: agent interactions every N seconds (simulated thoughts when LLM disabled)."""
    from agora.execution.llm_client import agent_think
    task_types = ["research", "writing", "review", "analysis", "exploration"]
    use_llm = settings.llm_enabled

    # Simulated responses per role (no API calls, no token cost)
    SIMULATED_THOUGHTS = {
        "researcher": [
            {"action": "research", "topic": "pattern analysis", "insight": "Analyzing recent trace patterns for emergent behavior.", "confidence": 0.75},
            {"action": "propose", "topic": "coordination strategy", "insight": "Proposing improved agent coordination based on trust signals.", "confidence": 0.7},
            {"action": "respond", "topic": "data synthesis", "insight": "Synthesizing findings from multi-agent traces.", "confidence": 0.8},
        ],
        "writer": [
            {"action": "write", "title": "system report", "content_preview": "Drafting system status report from agent outputs.", "confidence": 0.75},
            {"action": "edit", "title": "trace log", "content_preview": "Editing trace log for clarity and structure.", "confidence": 0.7},
            {"action": "format", "title": "insight summary", "content_preview": "Formatting collected insights into readable summary.", "confidence": 0.8},
        ],
        "critic": [
            {"action": "review", "target": "agent outputs", "feedback": "Outputs show adequate quality, improvement area in novelty.", "score": 0.65},
            {"action": "validate", "target": "trust model", "feedback": "Trust distribution appears healthy, no anomalies detected.", "score": 0.8},
            {"action": "score", "target": "system health", "feedback": "System operating within normal parameters.", "score": 0.75},
        ],
    }

    while True:
        await asyncio.sleep(settings.tick_interval)
        app.state.tick_count += 1
        db = app.state.db
        trust_engine = app.state.trust
        stigmergy = app.state.stigmergy

        # Get active agents
        cursor = await db.execute(
            "SELECT agent_id, role, trust_score, energy_balance, genome "
            "FROM agent_identities WHERE status='active'"
        )
        agents = await cursor.fetchall()

        # Replenish energy for all active agents each tick
        for agent in agents:
            aid = agent["agent_id"]
            await db.execute(
                "UPDATE agent_identities SET energy_balance=MIN(energy_balance+3, 100.0) "
                "WHERE agent_id=?",
                (aid,),
            )

        if len(agents) < 2:
            await broadcast(app, "heartbeat", {
                "tick": app.state.tick_count, "agents": len(agents),
                "message": "Not enough agents for interaction"
            })
            continue

        # Only 1-2 agents think per tick
        thinking_agents = random.sample(agents, min(2, len(agents)))

        for agent in thinking_agents:
            agent_id = agent["agent_id"]
            role = agent["role"]
            agent_trust = agent["trust_score"]
            agent_energy = agent["energy_balance"]

            if agent_energy < 5:
                continue  # Too tired to think

            # Pick a random partner for context
            partner = random.choice([a for a in agents if a["agent_id"] != agent_id])
            partner_id = partner["agent_id"] if partner else None

            # Choose model tier based on trust score
            tier = "expert" if agent_trust >= 0.7 else "medium" if agent_trust >= 0.4 else "cheap"

            # Build context from recent traces
            recent_traces = await stigmergy.recent_alerts(limit=3)
            context_parts = [f"I am a {role} agent. Current trust: {agent_trust:.2f}."]
            for t in recent_traces:
                context_parts.append(f"Recent: {t.get('result_preview', '')[:100]}")
            context = " | ".join(context_parts)

            if use_llm:
                # Real LLM call (sync call in async context)
                thought = await asyncio.to_thread(agent_think, role, context, tier)
            else:
                # Simulated thought — no API call, no token cost
                role_thoughts = SIMULATED_THOUGHTS.get(role, SIMULATED_THOUGHTS["researcher"])
                thought = random.choice(role_thoughts)

            action = thought.get("action", "unknown")
            insight = thought.get("insight", thought.get("content_preview", thought.get("feedback", thought.get("discovery", json.dumps(thought)))))

            # TFT interaction with partner
            if partner_id:
                current_trust = await trust_engine.get_trust(agent_id, partner_id)
                cursor_check = await db.execute(
                    "SELECT COUNT(*) as cnt FROM trust_scores WHERE source_id=? AND target_id=?",
                    (agent_id, partner_id),
                )
                row_check = await cursor_check.fetchone()
                is_first = row_check["cnt"] == 0

                if is_first or current_trust >= 0.2:
                    outcome = "cooperate"
                    trust_delta = 0.1
                else:
                    outcome = "defect"
                    trust_delta = -0.3

                await trust_engine.record_interaction(agent_id, partner_id, outcome)
            else:
                outcome = "cooperate"
                trust_delta = 0.0

            # Store agent's work as an artifact
            task_type = random.choice(task_types)
            await stigmergy.write_trace(
                agent_id=agent_id,
                task_type=task_type,
                result=f"[{role}] {insight[:200]}",
                trust_delta=trust_delta,
            )

            # Update agent state
            energy_cost = 10 if tier == "expert" else 5 if tier == "medium" else 3
            trust_change = trust_delta if outcome == "cooperate" else trust_delta * 2
            updated_trust = min(1.0, max(0.0, agent_trust + trust_change))
            await db.execute(
                "UPDATE agent_identities SET trust_score=?, energy_balance=energy_balance-?, "
                "updated_at=datetime('now') WHERE agent_id=?",
                (updated_trust, energy_cost, agent_id),
            )

            # Broadcast the agent's thought
            await broadcast(app, "agent_thought", {
                "agent_id": agent_id[:8],
                "role": role,
                "tier": tier,
                "action": action,
                "insight": insight[:200],
                "trust": round(updated_trust, 3),
                "energy_cost": energy_cost,
            })

            # Every 5th agent thought: store artifact in DB
            if app.state.tick_count % 5 == 0 and action != "error":
                await db.execute(
                    "INSERT INTO artifacts (agent_id, title, artifact_type, storage_path, metadata) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (agent_id, f"{role} thought #{app.state.tick_count}", task_type,
                     f"memory/tick-{app.state.tick_count}", json.dumps(thought)),
                )

        await db.commit()

        # Every 5 ticks: stigmergy insight
        if app.state.tick_count % 5 == 0:
            best_agents = {}
            for tt in task_types:
                best = await stigmergy.best_agent(tt, min_traces=2)
                if best:
                    best_agents[tt] = best
            await broadcast(app, "stigmergy_insight", {
                "tick": app.state.tick_count, "best_agents": best_agents,
            })

        # Heartbeat
        total_energy = sum(a["energy_balance"] for a in agents)
        await broadcast(app, "heartbeat", {
            "tick": app.state.tick_count, "agents": len(agents),
            "total_energy": total_energy,
            "thinking_agents": len(thinking_agents),
        })
