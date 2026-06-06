import React, { useEffect, useState } from 'react';
import { useAgent, AgentDetail } from '../context/AgentContext';

interface DashboardMetrics {
  totalTasks: number;
  tick: number;
}

const trustColor = (score: number) => {
  if (score >= 0.7) return '#22c55e';
  if (score >= 0.4) return '#eab308';
  return '#ef4444';
};

const Dashboard: React.FC = () => {
  const { liveAgents, openAgentByName, wsConnected } = useAgent();
  const [metrics, setMetrics] = useState<DashboardMetrics>({ totalTasks: 0, tick: 0 });

  // Fetch supplemental metrics (not agent-specific)
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const [healthRes, tasksRes] = await Promise.all([
          fetch('/api/v1/health'),
          fetch('/api/v1/tasks/'),
        ]);
        const health = healthRes.ok ? await healthRes.json() : {};
        const tasksJson = tasksRes.ok ? await tasksRes.json() : {};
        setMetrics({
          totalTasks: tasksJson.total || 0,
          tick: health.tick || 0,
        });
      } catch { /* silent */ }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const agents = liveAgents;
  const criticalAgents = agents.filter((a) => a.trustScore < 0.3).length;
  const activeCount = agents.filter((a) => a.status === 'active').length;

  const roles = agents.reduce<Record<string, number>>((acc, a) => {
    acc[a.role] = (acc[a.role] || 0) + 1;
    return acc;
  }, {});

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>
        📊 Dashboard
        <span style={{ ...styles.badge, background: wsConnected ? '#22c55e' : '#ef4444' }}>
          {wsConnected ? '🔴 LIVE' : '⏸️ POLLING'}
        </span>
      </h2>

      <div style={styles.cardRow}>
        <Card value={activeCount} label="Active Agents" color="#fbbf24" />
        <Card value={metrics.totalTasks} label="Open Tasks" color="#22c55e" />
        <Card value={criticalAgents} label="Low Trust" color={criticalAgents > 0 ? '#ef4444' : '#22c55e'} />
        <Card value={`#${metrics.tick}`} label="Tick" color="#88ccff" />
      </div>

      <div style={styles.columns}>
        {/* Agent table */}
        <div style={styles.col}>
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>👤 Agents ({agents.length})</h3>
            {agents.length === 0 && <div style={styles.emptyText}>No agents connected</div>}
            <div style={styles.agentTable}>
              {agents.map((a) => (
                <AgentRow key={a.id} agent={a} onClick={() => openAgentByName(a.name)} />
              ))}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div style={styles.col}>
          {/* Trust distribution */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>🤝 Trust Distribution</h3>
            {agents.map((a) => (
              <div
                key={a.id}
                style={styles.trustRow}
                onClick={() => openAgentByName(a.name)}
              >
                <span style={{ flex: 1, cursor: 'pointer' }}>{a.name}</span>
                <div style={styles.trustBarOuter}>
                  <div
                    style={{
                      ...styles.trustBarInner,
                      width: `${a.trustScore * 100}%`,
                      background: trustColor(a.trustScore),
                    }}
                  />
                </div>
                <span style={styles.trustScore}>{(a.trustScore * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>

          {/* Energy distribution */}
          <div style={{ ...styles.section, marginTop: 12 }}>
            <h3 style={styles.sectionTitle}>⚡ Energy</h3>
            {agents.sort((a, b) => b.energyBalance - a.energyBalance).map((a) => (
              <div
                key={a.id}
                style={styles.trustRow}
                onClick={() => openAgentByName(a.name)}
              >
                <span style={{ flex: 1, cursor: 'pointer' }}>{a.name}</span>
                <div style={styles.trustBarOuter}>
                  <div
                    style={{
                      ...styles.trustBarInner,
                      width: `${Math.min(100, a.energyBalance)}%`,
                      background: a.energyBalance > 20 ? '#44cc44' : '#cc4444',
                    }}
                  />
                </div>
                <span style={styles.trustScore}>{Math.round(a.energyBalance)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const Card: React.FC<{ value: string | number; label: string; color: string }> = ({ value, label, color }) => (
  <div style={styles.card}>
    <div style={{ ...styles.cardValue, color }}>{value}</div>
    <div style={styles.cardLabel}>{label}</div>
  </div>
);

const AgentRow: React.FC<{ agent: AgentDetail; onClick: () => void }> = ({ agent, onClick }) => (
  <div style={styles.agentRow} onClick={onClick}>
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
    <div style={styles.agentStats}>
      <span style={{ color: trustColor(agent.trustScore), fontSize: 12 }}>
        {(agent.trustScore * 100).toFixed(0)}%
      </span>
      <span style={{ color: '#6b7280', fontSize: 11 }}>
        ⚡{Math.round(agent.energyBalance)}
      </span>
    </div>
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#1a1a1a', color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif", overflowY: 'auto', padding: '0 16px 24px' },
  title: { fontSize: '18px', fontWeight: 700, color: '#fbbf24', margin: '12px 0', display: 'flex', alignItems: 'center', gap: 10 },
  badge: { fontSize: 10, padding: '2px 8px', borderRadius: 4, color: '#fff', fontWeight: 600 },
  cardRow: { display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' },
  card: { flex: '1 1 120px', background: '#2a2a2a', borderRadius: '8px', padding: '14px', textAlign: 'center', border: '1px solid #3a3a3a', cursor: 'default' },
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

export default Dashboard;
