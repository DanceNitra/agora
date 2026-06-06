"""Physical World — NPC movement, physical interactions, and library LLM oracle.

All NPC interactions require physical proximity:
  - NPCs move tile-by-tile via A* pathfinding
  - Help requests only work when both NPCs are in the same room
  - Knowledge queries require visiting the Library
  - Library has an LLM oracle that answers questions
"""

import asyncio
import json
import random
from datetime import datetime
from typing import Optional, Callable

from agora.agent_os.dungeon_map import (
    astar_path, astar_to_room, astar_to_npc,
    get_room_at, is_same_room, distance,
    MAP_W, MAP_H, TILE,
    build_passable_grid,
)

# ── NPC UUIDs and names ──
NPC_IDS = {
    "Kael":     "00000000-0000-0000-0000-000000000001",
    "Lyra":     "00000000-0000-0000-0000-000000000002",
    "Mordecai": "00000000-0000-0000-0000-000000000003",
    "Grom":     "00000000-0000-0000-0000-000000000004",
    "Zara":     "00000000-0000-0000-0000-000000000005",
    "Finn":     "00000000-0000-0000-0000-000000000006",
    "Guard":    "00000000-0000-0000-0000-000000000007",
}

UUID_TO_NAME = {v: k for k, v in NPC_IDS.items()}

# Interaction radius in pixels (about 1.5 tiles)
INTERACT_RADIUS = 48

# Library center (for knowledge queries)
LIBRARY_POS = (31 * TILE + TILE // 2, 3 * TILE + TILE // 2)  # tile (31, 3)


class PhysicalWorld:
    """Manages NPC positions, movement, and physical interactions."""

    def __init__(self, db, llm_enabled: bool = False, llm_client=None):
        self.db = db
        self.llm_enabled = llm_enabled
        self.llm_client = llm_client
        self._pending_moves: dict[str, list[tuple[float, float]]] = {}  # npc_id -> path
        self._active_requests: dict[int, dict] = {}  # help_request_id -> state

    async def load_positions(self) -> dict[str, dict]:
        """Load current NPC positions from DB."""
        cursor = await self.db.execute(
            "SELECT npc_id, npc_name, pos_x, pos_y, role FROM dungeon_npcs WHERE status='active'"
        )
        npcs = {}
        for row in await cursor.fetchall():
            npcs[row["npc_id"]] = {
                "name": row["npc_name"],
                "x": row["pos_x"],
                "y": row["pos_y"],
                "role": row["role"],
                "room": get_room_at(row["pos_x"], row["pos_y"]),
            }
        return npcs

    async def save_position(self, npc_id: str, x: float, y: float):
        """Save NPC position to DB."""
        room = get_room_at(x, y)
        await self.db.execute(
            "UPDATE dungeon_npcs SET pos_x=?, pos_y=?, updated_at=datetime('now') WHERE npc_id=?",
            (x, y, npc_id),
        )
        await self.db.execute(
            "UPDATE agent_brain SET updated_at=datetime('now') WHERE npc_id=?",
            (npc_id,),
        )

    async def move_npc_toward(
        self, npc_id: str,
        target_x: float, target_y: float,
        step_px: float = 4,
    ) -> tuple[float, float]:
        """Move NPC one step toward target. Returns new (x, y)."""
        npcs = await self.load_positions()
        if npc_id not in npcs:
            return 0, 0

        pos = npcs[npc_id]
        cx, cy = pos["x"], pos["y"]

        # Calculate path if not already following one
        path_key = npc_id
        if path_key not in self._pending_moves or not self._pending_moves[path_key]:
            path = astar_path(cx, cy, target_x, target_y)
            if not path:
                return cx, cy
            # Skip first node (current position)
            self._pending_moves[path_key] = path[1:] if len(path) > 1 else []

        path = self._pending_moves[path_key]
        if not path:
            return cx, cy

        # Move toward the next waypoint
        nx, ny = path[0]
        dx = nx - cx
        dy = ny - cy
        dist = (dx ** 2 + dy ** 2) ** 0.5

        if dist <= step_px + 1:
            # Reached waypoint → pop it
            self._pending_moves[path_key].pop(0)
            new_x, new_y = nx, ny
        else:
            # Move toward waypoint
            ratio = step_px / dist
            new_x = cx + dx * ratio
            new_y = cy + dy * ratio

        # Save new position
        await self.save_position(npc_id, new_x, new_y)
        return new_x, new_y

    async def move_to_room(self, npc_id: str, room_name: str) -> bool:
        """Plan a path to a room. Returns True if path exists."""
        npcs = await self.load_positions()
        if npc_id not in npcs:
            return False

        pos = npcs[npc_id]
        path = astar_to_room(pos["x"], pos["y"], room_name)
        if path:
            self._pending_moves[npc_id] = path[1:] if len(path) > 1 else []
            return True
        return False

    async def move_to_npc(self, mover_id: str, target_id: str) -> bool:
        """Plan a path to another NPC. Returns True if path exists."""
        npcs = await self.load_positions()
        if mover_id not in npcs or target_id not in npcs:
            return False

        pos = npcs[mover_id]
        target = npcs[target_id]
        path = astar_to_npc(pos["x"], pos["y"], target["x"], target["y"])
        if path:
            self._pending_moves[mover_id] = path[1:] if len(path) > 1 else []
            return True
        return False

    def can_interact(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Check if two entities are within interaction range."""
        return is_same_room(x1, y1, x2, y2) and distance(x1, y1, x2, y2) <= INTERACT_RADIUS * 3

    def is_in_same_room(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Check if two entities are in the same room."""
        return is_same_room(x1, y1, x2, y2)

    def is_at_library(self, x: float, y: float) -> bool:
        """Check if an NPC is at the library."""
        lib_x, lib_y = LIBRARY_POS
        return is_same_room(x, y, lib_x, lib_y) and distance(x, y, lib_x, lib_y) <= INTERACT_RADIUS * 2

    async def query_library(self, npc_name: str, question: str, broadcast_fn=None) -> str:
        """NPC visits the library and asks the LLM oracle a question.

        The library contains an ancient AI oracle (LLM) that has knowledge
        of the entire world. NPCs must physically visit the library to access it.
        """
        if self.llm_enabled and self.llm_client:
            try:
                prompt = (
                    f"You are the ancient Library Oracle in a fantasy dungeon. "
                    f"The NPC {npc_name} has come to you seeking knowledge. "
                    f"They ask: '{question}'\n\n"
                    f"Respond as the Oracle — wise, cryptic but helpful, "
                    f"with ancient knowledge of the dungeon, its secrets, "
                    f"and the relationships between its inhabitants."
                )

                # Use the LLM client to get a response
                response = await asyncio.to_thread(
                    self.llm_client, prompt,
                )
                answer = str(response)[:500]
            except Exception as e:
                answer = f"The Oracle's voice echoes... but the connection to the ancient realm is unstable: {e}"
        else:
            # Simulated oracle responses (fallback when LLM disabled)
            responses = [
                f"The ancient tomes whisper of {npc_name}'s quest. The Crystal of Eternity lies deep in the dungeon, protected by trials that test the soul.",
                f"Shelves of knowledge shift as the Oracle speaks: '{question}' — the answer lies not in books, but in cooperation between the dungeon's guardians.",
                f"A dusty scroll unrolls by itself. It shows {npc_name} and their companions working together to overcome a great obstacle.",
                f"The library's magical glow intensifies. 'Beware,' says the Oracle, 'the dungeon remembers every step. Trust your allies, for no one walks alone.'",
                f"Runes on the wall pulse with light: 'The blacksmith's hammer, the alchemist's brew, the scout's eyes — together they unlock what alone they cannot.'",
            ]
            answer = random.choice(responses)

        # Record the query
        await self.db.execute(
            "INSERT INTO artifacts (agent_id, title, artifact_type, storage_path, content) "
            "VALUES (?, ?, ?, ?, ?)",
            (NPC_IDS.get(npc_name, "system"), f"Library Query: {question[:50]}",
             "knowledge", f"library/query-{datetime.utcnow().isoformat()}", answer),
        )
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("library_query", {
                "npc": npc_name,
                "question": question[:100],
                "answer": answer[:200],
            })

        return answer

    async def physical_help_tick(self, broadcast_fn=None):
        """One tick of physical help-seeking and movement."""
        npcs = await self.load_positions()

        # Find pending help requests that need physical movement
        cursor = await self.db.execute(
            "SELECT hr.*, r.npc_name as requester_name, h.npc_name as helper_name, "
            "r.pos_x as rx, r.pos_y as ry, h.pos_x as hx, h.pos_y as hy "
            "FROM agent_help_requests hr "
            "JOIN dungeon_npcs r ON r.npc_id = hr.requester_id "
            "JOIN dungeon_npcs h ON h.npc_id = hr.helper_id "
            "WHERE hr.status IN ('pending', 'in_progress')"
        )
        requests = await cursor.fetchall()

        for req in requests:
            req_id = req["id"]
            requester_id = req["requester_id"]
            helper_id = req["helper_id"]
            requester_name = req["requester_name"]
            helper_name = req["helper_name"]

            # Get current positions
            r_pos = npcs.get(requester_id)
            h_pos = npcs.get(helper_id)
            if not r_pos or not h_pos:
                continue

            rx, ry = r_pos["x"], r_pos["y"]
            hx, hy = h_pos["x"], h_pos["y"]

            if req["status"] == "pending":
                # Requester needs to move toward helper (or vice versa)
                if not self.is_in_same_room(rx, ry, hx, hy):
                    # Plan movement — requester moves to helper's room
                    await self.move_to_npc(requester_id, helper_id)
                    message = f"{requester_name} is traveling to {helper_name} for help"
                    if broadcast_fn:
                        await broadcast_fn("npc_movement", {
                            "npc": requester_name,
                            "target": helper_name,
                            "reason": req["problem_type"],
                            "from_room": get_room_at(rx, ry),
                        })
                else:
                    # Same room → interaction possible
                    if self.can_interact(rx, ry, hx, hy):
                        # Close enough! Mark as in_progress
                        await self.db.execute(
                            "UPDATE agent_help_requests SET status='in_progress', accepted_at=datetime('now') WHERE id=?",
                            (req_id,),
                        )
                        if broadcast_fn:
                            await broadcast_fn("agent_interaction", {
                                "npc1": requester_name,
                                "npc2": helper_name,
                                "action": f"{requester_name} reached {helper_name} for {req['problem_type']}",
                            })

        # Move all NPCs that are traveling
        for npc_id in list(self._pending_moves.keys()):
            if self._pending_moves[npc_id]:
                nx, ny = await self.move_npc_toward(npc_id, 0, 0)
                # Update broadcast
                name = await self._get_npc_name(npc_id)
                if broadcast_fn and name:
                    await broadcast_fn("npc_moved", {
                        "npc": name,
                        "x": nx, "y": ny,
                        "room": get_room_at(nx, ny),
                    })

    async def _get_npc_name(self, npc_id: str) -> str | None:
        cursor = await self.db.execute(
            "SELECT npc_name FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
        )
        row = await cursor.fetchone()
        return row["npc_name"] if row else None
