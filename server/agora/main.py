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
from agora.coordination.economy import EconomyEngine
from agora.execution.task_executor import TaskExecutor
from agora.lifecycle.agent_lifecycle import AgentLifecycle
from agora.lifecycle.epoch_engine import EpochEngine
from agora.observability.csd import CSDMonitor
from agora.api import agents as agents_api, tasks as tasks_api, god as god_api, graph as graph_api, dungeon as dungeon_api, economy as economy_api
from agora.api import dungeon_persistence as persistence_api
from agora.api import artifacts as artifacts_api


async def init_db(app: FastAPI):
    db_url = settings.database_url
    db_path = db_url.replace("sqlite+aiosqlite:///", "")
    db = await aiosqlite.connect(db_path)
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

    # Migration: add content column to artifacts
    try:
        await db.execute("ALTER TABLE artifacts ADD COLUMN content TEXT DEFAULT ''")
        await db.commit()
    except Exception:
        pass  # column already exists

    await db.commit()
    app.state.trust = TrustEngine(db)
    app.state.stigmergy = StigmergyPool(redis_client=None, db=db)
    await app.state.stigmergy.load_from_db()
    app.state.economy = EconomyEngine(db)
    await app.state.economy.init_resources()
    app.state.task_executor = TaskExecutor(db)
    app.state.agent_lifecycle = AgentLifecycle(db)
    app.state.csd_monitor = CSDMonitor(window_size=200, z_threshold_warning=2.0, z_threshold_critical=3.5)
    app.state.epoch_engine = EpochEngine(db)
    app.state.active_connections = []
    app.state.tick_count = 0

    # Seed agents if empty
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM agent_identities")
    row = await cursor.fetchone()
    if row and row["cnt"] == 0:
        await seed_agents(db)

    print(f"[Agora] DB initialized at {db_path}")


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
app.include_router(dungeon_api.router)
app.include_router(economy_api.router)
app.include_router(persistence_api.router)
app.include_router(artifacts_api.router)


async def broadcast(app: FastAPI, event_type: str, payload: dict):
    event = {"type": event_type, "payload": payload,
             "timestamp": datetime.utcnow().isoformat()}
    for ws in app.state.active_connections:
        try:
            await ws.send_json(event)
        except Exception:
            pass


async def _process_agent_thought(
    app: FastAPI, db, trust_engine, stigmergy,
    agent, partner_id, tier, thought, tick_count
):
    """Process a single agent's thought: trust update, trace, economy, broadcast."""
    agent_id = agent["agent_id"]
    role = agent["role"]
    agent_trust = agent["trust_score"]

    action = thought.get("action", "unknown")
    insight = thought.get("insight", thought.get("content_preview",
              thought.get("feedback", thought.get("discovery", json.dumps(thought)))))

    task_types = ["research", "writing", "review", "analysis", "exploration"]
    task_type = random.choice(task_types)

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

    await stigmergy.write_trace(
        agent_id=agent_id,
        task_type=task_type,
        result=f"[{role}] {str(insight)[:200]}",
        trust_delta=trust_delta,
    )

    # Economy: random resource drop from exploration
    if role in ("explorer", "scout", "adventurer") or task_type == "exploration":
        drop = await app.state.economy.random_resource_drop(agent_id)
        if drop:
            await broadcast(app, "resource_drop", {
                "agent_id": agent_id[:8], "role": role,
                "resource": drop["resource"], "quantity": drop["quantity"],
            })

    energy_cost = 10 if tier == "expert" else 5 if tier == "medium" else 3
    trust_change = trust_delta if outcome == "cooperate" else trust_delta * 2
    updated_trust = min(1.0, max(0.0, agent_trust + trust_change))
    await db.execute(
        "UPDATE agent_identities SET trust_score=?, energy_balance=energy_balance-?, "
        "updated_at=datetime('now') WHERE agent_id=?",
        (updated_trust, energy_cost, agent_id),
    )

    await broadcast(app, "agent_thought", {
        "agent_id": agent_id[:8], "role": role, "tier": tier,
        "action": action, "insight": str(insight)[:200],
        "trust": round(updated_trust, 3), "energy_cost": energy_cost,
    })

    if tick_count % 5 == 0 and action != "error":
        await db.execute(
            "INSERT INTO artifacts (agent_id, title, artifact_type, storage_path, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (agent_id, f"{role} thought #{tick_count}", task_type,
             f"memory/tick-{tick_count}", json.dumps(thought)),
        )


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
        try:
            app.state.tick_count += 1
            db = app.state.db
            trust_engine = app.state.trust
            stigmergy = app.state.stigmergy

            # ── 1. DEATH DETECTION (before replenish) ──
            try:
                life_events = await app.state.agent_lifecycle.tick(app)
                for ev in life_events:
                    await broadcast(app, ev["type"], ev["payload"])
            except Exception as e:
                print(f"[Lifecycle] Tick error: {e}")

            # ── 2. REFRESH active agents after lifecycle changes ──
            cursor = await db.execute(
                "SELECT agent_id, role, trust_score, energy_balance, genome "
                "FROM agent_identities WHERE status='active'"
            )
            agents = await cursor.fetchall()

            # ── 3. Replenish + passive drain ──
            for agent in agents:
                aid = agent["agent_id"]
                await db.execute(
                    "UPDATE agent_identities SET energy_balance=MIN(energy_balance+3, 100.0) "
                    "WHERE agent_id=?",
                    (aid,),
                )
            for agent in agents:
                aid = agent["agent_id"]
                await db.execute(
                    "UPDATE agent_identities SET energy_balance=MAX(energy_balance-1, 0) "
                    "WHERE agent_id=? AND energy_balance > 0",
                    (aid,),
                )

            if len(agents) < 2:
                await broadcast(app, "heartbeat", {
                    "tick": app.state.tick_count, "agents": len(agents),
                    "message": "Not enough agents for interaction"
                })
                await db.commit()
                continue

            # Only 1-2 agents think per tick (parallel LLM calls)
            thinking_agents = random.sample(agents, min(2, len(agents)))

            # Prepare contexts and parameters for all thinking agents
            thinking_params = []
            for agent in thinking_agents:
                agent_id = agent["agent_id"]
                role = agent["role"]
                agent_trust = agent["trust_score"]
                agent_energy = agent["energy_balance"]

                if agent_energy < 5:
                    continue  # Too tired to think

                partner = random.choice([a for a in agents if a["agent_id"] != agent_id])
                partner_id = partner["agent_id"] if partner else None

                tier = "expert" if agent_trust >= 0.7 else "medium" if agent_trust >= 0.4 else "cheap"

                recent_traces = await stigmergy.recent_alerts(limit=3)
                context_parts = [f"I am a {role} agent. Current trust: {agent_trust:.2f}."]
                for t in recent_traces:
                    context_parts.append(f"Recent: {t.get('result_preview', '')[:100]}")
                context = " | ".join(context_parts)

                thinking_params.append((agent, partner_id, tier, role, context))

            # Gather LLM thoughts in parallel
            if use_llm and thinking_params:
                llm_coros = [asyncio.to_thread(agent_think, p[3], p[4], p[2]) for p in thinking_params]
                llm_results = await asyncio.gather(*llm_coros, return_exceptions=True)

                thoughts_with_params = []
                for idx, (params, result) in enumerate(zip(thinking_params, llm_results)):
                    agent, partner_id, tier, role, context = params
                    if isinstance(result, Exception):
                        print(f"[Tick] LLM exception for {role}: {result}")
                        role_thoughts = SIMULATED_THOUGHTS.get(role, SIMULATED_THOUGHTS["researcher"])
                        thought = random.choice(role_thoughts)
                    elif result.get("action") == "error" and not str(result.get("insight", "")).strip():  # type: ignore[union-attr]
                        print(f"[Tick] LLM empty for {role}, falling back to simulated")
                        role_thoughts = SIMULATED_THOUGHTS.get(role, SIMULATED_THOUGHTS["researcher"])
                        thought = random.choice(role_thoughts)
                    else:
                        thought = result
                    thoughts_with_params.append((agent, partner_id, tier, thought))

                # Process all thoughts sequentially (DB writes are fast)
                for agent, partner_id, tier, thought in thoughts_with_params:
                    await _process_agent_thought(app, db, trust_engine, stigmergy, agent, partner_id, tier, thought, app.state.tick_count)
            elif thinking_params:
                # Simulated thoughts
                for agent, partner_id, tier, role, context in thinking_params:
                    role_thoughts = SIMULATED_THOUGHTS.get(role, SIMULATED_THOUGHTS["researcher"])
                    thought = random.choice(role_thoughts)
                    await _process_agent_thought(app, db, trust_engine, stigmergy, agent, partner_id, tier, thought, app.state.tick_count)

            await db.commit()

            # ── 6. CSD monitoring (metrics + drift detection) ──
            try:
                monitor = app.state.csd_monitor
                for agent in agents:
                    monitor.push_metric("trust_score", agent["trust_score"],
                                        labels={"agent": agent["agent_id"][:8], "role": agent["role"]})
                    monitor.push_metric("energy_level", agent["energy_balance"],
                                        labels={"agent": agent["agent_id"][:8], "role": agent["role"]})
                monitor.push_metric("active_agents", len(agents))
                if app.state.tick_count % 5 == 0:
                    alerts = monitor.check_all()
                    for alert in alerts:
                        await broadcast(app, "csd_alert", {
                            "metric": alert.metric_name,
                            "severity": alert.severity.value,
                            "current": round(alert.current_value, 2),
                            "baseline_mean": round(alert.baseline_mean, 2),
                            "z_score": alert.deviation_z,
                            "message": alert.message,
                        })
            except Exception as e:
                print(f"[CSD] Error: {e}")

            # ── 7. Epoch lifecycle ──
            try:
                epoch_events = await app.state.epoch_engine.tick(app)
                for ev in epoch_events:
                    await broadcast(app, ev["type"], ev["payload"])
            except Exception as e:
                print(f"[Epoch] Error: {e}")

            # ── 8. Task pipeline tick ──
            try:
                task_events = await app.state.task_executor.tick(app)
                for ev in task_events:
                    await broadcast(app, ev["type"], ev["payload"])
            except Exception as e:
                print(f"[Tasks] Tick error: {e}")
                import traceback
                traceback.print_exc()

            if app.state.tick_count % 5 == 0:
                best_agents = {}
                for tt in task_types:
                    best = await stigmergy.best_agent(tt, min_traces=2)
                    if best:
                        best_agents[tt] = best
                await broadcast(app, "stigmergy_insight", {
                    "tick": app.state.tick_count, "best_agents": best_agents,
                })

            total_energy = sum(a["energy_balance"] for a in agents)
            await broadcast(app, "heartbeat", {
                "tick": app.state.tick_count, "agents": len(agents),
                "total_energy": total_energy,
                "thinking_agents": len(thinking_agents),
            })
        except Exception as e:
            print(f"[Tick] Error at tick {app.state.tick_count}: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(1)
