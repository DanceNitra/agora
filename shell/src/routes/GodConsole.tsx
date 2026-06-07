import React, { useEffect, useState, useCallback } from 'react';
import { useWebSocket, WSEvent, WSThoughtUpdate, WSTickUpdate } from '../hooks/useWebSocket';

// ═══════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════

interface NPC {
  npc_id: string; npc_name: string; role: string;
  health: number; status: string; pos_x: number; pos_y: number;
  stamina: number; hunger: number; fatigue: number;
  state_of_mind: string; current_goal: string; plan_stack: string;
  personality: string; archetype: string; emotional_state: string;
}

interface NPCDetail {
  npc: any; body: any; brain: any; soul: any;
  abilities: any[]; skills: any[]; memories: any[]; inventory: any[];
}

interface StateDist {
  state_of_mind: string; count: number;
  avg_health: number; avg_stamina: number; avg_hunger: number; avg_fatigue: number;
}

interface AOSSummary {
  state_distribution: StateDist[];
  help_requests: { total: number; completed: number };
  all_npcs: { npc_name: string; state_of_mind: string; current_goal: string; health: number }[];
}

interface Violation {
  id?: number; event_type?: string; source_id?: string; payload?: string;
  type?: string; detail?: string; severity?: string; npc_id?: string;
  created_at?: string;
}

interface ControllerStats {
  tick: number; rooms: string[]; priorities: Record<string, number>;
  multiprocessing: boolean;
}

interface TrustAgent {
  id: string; role: string; eigen_trust: number; ess_trust: number;
}

interface TrustMatrixData {
  agents: TrustAgent[];
  top_agents: TrustAgent[];
  matrix_stats: { n: number; pairs: number; density: number; mean_trust: number; };
}

// Quest types
interface Quest {
  id: string; title: string; goal: string; subsystem: string;
  success_criteria: string[]; reward: number; owner: string | null;
  status: string; depends_on: string[]; denial_reason: string | null;
  denial_fix: string | null; block_reason: string | null;
  verification_runs: number | null;
  created_at: string | null; assigned_at: string | null; completed_at: string | null;
}

interface QuestDashboard {
  quests: Quest[];
  counts: Record<string, number>;
  agents: string[];
  os_state: any;
}

type TabId = 'agents' | 'violations' | 'os' | 'controller' | 'health' | 'trust' | 'quests';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'agents', label: 'Agent Management', icon: '👤' },
  { id: 'violations', label: 'Byzantine', icon: '⚠️' },
  { id: 'os', label: 'Agent OS', icon: '🧠' },
  { id: 'controller', label: 'Controller', icon: '⚙️' },
  { id: 'health', label: 'Health', icon: '💚' },
  { id: 'trust', label: 'Trust Matrix', icon: '🔗' },
  { id: 'quests', label: 'Orchestrator', icon: '🎯' },
];

// ═══════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════

const GodConsoleV2: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('health');
  const [npcs, setNpcs] = useState<NPC[]>([]);
  const [selectedNpc, setSelectedNpc] = useState<NPC | null>(null);
  const [npcDetail, setNpcDetail] = useState<NPCDetail | null>(null);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [osSummary, setOsSummary] = useState<AOSSummary | null>(null);
  const [controllerStats, setControllerStats] = useState<ControllerStats | null>(null);
  const [healthData, setHealthData] = useState<any>(null);
  const [trustData, setTrustData] = useState<TrustMatrixData | null>(null);
  const [questData, setQuestData] = useState<QuestDashboard | null>(null);
  const [questAction, setQuestAction] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  const api = (path: string) => `${window.location.origin}${path}`;

  const refreshNpcs = useCallback(async () => {
    try {
      const res = await fetch(api('/api/v2/god/npcs'));
      if (res.ok) setNpcs((await res.json()).npcs || []);
    } catch {}
  }, [api]);

  const refreshOsSummary = useCallback(async () => {
    try {
      const res = await fetch(api('/api/v2/god/agent-os/summary'));
      if (res.ok) setOsSummary(await res.json());
    } catch {}
  }, [api]);

  const refreshTrust = useCallback(async () => {
    try {
      const res = await fetch(api('/api/v1/eval/trust/matrix'));
      if (res.ok) setTrustData(await res.json());
    } catch {}
  }, [api]);

  const refreshQuests = useCallback(async () => {
    try {
      const res = await fetch(api('/api/v2/god/quests'));
      if (res.ok) setQuestData(await res.json());
    } catch {}
  }, [api]);

  const refreshHealth = useCallback(async () => {
    try {
      const res = await fetch(api('/api/v2/god/health'));
      if (res.ok) setHealthData(await res.json());
    } catch {}
  }, [api]);

  const refreshViolations = useCallback(async () => {
    try {
      const res = await fetch(api('/api/v2/god/violations'));
      if (res.ok) setViolations((await res.json()).violations || []);
    } catch {}
  }, [api]);

  // ── WebSocket live updates ──
  const { connected, subscribe } = useWebSocket({
    onEvent: (event: WSEvent) => {
      // Update health tick counter on heartbeat
      if (event.type === 'heartbeat') {
        setHealthData((prev: any) => prev ? { ...prev, tick: event.payload.tick } : prev);
      }
    },
    onThought: (thought: WSThoughtUpdate) => {
      // Update NPC health/trust in the list when an agent thinks
      setNpcs((prev: NPC[]) => {
        if (!thought.agent_id || thought.trust === undefined) return prev;
        return prev.map((n: NPC) =>
          n.npc_id?.slice(0, 8) === thought.agent_id
            ? { ...n, trust: thought.trust }
            : n
        );
      });
    },
    onHeartbeat: (hb: WSTickUpdate) => {
      // Update tick count in health data
      setHealthData((prev: any) => prev ? { ...prev, tick: hb.tick, active_npcs: hb.agents } : prev);
    },
    onCSDAlert: () => {
      // Refresh violations on alert
      refreshViolations();
    },
    onEpochUpdate: () => {
      // Refresh trust matrix + OS summary on epoch
      refreshTrust();
      refreshOsSummary();
      refreshNpcs();
    },
    onHelpRequest: () => {
      refreshOsSummary();
    },
    onHelpAccepted: () => {
      refreshOsSummary();
    },
    onError: () => {},
  });

  // Track WS connection state
  useEffect(() => {
    setWsConnected(connected);
    const interval = setInterval(() => {
      // Check if we're still connected (ref approach in hook)
    }, 5000);
    return () => clearInterval(interval);
  }, [connected]);

  // Fetch data based on active tab
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        if (activeTab === 'agents' || activeTab === 'health') {
          await refreshNpcs();
        }
        if (activeTab === 'violations' || activeTab === 'health') {
          await refreshViolations();
        }
        if (activeTab === 'os' || activeTab === 'health') {
          await refreshOsSummary();
        }
        if (activeTab === 'controller' || activeTab === 'health') {
          const res = await fetch(api('/api/v2/god/controller'));
          if (res.ok) setControllerStats(await res.json());
        }
        if (activeTab === 'health') {
          await refreshHealth();
        }
        if (activeTab === 'trust') {
          await refreshTrust();
        }
        if (activeTab === 'quests') {
          await refreshQuests();
        }
      } catch (e) {
        console.error('Fetch error:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [activeTab, refreshNpcs, refreshOsSummary, refreshTrust, refreshHealth, refreshViolations, refreshQuests, api]);

  const loadNpcDetail = async (npc: NPC) => {
    setSelectedNpc(npc);
    setNpcDetail(null);
    try {
      const res = await fetch(api(`/api/v2/god/npcs/${npc.npc_id}/detail`));
      if (res.ok) setNpcDetail(await res.json());
    } catch (e) {
      console.error('Detail fetch error:', e);
    }
  };

  const toggleNpcStatus = async (npc: NPC, action: 'pause' | 'resume') => {
    try {
      await fetch(api(`/api/v2/god/npcs/${npc.npc_id}/${action}`), { method: 'POST' });
      await refreshNpcs();
    } catch (e) {
      console.error('Toggle error:', e);
    }
  };

  const performQuestAction = async (questId: string, action: string, agent?: string) => {
    setQuestAction(`${action} ${questId}...`);
    try {
      const base = `/api/v2/dungeon-os/quests/${questId}/${action}`;
      const body = agent ? JSON.stringify({ agent }) : JSON.stringify({ runs: 3 });
      const res = await fetch(api(base), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      const data = await res.json();
      if (data.error || data.detail) {
        alert(`Error: ${data.error || data.detail}`);
      }
      await refreshQuests();
    } catch (e) {
      console.error('Quest action error:', e);
      alert(`Action failed: ${e}`);
    }
    setQuestAction('');
  };

  const stateColor = (s: string) => {
    switch (s) {
      case 'focused': return '#22c55e';
      case 'planning': return '#88ccff';
      case 'resting': return '#eab308';
      case 'confused': return '#f97316';
      case 'panicked': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const trustColor = (s: string) => {
    if (s === 'active') return '#22c55e';
    if (s === 'paused') return '#eab308';
    return '#6b7280';
  };

  return (
    <div style={styles.container}>
      {/* Pulse animation keyframes */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>⚡ God Console 2.0</h2>
        <span style={{
          ...styles.liveBadge,
          background: wsConnected ? '#22c55e' : '#ef4444',
          animation: wsConnected ? 'pulse 2s infinite' : 'none',
        }}>
          {wsConnected ? '🔴 LIVE' : '⏹️ OFFLINE'}
        </span>
      </div>

      {/* Tabs */}
      <div style={styles.tabRow}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              ...styles.tab,
              ...(activeTab === t.id ? styles.tabActive : {}),
            }}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {loading && <div style={styles.loading}>Loading...</div>}

      {/* Tab content */}
      {activeTab === 'agents' && (
        <AgentManagementTab
          npcs={npcs}
          selectedNpc={selectedNpc}
          npcDetail={npcDetail}
          onSelectNpc={loadNpcDetail}
          onToggleStatus={toggleNpcStatus}
          onCloseDetail={() => { setSelectedNpc(null); setNpcDetail(null); }}
          stateColor={stateColor}
          trustColor={trustColor}
        />
      )}

      {activeTab === 'violations' && (
        <ViolationsTab violations={violations} stateColor={stateColor} />
      )}

      {activeTab === 'os' && (
        <AgentOSTab osSummary={osSummary} stateColor={stateColor} />
      )}

      {activeTab === 'controller' && (
        <ControllerTab stats={controllerStats} />
      )}

      {activeTab === 'health' && (
        <HealthTab
          health={healthData}
          npcs={npcs}
          violations={violations}
          osSummary={osSummary}
          controllerStats={controllerStats}
        />
      )}

      {activeTab === 'trust' && (
        <TrustTab data={trustData} />
      )}

      {activeTab === 'quests' && (
        <QuestsTab
          questData={questData}
          agents={questData?.agents || []}
          onAssign={(qId, agent) => performQuestAction(qId, 'assign', agent)}
          onSubmit={(qId, agent) => performQuestAction(qId, 'submit', agent)}
          onVerify={(qId) => performQuestAction(qId, 'verify')}
          questAction={questAction}
          stateColor={stateColor}
        />
      )}
    </div>
  );
};

// ═══════════════════════════════════════════
// TAB 1: AGENT MANAGEMENT
// ═══════════════════════════════════════════

const AgentManagementTab: React.FC<{
  npcs: NPC[]; selectedNpc: NPC | null; npcDetail: NPCDetail | null;
  onSelectNpc: (n: NPC) => void; onToggleStatus: (n: NPC, a: 'pause' | 'resume') => void;
  onCloseDetail: () => void; stateColor: (s: string) => string; trustColor: (s: string) => string;
}> = ({ npcs, selectedNpc, npcDetail, onSelectNpc, onToggleStatus, onCloseDetail, stateColor, trustColor }) => (
  <div style={styles.tabContent}>
    <div style={styles.twoCol}>
      {/* NPC List */}
      <div style={{ flex: 1, minWidth: 400 }}>
        <h3 style={styles.sectionTitle}>All NPCs ({npcs.length})</h3>
        <div style={styles.table}>
          <div style={styles.tableHeader}>
            <span style={{ flex: 2 }}>Name</span>
            <span style={{ flex: 1 }}>Role</span>
            <span style={{ flex: 1 }}>State</span>
            <span style={{ flex: 1, textAlign: 'center' }}>❤️</span>
            <span style={{ flex: 1, textAlign: 'center' }}>⚡</span>
            <span style={{ flex: 0.8 }}>Status</span>
            <span style={{ flex: 1 }}>Actions</span>
          </div>
          {npcs.map((n) => (
            <div
              key={n.npc_id}
              style={{
                ...styles.tableRow,
                background: selectedNpc?.npc_id === n.npc_id ? '#2a3a4a' : 'transparent',
                cursor: 'pointer',
              }}
              onClick={() => onSelectNpc(n)}
            >
              <span style={{ flex: 2, fontWeight: 600 }}>{n.npc_name}</span>
              <span style={{ flex: 1, fontSize: 12, textTransform: 'capitalize' }}>{n.role}</span>
              <span style={{ flex: 1, fontSize: 12, color: stateColor(n.state_of_mind) }}>
                {n.state_of_mind}
              </span>
              <span style={{ flex: 1, textAlign: 'center', fontSize: 13 }}>
                {n.health?.toFixed(0)}
              </span>
              <span style={{ flex: 1, textAlign: 'center', fontSize: 13 }}>
                {n.stamina?.toFixed(0)}
              </span>
              <span style={{ flex: 0.8, fontSize: 11 }}>
                <span style={{
                  display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                  background: trustColor(n.status), marginRight: 4,
                }} />
                {n.status}
              </span>
              <span style={{ flex: 1, display: 'flex', gap: 4 }}>
                {n.status === 'active' ? (
                  <button style={styles.smallBtn} onClick={(e) => { e.stopPropagation(); onToggleStatus(n, 'pause'); }}>
                    ⏸️
                  </button>
                ) : (
                  <button style={styles.smallBtn} onClick={(e) => { e.stopPropagation(); onToggleStatus(n, 'resume'); }}>
                    ▶️
                  </button>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* NPC Detail */}
      {npcDetail && selectedNpc && (
        <div style={{ flex: 1, minWidth: 350, background: '#1f2937', borderRadius: 8, padding: 12, border: '1px solid #374151' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#fbbf24', margin: 0 }}>
              {selectedNpc.npc_name}
            </h3>
            <button onClick={onCloseDetail} style={{ ...styles.smallBtn, fontSize: 14 }}>✕</button>
          </div>
          <DetailPanel npcDetail={npcDetail} stateColor={stateColor} />
        </div>
      )}
    </div>
  </div>
);

const DetailPanel: React.FC<{ npcDetail: NPCDetail; stateColor: (s: string) => string }> = ({ npcDetail, stateColor }) => {
  const n = npcDetail.npc;
  const brain = npcDetail.brain || {};
  const body = npcDetail.body || {};
  const soul = npcDetail.soul || {};

  return (
    <div>
      {/* Quick stats */}
      <div style={styles.statGrid}>
        <Stat label="Health" value={n.health?.toFixed(0)} color="#ef4444" />
        <Stat label="Stamina" value={body.stamina?.toFixed(0)} color="#22c55e" />
        <Stat label="Hunger" value={body.hunger?.toFixed(0)} color="#eab308" />
        <Stat label="Fatigue" value={body.fatigue?.toFixed(0)} color="#f97316" />
        <Stat label="Position" value={`(${n.pos_x},${n.pos_y})`} color="#88ccff" />
        <Stat label="Status" value={n.status} color={n.status === 'active' ? '#22c55e' : '#6b7280'} />
      </div>

      {/* Brain */}
      <div style={{ marginTop: 10 }}>
        <div style={styles.subtitle}>🧠 Brain</div>
        <div style={styles.keyVal}>
          <span>State: <b style={{ color: stateColor(brain.state_of_mind || 'unknown') }}>{brain.state_of_mind || '—'}</b></span>
          <span>Goal: {brain.current_goal || '—'}</span>
          <span>Plan: {brain.plan_stack ? (JSON.parse(brain.plan_stack)?.length || 0) + ' steps' : '0 steps'}</span>
          <span>Last: {brain.last_decision || '—'}</span>
        </div>
      </div>

      {/* Soul */}
      <div style={{ marginTop: 10 }}>
        <div style={styles.subtitle}>💎 Soul</div>
        <div style={styles.keyVal}>
          <span>Archetype: {soul.archetype || '—'}</span>
          <span>Emotion: {soul.emotional_state || '—'}</span>
          <span>Alignment: {soul.moral_alignment || '—'}</span>
          <span>Personality: {renderJson(soul.personality, ['openness', 'conscientiousness'])}</span>
        </div>
      </div>

      {/* Skills & Abilities */}
      <div style={{ marginTop: 10, display: 'flex', gap: 16 }}>
        <div style={{ flex: 1 }}>
          <div style={styles.subtitle}>📚 Skills ({npcDetail.skills.length})</div>
          {npcDetail.skills.slice(0, 5).map((s, i) => (
            <div key={i} style={styles.inlineItem}>
              <span>{s.skill_name}</span>
              <span style={{ color: '#88ccff' }}>Lv.{s.level}</span>
              <span style={{ fontSize: 11, color: '#6b7280' }}>{s.xp}/{s.xp_to_next}XP</span>
            </div>
          ))}
        </div>
        <div style={{ flex: 1 }}>
          <div style={styles.subtitle}>⚡ Abilities ({npcDetail.abilities.length})</div>
          {npcDetail.abilities.slice(0, 5).map((a, i) => (
            <div key={i} style={styles.inlineItem}>
              <span>{a.ability_name}</span>
              <span style={{ color: '#fbbf24' }}>Pw.{a.power_level}</span>
              <span style={{ fontSize: 11, color: a.is_passive ? '#22c55e' : '#f97316' }}>
                {a.is_passive ? 'passive' : 'active'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Inventory */}
      <div style={{ marginTop: 10 }}>
        <div style={styles.subtitle}>📦 Inventory ({npcDetail.inventory.length})</div>
        <div style={styles.inlineRow}>
          {npcDetail.inventory.map((i, idx) => (
            <span key={idx} style={styles.tag}>
              {i.name} x{i.quantity?.toFixed(1)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: string; color: string }> = ({ label, value, color }) => (
  <div style={styles.stat}>
    <div style={{ fontSize: 11, color: '#6b7280' }}>{label}</div>
    <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
  </div>
);

// ═══════════════════════════════════════════
// TAB 2: BYZANTINE VIOLATIONS
// ═══════════════════════════════════════════

const ViolationsTab: React.FC<{ violations: Violation[]; stateColor: (s: string) => string }> = ({ violations, stateColor }) => (
  <div style={styles.tabContent}>
    <h3 style={styles.sectionTitle}>⚠️ Byzantine Violations ({violations.length})</h3>
    {violations.length === 0 ? (
      <div style={{ color: '#22c55e', fontSize: 16, textAlign: 'center', padding: 40 }}>
        ✅ No violations detected — system is clean
      </div>
    ) : (
      <div style={styles.table}>
        <div style={styles.tableHeader}>
          <span style={{ flex: 1 }}>Time</span>
          <span style={{ flex: 2 }}>Type</span>
          <span style={{ flex: 1 }}>NPC</span>
          <span style={{ flex: 3 }}>Detail</span>
          <span style={{ flex: 0.8 }}>Severity</span>
        </div>
        {violations.map((v, i) => (
          <div key={v.id || i} style={styles.tableRow}>
            <span style={{ flex: 1, fontSize: 11, color: '#6b7280' }}>{v.created_at?.slice(11, 19) || '—'}</span>
            <span style={{ flex: 2, fontSize: 12, color: stateColor(v.type || v.event_type || '') }}>
              {v.type || v.event_type || '—'}
            </span>
            <span style={{ flex: 1, fontSize: 12 }}>{v.source_id?.slice(0, 8) || v.npc_id || '—'}</span>
            <span style={{ flex: 3, fontSize: 11, color: '#9ca3af' }}>{v.detail || v.payload || '—'}</span>
            <span style={{ flex: 0.8, fontSize: 11, color: v.severity === 'critical' ? '#ef4444' : '#eab308' }}>
              {v.severity || 'warning'}
            </span>
          </div>
        ))}
      </div>
    )}
  </div>
);

// ═══════════════════════════════════════════
// TAB 3: AGENT OS MONITORING
// ═══════════════════════════════════════════

const AgentOSTab: React.FC<{ osSummary: AOSSummary | null; stateColor: (s: string) => string }> = ({ osSummary, stateColor }) => {
  if (!osSummary) return <div style={styles.tabContent}>No Agent OS data available</div>;

  return (
    <div style={styles.tabContent}>
      <div style={styles.twoCol}>
        {/* State Distribution */}
        <div style={{ flex: 1 }}>
          <h3 style={styles.sectionTitle}>🌀 State Distribution</h3>
          <div style={styles.card}>
            {osSummary.state_distribution.map((s) => (
              <div key={s.state_of_mind} style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ color: stateColor(s.state_of_mind), fontWeight: 600, textTransform: 'capitalize' }}>
                    {s.state_of_mind}
                  </span>
                  <span style={{ color: '#d4d4d4' }}>{s.count} agents</span>
                </div>
                <div style={styles.barOuter}>
                  <div style={{
                    ...styles.barInner, width: `${(s.count / Math.max(...osSummary.state_distribution.map(x => x.count))) * 100}%`,
                    background: stateColor(s.state_of_mind),
                  }} />
                </div>
                <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
                  ❤️{s.avg_health} ⚡{s.avg_stamina} 🍖{s.avg_hunger} 💤{s.avg_fatigue}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Help Stats */}
        <div style={{ flex: 1 }}>
          <h3 style={styles.sectionTitle}>🆘 Help Requests</h3>
          <div style={styles.card}>
            <div style={{ display: 'flex', gap: 24 }}>
              <Stat label="Total" value={String(osSummary.help_requests.total)} color="#fbbf24" />
              <Stat label="Completed" value={String(osSummary.help_requests.completed)} color="#22c55e" />
              <Stat label="Pending" value={String(osSummary.help_requests.total - osSummary.help_requests.completed)} color="#f97316" />
            </div>
          </div>

          {/* All NPCs */}
          <h3 style={{ ...styles.sectionTitle, marginTop: 16 }}>👤 NPC Status Overview</h3>
          <div style={styles.card}>
            {osSummary.all_npcs.map((n, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #2a2a2a' }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{n.npc_name}</span>
                <span style={{ fontSize: 12, color: stateColor(n.state_of_mind), textTransform: 'capitalize' }}>
                  {n.state_of_mind}
                </span>
                <span style={{ fontSize: 11, color: '#6b7280', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {n.current_goal || '—'}
                </span>
                <span style={{ fontSize: 12, color: n.health < 50 ? '#ef4444' : '#22c55e' }}>
                  ❤️{n.health?.toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════
// TAB 4: CONTROLLER STATS
// ═══════════════════════════════════════════

const ControllerTab: React.FC<{ stats: ControllerStats | null }> = ({ stats }) => {
  if (!stats) return <div style={styles.tabContent}>No controller data available</div>;

  return (
    <div style={styles.tabContent}>
      <div style={styles.twoCol}>
        <div style={{ flex: 1 }}>
          <h3 style={styles.sectionTitle}>⚙️ Controller Status</h3>
          <div style={styles.card}>
            <div style={styles.keyVal}>
              <span>Tick: <b>#{stats.tick}</b></span>
              <span>Mode: <b style={{ color: stats.multiprocessing ? '#22c55e' : '#eab308' }}>
                {stats.multiprocessing ? '⚡ Multiprocessing' : '🔄 Single Process'}
              </b></span>
              <span>Active Rooms: {stats.rooms?.length || 0}</span>
            </div>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <h3 style={styles.sectionTitle}>🏠 Room Priorities</h3>
          <div style={styles.card}>
            {!stats.priorities || Object.keys(stats.priorities).length === 0 ? (
              <div style={{ color: '#6b7280', fontStyle: 'italic' }}>No tick data yet — waiting for next tick...</div>
            ) : (
              Object.entries(stats.priorities).sort((a, b) => b[1] - a[1]).map(([room, priority]) => (
                <div key={room} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #2a2a2a' }}>
                  <span style={{ fontWeight: 600, textTransform: 'capitalize', fontSize: 13 }}>{room.replace(/_/g, ' ')}</span>
                  <span style={{ color: priority > 20 ? '#ef4444' : priority > 10 ? '#f97316' : '#22c55e', fontSize: 13 }}>
                    {priority.toFixed(1)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════
// TAB 5: HEALTH
// ═══════════════════════════════════════════

const HealthTab: React.FC<{
  health: any; npcs: NPC[]; violations: Violation[];
  osSummary: AOSSummary | null; controllerStats: ControllerStats | null;
}> = ({ health, npcs, violations, osSummary, controllerStats }) => (
  <div style={styles.tabContent}>
    <div style={styles.cardRow}>
      <HealthCard value={health?.active_npcs ?? npcs.length} label="Active NPCs" color="#22c55e" />
      <HealthCard value={`#${health?.tick ?? 0}`} label="Tick" color="#88ccff" />
      <HealthCard value={health?.total_agents ?? 0} label="Thinking Agents" color="#fbbf24" />
      <HealthCard
        value={violations.length}
        label="Violations"
        color={violations.length > 0 ? '#ef4444' : '#22c55e'}
      />
      <HealthCard
        value={health?.multiprocessing ? 'ON' : 'OFF'}
        label="MP Mode"
        color={health?.multiprocessing ? '#22c55e' : '#6b7280'}
      />
      <HealthCard
        value={health?.redis_connected ? 'OK' : 'DOWN'}
        label="Redis"
        color={health?.redis_connected ? '#22c55e' : '#ef4444'}
      />
    </div>

    <div style={styles.twoCol}>
      {/* State of mind pie-style */}
      <div style={{ flex: 1 }}>
        <h3 style={styles.sectionTitle}>🌀 State of Mind</h3>
        <div style={styles.card}>
          {osSummary ? osSummary.state_distribution.map((s) => (
            <div key={s.state_of_mind} style={{ marginBottom: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                <span style={{ textTransform: 'capitalize' }}>{s.state_of_mind}</span>
                <span>{s.count}</span>
              </div>
              <div style={styles.barOuter}>
                <div style={{
                  ...styles.barInner, width: `${(s.count / Math.max(1, ...osSummary.state_distribution.map(x => x.count))) * 100}%`,
                  background: s.state_of_mind === 'focused' ? '#22c55e' : s.state_of_mind === 'confused' ? '#f97316' : '#eab308',
                }} />
              </div>
            </div>
          )) : <div style={{ color: '#6b7280' }}>Loading...</div>}
        </div>
      </div>

      {/* Room info */}
      <div style={{ flex: 1 }}>
        <h3 style={styles.sectionTitle}>🏠 Rooms</h3>
        <div style={styles.card}>
          {health && health.rooms?.length > 0 ? health.rooms.map((r: string) => (
            <div key={r} style={{ padding: '4px 0', fontSize: 13, textTransform: 'capitalize' }}>
              {r.replace(/_/g, ' ')}
            </div>
          )) : <div style={{ color: '#6b7280', fontStyle: 'italic' }}>Waiting for first tick...</div>}
        </div>
      </div>
    </div>
  </div>
);

// ═══════════════════════════════════════════
// TAB 6: TRUST MATRIX
// ═══════════════════════════════════════════

const TrustTab: React.FC<{ data: TrustMatrixData | null }> = ({ data }) => {
  if (!data) return <div style={styles.tabContent}>No trust data available</div>;

  const { agents, matrix_stats, top_agents } = data;
  const N = agents.length;
  const W = 600, H = 400;
  const cx = W / 2, cy = H / 2;
  const radius = Math.min(W, H) / 2.5;

  // Position nodes in a circle
  const positions = agents.map((_, i) => {
    const angle = (2 * Math.PI * i) / N - Math.PI / 2;
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });

  const maxTrust = Math.max(...agents.map(a => a.eigen_trust), 0.01);
  const minTrust = Math.min(...agents.map(a => a.eigen_trust), 0);

  const nodeRadius = (trust: number) => Math.max(8, 16 + (trust - minTrust) / (maxTrust - minTrust) * 20);

  const trustColorScale = (v: number) => {
    if (v >= 0.1) return '#22c55e';
    if (v >= 0.095) return '#88ccff';
    if (v >= 0.09) return '#fbbf24';
    return '#ef4444';
  };

  return (
    <div style={styles.tabContent}>
      {/* Stats cards */}
      <div style={styles.cardRow}>
        <HealthCard value={matrix_stats.n} label="Agents" color="#22c55e" />
        <HealthCard value={matrix_stats.pairs} label="Trust Pairs" color="#88ccff" />
        <HealthCard value={`${(matrix_stats.density * 100).toFixed(1)}%`} label="Density" color="#fbbf24" />
        <HealthCard value={matrix_stats.mean_trust.toFixed(3)} label="Mean Trust" color="#22c55e" />
      </div>

      <div style={{ display: 'flex', gap: 16, marginTop: 12 }}>
        {/* SVG force-directed graph */}
        <div style={{ flex: 2, ...styles.card, padding: 8 }}>
          <svg width={W} height={H} style={{ background: '#1a1a1a', borderRadius: 8 }}>
            {agents.flatMap((a, i) =>
              agents.slice(i + 1).map((b, j) => {
                const avgTrust = (a.eigen_trust + b.eigen_trust) / 2;
                if (avgTrust < 0.09) return null;
                const p1 = positions[i], p2 = positions[i + 1 + j];
                return (
                  <line key={`e-${i}`}
                    x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                    stroke={trustColorScale(avgTrust)}
                    strokeWidth={Math.max(0.5, avgTrust * 8)}
                    opacity={0.4}
                  />
                );
              })
            )}
            {agents.map((a, i) => {
              const p = positions[i];
              const r = nodeRadius(a.eigen_trust);
              return (
                <g key={`n-${i}`}>
                  <circle cx={p.x} cy={p.y} r={r}
                    fill={trustColorScale(a.eigen_trust)}
                    opacity={0.85} stroke="#fff" strokeWidth={1}
                  />
                  <text x={p.x} y={p.y + r + 13}
                    textAnchor="middle" fill="#d4d4d4"
                    fontSize={10} fontWeight={600}
                  >{a.role}</text>
                  <title>{a.role}: eigen={a.eigen_trust.toFixed(4)} ess={a.ess_trust.toFixed(4)}</title>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Ranking */}
        <div style={{ flex: 1, ...styles.card }}>
          <h3 style={{ ...styles.sectionTitle, marginTop: 0 }}>🏆 Trust Ranking</h3>
          {top_agents.map((a, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '6px 0', borderBottom: '1px solid #2a2a2a',
            }}>
              <span style={{ fontWeight: 600, fontSize: 13, color: trustColorScale(a.eigen_trust) }}>
                #{i + 1} {a.role}
              </span>
              <span style={{ fontSize: 12, color: '#d4d4d4' }}>
                {a.eigen_trust.toFixed(4)}
              </span>
            </div>
          ))}
          <div style={{ marginTop: 12, fontSize: 11, color: '#6b7280', borderTop: '1px solid #2a2a2a', paddingTop: 8 }}>
            <div>All {agents.length} agents:</div>
            {agents.map((a, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', fontSize: 11 }}>
                <span>#{i + 1} {a.role}</span>
                <span style={{ color: trustColorScale(a.eigen_trust) }}>{a.eigen_trust.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const HealthCard: React.FC<{ value: string | number; label: string; color: string }> = ({ value, label, color }) => (
  <div style={styles.card}>
    <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
    <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{label}</div>
  </div>
);

// ═══════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════
// TAB 7: QUESTS (Orchestrator Dashboard)
// ═══════════════════════════════════════════

const QuestsTab: React.FC<{
  questData: QuestDashboard | null;
  agents: string[];
  onAssign: (qId: string, agent: string) => void;
  onSubmit: (qId: string, agent: string) => void;
  onVerify: (qId: string) => void;
  questAction: string;
  stateColor: (s: string) => string;
}> = ({ questData, agents, onAssign, onSubmit, onVerify, questAction, stateColor }) => {
  const [selectedQuest, setSelectedQuest] = useState<Quest | null>(null);
  const [assignAgent, setAssignAgent] = useState<string>('');

  if (!questData) {
    return <div style={styles.loading}>Loading quest data...</div>;
  }

  const statusColor = (s: string) => {
    switch (s) {
      case 'open': return '#22c55e';
      case 'claimed': return '#eab308';
      case 'review': return '#88ccff';
      case 'done': return '#6b7280';
      case 'blocked': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const counts = questData.counts;
  const osState = questData.os_state?.state || {};
  const bootProgress = questData.os_state?.boot_progress || {};

  return (
    <div style={styles.tabContent}>
      {/* Summary cards */}
      <div style={styles.cardRow}>
        <div style={{ ...styles.card, flex: 1, minWidth: 120 }}>
          <div style={{ fontSize: 11, color: '#6b7280' }}>🟢 Open</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#22c55e' }}>{counts.open || 0}</div>
        </div>
        <div style={{ ...styles.card, flex: 1, minWidth: 120 }}>
          <div style={{ fontSize: 11, color: '#6b7280' }}>🟡 Claimed</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#eab308' }}>{counts.claimed || 0}</div>
        </div>
        <div style={{ ...styles.card, flex: 1, minWidth: 120 }}>
          <div style={{ fontSize: 11, color: '#6b7280' }}>🔵 Review</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#88ccff' }}>{counts.review || 0}</div>
        </div>
        <div style={{ ...styles.card, flex: 1, minWidth: 120 }}>
          <div style={{ fontSize: 11, color: '#6b7280' }}>✅ Done</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#6b7280' }}>{counts.done || 0}</div>
        </div>
      </div>

      {/* osState Boot Progress */}
      {osState && Object.keys(osState).length > 0 && (
        <div style={{ ...styles.card, marginBottom: 16 }}>
          <div style={styles.sectionTitle}>🖥️ osState Boot Progress (threshold: 70)</div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 8 }}>
            {Object.entries(bootProgress).map(([sub, pct]: [string, any]) => (
              <div key={sub} style={{ flex: 1, minWidth: 140 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
                  <span style={{ textTransform: 'capitalize' }}>{sub}</span>
                  <span style={{ color: pct >= 100 ? '#22c55e' : '#88ccff' }}>{osState[sub]}/70</span>
                </div>
                <div style={styles.barOuter}>
                  <div style={{ ...styles.barInner, width: `${Math.min(100, pct)}%`, background: pct >= 100 ? '#22c55e' : '#88ccff' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quest action status */}
      {questAction && (
        <div style={{ fontSize: 12, color: '#88ccff', marginBottom: 8 }}>
          ⏳ {questAction}
        </div>
      )}

      {/* Quest table */}
      <div style={styles.table}>
        <div style={styles.tableHeader}>
          <span style={{ flex: 2 }}>Quest</span>
          <span style={{ flex: 1 }}>Subsystem</span>
          <span style={{ flex: 1, textAlign: 'center' }}>Status</span>
          <span style={{ flex: 1 }}>Owner</span>
          <span style={{ flex: 2 }}>Actions</span>
        </div>
        {questData.quests.map((q) => (
          <div
            key={q.id}
            style={{
              ...styles.tableRow,
              background: selectedQuest?.id === q.id ? '#2a3a4a' : 'transparent',
              cursor: 'pointer',
            }}
            onClick={() => setSelectedQuest(q)}
          >
            <span style={{ flex: 2, fontWeight: 600 }}>{q.title}</span>
            <span style={{ flex: 1, fontSize: 11, textTransform: 'capitalize' }}>{q.subsystem}</span>
            <span style={{ flex: 1, textAlign: 'center' }}>
              <span style={{
                display: 'inline-block', padding: '2px 6px', borderRadius: 4,
                fontSize: 10, fontWeight: 600, color: '#fff',
                background: statusColor(q.status),
              }}>
                {q.status.toUpperCase()}
              </span>
            </span>
            <span style={{ flex: 1, fontSize: 12 }}>{q.owner || '—'}</span>
            <span style={{ flex: 2, display: 'flex', gap: 4, alignItems: 'center' }}>
              {q.status === 'open' && agents.length > 0 && (
                <>
                  <select
                    style={{ ...styles.smallBtn, padding: '3px 4px', fontSize: 11, width: 80 }}
                    value={assignAgent}
                    onChange={(e) => setAssignAgent(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <option value="">Agent...</option>
                    {agents.map((a) => <option key={a} value={a}>{a}</option>)}
                  </select>
                  <button
                    style={{ ...styles.smallBtn, background: '#22c55e33', borderColor: '#22c55e' }}
                    disabled={!assignAgent}
                    onClick={(e) => { e.stopPropagation(); if (assignAgent) { onAssign(q.id, assignAgent); setAssignAgent(''); } }}
                  >
                    Assign
                  </button>
                </>
              )}
              {q.status === 'claimed' && (
                <button
                  style={{ ...styles.smallBtn, background: '#eab30833', borderColor: '#eab308' }}
                  onClick={(e) => { e.stopPropagation(); onSubmit(q.id, q.owner || ''); }}
                >
                  Submit
                </button>
              )}
              {q.status === 'review' && (
                <button
                  style={{ ...styles.smallBtn, background: '#88ccff33', borderColor: '#88ccff' }}
                  onClick={(e) => { e.stopPropagation(); onVerify(q.id); }}
                >
                  Verify (N-run)
                </button>
              )}
              <span style={{ fontSize: 10, color: '#6b7280', marginLeft: 4 }}>
                {q.verification_runs ? `×${q.verification_runs}` : ''}
              </span>
            </span>
          </div>
        ))}
      </div>

      {/* Quest detail panel */}
      {selectedQuest && (
        <div style={{ marginTop: 16, background: '#1f2937', borderRadius: 8, padding: 12, border: '1px solid #374151' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#fbbf24', margin: 0 }}>
              {selectedQuest.title}
            </h3>
            <button onClick={() => setSelectedQuest(null)} style={{ ...styles.smallBtn, fontSize: 14 }}>✕</button>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
            <div style={{ fontSize: 12, color: '#9ca3af' }}>
              <b>ID:</b> {selectedQuest.id}
            </div>
            <div style={{ fontSize: 12, color: '#9ca3af' }}>
              <b>Subsystem:</b> {selectedQuest.subsystem}
            </div>
            <div style={{ fontSize: 12, color: '#9ca3af' }}>
              <b>Reward:</b> {selectedQuest.reward} pts
            </div>
            <div style={{ fontSize: 12, color: '#9ca3af' }}>
              <b>Status:</b>{' '}
              <span style={{ color: statusColor(selectedQuest.status), fontWeight: 600 }}>
                {selectedQuest.status.toUpperCase()}
              </span>
            </div>
          </div>
          <div style={{ fontSize: 13, color: '#d4d4d4', marginBottom: 8 }}>
            <b>Goal:</b> {selectedQuest.goal}
          </div>
          {selectedQuest.success_criteria && selectedQuest.success_criteria.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#9ca3af', marginBottom: 4 }}>Success Criteria:</div>
              <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: '#6b7280' }}>
                {selectedQuest.success_criteria.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}
          {selectedQuest.depends_on && selectedQuest.depends_on.length > 0 && (
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              <b>Depends on:</b> {selectedQuest.depends_on.join(', ')}
            </div>
          )}
          {selectedQuest.denial_reason && (
            <div style={{ marginTop: 8, padding: 8, borderRadius: 6, background: '#ef444422', border: '1px solid #ef444455' }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#ef4444' }}>⛔ Denial Reason</div>
              <div style={{ fontSize: 12, color: '#d4d4d4', marginTop: 2 }}>{selectedQuest.denial_reason}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════

const renderJson = (raw: string | null, keys?: string[]): string => {
  if (!raw) return '—';
  try {
    const obj = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (keys) {
      return keys.map((k) => `${k}:${obj[k]}`).join(' ');
    }
    return Object.entries(obj).slice(0, 3).map(([k, v]) => `${k}:${v}`).join(' ');
  } catch {
    return raw.slice(0, 60);
  }
};

// ═══════════════════════════════════════════
// STYLES
// ═══════════════════════════════════════════

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#1a1a1a', color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif", overflowY: 'auto', padding: '0 16px 24px' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontSize: '20px', fontWeight: 700, color: '#fbbf24', margin: '12px 0' },
  liveBadge: { fontSize: 10, padding: '2px 10px', borderRadius: 4, background: '#22c55e', color: '#fff', fontWeight: 600 },
  tabRow: { display: 'flex', gap: 4, marginBottom: 12, flexWrap: 'wrap' as const },
  tab: { padding: '8px 16px', borderRadius: 6, border: 'none', background: '#2a2a2a', color: '#9ca3af', fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'all 0.1s' },
  tabActive: { background: '#1a365d', color: '#88ccff', borderBottom: '2px solid #88ccff' },
  loading: { color: '#6b7280', fontSize: 13, textAlign: 'center', padding: 20 },
  tabContent: { flex: 1 },
  sectionTitle: { fontSize: 14, fontWeight: 600, color: '#d4d4d4', margin: '0 0 10px' },
  subtitle: { fontSize: 13, fontWeight: 600, color: '#9ca3af', marginBottom: 6, borderBottom: '1px solid #2a2a2a', paddingBottom: 4 },
  cardRow: { display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' as const },
  card: { background: '#2a2a2a', borderRadius: '8px', padding: '14px', border: '1px solid #3a3a3a' },
  twoCol: { display: 'flex', gap: '16px', flexWrap: 'wrap' as const },
  table: { background: '#2a2a2a', borderRadius: 8, border: '1px solid #3a3a3a', overflow: 'hidden' },
  tableHeader: { display: 'flex', padding: '8px 12px', background: '#1f2937', fontSize: 11, color: '#6b7280', fontWeight: 600, borderBottom: '1px solid #374151' },
  tableRow: { display: 'flex', padding: '8px 12px', alignItems: 'center', borderBottom: '1px solid #2a2a2a', fontSize: 13, transition: 'background 0.1s' },
  statGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 },
  stat: { textAlign: 'center', padding: 8, borderRadius: 6, background: '#1f2937' },
  keyVal: { display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 },
  inlineItem: { display: 'flex', justifyContent: 'space-between', gap: 8, padding: '2px 0', fontSize: 12, borderBottom: '1px solid #1f2937' },
  inlineRow: { display: 'flex', flexWrap: 'wrap' as const, gap: 6 },
  tag: { padding: '2px 8px', borderRadius: 4, background: '#1f2937', fontSize: 12, border: '1px solid #374151' },
  barOuter: { height: 10, background: '#3a3a3a', borderRadius: 5, overflow: 'hidden' },
  barInner: { height: '100%', borderRadius: 5, transition: 'width 0.3s' },
  smallBtn: { padding: '2px 6px', background: '#374151', border: '1px solid #4a4a4a', borderRadius: 4, color: '#d4d4d4', cursor: 'pointer', fontSize: 12 },
};

export default GodConsoleV2;
