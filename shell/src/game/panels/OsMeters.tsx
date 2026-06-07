/**
 * OsMeters.tsx — OS subsystem meters from world.ts Zustand store.
 * Shows comms, knowledge, tooling, economy, safety as mini bars.
 */
import React from 'react';
import { useWorldStore } from '../../state/world';

const SUBSYSTEMS: { key: keyof ReturnType<typeof useWorldStore.getState>['osState']; label: string; color: string }[] = [
  { key: 'comms', label: 'Comms', color: '#88ccff' },
  { key: 'knowledge', label: 'Knowledge', color: '#cc88ff' },
  { key: 'tooling', label: 'Tooling', color: '#ff8844' },
  { key: 'economy', label: 'Economy', color: '#fbbf24' },
  { key: 'safety', label: 'Safety', color: '#44cc88' },
];

const barColor = (val: number): string => {
  if (val >= 60) return '#22c55e';
  if (val >= 30) return '#eab308';
  return '#ef4444';
};

const OsMeters: React.FC = () => {
  const osState = useWorldStore((s) => s.osState);

  return (
    <div style={panelStyles.container}>
      <div style={panelStyles.header}>⚙️ OS Subsystems</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {SUBSYSTEMS.map(({ key, label, color }) => {
          const val = osState[key];
          return (
            <div key={key} style={panelStyles.row}>
              <span style={{ ...panelStyles.label, color }}>{label}</span>
              <div style={panelStyles.barOuter}>
                <div style={{
                  ...panelStyles.barInner,
                  width: `${val}%`,
                  background: barColor(val),
                }} />
              </div>
              <span style={panelStyles.value}>{val}</span>
            </div>
          );
        })}
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
  row: { display: 'flex', alignItems: 'center', gap: 6 },
  label: { width: 56, fontSize: 11, fontWeight: 600, textTransform: 'uppercase' },
  barOuter: { flex: 1, height: 8, background: '#2a2a3a', borderRadius: 4, overflow: 'hidden' },
  barInner: { height: '100%', borderRadius: 4, transition: 'width 0.3s ease' },
  value: { width: 22, textAlign: 'right', fontSize: 11, color: '#9ca3af', fontFamily: 'monospace' },
};

export default OsMeters;
