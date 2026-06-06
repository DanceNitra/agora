/**
 * Grid-based A* pathfinding for NPC navigation around dungeon walls.
 * Uses the shared DUNGEON_MAP for collision data.
 */
import { MAP_W, MAP_H, TILE, buildWalkGrid, DUNGEON_MAP } from '../config/map';

interface PathNode {
  x: number;
  y: number;
  g: number; // cost from start
  h: number; // heuristic cost to goal
  f: number; // total: g + h
  parent: PathNode | null;
}

function heuristic(ax: number, ay: number, bx: number, by: number): number {
  // Octile distance (diagonal movement allowed)
  const dx = Math.abs(ax - bx);
  const dy = Math.abs(ay - by);
  return dx + dy + (Math.SQRT2 - 2) * Math.min(dx, dy);
}

/**
 * Find a path from (sx, sy) to (gx, gy) using A* over the dungeon tile grid.
 * Coordinates are in tile grid units (not pixels).
 * Returns array of {x, y} grid coordinates — empty array if no path.
 */
export function findPath(
  sx: number,
  sy: number,
  gx: number,
  gy: number,
  walkGrid?: boolean[][],
): { x: number; y: number }[] {
  const grid = walkGrid ?? buildWalkGrid(DUNGEON_MAP);

  // Clamp to grid bounds
  sx = Math.max(0, Math.min(MAP_W - 1, Math.round(sx)));
  sy = Math.max(0, Math.min(MAP_H - 1, Math.round(sy)));
  gx = Math.max(0, Math.min(MAP_W - 1, Math.round(gx)));
  gy = Math.max(0, Math.min(MAP_H - 1, Math.round(gy)));

  // If goal is blocked, find nearest walkable tile
  if (!grid[gy]?.[gx]) {
    const nearest = findNearestWalkable(gx, gy, grid);
    if (!nearest) return [];
    gx = nearest.x;
    gy = nearest.y;
  }

  // If start is blocked (shouldn't happen, but safety)
  if (!grid[sy]?.[sx]) {
    const nearest = findNearestWalkable(sx, sy, grid);
    if (!nearest) return [];
    sx = nearest.x;
    sy = nearest.y;
  }

  // Already at goal
  if (sx === gx && sy === gy) return [{ x: sx, y: sy }];

  const openSet: PathNode[] = [{ x: sx, y: sy, g: 0, h: heuristic(sx, sy, gx, gy), f: 0, parent: null }];
  openSet[0].f = openSet[0].g + openSet[0].h;

  const closedSet = new Set<string>();
  const key = (x: number, y: number) => `${x},${y}`;

  // 8-directional movement
  const dirs = [
    { dx: 0, dy: -1 }, { dx: 0, dy: 1 }, { dx: -1, dy: 0 }, { dx: 1, dy: 0 },
    { dx: -1, dy: -1 }, { dx: 1, dy: -1 }, { dx: -1, dy: 1 }, { dx: 1, dy: 1 },
  ];

  const maxIterations = 1000;
  let iterations = 0;

  while (openSet.length > 0 && iterations < maxIterations) {
    iterations++;

    // Find lowest f in open set (simple linear scan)
    let lowestIdx = 0;
    for (let i = 1; i < openSet.length; i++) {
      if (openSet[i].f < openSet[lowestIdx].f) {
        lowestIdx = i;
      }
    }

    const current = openSet[lowestIdx];

    // Reached goal
    if (current.x === gx && current.y === gy) {
      return reconstructPath(current);
    }

    // Move current to closed
    openSet.splice(lowestIdx, 1);
    closedSet.add(key(current.x, current.y));

    for (const { dx, dy } of dirs) {
      const nx = current.x + dx;
      const ny = current.y + dy;
      const k = key(nx, ny);

      // Bounds check
      if (nx < 0 || nx >= MAP_W || ny < 0 || ny >= MAP_H) continue;
      if (!grid[ny][nx]) continue; // blocked
      if (closedSet.has(k)) continue;

      // Diagonal movement: check both cardinal neighbors aren't blocked
      if (dx !== 0 && dy !== 0) {
        if (!grid[current.y + dy][current.x]) continue;
        if (!grid[current.y][current.x + dx]) continue;
      }

      // Cost: 1 for cardinal, sqrt(2) for diagonal
      const moveCost = (dx !== 0 && dy !== 0) ? Math.SQRT2 : 1;
      const tentativeG = current.g + moveCost;

      const existing = openSet.find(n => n.x === nx && n.y === ny);
      if (existing) {
        if (tentativeG < existing.g) {
          existing.g = tentativeG;
          existing.f = tentativeG + existing.h;
          existing.parent = current;
        }
      } else {
        openSet.push({
          x: nx, y: ny,
          g: tentativeG,
          h: heuristic(nx, ny, gx, gy),
          f: tentativeG + heuristic(nx, ny, gx, gy),
          parent: current,
        });
      }
    }
  }

  // No path found — return direct line as fallback
  return [{ x: gx, y: gy }];
}

function reconstructPath(node: PathNode): { x: number; y: number }[] {
  const path: { x: number; y: number }[] = [];
  let current: PathNode | null = node;
  while (current) {
    path.unshift({ x: current.x, y: current.y });
    current = current.parent;
  }
  return path;
}

function findNearestWalkable(cx: number, cy: number, grid: boolean[][]): { x: number; y: number } | null {
  for (let r = 1; r < 20; r++) {
    for (let dy = -r; dy <= r; dy++) {
      for (let dx = -r; dx <= r; dx++) {
        const nx = cx + dx;
        const ny = cy + dy;
        if (nx < 0 || nx >= MAP_W || ny < 0 || ny >= MAP_H) continue;
        if (grid[ny]?.[nx]) return { x: nx, y: ny };
      }
    }
  }
  return null;
}

/**
 * Convert a pixel position to tile grid coordinates.
 */
export function pixelToTile(px: number, py: number): { tx: number; ty: number } {
  return {
    tx: Math.round(px / TILE),
    ty: Math.round(py / TILE),
  };
}

/**
 * Convert tile grid coordinates to pixel center.
 */
export function tileToPixel(tx: number, ty: number): { px: number; py: number } {
  return {
    px: tx * TILE + TILE / 2,
    py: ty * TILE + TILE / 2,
  };
}
