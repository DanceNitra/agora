/**
 * LogStream.tsx — scrollable event log.
 * Newest entries at the TOP, scrolls internally.
 */
import React from 'react';
import { useWorldStore } from '../../state/world';

const agentColor = (name: string): string => {
  const palette = ['#88ccff', '#44ff88', '#cc88ff', '#ff8844', '#44ffaa', '#ffff44', '#8888cc'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return palette[Math.abs(hash) % palette.length];
};

const LogStream: React.FC = () => {
  const log = useWorldStore((s) => s.log);

  // Newest entries first
  const reversed = [...log].reverse();

  return (
    <div style={panelStyles.container}>
      <div style={panelStyles.header}>📜 Event Log</div>
      <div style={panelStyles.logList}>
        {reversed.length === 0 ? (
          <div style={panelStyles.empty}>No events yet</div>
        ) : (
          reversed.slice(0, 50).map((entry, i) => (
            <div key={i} style={panelStyles.entry}>
              <span style={panelStyles.tick}>#{entry.tick}</span>
              <span style={{ ...panelStyles.agent, color: agentColor(entry.agent) }}>
                [{entry.agent}]
              </span>
              <span style={panelStyles.text}>{entry.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const panelStyles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: 'rgba(20,20,30,0.85)',
    borderLeft: 'none',
    padding: '8px 10px',
  },
  header: {
    fontSize: 13,
    fontWeight: 600,
    color: '#d4d4d4',
    borderBottom: '1px solid #3a3a4a',
    paddingBottom: 6,
    marginBottom: 6,
    flexShrink: 0,
  },
  logList: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
    fontSize: 11,
    scrollbarWidth: 'thin',
    scrollbarColor: '#3a3a4a transparent',
  },
  empty: { color: '#525252', fontStyle: 'italic', padding: 8, textAlign: 'center' },
  entry: { display: 'flex', gap: 4, alignItems: 'flex-start', lineHeight: 1.4, flexShrink: 0 },
  tick: { color: '#525252', fontFamily: 'monospace', flexShrink: 0, width: 28 },
  agent: { fontWeight: 600, flexShrink: 0 },
  text: { color: '#a3a3a3', wordBreak: 'break-word' },
};

export default LogStream;
