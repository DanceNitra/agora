"""Room Cluster Scheduler — proto Controller podľa OOOE filozofie.

Princíp:
  - Každá miestnosť = cluster agentov (Coupled state)
  - Agenti v rôznych miestnostiach = FREE → tickujú nezávisle
  - Agenti v rovnakej miestnosti = COUPLED → sync tick

Fáza I (tento modul): async task scheduler v jedinom procese.
Neskôr Fáza III: Controller-Worker s Redis geo-query + multiprocessing.
"""

import asyncio
import json
import random
from datetime import datetime
from typing import Callable, Optional

from agora.agent_os.dungeon_map import get_room_at

# Rooms in the dungeon
ROOMS = ["main_hall", "library", "treasury", "crypt"]

# Minimum agents needed for a cluster to tick (avoid empty cluster loops)
MIN_CLUSTER_SIZE = 1

# R_perception — agents more than this many tiles apart in the same room are
# still coupled if they're in the same room (room-level coupling threshold)
# For now: same room = always coupled (conservative)
INTERACT_TILES = 6  # ~192px for fine-grained coupling later


class RoomClusterScheduler:
    """Proto-Controller: groups agents by room and schedules cluster ticks."""

    def __init__(self, db):
        self.db = db
        self._room_priorities: dict[str, float] = {r: 0.0 for r in ROOMS}

    async def get_agent_rooms(self) -> dict[str, list[dict]]:
        """Group all active agents + NPCs by room.

        Returns dict[room_name, list[agent_info]]
        """
        # Get NPC positions from dungeon_npcs
        cursor = await self.db.execute(
            "SELECT npc_id, npc_name, pos_x, pos_y, role FROM dungeon_npcs WHERE status='active'"
        )
        npcs = await cursor.fetchall()

        # Get thinking agents from agent_identities
        cursor2 = await self.db.execute(
            "SELECT agent_id, role, trust_score, energy_balance, genome "
            "FROM agent_identities WHERE status='active'"
        )
        agents = await cursor2.fetchall()

        clusters: dict[str, list[dict]] = {r: [] for r in ROOMS}

        # Group NPCs by room
        for npc in npcs:
            room = get_room_at(npc["pos_x"], npc["pos_y"])
            clusters.setdefault(room, []).append({
                "type": "npc",
                "id": npc["npc_id"],
                "name": npc["npc_name"],
                "x": npc["pos_x"],
                "y": npc["pos_y"],
                "role": npc["role"],
            })

        # Group thinking agents by room (use pos_x/pos_y from dungeon_npcs)
        for agent in agents:
            aid = agent["agent_id"]
            # Find this agent's position in dungeon_npcs
            npc_match = next(
                (n for n in npcs if n["npc_id"] == aid), None
            )
            if npc_match:
                room = get_room_at(npc_match["pos_x"], npc_match["pos_y"])
            else:
                room = "main_hall"  # default for non-dungeon agents

            clusters.setdefault(room, []).append({
                "type": "agent",
                "id": aid,
                "role": agent["role"],
                "trust": agent["trust_score"],
                "energy": agent["energy_balance"],
                "genome": agent["genome"],
            })

        # Remove empty rooms
        return {r: items for r, items in clusters.items() if items}

    async def update_priorities(self, clusters: dict[str, list[dict]]):
        """Score each room cluster by activity level for priority scheduling.

        Priority = more work = higher score:
          - Confused/panicked NPCs → high priority (they need help)
          - Pending help requests → high priority (movement in progress)
          - More agents → moderate priority
        """
        for room, agents in clusters.items():
            score = 0.0

            # Count confused/panicked NPCs
            npc_ids = [a["id"] for a in agents if a["type"] == "npc"]
            if npc_ids:
                placeholders = ",".join("?" * len(npc_ids))
                cursor = await self.db.execute(
                    f"SELECT COUNT(*) as c FROM agent_brain "
                    f"WHERE npc_id IN ({placeholders}) "
                    f"AND state_of_mind IN ('confused', 'panicked', 'planning')",
                    npc_ids,
                )
                row = await cursor.fetchone()
                score += (row["c"] if row else 0) * 10.0

            # Count pending help requests involving this room
            cursor2 = await self.db.execute(
                f"SELECT COUNT(*) as c FROM agent_help_requests WHERE status='pending'"
            )
            row2 = await cursor2.fetchone()
            score += (row2["c"] if row2 else 0) * 5.0

            # Base: number of agents
            score += len(agents) * 2.0

            self._room_priorities[room] = score

    def get_schedule(self) -> list[str]:
        """Return rooms sorted by priority (highest first)."""
        return sorted(
            self._room_priorities.keys(),
            key=lambda r: self._room_priorities.get(r, 0),
            reverse=True,
        )

    async def run_cluster_tick(
        self,
        room: str,
        agents_in_room: list[dict],
        app,
        broadcast_fn: Optional[Callable] = None,
    ):
        """Run one tick for a single room cluster.

        Each cluster runs independently — in Phase III this will be
        dispatched to a Worker process.
        """
        npcs_in_room = [a for a in agents_in_room if a["type"] == "npc"]
        thinking_agents = [a for a in agents_in_room if a["type"] == "agent"]

        if not npcs_in_room and not thinking_agents:
            return

        room_label = room.replace("_", " ").title()

        # ── 1. Agent OS tick (body update + brain eval) for NPCs in this room ──
        if npcs_in_room and app.state.agent_os:
            npc_ids = [n["id"] for n in npcs_in_room]
            try:
                # Run OS tick for this cluster's NPCs only
                await app.state.agent_os.cluster_tick(
                    npc_ids=npc_ids,
                    broadcast_fn=broadcast_fn,
                )
            except Exception as e:
                print(f"[Scheduler:{room}] AgentOS error: {e}")

        # ── 2. Energy replenish/drain for thinking agents in this room ──
        db = app.state.db
        for agent in thinking_agents:
            aid = agent["id"]
            energy = agent["energy"]
            try:
                if energy < 20:
                    replenish = 4
                elif energy < 50:
                    replenish = 2
                else:
                    replenish = 1
                await db.execute(
                    "UPDATE agent_identities SET energy_balance=MIN(energy_balance+?, 100.0) "
                    "WHERE agent_id=?",
                    (replenish, aid),
                )
                drain = -2 if energy > 50 else -1
                await db.execute(
                    "UPDATE agent_identities SET energy_balance=MAX(energy_balance-?, 0) "
                    "WHERE agent_id=? AND energy_balance > 0",
                    (abs(drain), aid),
                )
            except Exception as e:
                print(f"[Scheduler:{room}] Energy error for {aid[:8]}: {e}")

        # ── 3. Physical world tick for this room's NPCs ──
        if npcs_in_room and app.state.physical_world:
            try:
                # We need the complete_help_fn similar to main.py
                complete_fn = (
                    lambda req_id, helper_name, problem_type, bfn: (
                        app.state.agent_os.complete_help(
                            req_id, helper_name, problem_type, bfn
                        )
                    )
                    if app.state.agent_os else None
                )
                # physical_help_tick handles ALL NPCs, not per-room (it processes DB requests)
                # But movement is per-NPC and independent per room
                await app.state.physical_world.physical_help_tick(
                    broadcast_fn=broadcast_fn,
                    complete_help_fn=complete_fn,
                )
                # Move NPCs in this room along their paths
                for npc_info in npcs_in_room:
                    nid = npc_info["id"]
                    if nid in app.state.physical_world._pending_moves:
                        nx, ny = await app.state.physical_world.move_npc_toward(nid, 0, 0)
                        if broadcast_fn:
                            await broadcast_fn("npc_moved", {
                                "npc": npc_info["name"],
                                "x": nx, "y": ny,
                                "room": room,
                            })
            except Exception as e:
                print(f"[Scheduler:{room}] Physical error: {e}")

        # ── 4. Room status broadcast ──
        if broadcast_fn:
            await broadcast_fn("room_tick", {
                "room": room,
                "npcs": len(npcs_in_room),
                "agents": len(thinking_agents),
                "label": room_label,
            })

    async def tick(self, app, broadcast_fn=None):
        """Main scheduler tick — runs all room clusters with State Store transaction."""
        ss = getattr(app.state, 'state_store', None)
        if ss:
            await ss.begin_tick(app.state.tick_count)

        try:
            clusters = await self.get_agent_rooms()
            await self.update_priorities(clusters)
            schedule = self.get_schedule()

            for room in schedule:
                if room in clusters and clusters[room]:
                    await self.run_cluster_tick(
                        room, clusters[room], app, broadcast_fn
                    )

            # ── Cross-room tasks (not cluster-specific) ──
            db = app.state.db
            await db.commit()

            if ss:
                await ss.commit_tick()
        except Exception:
            if ss:
                await ss.rollback_tick()
            raise
