/**
 * world.ts — renderer-agnostic game state (source of truth).
 *
 * The renderer is a *view*, never the owner.
 *
 * Built on Zustand.
 */

import { create } from 'zustand';

// ── Types ──────────────────────────────────────────────

export type TileType = 0 | 1 | 2; // 0=floor, 1=wall, 2=door

export interface AgentView {
  id: string;
  name: string;           // "Kael", "Lyra", "Mordecai", "Grom", "Zara", "Finn", "Guard"
  role: string;           // "adventurer", "scout", "sage", "blacksmith", "alchemist", "merchant", "guard"
  pos: [number, number];  // pixel coords (tile coords * TILE)
  target?: [number, number]; // where it's walking to (for tweened movement)
  status: string;         // last action summary
  color: number;          // tint color
  objective: string;
  health: number;
}

export interface AgentQuest {
  npcName: string;
  activeQuestTitle: string;
  questStatus: string;
}

export interface RoomLight {
  x: number; y: number; radius: number; color: number; intensity: number;
}

export interface WorldState {
  tick: number;
  mapGrid: number[][];
  tileSize: number;
  mapW: number;
  mapH: number;
  agents: Record<string, AgentView>;
  quests: AgentQuest[];
  // OS subsystem meters (0..100)
  osState: {
    comms: number;
    knowledge: number;
    tooling: number;
    economy: number;
    safety: number;
  };
  // Player (null if no player — dungeon is agent-only)
  playerPos: [number, number] | null;
  // Torch/light positions for Pixi lighting
  lights: RoomLight[];
  // Interactive stations
  stations: { name: string; x: number; y: number; description: string }[];
  // Event log
  log: { tick: number; agent: string; text: string }[];
}

// ── Constants from game/config/map.ts ──────────────────

export const TILE = 32;
export const MAP_W = 40;
export const MAP_H = 19;

// 0=floor, 1=wall, 2=door
export const DUNGEON_MAP: number[][] = [
  [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
  [1,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,0,0,0,0,0,0,0,0,1],
  [1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1],
  [1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,1,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1],
  [1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,2,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
  [1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
  [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
];

// ── Initial agents (from GameScene llmDefs) ────────────

const DEFAULT_AGENTS: AgentView[] = [
  { id: 'kael', name: 'Kael', role: 'adventurer', pos: [5*32, 7*32], color: 0x44aaff, objective: 'Explore the Grand Hall', status: 'idle', health: 100 },
  { id: 'lyra', name: 'Lyra', role: 'scout', pos: [15*32, 6*32], color: 0x44ff88, objective: 'Map the Grand Hall corridors', status: 'idle', health: 100 },
  { id: 'mordecai', name: 'Mordecai', role: 'sage', pos: [34*32, 2*32], color: 0xcc88ff, objective: 'Research in the Library', status: 'idle', health: 100 },
  { id: 'grom', name: 'Grom', role: 'blacksmith', pos: [4*32, 14*32], color: 0xff8844, objective: 'Forge weapons in the Armory', status: 'idle', health: 100 },
  { id: 'zara', name: 'Zara', role: 'alchemist', pos: [34*32, 14*32], color: 0x44ffaa, objective: 'Brew potions in the Crypt lab', status: 'idle', health: 100 },
  { id: 'finn', name: 'Finn', role: 'merchant', pos: [4*32, 2*32], color: 0xffff44, objective: 'Trade at the Entrance', status: 'idle', health: 100 },
  { id: 'guard', name: 'Guard', role: 'guard', pos: [10*32, 7*32], color: 0x8888cc, objective: 'Patrol the Grand Hall', status: 'idle', health: 100 },
];

const DEFAULT_STATIONS = [
  { name: 'Anvil', x: 4 * 32, y: 14 * 32, description: 'A heavy anvil in the Armory. Sparks still glow on its surface.' },
  { name: 'Cauldron', x: 34 * 32, y: 14 * 32, description: 'A bubbling cauldron in the Crypt, filled with luminous green liquid.' },
  { name: 'Counter', x: 4 * 32, y: 2 * 32, description: 'A wooden counter at the Entrance, cluttered with curious trinkets.' },
  { name: 'Bookshelf', x: 34 * 32, y: 2 * 32, description: 'Ancient tomes line the Library shelves.' },
  { name: 'Bar', x: 5 * 32, y: 7 * 32, description: 'A sturdy oak bar in the Tavern.' },
];

const DEFAULT_LIGHTS: RoomLight[] = [
  // Entrance
  { x: 4*32, y: 1*32, radius: 150, color: 0xff6622, intensity: 1.2 },
  { x: 4*32, y: 3*32, radius: 150, color: 0xff6622, intensity: 1.2 },
  // Grand Hall torches
  { x: 10*32, y: 4*32, radius: 180, color: 0xff6622, intensity: 1.5 },
  { x: 28*32, y: 4*32, radius: 180, color: 0xff6622, intensity: 1.5 },
  { x: 14*32, y: 10*32, radius: 160, color: 0xff6622, intensity: 1.3 },
  { x: 24*32, y: 10*32, radius: 160, color: 0xff6622, intensity: 1.3 },
  { x: 10*32, y: 17*32, radius: 180, color: 0xff6622, intensity: 1.5 },
  { x: 28*32, y: 17*32, radius: 180, color: 0xff6622, intensity: 1.5 },
  // Tavern
  { x: 4*32, y: 7*32, radius: 160, color: 0xff8844, intensity: 1.0 },
  // Library
  { x: 34*32, y: 2*32, radius: 160, color: 0x8888ff, intensity: 1.2 },
  // Treasury
  { x: 34*32, y: 8*32, radius: 160, color: 0xffcc44, intensity: 1.5 },
  // Crypt
  { x: 34*32, y: 14*32, radius: 160, color: 0x6644aa, intensity: 0.8 },
  // Armory
  { x: 4*32, y: 14*32, radius: 160, color: 0xff6644, intensity: 1.0 },
  // Pillar corner lights (Grand Hall center)
  { x: 19*32, y: 8*32, radius: 140, color: 0x88aaff, intensity: 0.6 },
  { x: 19*32, y: 12*32, radius: 140, color: 0x88aaff, intensity: 0.6 },
];

// ── Zustand Store ──────────────────────────────────────

interface WorldStore extends WorldState {
  patch: (p: Partial<WorldState>) => void;
  setAgent: (id: string, update: Partial<AgentView>) => void;
  setPlayerPos: (x: number, y: number) => void;
  pushLog: (entry: { agent: string; text: string }) => void;
  setOsState: (key: keyof WorldState['osState'], value: number) => void;
  isWalkable: (tileX: number, tileY: number) => boolean;
}

// Build agent record from default list
const buildAgentRecord = () => {
  const r: Record<string, AgentView> = {};
  for (const a of DEFAULT_AGENTS) r[a.id] = a;
  return r;
};

export const useWorldStore = create<WorldStore>((set, get) => ({
  // ── State ──
  tick: 0,
  mapGrid: DUNGEON_MAP,
  tileSize: TILE,
  mapW: MAP_W,
  mapH: MAP_H,
  agents: buildAgentRecord(),
  quests: [],
  osState: { comms: 25, knowledge: 40, tooling: 30, economy: 15, safety: 50 },
  playerPos: [4 * TILE, 2 * TILE],
  lights: DEFAULT_LIGHTS,
  stations: DEFAULT_STATIONS,
  log: [],

  // ── Actions ──
  patch: (p) => set((s) => ({ ...s, ...p })),

  setAgent: (id, update) => set((s) => ({
    agents: {
      ...s.agents,
      [id]: { ...s.agents[id], ...update },
    },
  })),

  setPlayerPos: (x, y) => set({ playerPos: [x, y] }),

  pushLog: (entry) => set((s) => ({
    log: [...s.log.slice(-49), { tick: s.tick, ...entry }],
  })),

  setOsState: (key, value) => set((s) => ({
    osState: { ...s.osState, [key]: Math.max(0, Math.min(100, value)) },
  })),

  isWalkable: (tileX, tileY) => {
    const { mapGrid, mapW, mapH } = get();
    if (tileX < 0 || tileX >= mapW || tileY < 0 || tileY >= mapH) return false;
    const tile = mapGrid[tileY]?.[tileX];
    return tile === 0 || tile === 2;
  },
}));

// ── Export the raw map array for Pixi tilemap builder ──
// TILE, MAP_W, MAP_H, DUNGEON_MAP already exported via export const above

// ── Utility: build walkability grid ──
export function buildWalkGrid(map: number[][] = DUNGEON_MAP): boolean[][] {
  return map.map(row => row.map(tile => tile === 0 || tile === 2));
}
