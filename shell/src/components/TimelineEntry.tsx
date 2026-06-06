import React, { useState } from 'react';

interface TimelineEvent {
  id: string;
  type: 'genesis' | 'task' | 'trust' | 'artifact' | 'alert';
  agentName: string;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

interface TimelineEntryProps {
  event: TimelineEvent;
}

const EVENT_CONFIG: Record<
  TimelineEvent['type'],
  { icon: string; color: string; label: string }
> = {
  genesis: { icon: '🧬', color: '#22c55e', label: 'Genesis' },
  task: { icon: '📋', color: '#3b82f6', label: 'Task' },
  trust: { icon: '🤝', color: '#eab308', label: 'Trust' },
  artifact: { icon: '📄', color: '#a855f7', label: 'Artifact' },
  alert: { icon: '⚠️', color: '#ef4444', label: 'Alert' },
};

const TimelineEntry: React.FC<TimelineEntryProps> = ({ event }) => {
  const [expanded, setExpanded] = useState(false);
  const config = EVENT_CONFIG[event.type];

  return (
    <div
      style={{
        ...styles.container,
        borderLeftColor: config.color,
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Icon + content row */}
      <div style={styles.mainRow}>
        <span style={styles.icon}>{config.icon}</span>
        <div style={styles.content}>
          <div style={styles.headerRow}>
            <span
              style={{
                ...styles.typeBadge,
                background: `${config.color}22`,
                color: config.color,
              }}
            >
              {config.label}
            </span>
            <span style={styles.agentName}>{event.agentName}</span>
            <span style={styles.timestamp}>
              {new Date(event.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div style={styles.message}>{event.message}</div>
        </div>
      </div>

      {/* Expandable details */}
      {expanded && event.details && (
        <div style={styles.detailsPanel}>
          {Object.entries(event.details).map(([key, value]) => (
            <div key={key} style={styles.detailRow}>
              <span style={styles.detailKey}>{key}:</span>
              <span style={styles.detailValue}>
                {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Expand hint */}
      {!expanded && event.details && (
        <div style={styles.expandHint}>Click for details ▾</div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#2a2a2a',
    border: '1px solid #3a3a3a',
    borderLeftWidth: 4,
    borderRadius: '6px',
    padding: '10px 12px',
    marginBottom: '6px',
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  mainRow: {
    display: 'flex',
    gap: '10px',
    alignItems: 'flex-start',
  },
  icon: {
    fontSize: '18px',
    lineHeight: '22px',
    flexShrink: 0,
    marginTop: 2,
  },
  content: {
    flex: 1,
    minWidth: 0,
  },
  headerRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '4px',
    flexWrap: 'wrap',
  },
  typeBadge: {
    padding: '1px 7px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
  },
  agentName: {
    fontWeight: 600,
    fontSize: '13px',
    color: '#d4d4d4',
  },
  timestamp: {
    fontSize: '11px',
    color: '#525252',
    marginLeft: 'auto',
    flexShrink: 0,
  },
  message: {
    fontSize: '13px',
    color: '#a3a3a3',
    lineHeight: 1.4,
  },
  expandHint: {
    fontSize: '11px',
    color: '#525252',
    marginTop: '6px',
    textAlign: 'right',
    fontStyle: 'italic',
  },
  detailsPanel: {
    marginTop: '8px',
    padding: '8px',
    background: '#1a1a1a',
    borderRadius: '4px',
    border: '1px solid #3a3a3a',
  },
  detailRow: {
    display: 'flex',
    gap: '6px',
    padding: '2px 0',
    fontSize: '12px',
  },
  detailKey: {
    color: '#fbbf24',
    fontWeight: 600,
    flexShrink: 0,
  },
  detailValue: {
    color: '#a3a3a3',
    wordBreak: 'break-all',
    whiteSpace: 'pre-wrap',
  },
};

export default TimelineEntry;
