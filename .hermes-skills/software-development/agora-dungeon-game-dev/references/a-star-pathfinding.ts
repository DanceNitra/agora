// a-star-pathfinding.ts
// Full A* pathfinding on tile-based 2D grid — for Agora Dungeon NPC movement
// Based on: Millington & Funge "Artificial Intelligence for Games"

// ============================================================
// 1. Node & Graph Data Structures
// ============================================================

export class GridNode {
    public gCost: number = 0; // Cost from start node
    public hCost: number = 0; // Heuristic estimated cost to target
    public parent: GridNode | null = null;

    constructor(
        public x: number,
        public y: number,
        public walkable: boolean = true,
        public terrainCost: number = 1.0 // mud=2, road=0.8, etc.
    ) {}

    public get fCost(): number {
        return this.gCost + this.hCost;
    }
}

export class GridGraph {
    public grid: GridNode[][] = [];

    constructor(public width: number, public height: number, obstacles: { x: number; y: number }[]) {
        // Initialize grid
        for (let x = 0; x < width; x++) {
            this.grid[x] = [];
            for (let y = 0; y < height; y++) {
                this.grid[x][y] = new GridNode(x, y);
            }
        }
        // Set obstacles
        obstacles.forEach(obs => {
            if (this.isValid(obs.x, obs.y)) {
                this.grid[obs.x][obs.y].walkable = false;
            }
        });
    }

    public getNode(x: number, y: number): GridNode | null {
        if (this.isValid(x, y)) return this.grid[x][y];
        return null;
    }

    public isValid(x: number, y: number): boolean {
        return x >= 0 && x < this.width && y >= 0 && y < this.height;
    }

    public getNeighbors(node: GridNode, allowDiagonals: boolean = true): GridNode[] {
        const neighbors: GridNode[] = [];
        const directions = [
            { dx: 0, dy: -1 },
            { dx: 0, dy: 1 },
            { dx: -1, dy: 0 },
            { dx: 1, dy: 0 },
        ];

        if (allowDiagonals) {
            directions.push(
                { dx: -1, dy: -1 },
                { dx: 1, dy: -1 },
                { dx: -1, dy: 1 },
                { dx: 1, dy: 1 }
            );
        }

        for (const dir of directions) {
            const checkX = node.x + dir.dx;
            const checkY = node.y + dir.dy;
            if (this.isValid(checkX, checkY)) {
                neighbors.push(this.grid[checkX][checkY]);
            }
        }
        return neighbors;
    }
}

// ============================================================
// 2. Heuristics
// ============================================================

export const Heuristics = {
    // Manhattan: optimal for 4-way movement (tile-based dungeons)
    manhattan: (dx: number, dy: number): number => Math.abs(dx) + Math.abs(dy),

    // Euclidean: optimal for 8-way movement (open outdoor)
    euclidean: (dx: number, dy: number): number => Math.sqrt(dx * dx + dy * dy),

    // Chebyshev: max(dx, dy) — for 8-way with equal diagonal cost
    chebyshev: (dx: number, dy: number): number => Math.max(Math.abs(dx), Math.abs(dy)),

    // Octile: for 8-way where diagonal costs 1.414 (sqrt(2))
    octile: (dx: number, dy: number): number => {
        const D = 1;           // straight cost
        const D2 = Math.SQRT2; // diagonal cost (1.414)
        return D * Math.max(Math.abs(dx), Math.abs(dy)) +
               (D2 - D) * Math.min(Math.abs(dx), Math.abs(dy));
    }
};

// ============================================================
// 3. A* Algorithm
// ============================================================

export function pathfindAStar(
    graph: GridGraph,
    start: GridNode,
    target: GridNode,
    heuristicFunc: (dx: number, dy: number) => number
): GridNode[] {
    let openList: GridNode[] = [];
    const closedSet: Set<GridNode> = new Set();

    openList.push(start);

    while (openList.length > 0) {
        // Sort by fCost — O(n log n), for production use a binary heap
        openList.sort((a, b) => a.fCost - b.fCost);
        const currentNode = openList.shift() as GridNode;

        closedSet.add(currentNode);

        // Target found
        if (currentNode === target) {
            return retracePath(start, target);
        }

        const neighbors = graph.getNeighbors(currentNode);

        for (const neighbor of neighbors) {
            if (!neighbor.walkable || closedSet.has(neighbor)) continue;

            // Diagonal cost = 1.414, straight = 1
            const moveCost = Heuristics.euclidean(
                currentNode.x - neighbor.x,
                currentNode.y - neighbor.y
            );
            const newCost = currentNode.gCost + moveCost * neighbor.terrainCost;

            const inOpenList = openList.includes(neighbor);

            if (newCost < neighbor.gCost || !inOpenList) {
                neighbor.gCost = newCost;
                neighbor.hCost = heuristicFunc(
                    target.x - neighbor.x,
                    target.y - neighbor.y
                );
                neighbor.parent = currentNode;

                if (!inOpenList) {
                    openList.push(neighbor);
                }
            }
        }
    }

    return []; // No path found
}

function retracePath(startNode: GridNode, endNode: GridNode): GridNode[] {
    const path: GridNode[] = [];
    let currentNode: GridNode | null = endNode;

    while (currentNode !== startNode && currentNode !== null) {
        path.push(currentNode);
        currentNode = currentNode.parent;
    }
    path.push(startNode);
    return path.reverse();
}

// ============================================================
// 4. Binary Heap Priority Queue (for production A*)
// ============================================================

export class MinHeap {
    private items: GridNode[] = [];

    push(node: GridNode) {
        this.items.push(node);
        this.bubbleUp(this.items.length - 1);
    }

    pop(): GridNode | undefined {
        if (this.items.length === 0) return undefined;
        const top = this.items[0];
        const last = this.items.pop()!;
        if (this.items.length > 0) {
            this.items[0] = last;
            this.sinkDown(0);
        }
        return top;
    }

    get size(): number { return this.items.length; }

    contains(node: GridNode): boolean {
        return this.items.includes(node);
    }

    private bubbleUp(index: number) {
        while (index > 0) {
            const parent = Math.floor((index - 1) / 2);
            if (this.items[index].fCost >= this.items[parent].fCost) break;
            [this.items[index], this.items[parent]] = [this.items[parent], this.items[index]];
            index = parent;
        }
    }

    private sinkDown(index: number) {
        const length = this.items.length;
        while (true) {
            let smallest = index;
            const left = 2 * index + 1;
            const right = 2 * index + 2;
            if (left < length && this.items[left].fCost < this.items[smallest].fCost) smallest = left;
            if (right < length && this.items[right].fCost < this.items[smallest].fCost) smallest = right;
            if (smallest === index) break;
            [this.items[index], this.items[smallest]] = [this.items[smallest], this.items[index]];
            index = smallest;
        }
    }
}

// Optimized A* with binary heap — 10-100x faster on large maps
export function pathfindAStarFast(
    graph: GridGraph,
    start: GridNode,
    target: GridNode,
    heuristicFunc: (dx: number, dy: number) => number
): GridNode[] {
    const openList = new MinHeap();
    const closedSet: Set<GridNode> = new Set();

    openList.push(start);

    while (openList.size > 0) {
        const currentNode = openList.pop()!;
        closedSet.add(currentNode);

        if (currentNode === target) {
            return retracePath(start, target);
        }

        const neighbors = graph.getNeighbors(currentNode);

        for (const neighbor of neighbors) {
            if (!neighbor.walkable || closedSet.has(neighbor)) continue;

            const moveCost = Heuristics.euclidean(
                currentNode.x - neighbor.x,
                currentNode.y - neighbor.y
            );
            const newCost = currentNode.gCost + moveCost * neighbor.terrainCost;

            const inOpenList = openList.contains(neighbor);

            if (newCost < neighbor.gCost || !inOpenList) {
                neighbor.gCost = newCost;
                neighbor.hCost = heuristicFunc(
                    target.x - neighbor.x,
                    target.y - neighbor.y
                );
                neighbor.parent = currentNode;

                if (!inOpenList) {
                    openList.push(neighbor);
                }
            }
        }
    }

    return [];
}

// ============================================================
// 5. Path Smoothing (Line-of-Sight)
// ============================================================

/**
 * Bresenham's line algorithm — checks if line between two nodes
 * passes through any non-walkable tiles.
 */
function rayClear(graph: GridGraph, a: GridNode, b: GridNode): boolean {
    let x0 = a.x, y0 = a.y;
    const x1 = b.x, y1 = b.y;

    const dx = Math.abs(x1 - x0);
    const dy = Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1;
    const sy = y0 < y1 ? 1 : -1;
    let err = dx - dy;

    while (x0 !== x1 || y0 !== y1) {
        const node = graph.getNode(x0, y0);
        if (node && !node.walkable) return false;

        const e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x0 += sx; }
        if (e2 < dx) { err += dx; y0 += sy; }
    }
    return true;
}

/**
 * Smooths blocky grid paths via line-of-sight shortcutting.
 * Removes unnecessary waypoints for natural-looking movement.
 */
export function smoothPath(graph: GridGraph, inputPath: GridNode[]): GridNode[] {
    if (inputPath.length <= 2) return inputPath;

    const outputPath: GridNode[] = [inputPath[0]];
    let inputIndex = 2;

    while (inputIndex < inputPath.length) {
        const lastOutput = outputPath[outputPath.length - 1];
        if (!rayClear(graph, lastOutput, inputPath[inputIndex])) {
            outputPath.push(inputPath[inputIndex - 1]);
        }
        inputIndex++;
    }

    outputPath.push(inputPath[inputPath.length - 1]);
    return outputPath;
}

// ============================================================
// 6. Hierarchical Pathfinding (HPA*)
// ============================================================

export interface Cluster {
    id: number;
    x: number;
    y: number;
    width: number;
    height: number;
    entranceNodes: { x: number; y: number }[];
}

export class HPAStar {
    constructor(
        private graph: GridGraph,
        private clusterSize: number = 10
    ) {}

    /**
     * Step 1: Abstract — build high-level graph from clusters
     * Step 2: Solve — A* on high-level graph
     * Step 3: Refine — A* within each cluster along the high-level path
     */
    public pathfind(start: GridNode, target: GridNode): GridNode[] {
        // Production: cluster the map, find entrance portals between clusters,
        // run high-level A*, then refine per cluster.
        // For now, falls back to flat A*.
        return pathfindAStarFast(this.graph, start, target, Heuristics.octile);
    }
}

// ============================================================
// 7. Usage Example
// ============================================================

/*
// Create a 20x20 dungeon map with walls
const graph = new GridGraph(20, 20, [
    { x: 5, y: 3 }, { x: 5, y: 4 }, { x: 5, y: 5 },  // vertical wall
    { x: 10, y: 7 }, { x: 11, y: 7 }, { x: 12, y: 7 }, // horizontal wall
]);

const start = graph.getNode(1, 1)!;
const target = graph.getNode(18, 18)!;

// Fast A*
const rawPath = pathfindAStarFast(graph, start, target, Heuristics.octile);
const smoothPath = smoothPath(graph, rawPath);

// smoothPath is now ready for NPC movement
console.log(`Path: ${smoothPath.map(n => `(${n.x},${n.y})`).join(' → ')}`);
*/
