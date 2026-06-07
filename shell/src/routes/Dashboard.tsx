import React, { useEffect, useState } from 'react';
import { useAgent, AgentDetail } from '../context/AgentContext';

interface DashboardMetrics {
  totalTasks: number;
  tick: number;
}

interface Resource {
  id: number;
  name: string;
  total_supply: number;
  base_price: number;
  current_price: number;
}

interface Trade {
  buyer_name: string;
  seller_name: string;
  resource_id: number;
  quantity: number;
  total_energy: number;
}

interface Offer {
  agent_name: string;
  offer_type: string;
  resource_id: number;
  quantity: number;
  price_per_unit: number;
}

// ── God Console 2.0 types ──

interface NPC {
  npc_id: string; npc_name: string; role: string;
  health: number; status: string;
  stamina: number; hunger: number; fatigue: number;
  state_of_mind: string; current_goal: string;
}

interface Violation {
  id?: number; event_type?: string; type?: string;
  detail?: string; severity?: string; source_id?: string;
  created_at?: string;
}

interface StateDist {
  state_of_mind: string; count: number;
  avg_health: number; avg_stamina: number;
}

interface ControllerStats {
  tick: number; rooms: string[]; priorities: Record<string, number>;
  multiprocessing: boolean;
}

interface HealthInfo {
  tick: number; multiprocessing: boolean; rooms: string[];
  state_of_minds: Record<string, number>;
  active_npcs: number; db_connected: boolean; redis_connected: boolean;
}

const trustColor = (score: number) => {
  if (score >= 0.7) return '#22c55e';
  if (score >= 0.4) return '#eab308';
  return '#ef4444';
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

const Dashboard: React.FC = () => {
  const { liveAgents, openAgentByName, wsConnected } = useAgent();
  const [metrics, setMetrics] = useState<DashboardMetrics>({ totalTasks: 0, tick: 0 });
  const [resources, setResources] = useState<Resource[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);

  // ── God Console 2.0 state ──
  const [npcs, setNpcs] = useState<NPC[]>([]);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [stateDist, setStateDist] = useState<StateDist[]>([]);
  const [controllerStats, setControllerStats] = useState<ControllerStats | null>(null);
  const [healthInfo, setHealthInfo] = useState<HealthInfo | null>(null);

  // Fetch supplemental metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const [healthRes, tasksRes, ecoRes, tradesRes, offersRes] = await Promise.all([
          fetch('/api/v1/health'),
          fetch('/api/v1/tasks/'),
          fetch('/api/v1/economy/resources'),
          fetch('/api/v1/economy/history?limit=5'),
          fetch('/api/v1/economy/offers'),
        ]);
        const health = healthRes.ok ? await healthRes.json() : {};
        const tasksJson = tasksRes.ok ? await tasksRes.json() : {};
        const ecoData = ecoRes.ok ? await ecoRes.json() : {};
        const tradesData = tradesRes.ok ? await tradesRes.json() : {};
        const offersData = offersRes.ok ? await offersRes.json() : {};
        setMetrics({
          totalTasks: tasksJson.total || 0,
          tick: health.tick || 0,
        });
        setResources(ecoData.resources || []);
        setTrades((tradesData.history || []).slice(0, 5));
        setOffers(offersData.offers || []);
      } catch { /* silent */ }
    };

    // ── Fetch God Console 2.0 data ──
    const fetchGC2 = async () => {
      try {
        const base = window.location.origin;
        const [npcsRes, violationsRes, osRes, ctrlRes, healthRes] = await Promise.all([
          fetch(`${base}/api/v2/god/npcs`),
          fetch(`${base}/api/v2/god/violations`),
          fetch(`${base}/api/v2/god/agent-os/summary`),
          fetch(`${base}/api/v2/god/controller`),
          fetch(`${base}/api/v2/god/health`),
        ]);
        if (npcsRes.ok) {
          const d = await npcsRes.json();
          setNpcs(d.npcs || []);
        }
        if (violationsRes.ok) {
          const d = await violationsRes.json();
          setViolations(d.violations || []);
        }
        if (osRes.ok) {
          const d = await osRes.json();
          setStateDist(d.state_distribution || []);
        }
        if (ctrlRes.ok) setControllerStats(await ctrlRes.json());
        if (healthRes.ok) setHealthInfo(await healthRes.json());
      } catch { /* silent */ }
    };

    fetchMetrics();
    fetchGC2();
    const interval = setInterval(() => { fetchMetrics(); fetchGC2(); }, 5000);
    return () => clearInterval(interval);
  }, []);

  const agents = liveAgents;
  const criticalAgents = agents.filter((a) => a.trustScore < 0.3).length;
  const activeCount = agents.filter((a) => a.status === 'active').length;
  const violationsCount = violations.length;

  const roles = agents.reduce<Record<string, number>>((acc, a) => {
    acc[a.role] = (acc[a.role] || 0) + 1;
    return acc;
  }, {});

  const totalEnergy = agents.reduce((sum, a) => sum + (a.energyBalance || 0), 0);
  const avgTrust = agents.length > 0
    ? agents.reduce((sum, a) => sum + (a.trustScore || 0), 0) / agents.length
    : 0;

  return (
    <div style={dashboardStyles.container}>
      <h2 style={dashboardStyles.title}>
        📊 Dashboard
        <span style={{ ...dashboardStyles.badge, background: wsConnected ? '#22c55e' : '#ef4444' }}>
          {wsConnected ? '🔴 LIVE' : '⏸️ POLLING'}
        </span>
      </h2>

      {/* ── TOP CARDS ── */}
      <div style={dashboardStyles.cardRow}>
        <Card value={activeCount} label="Active Agents" color="#fbbf24" />
        <Card value={metrics.totalTasks} label="Open Tasks" color="#22c55e" />
        <Card value={criticalAgents} label="Low Trust" color={criticalAgents > 0 ? '#ef4444' : '#22c55e'} />
        <Card value={`#${metrics.tick}`} label="Tick" color="#88ccff" />
        <Card value={violationsCount} label="Violations" color={violationsCount > 0 ? '#ef4444' : '#22c55e'} />
        <Card value={healthInfo?.multiprocessing ? 'ON' : 'OFF'} label="MP Mode" color={healthInfo?.multiprocessing ? '#22c55e' : '#6b7280'} />
        <Card value={healthInfo?.redis_connected ? 'OK' : 'DOWN'} label="Redis" color={healthInfo?.redis_connected ? '#22c55e' : '#ef4444'} />
      </div>

      {/* ── TOP ROW: Agent columns + System Health ── */}
      <div style={dashboardStyles.columns}>

        {/* ── AGENT TABLE ── */}
        <div style={dashboardStyles.col}>
          <div style={dashboardStyles.section}>
            <h3 style={dashboardStyles.sectionTitle}>👤 Agents ({agents.length})</h3>
            {agents.length === 0 && <div style={dashboardStyles.emptyText}>No agents connected</div>}
            <div style={dashboardStyles.agentTable}>
              {agents.map((a) => (
                <AgentRow key={a.id} agent={a} onClick={() => openAgentByName(a.name)} />
              ))}
            </div>
          </div>
        </div>

        {/* ── TRUST + ENERGY ── */}
        <div style={dashboardStyles.col}>
          <div style={dashboardStyles.section}>
            <h3 style={dashboardStyles.sectionTitle}>🤝 Trust Distribution</h3>
            {agents.map((a) => (
              <div
                key={a.id}
                style={dashboardStyles.trustRow}
                onClick={() => openAgentByName(a.name)}
              >
                <span style={{ flex: 1, cursor: 'pointer' }}>{a.name}</span>
                <div style={dashboardStyles.trustBarOuter}>
                  <div
                    style={{
                      ...dashboardStyles.trustBarInner,
                      width: `${a.trustScore * 100}%`,
                      background: trustColor(a.trustScore),
                    }}
                  />
                </div>
                <span style={dashboardStyles.trustScore}>{(a.trustScore * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>

          <div style={{ ...dashboardStyles.section, marginTop: 12 }}>
            <h3 style={dashboardStyles.sectionTitle}>⚡ Energy</h3>
            {agents.sort((a, b) => b.energyBalance - a.energyBalance).map((a) => (
              <div
                key={a.id}
                style={dashboardStyles.trustRow}
                onClick={() => openAgentByName(a.name)}
              >
                <span style={{ flex: 1, cursor: 'pointer' }}>{a.name}</span>
                <div style={dashboardStyles.trustBarOuter}>
                  <div
                    style={{
                      ...dashboardStyles.trustBarInner,
                      width: `${Math.min(100, a.energyBalance)}%`,
                      background: a.energyBalance > 20 ? '#44cc44' : '#cc4444',
                    }}
                  />
                </div>
                <span style={dashboardStyles.trustScore}>{Math.round(a.energyBalance)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── SYSTEM HEALTH COLUMN ── */}
        <div style={dashboardStyles.col}>
          <div style={dashboardStyles.section}>
            <h3 style={dashboardStyles.sectionTitle}>💚 System Health</h3>

            {/* Agent OS State Distribution */}
            <div style={healthStyles.stateSection}>
              <div style={healthStyles.subtitle}>🌀 State of Mind</div>
              {stateDist.length === 0 ? (
                <div style={healthStyles.empty}>No data</div>
              ) : stateDist.map((s) => (
                <div key={s.state_of_mind} style={healthStyles.stateRow}>
                  <span style={{ color: stateColor(s.state_of_mind), textTransform: 'capitalize', fontSize: 12 }}>
                    {s.state_of_mind}
                  </span>
                  <div style={healthStyles.barOuter}>
                    <div style={{
                      ...healthStyles.barInner,
                      width: `${(s.count / Math.max(1, ...stateDist.map(x => x.count))) * 100}%`,
                      background: stateColor(s.state_of_mind),
                    }} />
                  </div>
                  <span style={healthStyles.barLabel}>{s.count}</span>
                </div>
              ))}
            </div>

            {/* Summary stats */}
            <div style={healthStyles.statsRow}>
              <span>NPCs: <b>{npcs.length}</b></span>
              <span>Avg Trust: <b style={{ color: trustColor(avgTrust) }}>{(avgTrust * 100).toFixed(0)}%</b></span>
              <span>Energy: <b style={{ color: '#fbbf24' }}>{totalEnergy.toFixed(0)}</b></span>
            </div>

            {/* Controller info */}
            {controllerStats && (
              <div style={healthStyles.statsRow}>
                <span>Rooms: <b>{controllerStats.rooms?.length || 0}</b></span>
                <span>Mode: <b style={{ color: controllerStats.multiprocessing ? '#22c55e' : '#eab308' }}>
                  {controllerStats.multiprocessing ? 'MP' : 'SP'}
                </b></span>
                <span>Redis: <b style={{ color: healthInfo?.redis_connected ? '#22c55e' : '#ef4444' }}>
                  {healthInfo?.redis_connected ? 'OK' : 'DOWN'}
                </b></span>
              </div>
            )}

            {/* Room priorities */}
            {controllerStats?.priorities && Object.keys(controllerStats.priorities).length > 0 && (
              <div style={healthStyles.stateSection}>
                <div style={healthStyles.subtitle}>🏠 Room Priorities</div>
                {Object.entries(controllerStats.priorities)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 3)
                  .map(([room, pri]) => (
                    <div key={room} style={healthStyles.stateRow}>
                      <span style={{ fontSize: 12, textTransform: 'capitalize' }}>{room.replace(/_/g, ' ')}</span>
                      <div style={healthStyles.barOuter}>
                        <div style={{
                          ...healthStyles.barInner,
                          width: `${Math.min(100, pri)}%`,
                          background: pri > 20 ? '#ef4444' : pri > 10 ? '#f97316' : '#22c55e',
                        }} />
                      </div>
                      <span style={healthStyles.barLabel}>{pri.toFixed(0)}</span>
                    </div>
                  ))}
              </div>
            )}

            {/* Recent Violations */}
            {violationsCount > 0 && (
              <div style={healthStyles.stateSection}>
                <div style={{ ...healthStyles.subtitle, color: '#ef4444' }}>⚠️ Recent Violations</div>
                {violations.slice(0, 3).map((v, i) => (
                  <div key={v.id || i} style={{ fontSize: 11, padding: '2px 0', color: '#9ca3af' }}>
                    {v.type || v.event_type || 'violation'} — {v.detail?.slice(0, 60) || v.payload?.slice(0, 60) || ''}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── ECONOMY SECTION ── */}
      <div style={{ ...dashboardStyles.section, marginTop: 16 }}>
        <h3 style={dashboardStyles.sectionTitle}>💰 Economy</h3>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>

          {/* Resource prices */}
          <div style={{ flex: '1 1 200px' }}>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6 }}>Resource Prices</div>
            {resources.map((r) => (
              <div key={r.id} style={dashboardStyles.trustRow}>
                <span style={{ flex: 1, fontSize: 13, textTransform: 'capitalize' }}>{r.name.replace(/_/g, ' ')}</span>
                <span style={{ fontSize: 12, color: '#fbbf24' }}>${r.current_price?.toFixed(2)}</span>
                <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 8 }}>{r.total_supply?.toFixed(1)}</span>
              </div>
            ))}
          </div>

          {/* Active offers */}
          <div style={{ flex: '1 1 250px' }}>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6 }}>Active Offers ({offers.length})</div>
            {offers.length === 0 && <div style={{ fontSize: 12, color: '#525252', fontStyle: 'italic' }}>No active offers</div>}
            {offers.map((o, i) => (
              <div key={i} style={dashboardStyles.trustRow}>
                <span style={{ fontSize: 11, color: o.offer_type === 'sell' ? '#ef4444' : '#22c55e', fontWeight: 600, width: 32 }}>
                  {o.offer_type === 'sell' ? 'SELL' : 'BUY'}
                </span>
                <span style={{ flex: 1, fontSize: 12 }}>{o.agent_name}</span>
                <span style={{ fontSize: 11, color: '#6b7280' }}>#{o.resource_id}</span>
                <span style={{ fontSize: 12, color: '#d4d4d4' }}>{o.quantity?.toFixed(1)}</span>
                <span style={{ fontSize: 12, color: '#fbbf24' }}>@{o.price_per_unit?.toFixed(2)}</span>
              </div>
            ))}
          </div>

          {/* Recent trades */}
          <div style={{ flex: '1 1 250px' }}>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6 }}>Recent Trades ({trades.length})</div>
            {trades.length === 0 && <div style={{ fontSize: 12, color: '#525252', fontStyle: 'italic' }}>No trades yet</div>}
            {trades.map((t, i) => (
              <div key={i} style={dashboardStyles.trustRow}>
                <span style={{ fontSize: 11, color: '#22c55e' }}>{t.seller_name}</span>
                <span style={{ fontSize: 11, color: '#6b7280' }}>→</span>
                <span style={{ fontSize: 11, color: '#88ccff' }}>{t.buyer_name}</span>
                <span style={{ flex: 1 }} />
                <span style={{ fontSize: 12, color: '#d4d4d4' }}>#{t.resource_id}</span>
                <span style={{ fontSize: 12, color: '#fbbf24' }}>{t.total_energy?.toFixed(1)}⚡</span>
              </div>
            ))}
          </div>

        </div>
      </div>

    </div>
  );
};

// ── Sub-components ──

const Card: React.FC<{ value: string | number; label: string; color: string }> = ({ value, label, color }) => (
  <div style={dashboardStyles.card}>
    <div style={{ ...dashboardStyles.cardValue, color }}>{value}</div>
    <div style={dashboardStyles.cardLabel}>{label}</div>
  </div>
);

const AgentRow: React.FC<{ agent: AgentDetail; onClick: () => void }> = ({ agent, onClick }) => (
  <div style={dashboardStyles.agentRow} onClick={onClick}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%',
        background: agent.status === 'active' ? '#22c55e' : '#6b7280',
        flexShrink: 0,
      }} />
      <div>
        <div style={{ fontWeight: 600, fontSize: 13 }}>{agent.name}</div>
        <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'capitalize' }}>{agent.role}</div>
      </div>
    </div>
    <div style={dashboardStyles.agentStats}>
      <span style={{ color: trustColor(agent.trustScore), fontSize: 12 }}>
        {(agent.trustScore * 100).toFixed(0)}%
      </span>
      <span style={{ color: '#6b7280', fontSize: 11 }}>
        ⚡{Math.round(agent.energyBalance)}
      </span>
    </div>
  </div>
);

// ── Styles ──

const dashboardStyles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#1a1a1a', color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif", overflowY: 'auto', padding: '0 16px 24px' },
  title: { fontSize: '18px', fontWeight: 700, color: '#fbbf24', margin: '12px 0', display: 'flex', alignItems: 'center', gap: 10 },
  badge: { fontSize: 10, padding: '2px 8px', borderRadius: 4, color: '#fff', fontWeight: 600 },
  cardRow: { display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' },
  card: { flex: '1 1 100px', background: '#2a2a2a', borderRadius: '8px', padding: '14px', textAlign: 'center', border: '1px solid #3a3a3a', cursor: 'default' },
  cardValue: { fontSize: '28px', fontWeight: 700 },
  cardLabel: { fontSize: '12px', color: '#6b7280', marginTop: '4px' },
  columns: { display: 'flex', gap: '16px', flexWrap: 'wrap' },
  col: { flex: '1 1 300px', display: 'flex', flexDirection: 'column' },
  section: { background: '#2a2a2a', borderRadius: '8px', padding: '12px', border: '1px solid #3a3a3a' },
  sectionTitle: { fontSize: '14px', fontWeight: 600, color: '#d4d4d4', margin: '0 0 10px' },
  emptyText: { color: '#525252', fontSize: '13px', fontStyle: 'italic', textAlign: 'center', padding: 20 },
  agentTable: { display: 'flex', flexDirection: 'column', gap: 4 },
  agentRow: { display: 'flex', alignItems: 'center', padding: '8px 10px', borderRadius: 6, cursor: 'pointer', transition: 'background 0.1s', border: '1px solid transparent' },
  agentStats: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 },
  trustRow: { display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', fontSize: '13px', cursor: 'pointer' },
  trustBarOuter: { flex: 1, height: 10, background: '#3a3a3a', borderRadius: 5, overflow: 'hidden' },
  trustBarInner: { height: '100%', borderRadius: 5, transition: 'width 0.3s' },
  trustScore: { width: 40, textAlign: 'right', fontWeight: 600, color: '#d4d4d4' },
};

const healthStyles: Record<string, React.CSSProperties> = {
  stateSection: { marginTop: 10 },
  subtitle: { fontSize: 12, fontWeight: 600, color: '#9ca3af', borderBottom: '1px solid #3a3a3a', paddingBottom: 4, marginBottom: 6 },
  stateRow: { display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0' },
  barOuter: { flex: 1, height: 8, background: '#3a3a3a', borderRadius: 4, overflow: 'hidden' },
  barInner: { height: '100%', borderRadius: 4, transition: 'width 0.3s' },
  barLabel: { width: 24, textAlign: 'right', fontSize: 11, color: '#9ca3af' },
  statsRow: { display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 12, borderBottom: '1px solid #1f2937' },
  empty: { fontSize: 12, color: '#525252', fontStyle: 'italic' },
};

export default Dashboard;
