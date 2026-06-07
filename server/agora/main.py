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
from agora.coordination.economy_config import get_role_config, ROLE_ECONOMY
from agora.coordination.stigmergy import StigmergyPool
from agora.coordination.economy import EconomyEngine
from agora.agent_os.agent_os import AgentOS
from agora.agent_os.physical_world import PhysicalWorld
from agora.harness.state_store import StateStore
from agora.harness.lifecycle_hooks import LifecycleHooks
from agora.harness.tool_registry import ToolRegistry
from agora.harness.execution_loop import ExecutionEngine
from agora.harness.context_manager import ContextManager
from agora.harness.evaluation import EpochEvaluator
from agora.scheduler.room_cluster import RoomClusterScheduler
from agora.controller.controller import Controller
from agora.execution.task_executor import TaskExecutor
from agora.lifecycle.agent_lifecycle import AgentLifecycle
from agora.lifecycle.epoch_engine import EpochEngine
from agora.observability.csd import CSDMonitor
from agora.api import agents as agents_api, tasks as tasks_api, god as god_api, graph as graph_api, dungeon as dungeon_api, economy as economy_api
from agora.api import dungeon_persistence as persistence_api
from agora.api import artifacts as artifacts_api
from agora.api import agent_os_api
from agora.api import physical_api
from agora.api import tool_registry_api as tool_registry_api
from agora.api import evaluation_api


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

    # Seed initial agent inventories for dungeon NPCs
    cursor = await db.execute(
        "SELECT COUNT(*) as c FROM agent_inventory"
    )
    row = await cursor.fetchone()
    if row and row["c"] == 0:
        seed_data = [
            ("00000000-0000-0000-0000-000000000001", 1, 5.0),   # Kael: gold_ore
            ("00000000-0000-0000-0000-000000000002", 2, 4.0),   # Lyra: herbs
            ("00000000-0000-0000-0000-000000000003", 5, 3.0),   # Mordecai: scroll_fragment
            ("00000000-0000-0000-0000-000000000003", 3, 2.0),   # Mordecai: crystal_shards
            ("00000000-0000-0000-0000-000000000004", 4, 4.0),   # Grom: iron_ingot
            ("00000000-0000-0000-0000-000000000004", 1, 2.0),   # Grom: gold_ore
            ("00000000-0000-0000-0000-000000000005", 2, 5.0),   # Zara: herbs
            ("00000000-0000-0000-0000-000000000005", 3, 1.0),   # Zara: crystal_shards
            ("00000000-0000-0000-0000-000000000006", 1, 3.0),   # Finn: gold_ore (trading capital)
            ("00000000-0000-0000-0000-000000000006", 4, 3.0),   # Finn: iron_ingot
            ("00000000-0000-0000-0000-000000000007", 4, 2.0),   # Guard: iron_ingot
        ]
        for agent_id, res_id, qty in seed_data:
            await db.execute(
                "INSERT INTO agent_inventory (agent_id, resource_id, quantity) VALUES (?, ?, ?)",
                (agent_id, res_id, qty),
            )
        await db.commit()
        print(f"[Economy] Seeded inventories for {len(set(a[0] for a in seed_data))} agents")
    app.state.task_executor = TaskExecutor(db)
    app.state.state_store = StateStore(db)
    app.state.lifecycle_hooks = LifecycleHooks(app.state.state_store, db)
    app.state.tool_registry = ToolRegistry(app.state.state_store, db)
    # LLM client setup (for execution loop think)
    from agora.execution.llm_client import agent_think
    app.state.execution_engine = ExecutionEngine(
        app.state.state_store, app.state.tool_registry, db,
        llm_client=lambda prompt: agent_think("system", prompt).get("insight", prompt[:200])
        if settings.llm_enabled else None,
    )
    app.state.context_manager = ContextManager(app.state.state_store, db)
    app.state.epoch_evaluator = EpochEvaluator(
        app.state.state_store, db, app.state.lifecycle_hooks
    )
    app.state.agent_os = AgentOS(db, state_store=app.state.state_store)
    await app.state.agent_os.ensure_os_initialized()
    app.state.physical_world = PhysicalWorld(db, llm_enabled=settings.llm_enabled)
    app.state.scheduler = RoomClusterScheduler(db)
    app.state.controller = Controller(app, db, app.state.state_store)
    app.state.controller._enable_multiprocessing(max_workers=4)
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
app.include_router(agent_os_api.router)
app.include_router(physical_api.router)
app.include_router(tool_registry_api.router)
app.include_router(evaluation_api.router)


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


async def _economy_tick(app: FastAPI):
    """Production, consumption, and auto-trading for all active agents."""
    eco = app.state.economy
    db = app.state.db

    # Get active agents with their roles
    cursor = await db.execute(
        "SELECT a.agent_id, a.role, a.energy_balance, d.npc_name "
        "FROM agent_identities a "
        "LEFT JOIN dungeon_npcs d ON a.agent_id = d.npc_id "
        "WHERE a.status='active'"
    )
    agents = await cursor.fetchall()

    for agent in agents:
        agent_id = agent["agent_id"]
        role = agent["role"]
        npc_name = agent["npc_name"] or ""
        energy = agent["energy_balance"] or 0

        # Determine config by NPC name first, then by role
        cfg = get_role_config(npc_name)
        if not cfg.get("produces") and not cfg.get("consumes"):
            cfg = get_role_config(role)

        # Skip if agent has no production/consumption (generic agents)
        if not cfg.get("produces") and not cfg.get("consumes"):
            continue

        # 1. PRODUCTION — each tick, agents produce role-specific resources
        for res_id, qty in cfg.get("produces", []):
            if energy >= 5:  # need at least some energy to produce
                await eco.add_to_inventory(agent_id, res_id, qty)
                await db.execute(
                    "UPDATE agent_identities SET energy_balance=MAX(energy_balance-1, 0) WHERE agent_id=?",
                    (agent_id,),
                )

        # 2. CONSUMPTION — agents consume resources they need
        for res_id, qty in cfg.get("consumes", []):
            removed = await eco.remove_from_inventory(agent_id, res_id, qty)
            if not removed:
                # Can't consume → auto-create a buy offer
                open_offers = await eco.get_open_offers(res_id)
                existing_buy = [o for o in open_offers if o["agent_id"] == agent_id and o["offer_type"] == "buy"]
                if not existing_buy:  # don't spam duplicate offers
                    # Price: 80% of market → competitive buy
                    price = await eco.get_market_price(res_id)
                    await eco.create_offer(agent_id, "buy", res_id, qty * 2, round(price * 0.8, 2))

        # 3. AUTO-SELL — surplus resources → create sell offers
        surplus = cfg.get("surplus_threshold", 3.0)
        deficit = cfg.get("deficit_threshold", 1.0)

        # Check inventory for resources this role produces
        inv = await eco.get_agent_inventory(agent_id)
        for item in inv:
            res_id = item["resource_id"]
            qty = item["quantity"]

            # Is this a resource the role produces?
            produces_ids = [p[0] for p in cfg.get("produces", [])]
            if res_id in produces_ids and qty > surplus:
                # Sell surplus
                sell_qty = qty - deficit
                if sell_qty > 0.5:
                    open_offers = await eco.get_open_offers(res_id)
                    existing_sell = [o for o in open_offers if o["agent_id"] == agent_id and o["offer_type"] == "sell"]
                    if not existing_sell:
                        price = await eco.get_market_price(res_id)
                        result = await eco.create_offer(agent_id, "sell", res_id, sell_qty, round(price * 1.1, 2))
                        if result.get("status") == "filled":
                            await app.state.stigmergy.write_trace(
                                agent_id=agent_id,
                                task_type="trade",
                                result=f"[{npc_name or role}] Sold {sell_qty:.1f}x resource #{res_id} for {result.get('total_energy', 0)} energy",
                                trust_delta=0.05,
                            )

    # ── D6: Finn arbitrage — buy low, sell high ──
    finn_id = "00000000-0000-0000-0000-000000000006"
    finn_name = "Finn"

    # Is Finn active?
    cursor = await db.execute(
        "SELECT energy_balance FROM agent_identities WHERE agent_id=? AND status='active'",
        (finn_id,),
    )
    finn = await cursor.fetchone()
    if finn and finn["energy_balance"] > 20:
        finn_energy = finn["energy_balance"]
        # Get all open offers
        all_offers = await eco.get_open_offers()
        sells = [o for o in all_offers if o["offer_type"] == "sell" and o["agent_id"] != finn_id]
        buys = [o for o in all_offers if o["offer_type"] == "buy" and o["agent_id"] != finn_id]

        for sell in sells:
            if finn_energy < 10:
                break
            # Find a buy offer for the same resource with higher price
            matching_buy = next(
                (b for b in buys if b["resource_id"] == sell["resource_id"]
                 and b["price_per_unit"] > sell["price_per_unit"] * 1.15),
                None
            )
            if matching_buy:
                # Can Finn execute this arbitrage?
                spread = matching_buy["price_per_unit"] - sell["price_per_unit"]
                trade_qty = min(sell["quantity"], matching_buy["quantity"], 3.0)
                total_cost = trade_qty * sell["price_per_unit"]
                total_revenue = trade_qty * matching_buy["price_per_unit"]
                profit = total_revenue - total_cost

                if profit > 1.0 and finn_energy >= total_cost:
                    # Buy from seller at their price
                    await eco.remove_from_inventory(sell["agent_id"], sell["resource_id"], trade_qty)
                    await eco.add_to_inventory(finn_id, sell["resource_id"], trade_qty)
                    await db.execute(
                        "UPDATE agent_identities SET energy_balance=energy_balance-? WHERE agent_id=?",
                        (total_cost, finn_id),
                    )
                    await db.execute(
                        "UPDATE agent_identities SET energy_balance=energy_balance+? WHERE agent_id=?",
                        (total_cost, sell["agent_id"]),
                    )

                    # Sell to buyer at their price
                    await eco.remove_from_inventory(finn_id, sell["resource_id"], trade_qty)
                    await eco.add_to_inventory(matching_buy["agent_id"], sell["resource_id"], trade_qty)
                    await db.execute(
                        "UPDATE agent_identities SET energy_balance=energy_balance-? WHERE agent_id=?",
                        (total_revenue, matching_buy["agent_id"]),
                    )
                    await db.execute(
                        "UPDATE agent_identities SET energy_balance=energy_balance+? WHERE agent_id=?",
                        (total_revenue - total_cost, finn_id),  # Finn keeps the profit
                    )

                    # Update offer quantities
                    for offer_id, qty in [(sell["id"], trade_qty), (matching_buy["id"], trade_qty)]:
                        remaining = qty_to_check = None
                        cursor_o = await db.execute("SELECT quantity FROM trade_offers WHERE id=?", (offer_id,))
                        row_o = await cursor_o.fetchone()
                        if row_o:
                            new_qty = row_o["quantity"] - qty
                            if new_qty <= 0:
                                await db.execute("UPDATE trade_offers SET status='filled', filled_at=datetime('now') WHERE id=?", (offer_id,))
                            else:
                                await db.execute("UPDATE trade_offers SET quantity=? WHERE id=?", (new_qty, offer_id))

                    # Record trade history
                    await db.execute(
                        "INSERT INTO trade_history (buyer_id, seller_id, resource_id, quantity, price_per_unit, total_energy) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (finn_id, sell["agent_id"], sell["resource_id"], trade_qty, sell["price_per_unit"], total_cost),
                    )
                    await db.execute(
                        "INSERT INTO trade_history (buyer_id, seller_id, resource_id, quantity, price_per_unit, total_energy) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (matching_buy["agent_id"], finn_id, sell["resource_id"], trade_qty, matching_buy["price_per_unit"], total_revenue),
                    )

                    await app.state.stigmergy.write_trace(
                        agent_id=finn_id,
                        task_type="trade",
                        result=f"[Finn] Arbitrage: bought #{sell['resource_id']} @{sell['price_per_unit']} → sold @{matching_buy['price_per_unit']}, profit {profit:.1f}⚡",
                        trust_delta=0.1,
                    )

                    finn_energy += profit - total_cost  # deduct cost

    await db.commit()


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

            # ── 1. DEATH DETECTION (before replenish, global) ──
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

            if len(agents) < 2:
                await broadcast(app, "heartbeat", {
                    "tick": app.state.tick_count, "agents": len(agents),
                    "message": "Not enough agents for interaction"
                })
                await db.commit()
                continue

            # ── 2.5. LIFECYCLE HOOKS — pre-tick byzantine validation ──
            npc_ids = []
            try:
                hooks = app.state.lifecycle_hooks
                all_active_npcs = await app.state.state_store.get_all_active_npcs()
                npc_ids = [n["npc_id"] for n in all_active_npcs]
                pre_violations = await hooks.pre_tick(npc_ids)
                for v in pre_violations:
                    await broadcast(app, "byzantine_violation", {
                        "phase": "pre_tick",
                        "type": v["type"],
                        "detail": v["detail"],
                    })
            except Exception as e:
                print(f"[LifecycleHooks] Pre-tick error: {e}")

            # ── 3. CONTROLLER — room cluster dispatch ──
            # Each room = independent cluster dispatched by Controller
            try:
                controller_events = await app.state.controller.tick()
                for ev in controller_events:
                    await broadcast(app, ev["type"], ev["payload"])
            except Exception as e:
                print(f"[Controller] Error: {e}")
                import traceback
                traceback.print_exc()

            # ── 3.5. LIFECYCLE HOOKS — post-tick byzantine validation ──
            try:
                hooks = app.state.lifecycle_hooks
                post_violations = await hooks.post_tick(npc_ids)
                for v in post_violations:
                    await broadcast(app, "byzantine_violation", {
                        "phase": "post_tick",
                        "type": v["type"],
                        "severity": v.get("severity", "warning"),
                        "detail": v["detail"],
                    })

                # Periodic deep checks (every 10 ticks)
                if app.state.tick_count % 10 == 0:
                    for nid in npc_ids:
                        skill_v = await hooks.validate_skill_limits(nid)
                        if skill_v:
                            await broadcast(app, "byzantine_violation", {
                                "phase": "deep_check",
                                "type": skill_v["type"],
                                "severity": skill_v.get("severity", "warning"),
                                "detail": skill_v["detail"],
                            })

                    dup_violations = await hooks.detect_duplicate_help_requests()
                    for v in dup_violations:
                        await broadcast(app, "byzantine_violation", {
                            "phase": "deep_check",
                            "type": v["type"],
                            "severity": v.get("severity", "warning"),
                            "detail": v["detail"],
                        })
            except Exception as e:
                print(f"[LifecycleHooks] Post-tick error: {e}")

            # Only 1-2 agents think per tick (parallel LLM calls, global pool)
            thinking_agents = random.sample(agents, min(2, len(agents)))
            # ── 4. PROCESS THOUGHTS (global — LLM inferences batch) ──
            # Prepare contexts and parameters for all thinking agents
            thinking_params = []
            for agent in thinking_agents:
                agent_id = agent["agent_id"]
                role = agent["role"]
                agent_trust = agent["trust_score"]
                agent_energy = agent["energy_balance"]

                if agent_energy < 5:
                    continue

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
                    elif result.get("action") == "error" and not str(result.get("insight", "")).strip():
                        print(f"[Tick] LLM empty for {role}, falling back to simulated")
                        role_thoughts = SIMULATED_THOUGHTS.get(role, SIMULATED_THOUGHTS["researcher"])
                        thought = random.choice(role_thoughts)
                    else:
                        thought = result
                    thoughts_with_params.append((agent, partner_id, tier, thought))

                for agent, partner_id, tier, thought in thoughts_with_params:
                    await _process_agent_thought(app, db, trust_engine, stigmergy, agent, partner_id, tier, thought, app.state.tick_count)
            elif thinking_params:
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

            # ── 9. Economy tick (production, consumption, auto-trade) ──
            if app.state.tick_count % 2 == 0:  # every 2 ticks
                try:
                    await _economy_tick(app)
                except Exception as e:
                    print(f"[Economy] Tick error: {e}")
                    import traceback
                    traceback.print_exc()

            # ── 10. Stigmergic economy signals (every 10 ticks) ──
            if app.state.tick_count > 0 and app.state.tick_count % 10 == 0:
                try:
                    resources = await app.state.economy.get_all_resources()
                    price_signals = []
                    for r in resources:
                        price = await app.state.economy.get_market_price(r["id"])
                        price_signals.append(f"{r['name']}={price}")
                    await app.state.stigmergy.write_trace(
                        agent_id="system",
                        task_type="market_prices",
                        result=" | ".join(price_signals),
                        trust_delta=0.0,
                    )
                    await app.state.stigmergy.write_trace(
                        agent_id="system",
                        task_type="market_activity",
                        result=f"Active agents: {len(agents)}. Total energy: {sum(a['energy_balance'] for a in agents):.0f}",
                        trust_delta=0.0,
                    )
                except Exception as e:
                    print(f"[Stigmergy] Market signal error: {e}")

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
