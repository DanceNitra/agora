import React, { useEffect, useState } from 'react';

interface CSDAlert {
  id: string;
  agentId: string;
  agentName: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  timestamp: string;
}

interface TrustEntry {
  agentId: string;
  agentName: string;
  score: number;
}

interface AgentCountEntry {
  role: string;
  count: number;
}

const Dashboard: React.FC = () => {
  const [csdAlerts, setCsdAlerts] = useState<CSDAlert[]>([]);
  const [trustDistribution, setTrustDistribution] = useState<TrustEntry[]>([]);
  const [agentCounts, setAgentCounts] = useState<AgentCountEntry[]>([]);
  const [energyFlow, setEnergyFlow] = useState(0);
  const [totalAgents, setTotalAgents] = useState(0);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch('/api/v1/metrics');
        if (res.ok) {
          const json = await res.json();
          setCsdAlerts(json.alerts ?? []);
          setTrustDistribution(json.trustDistribution ?? []);
          setAgentCounts(json.agentCounts ?? []);
          setEnergyFlow(json.energyFlow ?? 0);
          setTotalAgents(json.totalAgents ?? 0);
          return;
        }
      } catch {
        // Fallback to defaults
      }
      // Fallback data
      setCsdAlerts([
        { id: 'a1', agentId: 'ag-3', agentName: 'Gamma', severity: 'critical', message: 'Trust score dropped below 0.3 threshold', timestamp: new Date().toISOString() },
        { id: 'a2', agentId: 'ag-7', agentName: 'Theta', severity: 'warning', message: 'Specialization entropy increasing rapidly', timestamp: new Date(Date.now() - 60000).toISOString() },
        { id: 'a3', agentId: 'ag-2', agentName: 'Beta', severity: 'info', message: 'Completed artifact generation cycle', timestamp: new Date(Date.now() - 120000).toISOString() },
      ]);
      setTrustDistribution([
        { agentId: 'ag-1', agentName: 'Alpha', score: 0.85 },
        { agentId: 'ag-2', agentName: 'Beta', score: 0.92 },
        { agentId: 'ag-3', agentName: 'Gamma', score: 0.45 },
        { agentId: 'ag-4', agentName: 'Delta', score: 0.3 },
        { agentId: 'ag-5', agentName: 'Epsilon', score: 0.72 },
      ]);
      setAgentCounts([
        { role: 'researcher', count: 3 },
        { role: 'writer', count: 2 },
        { role: 'critic', count: 1 },
        { role: 'analyst', count: 2 },
        { role: 'explorer', count: 2 },
      ]);
      setEnergyFlow(247.3);
      setTotalAgents(10);
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 15000);
    return () => clearInterval(interval);
  }, []);

  const severityColor = (sev: string) => {
    switch (sev) {
      case 'critical': return '#ef4444';
      case 'warning': return '#eab308';
      default: return '#3b82f6';
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>📊 Dashboard</h2>

      {/* Top summary cards */}
      <div style={styles.cardRow}>
        <div style={styles.card}>
          <div style={styles.cardValue}>{totalAgents}</div>
          <div style={styles.cardLabel}>Total Agents</div>
        </div>
        <div style={styles.card}>
          <div style={{ ...styles.cardValue, color: energyFlow > 300 ? '#eab308' : '#22c55e' }}>
            {energyFlow.toFixed(1)}
          </div>
          <div style={styles.cardLabel}>Energy Flow</div>
        </div>
        <div style={styles.card}>
          <div
            style={{
              ...styles.cardValue,
              color: csdAlerts.filter((a) => a.severity === 'critical').length > 0
                ? '#ef4444'
                : '#22c55e',
            }}
          >
            {csdAlerts.filter((a) => a.severity === 'critical').length}
          </div>
          <div style={styles.cardLabel}>Critical Alerts</div>
        </div>
      </div>

      {/* Two-column layout */}
      <div style={styles.columns}>
        {/* Left column */}
        <div style={styles.col}>

          {/* CSD Alerts */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>⚠️ CSD Alerts</h3>
            {csdAlerts.length === 0 ? (
              <div style={styles.emptyText}>No alerts</div>
            ) : (
              csdAlerts.map((alert) => (
                <div key={alert.id} style={styles.alertRow}>
                  <span
                    style={{
                      ...styles.severityDot,
                      background: severityColor(alert.severity),
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={styles.alertAgent}>{alert.agentName}</div>
                    <div style={styles.alertMsg}>{alert.message}</div>
                  </div>
                  <span style={styles.alertTime}>
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* Specialization Entropy Chart Placeholder */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>📈 Specialization Entropy</h3>
            <div style={styles.chartPlaceholder}>
              <svg viewBox="0 0 200 80" style={{ width: '100%', height: 80 }}>
                <path
                  d="M0,60 Q20,65 40,45 Q60,25 80,40 Q100,55 120,30 Q140,10 160,25 Q180,40 200,20"
                  fill="none"
                  stroke="#fbbf24"
                  strokeWidth="2"
                />
                <circle cx={200} cy={20} r={3} fill="#fbbf24" />
                <text x={170} y={14} fill="#6b7280" fontSize="9">trending</text>
              </svg>
              <div style={styles.chartNote}>
                Real-time entropy chart will render here when connected to the metrics stream.
              </div>
            </div>
          </div>

          {/* Agent Counts */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>👥 Agent Count by Role</h3>
            {agentCounts.map((ac) => (
              <div key={ac.role} style={styles.countRow}>
                <span style={{ flex: 1, color: '#a3a3a3' }}>{ac.role}</span>
                <div style={styles.barOuter}>
                  <div
                    style={{
                      ...styles.barInner,
                      width: `${Math.min(100, (ac.count / Math.max(...agentCounts.map((c) => c.count))) * 100)}%`,
                    }}
                  />
                </div>
                <span style={styles.countNumber}>{ac.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right column */}
        <div style={styles.col}>

          {/* Trust Distribution */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>🤝 Trust Distribution</h3>
            {trustDistribution.map((t) => (
              <div key={t.agentId} style={styles.trustRow}>
                <span style={{ flex: 1 }}>{t.agentName}</span>
                <div style={styles.trustBarOuter}>
                  <div
                    style={{
                      ...styles.trustBarInner,
                      width: `${t.score * 100}%`,
                      background:
                        t.score >= 0.7 ? '#22c55e' :
                        t.score >= 0.4 ? '#eab308' : '#ef4444',
                    }}
                  />
                </div>
                <span style={styles.trustScore}>{(t.score * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>

          {/* Energy Flow Visualization */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>⚡ Energy Flow</h3>
            <div style={styles.energyDisplay}>
              <div style={styles.energyGaugeOuter}>
                <div
                  style={{
                    ...styles.energyGaugeInner,
                    width: `${Math.min(100, (energyFlow / 500) * 100)}%`,
                    background: energyFlow > 300
                      ? 'linear-gradient(90deg, #22c55e, #eab308, #ef4444)'
                      : 'linear-gradient(90deg, #22c55e, #16a34a)',
                  }}
                />
              </div>
              <div style={styles.energyValue}>{energyFlow.toFixed(1)} units/s</div>
              <div style={styles.energyStatus}>
                {energyFlow > 300
                  ? '⚠️ Elevated — possible cascade risk'
                  : '✅ Normal operating range'}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: '#1a1a1a',
    color: '#d4d4d4',
    fontFamily: "'Inter', system-ui, sans-serif",
    overflowY: 'auto',
    padding: '0 16px 24px',
  },
  title: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#fbbf24',
    margin: '12px 0',
  },
  cardRow: {
    display: 'flex',
    gap: '12px',
    marginBottom: '16px',
  },
  card: {
    flex: 1,
    background: '#2a2a2a',
    borderRadius: '8px',
    padding: '14px',
    textAlign: 'center',
    border: '1px solid #3a3a3a',
  },
  cardValue: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#fbbf24',
  },
  cardLabel: {
    fontSize: '12px',
    color: '#6b7280',
    marginTop: '4px',
  },
  columns: {
    display: 'flex',
    gap: '16px',
    flexWrap: 'wrap' as const,
  },
  col: {
    flex: '1 1 300px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  section: {
    background: '#2a2a2a',
    borderRadius: '8px',
    padding: '12px',
    border: '1px solid #3a3a3a',
  },
  sectionTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#d4d4d4',
    margin: '0 0 10px',
  },
  emptyText: {
    color: '#525252',
    fontSize: '13px',
    fontStyle: 'italic',
  },
  alertRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    padding: '6px 0',
    borderBottom: '1px solid #2a2a2a',
  },
  severityDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    flexShrink: 0,
    marginTop: 5,
  },
  alertAgent: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#d4d4d4',
  },
  alertMsg: {
    fontSize: '12px',
    color: '#6b7280',
  },
  alertTime: {
    fontSize: '11px',
    color: '#525252',
    flexShrink: 0,
  },
  chartPlaceholder: {
    textAlign: 'center',
  },
  chartNote: {
    fontSize: '11px',
    color: '#525252',
    marginTop: '4px',
    fontStyle: 'italic',
  },
  countRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 0',
    fontSize: '13px',
  },
  barOuter: {
    flex: 1,
    height: 8,
    background: '#3a3a3a',
    borderRadius: 4,
    overflow: 'hidden',
  },
  barInner: {
    height: '100%',
    background: '#fbbf24',
    borderRadius: 4,
    transition: 'width 0.3s',
  },
  countNumber: {
    width: 24,
    textAlign: 'right',
    color: '#d4d4d4',
    fontWeight: 600,
  },
  trustRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 0',
    fontSize: '13px',
  },
  trustBarOuter: {
    flex: 1,
    height: 10,
    background: '#3a3a3a',
    borderRadius: 5,
    overflow: 'hidden',
  },
  trustBarInner: {
    height: '100%',
    borderRadius: 5,
    transition: 'width 0.3s',
  },
  trustScore: {
    width: 40,
    textAlign: 'right',
    fontWeight: 600,
    color: '#d4d4d4',
  },
  energyDisplay: {
    textAlign: 'center',
  },
  energyGaugeOuter: {
    height: 16,
    background: '#3a3a3a',
    borderRadius: 8,
    overflow: 'hidden',
    marginBottom: 8,
  },
  energyGaugeInner: {
    height: '100%',
    borderRadius: 8,
    transition: 'width 0.5s',
  },
  energyValue: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#fbbf24',
    marginBottom: 4,
  },
  energyStatus: {
    fontSize: '12px',
    color: '#6b7280',
  },
};

export default Dashboard;
