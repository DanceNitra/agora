import React, { useEffect, useState } from 'react';

interface AgentData {
  agent_id: string;
  role: string;
  trust_score: number;
  energy_balance: number;
}

interface DashboardData {
  totalAgents: number;
  agents: AgentData[];
  totalTasks: number;
  tick: number;
}

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const [healthRes, agentsRes, tasksRes] = await Promise.all([
          fetch('/api/v1/health'),
          fetch('/api/v1/agents/'),
          fetch('/api/v1/tasks/'),
        ]);

        const health = healthRes.ok ? await healthRes.json() : { agents: 0, tick: 0 };
        const agentsJson = agentsRes.ok ? await agentsRes.json() : { agents: [], total: 0 };
        const tasksJson = tasksRes.ok ? await tasksRes.json() : { tasks: [], total: 0 };

        setData({
          totalAgents: agentsJson.total || health.agents || 0,
          agents: agentsJson.agents || [],
          totalTasks: tasksJson.total || 0,
          tick: health.tick || 0,
        });
      } catch {
        // Keep previous data on error
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const trustColor = (score: number) => {
    if (score >= 0.7) return '#22c55e';
    if (score >= 0.4) return '#eab308';
    return '#ef4444';
  };

  if (!data) {
    return (
      <div style={styles.container}>
        <h2 style={styles.title}>📊 Dashboard</h2>
        <div style={{ textAlign: 'center', color: '#525252', marginTop: 40 }}>Loading…</div>
      </div>
    );
  }

  const criticalAgents = data.agents.filter((a) => a.trust_score < 0.3).length;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>📊 Dashboard</h2>

      <div style={styles.cardRow}>
        <div style={styles.card}>
          <div style={styles.cardValue}>{data.totalAgents}</div>
          <div style={styles.cardLabel}>Active Agents</div>
        </div>
        <div style={styles.card}>
          <div style={{ ...styles.cardValue, color: '#22c55e' }}>{data.totalTasks}</div>
          <div style={styles.cardLabel}>Open Tasks</div>
        </div>
        <div style={styles.card}>
          <div style={{ ...styles.cardValue, color: criticalAgents > 0 ? '#ef4444' : '#22c55e' }}>
            {criticalAgents}
          </div>
          <div style={styles.cardLabel}>Low Trust Agents</div>
        </div>
        <div style={styles.card}>
          <div style={styles.cardValue}>#{data.tick}</div>
          <div style={styles.cardLabel}>Tick</div>
        </div>
      </div>

      <div style={styles.columns}>
        <div style={styles.col}>
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>🤝 Trust Distribution</h3>
            {data.agents.length === 0 && <div style={styles.emptyText}>No agents yet</div>}
            {data.agents.map((a) => (
              <div key={a.agent_id} style={styles.trustRow}>
                <span style={{ flex: 1 }}>{a.agent_id.slice(0, 8)}</span>
                <div style={styles.trustBarOuter}>
                  <div
                    style={{
                      ...styles.trustBarInner,
                      width: `${a.trust_score * 100}%`,
                      background: trustColor(a.trust_score),
                    }}
                  />
                </div>
                <span style={styles.trustScore}>{(a.trust_score * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
        <div style={styles.col}>
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>👥 Agents by Role</h3>
            {data.agents.length === 0 && <div style={styles.emptyText}>No agents yet</div>}
            {Object.entries(
              data.agents.reduce<Record<string, number>>((acc, a) => {
                acc[a.role] = (acc[a.role] || 0) + 1;
                return acc;
              }, {}),
            ).map(([role, count]) => (
              <div key={role} style={styles.countRow}>
                <span style={{ flex: 1, color: '#a3a3a3' }}>{role}</span>
                <div style={styles.barOuter}>
                  <div
                    style={{
                      ...styles.barInner,
                      width: `${(count / data.totalAgents) * 100}%`,
                    }}
                  />
                </div>
                <span style={styles.countNumber}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#1a1a1a', color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif", overflowY: 'auto', padding: '0 16px 24px' },
  title: { fontSize: '18px', fontWeight: 700, color: '#fbbf24', margin: '12px 0' },
  cardRow: { display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' },
  card: { flex: '1 1 120px', background: '#2a2a2a', borderRadius: '8px', padding: '14px', textAlign: 'center', border: '1px solid #3a3a3a' },
  cardValue: { fontSize: '28px', fontWeight: 700, color: '#fbbf24' },
  cardLabel: { fontSize: '12px', color: '#6b7280', marginTop: '4px' },
  columns: { display: 'flex', gap: '16px', flexWrap: 'wrap' as const },
  col: { flex: '1 1 300px', display: 'flex', flexDirection: 'column', gap: '12px' },
  section: { background: '#2a2a2a', borderRadius: '8px', padding: '12px', border: '1px solid #3a3a3a' },
  sectionTitle: { fontSize: '14px', fontWeight: 600, color: '#d4d4d4', margin: '0 0 10px' },
  emptyText: { color: '#525252', fontSize: '13px', fontStyle: 'italic' },
  trustRow: { display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', fontSize: '13px' },
  trustBarOuter: { flex: 1, height: 10, background: '#3a3a3a', borderRadius: 5, overflow: 'hidden' },
  trustBarInner: { height: '100%', borderRadius: 5, transition: 'width 0.3s' },
  trustScore: { width: 40, textAlign: 'right', fontWeight: 600, color: '#d4d4d4' },
  countRow: { display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', fontSize: '13px' },
  barOuter: { flex: 1, height: 8, background: '#3a3a3a', borderRadius: 4, overflow: 'hidden' },
  barInner: { height: '100%', background: '#fbbf24', borderRadius: 4, transition: 'width 0.3s' },
  countNumber: { width: 24, textAlign: 'right', color: '#d4d4d4', fontWeight: 600 },
};

export default Dashboard;
