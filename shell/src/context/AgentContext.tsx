import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';

// ── Agent Data Types ──

export interface AgentDetail {
  id: string;
  name: string;
  role: string;
  trustScore: number;
  energyBalance: number;
  health: number;
  status: string;
  objective: string;
  inventory: string[];
  position: { x: number; y: number };
  memories: { text: string; importance: number; timestamp: number }[];
  artifacts: { id: number; title: string; type: string }[];
  tasks: { id: number; title: string; status: string; difficulty?: number }[];
  nearbyNPCs: string[];
}

// ── Context ──

interface AgentContextType {
  selectedAgent: AgentDetail | null;
  setSelectedAgent: (agent: AgentDetail | null) => void;
  liveAgents: AgentDetail[];
  wsConnected: boolean;
  openAgentByName: (name: string) => Promise<void>;
}

const AgentContext = createContext<AgentContextType | null>(null);

export const useAgent = () => {
  const ctx = useContext(AgentContext);
  if (!ctx) throw new Error('useAgent must be used within AgentProvider');
  return ctx;
};

// ── API helpers ──

async function fetchAgentDetail(name: string): Promise<AgentDetail | null> {
  try {
    const [agentRes, memRes, artRes, taskRes] = await Promise.all([
      fetch(`/api/v1/agents/${name}`),
      fetch(`/api/v1/dungeon/memories?agent_name=${name}`),
      fetch(`/api/v1/artifacts/?agent_id=${name}&limit=5`),
      fetch(`/api/v1/tasks/?assigned_to=${name}&limit=5`),
    ]);

    const agent = agentRes.ok ? await agentRes.json() : null;
    const memories = memRes.ok ? (await memRes.json()).memories || [] : [];
    const artifacts = artRes.ok ? (await artRes.json()).artifacts || [] : [];
    const tasks = taskRes.ok ? (await taskRes.json()).tasks || [] : [];

    if (!agent) return null;

    return {
      id: agent.agent_id || name,
      name: agent.name || name,
      role: agent.role || 'unknown',
      trustScore: agent.trust_score ?? 0.5,
      energyBalance: agent.energy_balance ?? 0,
      health: agent.health ?? 100,
      status: agent.status || 'active',
      objective: agent.objective || 'Explore the dungeon',
      inventory: agent.inventory || [],
      position: { x: agent.pos_x || 0, y: agent.pos_y || 0 },
      memories: memories.slice(-5),
      artifacts: artifacts.map((a: any) => ({ id: a.id, title: a.title, type: a.artifact_type })),
      tasks: tasks.map((t: any) => ({ id: t.id, title: t.title, status: t.status, difficulty: t.difficulty })),
      nearbyNPCs: agent.nearby_npcs || [],
    };
  } catch {
    return null;
  }
}

// ── Provider ──

export const AgentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedAgent, setSelectedAgent] = useState<AgentDetail | null>(null);
  const [liveAgents, setLiveAgents] = useState<AgentDetail[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // WebSocket for live agent updates
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => setWsConnected(true);

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimerRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          // Handle tick/heartbeat updates
          if (data.type === 'tick' || data.type === 'heartbeat') {
            if (data.agents) {
              setLiveAgents((prev) => {
                const merged = [...prev];
                for (const update of data.agents) {
                  const idx = merged.findIndex((a) => a.id === update.agent_id || a.name === update.name);
                  if (idx >= 0) {
                    merged[idx] = { ...merged[idx], ...mapAgentUpdate(update) };
                  } else {
                    merged.push(mapAgentUpdate(update));
                  }
                }
                return merged;
              });
            }
          }
          // Handle agent state snapshots
          if (data.type === 'agent_state' && data.agents) {
            setLiveAgents(data.agents.map(mapAgentUpdate));
          }
        } catch {
          // Non-JSON messages ignored
        }
      };
    };

    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, []);

  // Periodic refresh of live agents (fallback when WS doesn't push)
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/v1/agents/');
        if (res.ok) {
          const json = await res.json();
          setLiveAgents((json.agents || []).map((a: any) => ({
            id: a.agent_id || a.name,
            name: a.name || a.agent_id || 'unknown',
            role: a.role || 'unknown',
            trustScore: a.trust_score ?? 0.5,
            energyBalance: a.energy_balance ?? 0,
            health: a.health ?? 100,
            status: a.status || 'active',
            objective: a.objective || '',
            inventory: a.inventory || [],
            position: { x: a.pos_x || 0, y: a.pos_y || 0 },
            memories: [],
            artifacts: [],
            tasks: [],
            nearbyNPCs: a.nearby_npcs || [],
          })));
        }
      } catch { /* silent */ }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const openAgentByName = useCallback(async (name: string) => {
    const detail = await fetchAgentDetail(name);
    if (detail) setSelectedAgent(detail);
  }, []);

  return (
    <AgentContext.Provider value={{ selectedAgent, setSelectedAgent, liveAgents, wsConnected, openAgentByName }}>
      {children}
    </AgentContext.Provider>
  );
};

function mapAgentUpdate(update: any): AgentDetail {
  return {
    id: update.agent_id || update.name || 'unknown',
    name: update.name || update.agent_id || 'unknown',
    role: update.role || 'unknown',
    trustScore: update.trust_score ?? update.trustScore ?? 0.5,
    energyBalance: update.energy_balance ?? update.energyBalance ?? 0,
    health: update.health ?? 100,
    status: update.status || 'active',
    objective: update.objective || '',
    inventory: update.inventory || [],
    position: { x: update.pos_x ?? update.x ?? 0, y: update.pos_y ?? update.y ?? 0 },
    memories: update.memories || [],
    artifacts: update.artifacts || [],
    tasks: update.tasks || [],
    nearbyNPCs: update.nearby_npcs || [],
  };
}
