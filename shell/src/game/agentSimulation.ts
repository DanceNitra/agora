/**
 * agentSimulation.ts — local agent simulation for standalone demo mode.
 *
 * When the backend isn't broadcasting, this module generates synthetic
 * agent state so the PixiJS dungeon always feels alive.
 *
 * Flow:
 *   1. Every 2-4 seconds, pick a random agent and move them
 *   2. Push log entries for visual interest
 *   3. Slightly fluctuate OS state
 *   4. Generate quest updates
 */

import { useWorldStore, AgentView, TILE, MAP_W, MAP_H } from '../state/world';

// ── Config ──
const MOVE_INTERVAL = 2500; // ms between agent moves
const LOG_INTERVAL = 5000;  // ms between log events
const OS_INTERVAL = 8000;   // ms between OS fluctuations
const QUEST_INTERVAL = 15000; // ms between quest updates

const STATUSES = ['idle', 'moving', 'working', 'patrolling', 'researching', 'trading'];

const LOG_TEMPLATES: { agent: string; templates: string[] }[] = [
  { agent: 'Kael', templates: ['Sweeping the dungeon floor', 'Inspecting the eastern wall', 'Polishing armor', 'Humming an old tune'] },
  { agent: 'Lyra', templates: ['Pacing near the entrance', 'Scanning the horizon', 'Checking map coordinates', 'Whistling softly'] },
  { agent: 'Mordecai', templates: ['Muttering arcane incantations', 'Reading a dusty tome', 'Examining a crystal shard', 'Scribbling notes'] },
  { agent: 'Grom', templates: ['Hammering on the anvil', 'Shaping a blade', 'Tempering steel', 'Organizing tools'] },
  { agent: 'Zara', templates: ['Stirring the cauldron', 'Crushing herbs with a mortar', 'Decanting a glowing liquid', 'Labeling vials'] },
  { agent: 'Finn', templates: ['Counting coins', 'Arranging wares on the counter', 'Haggling with a shadow', 'Updating the ledger'] },
  { agent: 'Guard', templates: ['Pacing the perimeter', 'Adjusting helmet strap', 'Leaning on a spear', 'Yawning'] },
];

let moveTimer: ReturnType<typeof setInterval> | null = null;
let logTimer: ReturnType<typeof setInterval> | null = null;
let osTimer: ReturnType<typeof setInterval> | null = null;
let questTimer: ReturnType<typeof setInterval> | null = null;
let destroyed = false;

// ── Get a random walkable tile position ──
function randomWalkablePos(): [number, number] | null {
  const map = useWorldStore.getState().mapGrid;
  for (let attempt = 0; attempt < 50; attempt++) {
    const x = Math.floor(Math.random() * MAP_W);
    const y = Math.floor(Math.random() * MAP_H);
    if (x >= 0 && x < MAP_W && y >= 0 && y < MAP_H && (map[y][x] === 0 || map[y][x] === 2)) {
      return [x * TILE, y * TILE];
    }
  }
  return null;
}

// ── Move a random agent ──
function moveRandomAgent(): void {
  const agents = useWorldStore.getState().agents;
  const ids = Object.keys(agents);
  if (ids.length === 0) return;

  const id = ids[Math.floor(Math.random() * ids.length)];
  const target = randomWalkablePos();
  if (!target) return;

  const status = STATUSES[Math.floor(Math.random() * STATUSES.length)];
  useWorldStore.getState().setAgent(id, {
    target: target,
    status: status,
  });
}

// ── Push a random log entry ──
function pushRandomLog(): void {
  const template = LOG_TEMPLATES[Math.floor(Math.random() * LOG_TEMPLATES.length)];
  const text = template.templates[Math.floor(Math.random() * template.templates.length)];
  useWorldStore.getState().pushLog({ agent: template.agent, text });
}

// ── Fluctuate OS state ──
function fluctuateOS(): void {
  const store = useWorldStore.getState();
  const keys = Object.keys(store.osState) as (keyof typeof store.osState)[];
  const key = keys[Math.floor(Math.random() * keys.length)];
  const delta = Math.floor(Math.random() * 10) - 3; // -3 to +7
  store.setOsState(key, store.osState[key] + delta);
}

// ── Update quests ──
const NPC_NAMES = ['Elder Quinn', 'Mysterious Stranger', 'Village Chief', 'Wandering Bard', 'Ancient Spirit'];
const QUESTS = [
  'Retrieve the Lost Artifact',
  'Slay the Cave Troll',
  'Deliver the Sealed Letter',
  'Gather Herbs for the Apothecary',
  'Escort the Merchant Caravan',
  'Investigate the Haunted Ruins',
  'Forge the Legendary Blade',
  'Brew the Elixir of Power',
];

let questIndex = 0;

function pushQuestUpdate(): void {
  const npc = NPC_NAMES[Math.floor(Math.random() * NPC_NAMES.length)];
  const quest = QUESTS[questIndex % QUESTS.length];
  questIndex++;

  useWorldStore.getState().patch({
    quests: [
      {
        npcName: npc,
        activeQuestTitle: quest,
        questStatus: 'active',
      },
    ],
  });

  useWorldStore.getState().pushLog({
    agent: npc,
    text: `"${quest}" — a new quest has arrived!`,
  });
}

// ── Tick increment ──
function incrementTick(): void {
  const store = useWorldStore.getState();
  store.patch({ tick: store.tick + 1 });
}

// ── Public API ──

export function startSimulation(): void {
  destroyed = false;

  // Initial quest
  pushQuestUpdate();

  // Move agents around
  moveTimer = setInterval(() => {
    if (destroyed) return;
    moveRandomAgent();
    incrementTick();
  }, MOVE_INTERVAL);

  // Log events
  logTimer = setInterval(() => {
    if (destroyed) return;
    pushRandomLog();
  }, LOG_INTERVAL);

  // OS fluctuation
  osTimer = setInterval(() => {
    if (destroyed) return;
    fluctuateOS();
  }, OS_INTERVAL);

  // Quest updates
  questTimer = setInterval(() => {
    if (destroyed) return;
    pushQuestUpdate();
  }, QUEST_INTERVAL);
}

export function stopSimulation(): void {
  destroyed = true;
  if (moveTimer) clearInterval(moveTimer);
  if (logTimer) clearInterval(logTimer);
  if (osTimer) clearInterval(osTimer);
  if (questTimer) clearInterval(questTimer);
  moveTimer = null;
  logTimer = null;
  osTimer = null;
  questTimer = null;
}
