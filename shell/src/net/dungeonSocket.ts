/**
 * dungeonSocket.ts — WebSocket bridge between the Python backend and the
 * PixiJS dungeon world.ts Zustand store.
 *
 * Flow:
 *   Backend event → WS → this module → worldStore.patch() / setAgent() / pushLog()
 *   → PixiJS ticker reads store → agents move, log updates, OS meters change
 *
 * Connects on init, auto-reconnects on disconnect (3s backoff).
 * Subscribes to "all" topic by default.
 */

import { useWorldStore, AgentView } from '../state/world';

// ── Config ──
const RECONNECT_DELAY = 3000;
const PING_INTERVAL = 15000; // keepalive

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pingTimer: ReturnType<typeof setInterval> | null = null;
let destroyed = false;

// ── Agent update mapper ──
function mapBackendAgent(update: any): Partial<AgentView> | null {
  const posX = (update.pos_x ?? update.x) as number | undefined;
  const posY = (update.pos_y ?? update.y) as number | undefined;
  if (posX === undefined || posY === undefined) return null;

  return {
    pos: [posX, posY],
    target: update.target_x !== undefined && update.target_y !== undefined
      ? [update.target_x, update.target_y]
      : undefined,
    status: update.status || 'idle',
    health: update.health ?? 100,
    objective: update.objective || undefined,
  };
}

// ── Handle incoming event ──
function handleEvent(type: string, payload: any): void {
  const store = useWorldStore.getState();

  switch (type) {
    case 'heartbeat':
    case 'epoch_start':
    case 'epoch_end': {
      const patch: any = {};
      if (payload.tick !== undefined) patch.tick = payload.tick;

      // Agent positions
      if (payload.agents && Array.isArray(payload.agents)) {
        for (const agent of payload.agents) {
          const id = agent.agent_id || agent.name;
          if (!id) continue;
          const update = mapBackendAgent(agent);
          if (update) store.setAgent(id, update);
        }
      }

      // OS state
      if (payload.os_state) {
        for (const [key, val] of Object.entries(payload.os_state)) {
          if (key in store.osState) {
            store.setOsState(key as keyof typeof store.osState, val as number);
          }
        }
      }

      if (Object.keys(patch).length > 0) store.patch(patch);
      break;
    }

    case 'agent_thought': {
      const agentName = payload.agent_name || payload.agent_id || 'unknown';
      const thought = payload.thought || payload.text || '...';
      store.pushLog({ agent: agentName, text: thought });

      // Update agent status
      if (payload.agent_id || payload.agent_name) {
        const id = payload.agent_id || payload.agent_name;
        store.setAgent(id, { status: payload.status || 'thinking' });
      }
      break;
    }

    case 'agent_moved': {
      const id = payload.agent_id || payload.name;
      if (!id) break;
      const update = mapBackendAgent(payload);
      if (update) store.setAgent(id, update);
      break;
    }

    case 'quest_update': {
      store.patch({
        quests: payload.quests || store.quests,
      });
      store.pushLog({
        agent: 'System',
        text: payload.text || `Quest update: ${payload.status || 'changed'}`,
      });
      break;
    }

    case 'resource_drop': {
      store.pushLog({
        agent: payload.agent_name || 'System',
        text: `Dropped ${payload.quantity || ''} ${payload.resource_name || 'resources'}`,
      });
      break;
    }

    case 'byzantine_violation': {
      store.pushLog({
        agent: payload.source_id || 'Security',
        text: `⚠️ Violation: ${payload.detail || payload.type || 'unknown'}`,
      });
      break;
    }

    case 'message': {
      if (payload.text) {
        store.pushLog({ agent: 'System', text: payload.text.slice(0, 200) });
      }
      break;
    }
  }
}

// ── Connect ──
function connect(): void {
  if (destroyed || ws?.readyState === WebSocket.OPEN) return;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${window.location.host}/ws`;

  try {
    ws = new WebSocket(url);

    ws.onopen = () => {
      // Subscribe to all topics
      ws?.send(JSON.stringify({
        type: 'subscribe',
        topics: ['all'],
      }));

      // Start ping keepalive
      if (pingTimer) clearInterval(pingTimer);
      pingTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        const eventType = msg.type || 'message';
        const payload = msg.payload || msg;
        handleEvent(eventType, payload);
      } catch {
        // Non-JSON messages ignored
      }
    };

    ws.onclose = () => {
      if (pingTimer) clearInterval(pingTimer);
      if (!destroyed) {
        reconnectTimer = setTimeout(connect, RECONNECT_DELAY);
      }
    };

    ws.onerror = () => {
      ws?.close();
    };
  } catch {
    if (!destroyed) {
      reconnectTimer = setTimeout(connect, RECONNECT_DELAY);
    }
  }
}

// ── Public API ──

/** Start the WebSocket bridge. Call once on app mount. */
export function startDungeonSocket(): void {
  destroyed = false;
  connect();
}

/** Stop the bridge. Call on app unmount. */
export function stopDungeonSocket(): void {
  destroyed = true;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  if (pingTimer) clearInterval(pingTimer);
  if (ws) {
    ws.close();
    ws = null;
  }
}
