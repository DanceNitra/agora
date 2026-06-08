"""Controller-Worker — Phase III OOOE.

Controller:
  - Získa room clustre z Redis/DB
  - Gather → Dispatch (worker computation) → Apply (DB writes)

Fáza IIIa: single-process (fallback)
Fáza IIIb: multiprocessing (ProcessPoolExecutor)  ← AKTÍVNA
Fáza IIIc: Redis-backed distributed workers (future)
"""

import asyncio
import json
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from typing import Any, Callable, Optional

from agora.coordination.redis_geo import (
    get_all_npc_rooms, get_npcs_in_room, update_npc_position, sync_all_npcs_to_redis,
)
from agora.agent_os.dungeon_map import get_room_at

# Rooms in the dungeon
ROOMS = ["main_hall", "library", "treasury", "crypt", "forge"]

# How many ticks between Redis syncs (DB → Redis)
REDIS_SYNC_INTERVAL = 5

# Min room count to bother with multiprocessing
MP_MIN_ROOMS = 3


class Controller:
    """Central dispatcher — OOOE Controller podľa Phase III.

    Získava room clustre → gather → parallel compute → sequential apply.
    """

    def __init__(self, app, db, state_store=None):
        self.app = app
        self.db = db
        self.state_store = state_store
        self._room_priorities: dict[str, float] = {}
        self._tick_count = 0
        self._executor: Optional[ProcessPoolExecutor] = None
        self._multiprocessing = False
        # Cache worker computation for gather/dispatch
        self._room_worker_data: dict[str, list[dict]] = {}

    # ═══════════════════════════════════════════
    # CLUSTER DISCOVERY
    # ═══════════════════════════════════════════

    async def get_clusters(self) -> dict[str, list[dict]]:
        """Get room clusters — uses Redis geo if available, else DB.

        Returns {room_name: [agent_info, ...]}
        """
        clusters: dict[str, list[dict]] = {r: [] for r in ROOMS}

        # Try Redis first
        try:
            room_map = await get_all_npc_rooms()
            if room_map and len(room_map) >= 3:
                for name, room in room_map.items():
                    if room in clusters:
                        clusters[room].append({
                            "type": "npc", "name": name,
                            "source": "redis",
                        })
                return {r: items for r, items in clusters.items() if items}
        except Exception:
            pass

        # Fallback: DB query + sync to Redis
        synced_count = 0
        try:
            cursor = await self.db.execute(
                "SELECT npc_id, npc_name, pos_x, pos_y, role FROM dungeon_npcs WHERE status='active'"
            )
            npcs = await cursor.fetchall()
            for npc in npcs:
                room = get_room_at(npc["pos_x"], npc["pos_y"])
                clusters.setdefault(room, []).append({
                    "type": "npc",
                    "id": npc["npc_id"],
                    "name": npc["npc_name"],
                    "role": npc["role"],
                    "x": npc["pos_x"],
                    "y": npc["pos_y"],
                })
                # Sync to Redis (first run only)
                try:
                    from agora.coordination.redis_geo import update_npc_position
                    asyncio.ensure_future(update_npc_position(
                        npc["npc_name"], npc["pos_x"], npc["pos_y"], room,
                    ))
                    synced_count += 1
                except Exception:
                    pass

            # Add thinking agents
            cursor2 = await self.db.execute(
                "SELECT agent_id, role, trust_score, energy_balance "
                "FROM agent_identities WHERE status='active'"
            )
            agents = await cursor2.fetchall()
            for agent in agents:
                aid = agent["agent_id"]
                match = next((n for n in npcs if n["npc_id"] == aid), None)
                room = get_room_at(match["pos_x"], match["pos_y"]) if match else "main_hall"
                clusters.setdefault(room, []).append({
                    "type": "agent",
                    "id": aid,
                    "role": agent["role"],
                })
        except Exception as e:
            print(f"[Controller] DB cluster error: {e}")

        if synced_count > 0:
            print(f"[Controller] Synced {synced_count} NPCs to Redis")

        return {r: items for r, items in clusters.items() if items}

    # ═══════════════════════════════════════════
    # PRIORITY
    # ═══════════════════════════════════════════

    async def update_priorities(self, clusters: dict[str, list[dict]]):
        """Score each room by urgency/activity."""
        for room, agents in clusters.items():
            score = len(agents) * 2.0

            npc_names = [a.get("name", "") for a in agents if a.get("type") == "npc"]
            if npc_names:
                try:
                    cursor = await self.db.execute(
                        "SELECT COUNT(*) as c FROM agent_brain b "
                        "JOIN dungeon_npcs d ON d.npc_id = b.npc_id "
                        "WHERE d.npc_name IN ({}) AND b.state_of_mind IN ('confused', 'panicked', 'planning')".format(
                            ",".join("?" * len(npc_names))
                        ),
                        npc_names,
                    )
                    row = await cursor.fetchone()
                    score += (row["c"] if row else 0) * 10.0
                except Exception:
                    pass

            self._room_priorities[room] = score

    def get_schedule(self) -> list[str]:
        """Return rooms sorted by priority (highest first)."""
        return sorted(
            self._room_priorities.keys(),
            key=lambda r: self._room_priorities.get(r, 0),
            reverse=True,
        )

    # ═══════════════════════════════════════════
    # GATHER → DISPATCH → APPLY
    # ═══════════════════════════════════════════

    async def _gather_npc_data(self, agents_in_room: list[dict]) -> list[dict]:
        """Čítame NPC stavy z DB pre worker spracovanie.

        Vracia serializable list dictov:
          [{npc_id, npc_name, health, stamina, hunger, fatigue,
            state_of_mind, current_goal, plan_stack}]
        """
        npcs_data = []
        for a in agents_in_room:
            if a.get("type") != "npc":
                continue
            npc_id = a.get("id")
            if not npc_id:
                cursor = await self.db.execute(
                    "SELECT npc_id FROM dungeon_npcs WHERE npc_name=?",
                    (a.get("name"),),
                )
                row = await cursor.fetchone()
                if row:
                    npc_id = row["npc_id"]
                else:
                    continue
            npc_name = a.get("name", "")

            # Gather NPC state
            cursor = await self.db.execute(
                "SELECT health FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
            )
            npc_row = await cursor.fetchone()
            health = npc_row["health"] if npc_row else 100.0

            stamina, hunger, fatigue = 100.0, 0.0, 0.0
            cursor = await self.db.execute(
                "SELECT stamina, hunger, fatigue FROM agent_body WHERE npc_id=?",
                (npc_id,),
            )
            body_row = await cursor.fetchone()
            if body_row:
                stamina = body_row["stamina"]
                hunger = body_row["hunger"]
                fatigue = body_row["fatigue"]

            state_of_mind = "focused"
            current_goal = ""
            plan_stack = "[]"
            cursor = await self.db.execute(
                "SELECT state_of_mind, current_goal, plan_stack FROM agent_brain WHERE npc_id=?",
                (npc_id,),
            )
            brain_row = await cursor.fetchone()
            if brain_row:
                state_of_mind = brain_row["state_of_mind"] or "focused"
                current_goal = brain_row["current_goal"] or ""
                plan_stack = brain_row["plan_stack"] or "[]"

            npcs_data.append({
                "npc_id": npc_id,
                "npc_name": npc_name,
                "health": health,
                "stamina": stamina,
                "hunger": hunger,
                "fatigue": fatigue,
                "state_of_mind": state_of_mind,
                "current_goal": current_goal,
                "plan_stack": plan_stack,
            })

        return npcs_data

    async def _apply_npc_updates(self, room: str, updates: list[dict]):
        """Aplikujeme výsledky worker computation do DB + Redis."""
        if not updates:
            return

        for u in updates:
            npc_id = u["npc_id"]

            # Update dungeon_npcs health
            await self.db.execute(
                "UPDATE dungeon_npcs SET health=? WHERE npc_id=?",
                (u["health"], npc_id),
            )

            # Update agent_body
            await self.db.execute(
                "UPDATE agent_body SET stamina=?, hunger=?, fatigue=? WHERE npc_id=?",
                (u["stamina"], u["hunger"], u["fatigue"], npc_id),
            )

            # Update agent_brain (state_of_mind)
            await self.db.execute(
                "UPDATE agent_brain SET state_of_mind=? WHERE npc_id=?",
                (u["state_of_mind"], npc_id),
            )

            # Redis sync (position)
            try:
                await update_npc_position(
                    u["npc_name"],
                    0,  # position doesn't change from body update
                    0,
                    room,
                )
            except Exception:
                pass

    # ═══════════════════════════════════════════
    # ROOM TICK (IN-PROCESS — fallback)
    # ═══════════════════════════════════════════

    async def _run_room_tick(self, room: str, agents_in_room: list[dict]) -> dict:
        """Execute one room cluster tick IN-PROCESS.

        Gather → compute → apply all in one method (Phase IIIa fallback).
        """
        result = {
            "room": room,
            "npcs_ticked": 0,
            "errors": [],
            "events": [],
            "duration_ms": 0,
        }
        start = time.monotonic()

        try:
            # ── 1. GATHER NPC state ──
            npc_states = await self._gather_npc_data(agents_in_room)
            if npc_states:
                result["npcs_ticked"] = len(npc_states)

            # ── 2. COMPUTE (in-process) ──
            from agora.controller.worker import process_room_worker

            task_dict = {
                "room": room,
                "npcs": npc_states,
                "tick_count": self._tick_count,
            }
            worker_result = process_room_worker(task_dict)

            if not worker_result.get("success"):
                result["errors"].append(worker_result.get("error", "Worker failed"))

            # ── 3. APPLY to DB ──
            await self._apply_npc_updates(room, worker_result.get("npc_updates", []))
            result["events"].extend(worker_result.get("events", []))

            # ── 4. AGENT OS cluster tick (LLM + help-seeking) ──
            npcs = [a for a in agents_in_room if a.get("type") == "npc"]
            npc_ids = [u["npc_id"] for u in worker_result.get("npc_updates", [])]
            if npc_ids and hasattr(self.app.state, "agent_os") and self.app.state.agent_os:
                try:
                    await self.app.state.agent_os.cluster_tick(
                        npc_ids=npc_ids,
                        broadcast_fn=lambda t, p: result["events"].append(
                            {"type": t, "payload": p}
                        ),
                        skip_body_update=True,  # worker už spravil body update
                    )
                except Exception as e:
                    result["errors"].append(f"AgentOS error: {e}")

            # ── 5. ENERGY replenish ──
            thinking = [a for a in agents_in_room if a.get("type") == "agent"]
            for agent in thinking:
                aid = agent.get("id")
                if not aid:
                    continue
                try:
                    cursor = await self.db.execute(
                        "SELECT energy_balance FROM agent_identities WHERE agent_id=? AND status='active'",
                        (aid,),
                    )
                    row = await cursor.fetchone()
                    if row:
                        energy = row["energy_balance"]
                        replenish = 4 if energy < 20 else (2 if energy < 50 else 1)
                        await self.db.execute(
                            "UPDATE agent_identities SET energy_balance=MIN(energy_balance+?, 100.0) WHERE agent_id=?",
                            (replenish, aid),
                        )
                except Exception as e:
                    result["errors"].append(f"Energy error: {e}")

            # ── 6. PHYSICAL WORLD movement ──
            if npcs and hasattr(self.app.state, "physical_world") and self.app.state.physical_world:
                try:
                    complete_fn = (
                        lambda req_id, helper_name, problem_type, bfn: (
                            self.app.state.agent_os.complete_help(
                                req_id, helper_name, problem_type, bfn,
                            )
                        )
                        if hasattr(self.app.state, "agent_os") and self.app.state.agent_os
                        else None
                    )
                    await self.app.state.physical_world.physical_help_tick(
                        broadcast_fn=lambda t, p: result["events"].append(
                            {"type": t, "payload": p}
                        ),
                        complete_help_fn=complete_fn,
                    )
                    for npc_info in npcs:
                        nid = npc_info.get("id") or npc_info.get("name")
                        name = npc_info.get("name", "")
                        if nid and nid in self.app.state.physical_world._pending_moves:
                            nx, ny = await self.app.state.physical_world.move_npc_toward(nid, 0, 0)
                        if name:
                            await update_npc_position(name, 0, 0, room)
                except Exception as e:
                    result["errors"].append(f"Physical error: {e}")

        except Exception as e:
            result["errors"].append(f"Room tick error: {e}")

        result["duration_ms"] = round((time.monotonic() - start) * 1000, 1)
        return result

    # ═══════════════════════════════════════════
    # MULTIPROCESSING WORKER
    # ═══════════════════════════════════════════

    def _enable_multiprocessing(self, max_workers: Optional[int] = None):
        """Enable parallel room tick via ProcessPoolExecutor."""
        if self._executor:
            return
        import os
        cpus = max_workers or max(2, os.cpu_count() or 2)
        self._executor = ProcessPoolExecutor(max_workers=cpus)
        self._multiprocessing = True
        print(f"[Controller] Multiprocessing enabled: {cpus} workers")

    async def _run_room_parallel(self, room: str, agents: list[dict]) -> dict:
        """Run room tick PARTIALLY in worker process (Phase IIIb).

        GATHER (main) → DISPATCH compute (worker) → APPLY (main).
        """
        result = {
            "room": room,
            "npcs_ticked": 0,
            "errors": [],
            "events": [],
            "duration_ms": 0,
        }
        tick_start = time.monotonic()

        try:
            # ── 1. GATHER (main process — DB reads) ──
            npc_states = await self._gather_npc_data(agents)
            if npc_states:
                result["npcs_ticked"] = len(npc_states)

            # ── 2. DISPATCH (worker process — pure computation) ──
            task_dict = {
                "room": room,
                "npcs": npc_states,
                "tick_count": self._tick_count,
            }
            loop = asyncio.get_event_loop()
            worker_result = await loop.run_in_executor(
                self._executor,
                _run_worker_wrapper,
                task_dict,
            )

            if not worker_result.get("success"):
                result["errors"].append(worker_result.get("error", "Worker failed"))
                return result

            # ── 3. APPLY (main process — DB writes) ──
            await self._apply_npc_updates(room, worker_result.get("npc_updates", []))
            result["events"].extend(worker_result.get("events", []))

            # ── 4. AGENT OS cluster tick (main process — needs app state) ──
            npcs = [a for a in agents if a.get("type") == "npc"]
            npc_ids = [u["npc_id"] for u in worker_result.get("npc_updates", [])]
            if npc_ids and hasattr(self.app.state, "agent_os") and self.app.state.agent_os:
                try:
                    await self.app.state.agent_os.cluster_tick(
                        npc_ids=npc_ids,
                        broadcast_fn=lambda t, p: result["events"].append(
                            {"type": t, "payload": p}
                        ),
                        skip_body_update=True,  # worker už spravil body update
                    )
                except Exception as e:
                    result["errors"].append(f"AgentOS error: {e}")

            # ── 5. ENERGY replenish (main process — DB writes) ──
            thinking = [a for a in agents if a.get("type") == "agent"]
            for agent in thinking:
                aid = agent.get("id")
                if not aid:
                    continue
                try:
                    cursor = await self.db.execute(
                        "SELECT energy_balance FROM agent_identities WHERE agent_id=? AND status='active'",
                        (aid,),
                    )
                    row = await cursor.fetchone()
                    if row:
                        energy = row["energy_balance"]
                        replenish = 4 if energy < 20 else (2 if energy < 50 else 1)
                        await self.db.execute(
                            "UPDATE agent_identities SET energy_balance=MIN(energy_balance+?, 100.0) WHERE agent_id=?",
                            (replenish, aid),
                        )
                except Exception as e:
                    result["errors"].append(f"Energy error: {e}")

            # ── 6. PHYSICAL WORLD movement (main process — needs app state) ──
            if npcs and hasattr(self.app.state, "physical_world") and self.app.state.physical_world:
                try:
                    complete_fn = (
                        lambda req_id, helper_name, problem_type, bfn: (
                            self.app.state.agent_os.complete_help(
                                req_id, helper_name, problem_type, bfn,
                            )
                        )
                        if hasattr(self.app.state, "agent_os") and self.app.state.agent_os
                        else None
                    )
                    await self.app.state.physical_world.physical_help_tick(
                        broadcast_fn=lambda t, p: result["events"].append(
                            {"type": t, "payload": p}
                        ),
                        complete_help_fn=complete_fn,
                    )
                    for npc_info in npcs:
                        nid = npc_info.get("id") or npc_info.get("name")
                        name = npc_info.get("name", "")
                        if nid and nid in self.app.state.physical_world._pending_moves:
                            nx, ny = await self.app.state.physical_world.move_npc_toward(nid, 0, 0)
                        if name:
                            await update_npc_position(name, 0, 0, room)
                except Exception as e:
                    result["errors"].append(f"Physical error: {e}")

        except Exception as e:
            result["errors"].append(f"Room tick error: {e}")

        result["duration_ms"] = round((time.monotonic() - tick_start) * 1000, 1)
        return result

    # ═══════════════════════════════════════════
    # MAIN TICK
    # ═══════════════════════════════════════════

    async def tick(self) -> list[dict]:
        """Main controller tick — discover → gather → parallel compute → apply.

        Returns aggregated events for broadcasting.
        """
        self._tick_count += 1
        all_events = []

        # ── Redis sync (first tick + every N ticks) ──
        if self._tick_count == 1 or self._tick_count % REDIS_SYNC_INTERVAL == 1:
            try:
                await sync_all_npcs_to_redis(self.db)
                rmap = await get_all_npc_rooms()
                print(f"[Controller] Redis has {len(rmap)} NPCs after sync")
            except Exception as e:
                print(f"[Controller] Redis sync error: {e}")

        # ── Discover clusters ──
        clusters = None
        try:
            clusters = await self.get_clusters()
        except Exception as e:
            print(f"[Controller] Cluster discovery error: {e}")

        if not clusters:
            return all_events

        await self.update_priorities(clusters)
        schedule = self.get_schedule()

        # ── State Store transaction ──
        ss = getattr(self.app.state, "state_store", None)
        if ss:
            await ss.begin_tick(self._tick_count)

        try:
            # ── Dispatch room ticks (parallel OR in-process) ──
            room_results = []
            tasks = []

            for room in schedule:
                if room in clusters and clusters[room]:
                    if self._multiprocessing and len(schedule) >= MP_MIN_ROOMS:
                        # Fire parallel — tasks run concurrently via asyncio.gather
                        tasks.append(self._run_room_parallel(room, clusters[room]))
                    else:
                        tasks.append(self._run_room_tick(room, clusters[room]))

            # Run all room ticks concurrently (whether parallel or in-process)
            if tasks:
                room_results = await asyncio.gather(*tasks, return_exceptions=True)
                # Handle exceptions
                processed = []
                for r in room_results:
                    if isinstance(r, Exception):
                        print(f"[Controller] Room exception: {r}")
                        processed.append({"room": "unknown", "npcs_ticked": 0,
                                          "errors": [str(r)], "events": [], "duration_ms": 0})
                    else:
                        processed.append(r)
                room_results = processed

            # ── Merge events ──
            for r in room_results:
                all_events.extend(r.get("events", []))
                if r.get("errors"):
                    for err in r["errors"]:
                        all_events.append({
                            "type": "controller_error",
                            "payload": {"room": r["room"], "error": err},
                        })

            # ── Commit DB ──
            await self.db.commit()
            if ss:
                await ss.commit_tick()

            # ── Log ──
            total_npcs = sum(r.get("npcs_ticked", 0) for r in room_results)
            if room_results:
                durations = ", ".join(f"{r['room']}={r['duration_ms']}ms" for r in room_results)
                mode = "MP" if self._multiprocessing and len(schedule) >= MP_MIN_ROOMS else "INLINE"
                print(f"[Controller] Tick {self._tick_count} [{mode}]: "
                      f"{len(room_results)} rooms, {total_npcs} NPCs [{durations}]")

        except Exception:
            if ss:
                await ss.rollback_tick()
            raise

        return all_events

    # ═══════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════

    def get_stats(self) -> dict:
        return {
            "tick": self._tick_count,
            "rooms": list(self._room_priorities.keys()),
            "priorities": {k: round(v, 1) for k, v in sorted(
                self._room_priorities.items(), key=lambda x: -x[1]
            )},
            "multiprocessing": self._multiprocessing,
        }

    async def cleanup(self):
        """Shutdown executor."""
        if self._executor:
            self._executor.shutdown()
            self._executor = None


# ═══════════════════════════════════════════
# MODULE-LEVEL WRAPPER (picklable for ProcessPoolExecutor)
# ═══════════════════════════════════════════


def _run_worker_wrapper(task_dict: dict) -> dict:
    """Picklable wrapper okolo worker funkcie.

    TOTO musí byť na module level (nie metóda triedy),
    aby to ProcessPoolExecutor vedel serializovať.
    """
    from agora.controller.worker import process_room_worker
    return process_room_worker(task_dict)
