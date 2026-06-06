import React from 'react';
import { useAgent, AgentDetail } from '../context/AgentContext';

const trustColor = (score: number) => {
  if (score >= 0.7) return '#22c55e';
  if (score >= 0.4) return '#eab308';
  return '#ef4444';
};

const AgentDetailPanel: React.FC = () => {
  const { selectedAgent, setSelectedAgent } = useAgent();

  if (!selectedAgent) return null;

  const a = selectedAgent;

  return (
    <div style={styles.overlay} onClick={() => setSelectedAgent(null)}>
      <div style={styles.panel} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.name}>{a.name}</div>
            <div style={styles.role}>{a.role}</div>
          </div>
          <button onClick={() => setSelectedAgent(null)} style={styles.closeBtn}>✕</button>
        </div>

        {/* Status badge */}
        <div style={styles.statusRow}>
          <span style={{
            ...styles.badge,
            background: a.status === 'active' ? '#22c55e' : a.status === 'paused' ? '#eab308' : '#ef4444',
          }}>
            {a.status.toUpperCase()}
          </span>
          <span style={styles.wsBadge}>
            📍 ({Math.round(a.position.x)}, {Math.round(a.position.y)})
          </span>
        </div>

        {/* Metrics */}
        <div style={styles.metricsRow}>
          <MetricBox label="Trust" value={`${(a.trustScore * 100).toFixed(0)}%`} color={trustColor(a.trustScore)} />
          <MetricBox label="Energy" value={a.energyBalance.toString()} color={a.energyBalance > 20 ? '#44cc44' : '#cc4444'} />
          <MetricBox label="HP" value={`${a.health}/100`} color={a.health > 60 ? '#44cc44' : a.health > 30 ? '#cccc44' : '#cc4444'} />
          <MetricBox label="Tasks" value={a.tasks.length.toString()} color="#88ccff" />
        </div>

        {/* Objective */}
        {a.objective && (
          <div style={styles.section}>
            <div style={styles.sectionLabel}>🎯 Objective</div>
            <div style={styles.objective}>{a.objective}</div>
          </div>
        )}

        {/* Inventory */}
        {a.inventory.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionLabel}>🎒 Inventory</div>
            <div style={styles.inventoryRow}>
              {a.inventory.map((item, i) => (
                <span key={i} style={styles.inventoryItem}>{item}</span>
              ))}
            </div>
          </div>
        )}

        {/* Tasks */}
        {a.tasks.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionLabel}>📋 Active Tasks</div>
            {a.tasks.slice(0, 3).map((t) => (
              <div key={t.id} style={styles.taskRow}>
                <span style={{ color: t.status === 'active' ? '#fbbf24' : '#6b7280' }}>
                  {t.status === 'active' ? '◉' : '○'}
                </span>
                <span style={{ marginLeft: 6, flex: 1, fontSize: 12 }}>{t.title}</span>
                {t.difficulty && <span style={{ color: '#6b7280', fontSize: 11 }}>⚡{t.difficulty}</span>}
              </div>
            ))}
          </div>
        )}

        {/* Recent Memories */}
        {a.memories.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionLabel}>🧠 Recent Memories</div>
            {a.memories.slice(-3).reverse().map((m, i) => (
              <div key={i} style={styles.memoryRow}>
                <span style={{ color: m.importance > 7 ? '#fbbf24' : '#a3a3a3', fontSize: 11 }}>
                  [{m.importance}/10]
                </span>
                <span style={{ marginLeft: 4, fontSize: 11 }}>{m.text.slice(0, 80)}{m.text.length > 80 ? '…' : ''}</span>
              </div>
            ))}
          </div>
        )}

        {/* Artifacts */}
        {a.artifacts.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionLabel}>📦 Recent Artifacts</div>
            {a.artifacts.map((art) => (
              <div key={art.id} style={{ fontSize: 11, color: '#a3a3a3', padding: '2px 0' }}>
                📄 {art.title} <span style={{ color: '#6b7280' }}>({art.type})</span>
              </div>
            ))}
          </div>
        )}

        {/* Nearby NPCs */}
        {a.nearbyNPCs.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionLabel}>👥 Nearby</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {a.nearbyNPCs.map((npc, i) => (
                <span key={i} style={styles.nearbyNpc}>{typeof npc === 'string' ? npc : (npc as any).name || ''}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const MetricBox: React.FC<{ label: string; value: string; color: string }> = ({ label, value, color }) => (
  <div style={styles.metricBox}>
    <div style={{ ...styles.metricValue, color }}>{value}</div>
    <div style={styles.metricLabel}>{label}</div>
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed', inset: 0, zIndex: 1000,
    background: 'rgba(0,0,0,0.5)', display: 'flex',
    justifyContent: 'center', alignItems: 'center',
  },
  panel: {
    background: '#1e1e1e', border: '1px solid #3a3a3a', borderRadius: '12px',
    width: '400px', maxHeight: '85vh', overflowY: 'auto',
    padding: '20px', boxShadow: '0 8px 40px rgba(0,0,0,0.6)',
    color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif",
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 },
  name: { fontSize: 20, fontWeight: 700, color: '#fbbf24' },
  role: { fontSize: 12, color: '#6b7280', marginTop: 2, textTransform: 'capitalize' },
  closeBtn: { background: 'none', border: 'none', color: '#a3a3a3', cursor: 'pointer', fontSize: 18, padding: 4 },
  statusRow: { display: 'flex', gap: 8, marginBottom: 14, alignItems: 'center' },
  badge: { padding: '2px 10px', borderRadius: 4, color: '#fff', fontSize: 11, fontWeight: 600 },
  wsBadge: { color: '#6b7280', fontSize: 11 },
  metricsRow: { display: 'flex', gap: 8, marginBottom: 16 },
  metricBox: { flex: 1, background: '#2a2a2a', borderRadius: 8, padding: '10px 6px', textAlign: 'center', border: '1px solid #3a3a3a' },
  metricValue: { fontSize: 20, fontWeight: 700 },
  metricLabel: { fontSize: 10, color: '#6b7280', marginTop: 2 },
  section: { marginBottom: 14 },
  sectionLabel: { fontSize: 12, fontWeight: 600, color: '#d4d4d4', marginBottom: 6 },
  objective: { fontSize: 13, color: '#a3a3a3', fontStyle: 'italic', padding: '6px 10px', background: '#2a2a2a', borderRadius: 6, border: '1px solid #3a3a3a' },
  inventoryRow: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  inventoryItem: { fontSize: 11, padding: '3px 8px', background: '#2a2a2a', borderRadius: 4, border: '1px solid #3a3a3a', color: '#a3a3a3' },
  taskRow: { display: 'flex', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #2a2a2a' },
  memoryRow: { padding: '3px 0', borderBottom: '1px solid #2a2a2a', display: 'flex' },
  nearbyNpc: { fontSize: 11, padding: '2px 8px', background: '#2a2a2a', borderRadius: 4, border: '1px solid #3a3a3a', color: '#a3a3a3' },
};

export default AgentDetailPanel;
