"""Worker — spracúva room cluster tick v separátnom procese (Phase IIIb/IIIc).

Worker dostane:
  - room_name: ktorú room tickovať
  - npc_ids: ktoré NPC patria do tej room
  - Úloha: zavolať AgentOS + PhysicalWorld pre daný cluster

Aktuálne: interface pre budúce multiprocessing nasadenie.
Worker bude serializovaný cez pickle a poslaný ProcessPoolExecutoru.
"""

import json
import time
from typing import Any, Optional


class WorkerTask:
    """Serializable task pre worker proces.

    Obsahuje všetky dáta potrebné pre room tick.
    """

    def __init__(self, room: str, npc_ids: list[str], tick_count: int,
                 npc_names: list[str] = None):
        self.room = room
        self.npc_ids = npc_ids
        self.npc_names = npc_names or []
        self.tick_count = tick_count

    def to_dict(self) -> dict:
        return {
            "room": self.room,
            "npc_ids": self.npc_ids,
            "npc_names": self.npc_names,
            "tick_count": self.tick_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkerTask':
        return cls(
            room=data["room"],
            npc_ids=data["npc_ids"],
            tick_count=data["tick_count"],
            npc_names=data.get("npc_names", []),
        )


class WorkerResult:
    """Result from a worker process after completing a room tick."""

    def __init__(self, room: str, success: bool, npcs_ticked: int = 0,
                 duration_ms: float = 0.0, error: str = "",
                 events: list[dict] = None):
        self.room = room
        self.success = success
        self.npcs_ticked = npcs_ticked
        self.duration_ms = duration_ms
        self.error = error
        self.events = events or []

    def to_dict(self) -> dict:
        return {
            "room": self.room,
            "success": self.success,
            "npcs_ticked": self.npcs_ticked,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "events": self.events,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkerResult':
        return cls(
            room=data["room"],
            success=data["success"],
            npcs_ticked=data.get("npcs_ticked", 0),
            duration_ms=data.get("duration_ms", 0.0),
            error=data.get("error", ""),
            events=data.get("events", []),
        )


def run_worker_task(task_dict: dict) -> dict:
    """Execute a worker task in a subprocess.

    Táto funkcia je entry point pre ProcessPoolExecutor.
    Serializuje task → vykoná → vráti výsledok.

    NOTE: V aktuálnej Phase IIIa beží všetko in-process cez Controller.
    Tento modul je pripravený pre Phase IIIb multiprocessing.
    """
    task = WorkerTask.from_dict(task_dict)
    start = time.monotonic()

    try:
        # V Phase IIIb: worker by mal vlastné DB spojenie + Redis
        # a volal by AgentOS.cluster_tick() priamo
        print(f"[Worker:{task.room}] Task received: {len(task.npc_ids)} NPCs, tick {task.tick_count}")

        result = WorkerResult(
            room=task.room,
            success=True,
            npcs_ticked=len(task.npc_ids),
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )
    except Exception as e:
        result = WorkerResult(
            room=task.room,
            success=False,
            error=str(e),
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )

    return result.to_dict()
