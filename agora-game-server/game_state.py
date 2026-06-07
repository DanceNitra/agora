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

    def create_default_dungeon(self, width: int = 50, height: int = 50) -> None:
        """Generate a simple, clean dungeon layout with rooms along perimeter and open center."""
        W, H = width, height
        self.state.width = W
        self.state.height = H

        # Step 1: Fill entire grid with floor tiles
        self.state.tiles = []
        for y in range(H):
            row = []
            for x in range(W):
                row.append(Tile(x, y, "floor", (x + y) % 4, True, "#3a3a50"))
            self.state.tiles.append(row)

        # Step 2: Outer walls (border)
        for x in range(W):
            self.state.tiles[0][x] = Tile(x, 0, "wall", 0, False, "#2a2a3e")
            self.state.tiles[H-1][x] = Tile(x, H-1, "wall", 0, False, "#2a2a3e")
        for y in range(H):
            self.state.tiles[y][0] = Tile(0, y, "wall", 0, False, "#2a2a3e")
            self.state.tiles[y][W-1] = Tile(W-1, y, "wall", 0, False, "#2a2a3e")

        # Step 3: Zone floor colors
        # Top zone (y=3 to y=9) - Throne Room center, Library left, Treasury right
        for y in range(3, 10):
            for x in range(3, 47):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    if x <= 15:
                        t.color = "#3a3a50"   # Library
                    elif 17 <= x <= 33:
                        t.color = "#4a2a4a"   # Throne Room
                    else:
                        t.color = "#4a4a30"   # Treasury

        # Great Hall (y=10 to y=35)
        for y in range(10, 36):
            for x in range(3, 47):
                if self.state.tiles[y][x].type == "floor":
                    self.state.tiles[y][x].color = "#3a4a5a"

        # Central aisle markers (slightly different shade down the middle)
        for y in range(10, 36):
            for x in [23, 24, 25, 26]:
                if self.state.tiles[y][x].type == "floor":
                    self.state.tiles[y][x].color = "#3a4a62"

        # Throne platform (raised colour area in great hall, near top)
        for y in range(12, 16):
            for x in range(22, 28):
                if self.state.tiles[y][x].type == "floor":
                    self.state.tiles[y][x].color = "#5a2a4a"

        # Bottom zone (y=36 to y=41) - Entrance center, Barracks left, Armory right
        for y in range(36, 42):
            for x in range(3, 47):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    if x <= 15:
                        t.color = "#3a3a3a"   # Barracks
                    elif 17 <= x <= 33:
                        t.color = "#3a4050"   # Entrance
                    else:
                        t.color = "#3d4040"   # Armory

        # Gate bottom (y=42 to y=47) - entrance area
        for y in range(42, 48):
            for x in range(18, 32):
                if self.state.tiles[y][x].type == "floor":
                    self.state.tiles[y][x].color = "#3a4050"

        # Step 4: Pillars (columns between rooms + great hall)
        PILLARS = []
        # Between Library and Throne Room
        for py in range(4, 9):
            PILLARS.append((16, py))
        # Between Throne Room and Treasury
        for py in range(4, 9):
            PILLARS.append((34, py))

        # Great Hall pillars (regular grid, like a basilica)
        for px in [8, 15, 22, 28, 35, 42]:
            for py in [12, 16, 20, 24, 28, 32]:
                PILLARS.append((px, py))

        # Between Barracks and Entrance
        for py in range(37, 41):
            PILLARS.append((16, py))
        # Between Entrance and Armory
        for py in range(37, 41):
            PILLARS.append((34, py))

        # Gate pillars
        for px in [20, 25, 30]:
            for py in [44, 46]:
                PILLARS.append((px, py))

        for px, py in PILLARS:
            if 0 < px < W-1 and 0 < py < H-1:
                col = "#5a3a5a" if (18 <= px <= 32 and 3 <= py <= 9) else "#4a4a5e"
                self.state.tiles[py][px] = Tile(px, py, "pillar", 0, False, col)

        # Step 5: Decorative elements
        # Throne at center of throne zone
        for tx, ty in [(24, 4), (25, 4), (24, 5), (25, 5)]:
            self.state.tiles[ty][tx] = Tile(tx, ty, "throne", 0, True, "#6a3a2a")
        # Chests in Treasury
        for cx, cy in [(38, 6), (44, 6), (41, 7), (45, 5)]:
            self.state.tiles[cy][cx] = Tile(cx, cy, "chest", 0, False, "#8a6a3a")

        # Step 6: Torches along outer walls (left and right edges)
        TORCHES = []
        # Left wall torches
        for ty in [5, 8, 13, 18, 22, 27, 32, 37, 40]:
            TORCHES.append((3, ty))
        # Right wall torches
        for ty in [5, 8, 13, 18, 22, 27, 32, 37, 40]:
            TORCHES.append((46, ty))
        # Bottom gate torches
        for tx in [18, 24, 30]:
            TORCHES.append((tx, 47))
        for tx, ty in TORCHES:
            if 0 < tx < W-1 and 0 < ty < H-1:
                self.state.tiles[ty][tx] = Tile(tx, ty, "torch", 0, False, "#553311")

        # Step 7: Lighting — DISABLED (lights cause visual artifacts on walls)
        self.state.lights = []

        # Step 8: Entities (agents)
        self.state.entities = {}
        # King — center throne room
        self.add_entity("king", "King Aldric", "agent", 24.5, 5.5, "#c0392b")
        # Guard — left of entrance gate
        self.add_entity("guard_l", "Sergeant Voss", "agent", 13, 44, "#2980b9")
        # Guard — right of entrance gate
        self.add_entity("guard_r", "Dame Elara", "agent", 37, 44, "#2980b9")
        # Priest — near throne platform in great hall
        self.add_entity("priest", "High Priest Orin", "agent", 16, 14, "#8e44ad")
        # Thief — lurking in shadows near treasury
        self.add_entity("thief", "Shadow Kael", "agent", 42, 10, "#7f8c8d")
        # Scholar — in library
        self.add_entity("scholar", "Sage Mira", "agent", 9, 7, "#f39c12")

        self.state.tick = 0
        self.state.last_updated = time.time()
        self._changed("dungeon_init", {"width": W, "height": H})

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
