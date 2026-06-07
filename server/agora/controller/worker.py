"""Worker — spracúva room cluster tick v separátnom procese (Phase IIIb).

Architektúra:
  1. CONTROLLER (main process): gather → serializable room data
  2. WORKER (subprocess): compute → serializable state changes
  3. CONTROLLER (main process): apply → DB + Redis writes

Worker NIKDY nepíše do DB — len vracia zmeny stavu ako dict.
Hlavný proces sekvenčne commitne výsledky (nemáme SQLite write contention).
"""

import json
import math
import random
import time
from typing import Any, Optional


class WorkerTask:
    """Serializable task pre worker proces — čisto dáta, žiadne objekty."""

    def __init__(self, room: str, npcs: list[dict], tick_count: int):
        """
        npcs: list of dicts so všetkými dátami potrebnými pre tick
              [{npc_id, npc_name, health, stamina, hunger, fatigue,
                state_of_mind, current_goal}]
        """
        self.room = room
        self.npcs = npcs
        self.tick_count = tick_count

    def to_dict(self) -> dict:
        return {
            "room": self.room,
            "npcs": self.npcs,
            "tick_count": self.tick_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkerTask":
        return cls(
            room=data["room"],
            npcs=data.get("npcs", []),
            tick_count=data.get("tick_count", 0),
        )


class WorkerResult:
    """Serializable výsledok z worker procesu."""

    def __init__(
        self,
        room: str,
        success: bool,
        npc_updates: Optional[list[dict]] = None,
        events: Optional[list[dict]] = None,
        duration_ms: float = 0.0,
        error: str = "",
    ):
        self.room = room
        self.success = success
        self.npc_updates = npc_updates or []
        self.events = events or []
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self) -> dict:
        return {
            "room": self.room,
            "success": self.success,
            "npc_updates": self.npc_updates,
            "events": self.events,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkerResult":
        return cls(
            room=data["room"],
            success=data["success"],
            npc_updates=data.get("npc_updates", []),
            events=data.get("events", []),
            duration_ms=data.get("duration_ms", 0.0),
            error=data.get("error", ""),
        )


# ══════════════════════════════════════════════════════════════
# COMPUTATION LOGIC (pure functions, run in subprocess)
# ══════════════════════════════════════════════════════════════


def _compute_body_update(npc: dict) -> dict:
    """Čisto matematický výpočet body zmien — žiadne I/O."""
    stamina = max(0.0, npc.get("stamina", 100) - random.uniform(0.5, 2.0))
    hunger = min(100.0, npc.get("hunger", 0) + random.uniform(0.2, 0.8))
    fatigue = min(100.0, npc.get("fatigue", 0) + random.uniform(0.3, 1.0))
    health = npc.get("health", 100)

    # Health penalties
    if hunger > 80:
        health = max(0, health - 0.5)
    if fatigue > 80:
        health = max(0, health - 0.3)
    if stamina < 10:
        health = max(0, health - 0.2)

    return {
        "stamina": round(stamina, 1),
        "hunger": round(hunger, 1),
        "fatigue": round(fatigue, 1),
        "health": round(health, 1),
    }


def _compute_state_of_mind(npc: dict) -> str:
    """Čisto logické vyhodnotenie state_of_mind — žiadne I/O."""
    health = npc.get("health", 100)
    stamina = npc.get("stamina", 100)
    fatigue = npc.get("fatigue", 0)

    if health < 20:
        return "panicked"
    elif fatigue > 70 or stamina < 20:
        return "resting"
    elif health < 50:
        return "confused"
    else:
        plan_stack = json.loads(npc.get("plan_stack", "[]"))
        current_goal = npc.get("current_goal")
        if not plan_stack and current_goal:
            return "planning"
        else:
            return "focused"


def process_room_worker(task_dict: dict) -> dict:
    """Entry point pre ProcessPoolExecutor — čisto computation.

    Dostane serializované NPC dáta, vráti zmeny stavu.
    ŽIADNE DB/Redis/I/O volania.
    """
    task = WorkerTask.from_dict(task_dict)
    start = time.monotonic()

    try:
        npc_updates = []
        events = []

        for npc in task.npcs:
            npc_id = npc.get("npc_id", "")
            npc_name = npc.get("npc_name", "")

            # 1. Compute body updates
            body_update = _compute_body_update(npc)

            # 2. Compute state of mind
            merged = {**npc, **body_update}
            new_state = _compute_state_of_mind(merged)

            # 3. Build state change
            update = {
                "npc_id": npc_id,
                "npc_name": npc_name,
                "stamina": body_update["stamina"],
                "hunger": body_update["hunger"],
                "fatigue": body_update["fatigue"],
                "health": body_update["health"],
                "state_of_mind": new_state,
            }
            npc_updates.append(update)

            # 4. Event for state change
            if new_state != npc.get("state_of_mind"):
                events.append({
                    "type": "npc_state_change",
                    "payload": {
                        "npc_id": npc_id,
                        "npc_name": npc_name,
                        "from": npc.get("state_of_mind", "unknown"),
                        "to": new_state,
                    },
                })

        duration = round((time.monotonic() - start) * 1000, 1)
        result = WorkerResult(
            room=task.room,
            success=True,
            npc_updates=npc_updates,
            events=events,
            duration_ms=duration,
        )

    except Exception as e:
        result = WorkerResult(
            room=task.room,
            success=False,
            error=str(e),
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )

    return result.to_dict()
