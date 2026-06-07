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

    def create_default_dungeon(self, width: int = 24, height: int = 20) -> None:
        """Generate a medieval dungeon layout with proper rooms, walls, and archways."""
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

        # Step 2: Outer walls (border) - variant 1 = Wall_Half.obj (1×1 tile)
        for x in range(W):
            self.state.tiles[0][x] = Tile(x, 0, "wall", 1, False, "#2a2a3e")
            self.state.tiles[H-1][x] = Tile(x, H-1, "wall", 1, False, "#2a2a3e")
        for y in range(H):
            self.state.tiles[y][0] = Tile(0, y, "wall", 1, False, "#2a2a3e")
            self.state.tiles[y][W-1] = Tile(W-1, y, "wall", 1, False, "#2a2a3e")

        # Step 3: Inner walls separating rooms (variant 0 = Wall.obj scale 0.5, spans 2 tiles)
        # Inner walls between Throne Room and side chambers
        WALL_H = [
            # Top row: Library | Throne Room | Treasury (y=1 to y=4)
            (6, 1, 4),    # x=6 between Library(1-5) and Throne(7-16)
            (17, 1, 4),   # x=17 between Throne(7-16) and Treasury(18-22)
            # Bottom row: Barracks | Entrance | Armory (y=16 to y=19)
            (6, 16, 19),  # x=6 between Barracks(1-5) and Entrance(7-16)
            (17, 16, 19), # x=17 between Entrance(7-16) and Armory(18-22)
        ]
        # Middle wall rows with archway gaps: y=5 and y=15
        # y=5 separates throne zone from great hall
        # y=15 separates great hall from entrance zone
        WALL_ROW_Y = [5, 15]
        WALL_COLS = range(1, W-1)  # inner columns

        # Draw vertical inner walls
        for wx, y_start, y_end in WALL_H:
            for wy in range(y_start, y_end + 1):
                if self.state.tiles[wy][wx].type == "floor":
                    self.state.tiles[wy][wx] = Tile(wx, wy, "wall", 0, False, "#2a2a3e")

        # Draw horizontal inner wall rows with archway gaps
        for wy in WALL_ROW_Y:
            for wx in WALL_COLS:
                # Archway gaps: 3-tile-wide openings between rooms
                is_archway = (
                    # Between Library and Throne Room (left arch)
                    (8 <= wx <= 10) or
                    # Between Throne Room and Treasury (right arch)  
                    (13 <= wx <= 15) or
                    # Center arch (entrance to great hall)
                    (wx in [11, 12])
                )
                if not is_archway and self.state.tiles[wy][wx].type == "floor":
                    self.state.tiles[wy][wx] = Tile(wx, wy, "wall", 0, False, "#2a2a3e")

        # Step 4: Zone floor colors
        # Throne Room (y=1 to y=4, x=7 to x=16)
        for y in range(1, 5):
            for x in range(7, 17):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#4a2a4a"  # Regal purple

        # Library (y=1 to y=4, x=1 to x=5)
        for y in range(1, 5):
            for x in range(1, 6):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#3a3a50"  # Deep blue

        # Treasury (y=1 to y=4, x=18 to x=22)
        for y in range(1, 5):
            for x in range(18, 23):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#4a4a30"  # Gold-ish

        # Great Hall (y=6 to y=14)
        for y in range(6, 15):
            for x in range(1, 23):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#3a4a5a"  # Stone blue

        # Central aisle in great hall (darker strip)
        for y in range(6, 15):
            for x in [10, 11, 12, 13]:
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#3a4a62"

        # Throne platform (raised area before throne room)
        for y in range(6, 8):
            for x in range(10, 14):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#5a2a4a"

        # Entrance Hall (y=16 to y=18, x=7 to x=16)
        for y in range(16, 19):
            for x in range(7, 17):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#3a4050"

        # Barracks (y=16 to y=18, x=1 to x=5)
        for y in range(16, 19):
            for x in range(1, 6):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#3a3a3a"

        # Armory (y=16 to y=18, x=18 to x=22)
        for y in range(16, 19):
            for x in range(18, 23):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#3d4040"

        # Gate path (x=10 to x=13, opens south)
        for y in range(19, 20):
            for x in range(10, 14):
                t = self.state.tiles[y][x]
                if t.type == "floor":
                    t.color = "#3a4050"

        # Break the outer wall for the gate entrance
        for x in range(10, 14):
            if self.state.tiles[H-2][x].type == "wall":
                self.state.tiles[H-2][x] = Tile(x, H-2, "floor", 0, True, "#3a4050")

        # Step 5: Pillars in Great Hall (3 columns × 3 rows = 9 total)
        PILLARS = []
        for px in [5, 12, 18]:
            for py in [8, 11]:
                PILLARS.append((px, py))
        # Additional framing pillars
        for px in [5, 18]:
            for py in [7, 12]:
                PILLARS.append((px, py))

        for px, py in PILLARS:
            if 0 < px < W-1 and 0 < py < H-1:
                self.state.tiles[py][px] = Tile(px, py, "pillar", 0, False, "#4a4a5e")

        # Step 6: Decorative elements
        # Throne at center of throne room
        for tx, ty in [(11, 2), (12, 2)]:
            self.state.tiles[ty][tx] = Tile(tx, ty, "throne", 0, True, "#6a3a2a")

        # Chests in Treasury
        for cx, cy in [(19, 2), (21, 3), (20, 2)]:
            self.state.tiles[cy][cx] = Tile(cx, cy, "chest", 0, False, "#8a6a3a")

        # Step 7: Torches along walls (spaced every 3 tiles)
        TORCHES = []
        # Left wall
        for ty in [3, 7, 10, 13, 17]:
            TORCHES.append((1, ty))
        # Right wall
        for ty in [3, 7, 10, 13, 17]:
            TORCHES.append((22, ty))
        # Side walls of throne room
        for tx in [7, 16]:
            for ty in [3, 4]:
                TORCHES.append((tx, ty))
        # Gate torches
        for tx in [9, 14]:
            TORCHES.append((tx, 18))

        for tx, ty in TORCHES:
            if 0 < tx < W-1 and 0 < ty < H-1:
                self.state.tiles[ty][tx] = Tile(tx, ty, "torch", 0, False, "#553311")

        # Step 8: Floor decorations (Diamond pattern in throne room)
        for dx, dy in [(11, 3), (12, 3)]:
            if self.state.tiles[dy][dx].type == "floor":
                self.state.tiles[dy][dx] = Tile(dx, dy, "floor_vip", 0, True, "#5a3a5a")

        # Step 9: Lighting — DISABLED
        self.state.lights = []

        # Step 10: Entities (agents)
        self.state.entities = {}
        self.add_entity("king", "King Aldric", "agent", 12.5, 3.5, "#c0392b")
        self.add_entity("guard_l", "Sergeant Voss", "agent", 10, 18, "#2980b9")
        self.add_entity("guard_r", "Dame Elara", "agent", 14, 18, "#2980b9")
        self.add_entity("priest", "High Priest Orin", "agent", 12, 7, "#8e44ad")
        self.add_entity("thief", "Shadow Kael", "agent", 20, 11, "#7f8c8d")
        self.add_entity("scholar", "Sage Mira", "agent", 4, 3, "#f39c12")

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
