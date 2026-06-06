"""Dungeon map — grid, room definitions, and A* pathfinding for NPC physical movement.

Map: 40×19 tiles, 32px per tile
  0 = floor (walkable)
  1 = wall (blocked)
  2 = door (walkable, connects rooms)

Rooms:
  - Main Hall: cols 0-24, rows 0-18
  - Library:  cols 25-38, rows 1-5   (top-right)
  - Treasury: cols 25-33, rows 7-11  (middle-right)
  - Crypt:    cols 25-38, rows 13-17 (bottom-right)
"""

from __future__ import annotations
import heapq
import math
from typing import Optional

# ── Map dimensions ──
MAP_W = 40
MAP_H = 19
TILE = 32

# ── Map grid: 0=floor, 1=wall, 2=door ──
DUNGEON_MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,1,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,1,0,0,0,1,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,2,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,2,0,1,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,1,1,1,1,2,1,1,1,1,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]


def build_passable_grid() -> list[list[bool]]:
    """True = walkable (floor or door), False = blocked (wall)."""
    return [[tile in (0, 2) for tile in row] for row in DUNGEON_MAP]


# ── Room definitions (tile coordinates) ──

ROOMS = {
    "main_hall":  {"x1": 0,  "y1": 0,  "x2": 23, "y2": 18},
    "library":    {"x1": 25, "y1": 1,  "x2": 38, "y2": 5},
    "treasury":   {"x1": 25, "y1": 7,  "x2": 33, "y2": 11},
    "crypt":      {"x1": 25, "y1": 13, "x2": 38, "y2": 17},
}


def get_room_at(pixel_x: float, pixel_y: float) -> str:
    """Get room name at pixel position."""
    tx = int(pixel_x / TILE)
    ty = int(pixel_y / TILE)
    for name, bounds in ROOMS.items():
        if bounds["x1"] <= tx <= bounds["x2"] and bounds["y1"] <= ty <= bounds["y2"]:
            return name
    return "main_hall"


def is_same_room(x1: float, y1: float, x2: float, y2: float) -> bool:
    """Check if two positions are in the same room."""
    return get_room_at(x1, y1) == get_room_at(x2, y2)


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance."""
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


# ── A* Pathfinding ──

def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Octile distance — allows diagonal movement approximation."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)


def astar_path(
    start_x: float, start_y: float,
    goal_x: float, goal_y: float,
    max_steps: int = 200,
) -> list[tuple[float, float]] | None:
    """A* path from (start_x, start_y) to (goal_x, goal_y) in tile coords.
    Returns list of (x, y) pixel positions, or None if unreachable."""
    grid = build_passable_grid()

    sx, sy = int(start_x / TILE), int(start_y / TILE)
    gx, gy = int(goal_x / TILE), int(goal_y / TILE)

    # Clamp to grid
    sx = max(0, min(sx, MAP_W - 1))
    sy = max(0, min(sy, MAP_H - 1))
    gx = max(0, min(gx, MAP_W - 1))
    gy = max(0, min(gy, MAP_H - 1))

    if not grid[sy][sx] or not grid[gy][gx]:
        return None  # Start or goal is blocked

    if (sx, sy) == (gx, gy):
        return [(start_x, start_y)]  # Already there

    # A* with 4-directional movement
    open_set = [(0, sx, sy)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {(sx, sy): 0}
    f_score: dict[tuple[int, int], float] = {(sx, sy): _heuristic((sx, sy), (gx, gy))}

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    while open_set:
        _, cx, cy = heapq.heappop(open_set)

        if (cx, cy) == (gx, gy):
            # Reconstruct path
            tile_path: list[tuple[int, int]] = []
            current = (gx, gy)
            while current in came_from:
                tile_path.append(current)
                current = came_from[current]
            tile_path.append((sx, sy))
            tile_path.reverse()

            # Convert to pixel positions (center of tiles)
            pixel_path = [(tx * TILE + TILE // 2, ty * TILE + TILE // 2) for tx, ty in tile_path]
            return pixel_path

        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H and grid[ny][nx]:
                tentative_g = g_score.get((cx, cy), float("inf")) + 1
                if tentative_g < g_score.get((nx, ny), float("inf")):
                    came_from[(nx, ny)] = (cx, cy)
                    g_score[(nx, ny)] = tentative_g
                    f = tentative_g + _heuristic((nx, ny), (gx, gy))
                    f_score[(nx, ny)] = f
                    heapq.heappush(open_set, (f, nx, ny))

    return None  # No path


def astar_to_room(start_x: float, start_y: float, target_room: str) -> Optional[list[tuple[float, float]]]:
    """Find path from current position to the center of a named room."""
    room = ROOMS.get(target_room)
    if not room:
        return None
    # Use exact center of the room's walkable area
    center_x = ((room["x1"] + room["x2"]) // 2) * TILE + TILE // 2
    center_y = ((room["y1"] + room["y2"]) // 2) * TILE + TILE // 2
    return astar_path(start_x, start_y, center_x, center_y)


def astar_to_npc(start_x: float, start_y: float, target_x: float, target_y: float) -> Optional[list[tuple[float, float]]]:
    """Find path to another NPC's position."""
    return astar_path(start_x, start_y, target_x, target_y)
