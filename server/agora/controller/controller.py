"""Controller-Worker — Phase III OOOE.

Controller:
  - Získa room clustre z Redis geo-query
  - Dispatchnuje room ticky workerom (alebo in-process)
  - Zbiera výsledky a merguje
  - Fallback: single-process ak nie sú workeri

Worker:
  - Spracuje jeden room cluster tick
  - Volá AgentOS + PhysicalWorld pre NPC v room
  - Vracia výsledky

Fáza IIIa: single-process (tento modul)
Fáza IIIb: multiprocessing (concurrent.futures.ProcessPoolExecutor)
Fáza IIIc: Redis-backed distributed workers
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


class Controller:
    """Central dispatcher — OOOE Controller podľa Phase III.

    Získava room clustre → dispatchuje workerom → merguje výsledky.
    """

    def __init__(self, app, db, state_store=None):
        self.app = app
        self.db = db
        self.state_store = state_store
        self._workers: dict[str, Any] = {}  # room_name -> worker (future Phase IIIb)
        self._room_priorities: dict[str, float] = {}
        self._tick_count = 0
        self._executor: Optional[ProcessPoolExecutor] = None
        self._multiprocessing = False

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
                    "role": npc.get("role", ""),
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
                # Find position from dungeon NPCs
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
            score = len(agents) * 2.0  # base: number of agents

            # Confused/panicked NPCs = higher priority
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
    # ROOM TICK (in-process worker)
    # ═══════════════════════════════════════════

    async def _run_room_tick(self, room: str, agents_in_room: list[dict]) -> dict:
        """Execute one room cluster tick (in-process).

        Returns summary dict with results.
        """
        result = {
            "room": room,
            "npcs_ticked": 0,
            "errors": [],
            "events": [],
            "duration_ms": 0,
        }
        start = time.monotonic()

        npcs = [a for a in agents_in_room if a.get("type") == "npc"]
        thinking = [a for a in agents_in_room if a.get("type") == "agent"]

        try:
            # ── 1. Agent OS tick for NPCs in this room ──
            if npcs and hasattr(self.app.state, 'agent_os') and self.app.state.agent_os:
                npc_ids = [n.get("id") or n.get("name") for n in npcs]
                # Resolve names to IDs
                resolved_ids = []
                for n in npcs:
                    nid = n.get("id")
                    if not nid:
                        cursor = await self.db.execute(
                            "SELECT npc_id FROM dungeon_npcs WHERE npc_name=?", (n.get("name"),)
                        )
                        row = await cursor.fetchone()
                        if row:
                            nid = row["npc_id"]
                    if nid:
                        resolved_ids.append(nid)

                if resolved_ids:
                    await self.app.state.agent_os.cluster_tick(
                        npc_ids=resolved_ids,
                        broadcast_fn=lambda t, p: result["events"].append({"type": t, "payload": p}),
                    )
                    result["npcs_ticked"] = len(resolved_ids)

            # ── 2. Energy replenish for thinking agents ──
            db = self.db
            for agent in thinking:
                aid = agent.get("id")
                if not aid:
                    continue
                try:
                    cursor = await db.execute(
                        "SELECT energy_balance FROM agent_identities WHERE agent_id=? AND status='active'",
                        (aid,),
                    )
                    row = await cursor.fetchone()
                    if row:
                        energy = row["energy_balance"]
                        replenish = 4 if energy < 20 else (2 if energy < 50 else 1)
                        await db.execute(
                            "UPDATE agent_identities SET energy_balance=MIN(energy_balance+?, 100.0) WHERE agent_id=?",
                            (replenish, aid),
                        )
                except Exception as e:
                    result["errors"].append(f"Energy error: {e}")

            # ── 3. Physical movement + Redis sync ──
            if npcs and hasattr(self.app.state, 'physical_world') and self.app.state.physical_world:
                try:
                    complete_fn = (
                        lambda req_id, helper_name, problem_type, bfn: (
                            self.app.state.agent_os.complete_help(
                                req_id, helper_name, problem_type, bfn,
                            )
                        )
                        if hasattr(self.app.state, 'agent_os') and self.app.state.agent_os
                        else None
                    )
                    await self.app.state.physical_world.physical_help_tick(
                        broadcast_fn=lambda t, p: result["events"].append({"type": t, "payload": p}),
                        complete_help_fn=complete_fn,
                    )
                    # Move NPCs along paths AND sync ALL NPC positions to Redis
                    for npc_info in npcs:
                        nid = npc_info.get("id") or npc_info.get("name")
                        name = npc_info.get("name", "")
                        if nid and nid in self.app.state.physical_world._pending_moves:
                            nx, ny = await self.app.state.physical_world.move_npc_toward(nid, 0, 0)
                        else:
                            # Still sync position even if not moving
                            nx = npc_info.get("x", 0)
                            ny = npc_info.get("y", 0)
                        if name:
                            await update_npc_position(name, nx, ny, room)
                except Exception as e:
                    result["errors"].append(f"Physical error: {e}")

        except Exception as e:
            result["errors"].append(f"Room tick error: {e}")

        result["duration_ms"] = round((time.monotonic() - start) * 1000, 1)
        return result

    # ═══════════════════════════════════════════
    # MULTIPROCESSING WORKER
    # ═══════════════════════════════════════════

    def _enable_multiprocessing(self, max_workers: int = 4):
        """Enable parallel room tick via ProcessPoolExecutor.

        Volá sa explicitne — nie je predvolene zapnuté.
        """
        if not self._executor:
            self._executor = ProcessPoolExecutor(max_workers=max_workers)
            self._multiprocessing = True
            print(f"[Controller] Multiprocessing enabled: {max_workers} workers")

    async def _run_room_parallel(self, room: str, agents: list[dict]) -> dict:
        """Run room tick in separate process (Phase IIIb).

        Serializuje room+agents, dispatchne worker processu.
        """
        # For Phase IIIb: run_room_tick needs app state access
        # which doesn't serialize across processes easily.
        # For now, fall back to in-process for correctness.
        return await self._run_room_tick(room, agents)

    # ═══════════════════════════════════════════
    # MAIN TICK
    # ═══════════════════════════════════════════

    async def tick(self) -> list[dict]:
        """Main controller tick — discover clusters → dispatch → merge.

        Returns aggregated events for broadcasting.
        """
        self._tick_count += 1
        all_events = []

        # ── Redis sync (first tick + every N ticks) ──
        if self._tick_count == 1 or self._tick_count % REDIS_SYNC_INTERVAL == 1:
            try:
                await sync_all_npcs_to_redis(self.db)
                # Verify sync
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
        ss = getattr(self.app.state, 'state_store', None)
        if ss:
            await ss.begin_tick(self._tick_count)

        try:
            # ── Dispatch room ticks ──
            room_results = []
            for room in schedule:
                if room in clusters and clusters[room]:
                    if self._multiprocessing and len(schedule) > 2:
                        result = await self._run_room_parallel(room, clusters[room])
                    else:
                        result = await self._run_room_tick(room, clusters[room])
                    room_results.append(result)

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
                print(f"[Controller] Tick {self._tick_count}: {len(room_results)} rooms, {total_npcs} NPCs [{durations}]")

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
