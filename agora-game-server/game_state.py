"""game_state.py — Dungeon OS game state engine.

Single source of truth for the 3D dungeon isometric world.
All mutations broadcast via WebSocket to connected browsers.
"""

from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Any
from collections.abc import Callable

logger = logging.getLogger("dungeon.game_state")


# ── Data Models ──────────────────────────────────────────────


@dataclass
class Tile:
    x: int
    y: int
    type: str = "floor"  # floor, wall, door, pillar, torch, chest
    variant: int = 0
    walkable: bool = True
    color: str = "#3a3a50"


@dataclass
class Entity:
    id: str
    name: str
    entity_type: str = "agent"  # agent, object, decoration
    x: float = 0
    y: float = 0
    z: float = 0  # height above floor
    color: str = "#ff6600"
    health: int = 100
    max_health: int = 100
    state: str = "idle"  # idle, walking, thinking, casting
    thought: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PointLight:
    id: str
    x: float
    y: float
    color: str = "#ffaa44"
    intensity: float = 1.0
    radius: float = 5.0
    flicker: bool = True


@dataclass
class VisualEffect:
    id: str
    effect_type: str  # spark, glow, text, explosion
    x: float
    y: float
    z: float = 0
    color: str = "#ffffff"
    duration: float = 1.0
    created_at: float = 0.0


@dataclass
class DungeonState:
    width: int = 32
    height: int = 18
    tiles: list[list[Tile]] = field(default_factory=list)
    entities: dict[str, Entity] = field(default_factory=dict)
    lights: list[PointLight] = field(default_factory=list)
    effects: list[VisualEffect] = field(default_factory=list)
    ambient_color: str = "#1a1a2e"
    ambient_intensity: float = 0.3
    camera_x: float = 0
    camera_y: float = 0
    camera_zoom: float = 1.0
    tick: int = 0
    last_updated: float = 0.0
    tasks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "tiles": [[asdict(t) for t in row] for row in self.tiles],
            "entities": {k: asdict(v) for k, v in self.entities.items()},
            "lights": [asdict(l) for l in self.lights],
            "effects": [asdict(e) for e in self.effects],
            "ambient_color": self.ambient_color,
            "ambient_intensity": self.ambient_intensity,
            "camera": {
                "x": self.camera_x,
                "y": self.camera_y,
                "zoom": self.camera_zoom,
            },
            "tick": self.tick,
            "last_updated": self.last_updated,
            "tasks": self.tasks,
        }


# ── Game Engine ──────────────────────────────────────────────


class GameEngine:
    """Core game state engine. Thread-safe-ish single-writer pattern."""

    def __init__(self) -> None:
        self.state = DungeonState()
        self._broadcast_fn: Callable[[dict[str, Any]], None] | None = None
        self._change_log: list[dict[str, Any]] = []
        self._auto_broadcast = False
        self._first_snapshot = True

    def set_broadcast(self, fn: Callable[[dict[str, Any]], None]) -> None:
        """Register WebSocket broadcast callback."""
        self._broadcast_fn = fn

    def set_auto_broadcast(self, enabled: bool = True) -> None:
        self._auto_broadcast = enabled

    def _changed(self, event_type: str, data: dict[str, Any]) -> None:
        """Log change and optionally broadcast."""
        entry = {"type": event_type, "data": data, "ts": time.time()}
        self._change_log.append(entry)
        if len(self._change_log) > 1000:
            self._change_log = self._change_log[-500:]
        if self._auto_broadcast and self._broadcast_fn:
            self._broadcast_fn(entry)

    def create_default_dungeon(self, width: int = 24, height: int = 20) -> None:
        """Generate a medieval dungeon layout with proper rooms, walls, and archways."""
        W, H = width, height
        self.state.width = W
        self.state.height = H

        # ── Tile helpers ────────────────────────────────────────────────
        WALLCOL = "#2c2f3c"

        def sett(x, y, t, v=0, walk=True, col=None):
            if 0 <= x < W and 0 <= y < H:
                c = col if col is not None else self.state.tiles[y][x].color
                self.state.tiles[y][x] = Tile(x, y, t, v, walk, c)

        def zone(x0, x1, y0, y1, col):
            for yy in range(y0, y1 + 1):
                for xx in range(x0, x1 + 1):
                    if self.state.tiles[yy][xx].type == "floor":
                        self.state.tiles[yy][xx].color = col

        def wall(x, y):      sett(x, y, "wall", 1, False, WALLCOL)       # solid backdrop (Wall_Half)
        def pillar(x, y):    sett(x, y, "pillar", 0, False, "#4a4a5e")   # colonnade post
        def arch(x, y):      sett(x, y, "arch", 0, True)                 # walkable gothic arch
        def door(x, y):      sett(x, y, "door", 0, True)
        def window(x, y):    sett(x, y, "window", 0, False, WALLCOL)
        def overgrown(x, y): sett(x, y, "wall_overgrown", 0, False, WALLCOL)
        def broken(x, y):    sett(x, y, "wall_broken", 0, False, WALLCOL)

        def prop(x, y, t, v=0, walk=False):
            if 0 < x < W - 1 and 0 < y < H - 1 and self.state.tiles[y][x].type == "floor":
                sett(x, y, t, v, walk)
                return True
            return False

        # Step 1: floor fill (dark stone)
        self.state.tiles = [[Tile(x, y, "floor", (x + y) % 4, True, "#41454f")
                             for x in range(W)] for y in range(H)]

        # Step 2: SOLID PERIMETER — full stone wall all the way around the dungeon,
        # with a single gate opening in the south wall. (No window grilles — they
        # read as ugly holes; keep the walls solid.)
        for x in range(W):
            wall(x, 0); wall(x, H - 1)
        for y in range(H):
            wall(0, y); wall(W - 1, y)
        door(11, H - 1); door(12, H - 1)      # main gate (the one opening)

        # Step 3: one light interior colonnade framing the nave (sparse — never blocks a path)
        for y in (4, 8, 12, 16):
            pillar(5, y); pillar(W - 6, y)

        # Step 5: a few subtle floor zones, just for readability (no walls dividing them)
        zone(7, 16, 1, 4, "#473a48")          # throne end   (back-centre)
        zone(1, 6, 1, 4, "#384450")           # study        (back-left)
        zone(17, 22, 1, 4, "#46402f")         # treasury     (back-right)

        # Step 6: Throne + flanking statues + a short strip of VIP floor
        sett(11, 2, "throne", 0, True, "#52404e"); sett(12, 2, "throne", 0, True, "#52404e")
        prop(9, 2, "statue", 1); prop(14, 2, "statue", 3)
        for dx in (10, 11, 12, 13):
            sett(dx, 3, "floor_vip", 0, True, "#5a3a5a")

        # Step 7: a handful of props for flavour (kept minimal)
        prop(2, 1, "bookcase", 0); prop(3, 1, "bookcase", 0); prop(1, 3, "bookcase", 1)
        prop(19, 2, "chest_gold"); prop(20, 2, "chest"); prop(21, 2, "chest_gold")
        prop(2, 17, "barrel"); prop(3, 17, "crate")
        prop(20, 17, "crate"); prop(21, 17, "barrel")
        for bx in (8, 15):
            prop(bx, 1, "banner", 2)

        # Step 8: Torches on the backdrop walls + a couple of free-standing braziers
        TORCHES = []
        for ty in (3, 7, 11, 15):
            TORCHES.append((1, ty))           # west wall
        for tx in (4, 9, 14, 19):
            TORCHES.append((tx, 1))           # north wall
        for bx, by in [(8, 9), (15, 9), (11, 13)]:
            TORCHES.append((bx, by))          # braziers out in the open hall
        for tx in (10, 13):
            TORCHES.append((tx, H - 2))       # flanking the gate
        for tx, ty in TORCHES:
            prop(tx, ty, "torch")

        # Step 9: Lighting — a few warm pools (sparse point lights)
        self.state.lights = []
        KEY = [(11.5, 3, 9), (3, 3, 8), (20, 3, 8), (6, 9, 9), (17, 9, 9),
               (11.5, 10, 9), (3, 16, 8), (20, 16, 8), (11.5, 18, 8)]
        for i, (lx, ly, r) in enumerate(KEY):
            self.add_light(f"key_{i}", lx, ly, "#ffa844", intensity=3.4, radius=r, flicker=(i % 2 == 0))

        # Step 10: Entities — spread across the open hall so they fan out to tasks
        self.state.entities = {}
        self.add_entity("king", "King Aldric", "agent", 11.5, 3, "#c0392b")
        self.add_entity("guard_l", "Sergeant Voss", "agent", 9, 15, "#2980b9")
        self.add_entity("guard_r", "Dame Elara", "agent", 14, 15, "#2980b9")
        self.add_entity("priest", "High Priest Orin", "agent", 11.5, 9, "#8e44ad")
        self.add_entity("thief", "Shadow Kael", "agent", 20, 4, "#7f8c8d")
        self.add_entity("scholar", "Sage Mira", "agent", 3, 4, "#f39c12")
        self.add_entity("artificer", "Artificer Rooke", "agent", 17, 12, "#16a085")

        self.state.tick = 0
        self.state.last_updated = time.time()
        self._changed("dungeon_init", {"width": W, "height": H})
        return

    def add_entity(self, entity_id: str, name: str, entity_type: str = "agent",
                   x: float = 0, y: float = 0, color: str = "#ff6600") -> Entity:
        entity = Entity(id=entity_id, name=name, entity_type=entity_type,
                        x=x, y=y, color=color)
        self.state.entities[entity_id] = entity
        self._changed("entity_added", {"id": entity_id, "name": name, "x": x, "y": y})
        return entity

    def move_entity(self, entity_id: str, x: float, y: float, z: float | None = None) -> Entity | None:
        entity = self.state.entities.get(entity_id)
        if not entity:
            return None
        old_x, old_y = entity.x, entity.y
        entity.x = x
        entity.y = y
        if z is not None:
            entity.z = z
        self._changed("entity_moved", {
            "id": entity_id, "x": x, "y": y,
            "old_x": old_x, "old_y": old_y,
        })
        return entity

    def set_tasks(self, tasks: list[dict[str, Any]]) -> None:
        """Replace the live task/quest board and broadcast it to clients."""
        self.state.tasks = tasks
        self._changed("tasks_update", {"tasks": tasks})

    def face_entity(self, entity_id: str, tx: float, ty: float) -> Entity | None:
        """Make an entity face toward grid tile (tx, ty) — purely a client visual hint."""
        entity = self.state.entities.get(entity_id)
        if not entity:
            return None
        self._changed("entity_face", {"id": entity_id, "tx": tx, "ty": ty})
        return entity

    def set_entity_state(self, entity_id: str, state: str) -> Entity | None:
        entity = self.state.entities.get(entity_id)
        if not entity:
            return None
        old_state = entity.state
        entity.state = state
        self._changed("entity_state", {
            "id": entity_id, "state": state, "old_state": old_state,
        })
        return entity

    def set_entity_thought(self, entity_id: str, text: str) -> Entity | None:
        entity = self.state.entities.get(entity_id)
        if not entity:
            return None
        entity.thought = text
        self._changed("entity_thought", {
            "id": entity_id, "text": text,
        })
        return entity

    def set_entity_health(self, entity_id: str, health: int) -> Entity | None:
        entity = self.state.entities.get(entity_id)
        if not entity:
            return None
        entity.health = max(0, min(entity.max_health, health))
        self._changed("entity_health", {
            "id": entity_id, "health": entity.health,
        })
        return entity

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id in self.state.entities:
            del self.state.entities[entity_id]
            self._changed("entity_removed", {"id": entity_id})
            return True
        return False

    def set_lighting(self, ambient_color: str | None = None,
                     ambient_intensity: float | None = None) -> None:
        if ambient_color is not None:
            self.state.ambient_color = ambient_color
        if ambient_intensity is not None:
            self.state.ambient_intensity = ambient_intensity
        self._changed("lighting_updated", {
            "ambient_color": self.state.ambient_color,
            "ambient_intensity": self.state.ambient_intensity,
        })

    def add_light(self, light_id: str, x: float, y: float,
                  color: str = "#ffaa44", intensity: float = 1.0,
                  radius: float = 5.0, flicker: bool = True) -> PointLight:
        light = PointLight(light_id, x, y, color, intensity, radius, flicker)
        self.state.lights.append(light)
        self._changed("light_added", {
            "id": light_id, "x": x, "y": y, "color": color,
        })
        return light

    def remove_light(self, light_id: str) -> bool:
        for i, l in enumerate(self.state.lights):
            if l.id == light_id:
                self.state.lights.pop(i)
                self._changed("light_removed", {"id": light_id})
                return True
        return False

    def add_effect(self, effect_type: str, x: float, y: float,
                   z: float = 0, color: str = "#ffffff",
                   duration: float = 1.0) -> str:
        effect_id = f"fx_{int(time.time() * 1000)}_{len(self.state.effects)}"
        effect = VisualEffect(
            id=effect_id, effect_type=effect_type,
            x=x, y=y, z=z, color=color, duration=duration,
            created_at=time.time(),
        )
        self.state.effects.append(effect)
        self._changed("effect_added", {
            "id": effect_id, "type": effect_type,
            "x": x, "y": y, "color": color,
        })
        # Auto-clean expired effects
        self._clean_effects()
        return effect_id

    def _clean_effects(self) -> None:
        now = time.time()
        self.state.effects = [
            e for e in self.state.effects
            if now - e.created_at < e.duration
        ]

    def set_camera(self, x: float, y: float, zoom: float | None = None) -> None:
        self.state.camera_x = x
        self.state.camera_y = y
        if zoom is not None:
            self.state.camera_zoom = max(0.1, min(5.0, zoom))
        self._changed("camera_updated", {
            "x": x, "y": y, "zoom": self.state.camera_zoom,
        })

    def tick(self) -> int:
        """Advance one game tick."""
        self.state.tick += 1
        self.state.last_updated = time.time()
        self._clean_effects()
        self._changed("tick", {"tick": self.state.tick})
        return self.state.tick

    def get_snapshot(self) -> dict[str, Any]:
        """Full state snapshot (sent on browser connect)."""
        return self.state.to_dict()

    def get_state(self) -> dict[str, Any]:
        """Alias for get_snapshot"""
        return self.get_snapshot()
