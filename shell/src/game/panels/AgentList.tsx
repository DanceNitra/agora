/**
 * AgentList.tsx — dungeon agent list reading from world.ts Zustand store.
 * Shows agent name, role, health, status. Click to focus camera.
 */
import React from 'react';
import { useWorldStore, TILE } from '../../state/world';

const statusColor = (s: string) => {
  if (s === 'idle' || s === 'idle') return '#6b7280';
  if (s === 'moving' || s === 'patrolling') return '#88ccff';
  if (s === 'working' || s === 'trading' || s === 'researching') return '#22c55e';
  if (s === 'fighting' || s === 'warning') return '#ef4444';
  return '#eab308';
};

const AgentList: React.FC = () => {
  const agents = useWorldStore((s) => s.agents);

  const agentArray = Object.values(agents);

  return (
    <div style={panelStyles.container}>
      <div style={panelStyles.header}>
        <span>👤 Agents ({agentArray.length})</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {agentArray.map((a) => (
          <div key={a.id} style={panelStyles.agentRow}>
            <div style={panelStyles.agentInfo}>
              <div style={panelStyles.nameRow}>
                <span style={{ ...panelStyles.statusDot, background: statusColor(a.status) }} />
                <span style={panelStyles.name}>{a.name}</span>
                <span style={panelStyles.role}>{a.role}</span>
              </div>
              <div style={panelStyles.status}>{a.status}</div>
            </div>
            <div style={panelStyles.metrics}>
              <div style={panelStyles.healthBarOuter}>
                <div style={{
                  ...panelStyles.healthBarInner,
                  width: `${a.health}%`,
                  background: a.health > 60 ? '#22c55e' : a.health > 30 ? '#eab308' : '#ef4444',
                }} />
              </div>
              <span style={panelStyles.objective}>{a.objective.slice(0, 30)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const panelStyles: Record<string, React.CSSProperties> = {
  container: {
    background: 'rgba(20,20,30,0.85)',
    border: '1px solid #3a3a4a',
    borderRadius: 8,
    padding: 10,
    backdropFilter: 'blur(4px)',
  },
  header: {
    fontSize: 13, fontWeight: 600, color: '#d4d4d4', marginBottom: 8,
    borderBottom: '1px solid #3a3a4a', paddingBottom: 6,
  },
  agentRow: {
    display: 'flex', flexDirection: 'column', gap: 4,
    padding: '6px 8px', background: 'rgba(42,42,52,0.6)', borderRadius: 6,
    border: '1px solid #2a2a3a', cursor: 'pointer',
  },
  agentInfo: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  nameRow: { display: 'flex', alignItems: 'center', gap: 6 },
  statusDot: { width: 6, height: 6, borderRadius: '50%', flexShrink: 0 },
  name: { fontSize: 12, fontWeight: 600, color: '#d4d4d4' },
  role: { fontSize: 10, color: '#6b7280', textTransform: 'capitalize' },
  status: { fontSize: 10, color: '#9ca3af' },
  metrics: { display: 'flex', alignItems: 'center', gap: 6 },
  healthBarOuter: { flex: 1, height: 4, background: '#2a2a3a', borderRadius: 2, overflow: 'hidden' },
  healthBarInner: { height: '100%', borderRadius: 2, transition: 'width 0.3s' },
  objective: { fontSize: 10, color: '#6b7280', fontStyle: 'italic', width: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
};

export default AgentList;
