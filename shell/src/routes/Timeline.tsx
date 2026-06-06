import React, { useState, useEffect, useRef } from 'react';
import { useSSE } from '../hooks/useSSE';
import TimelineEntry from '../components/TimelineEntry';

interface TimelineEvent {
  id: string;
  type: 'genesis' | 'task' | 'trust' | 'artifact' | 'alert';
  agentName: string;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

const ALL_EVENT_TYPES = ['genesis', 'task', 'trust', 'artifact', 'alert'] as const;

const Timeline: React.FC = () => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // SSE connection via our hook
  const { connected, lastEvent, error } = useSSE<TimelineEvent>(
    '/api/v1/timeline/stream',
  );

  // Append incoming events
  useEffect(() => {
    if (!lastEvent) return;
    setEvents((prev) => {
      // Prevent duplicates
      if (prev.some((e) => e.id === lastEvent.id)) return prev;
      return [...prev, lastEvent].slice(-500); // keep last 500
    });
  }, [lastEvent]);

  // Auto-scroll
  useEffect(() => {
    if (!autoScroll || !scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [events, autoScroll]);

  const filtered =
    filter === 'all'
      ? events
      : events.filter((e) => e.type === filter);

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>⏱ Timeline</h2>
        <div style={styles.statusRow}>
          <span
            style={{
              ...styles.dot,
              background: connected ? '#22c55e' : '#ef4444',
            }}
          />
          <span style={styles.statusText}>
            {connected ? 'Live' : 'Disconnected'}
          </span>
          <span style={styles.count}>{events.length} events</span>
        </div>
      </div>

      {/* Filters */}
      <div style={styles.filterBar}>
        <button
          style={{
            ...styles.filterBtn,
            background: filter === 'all' ? '#fbbf24' : 'transparent',
            color: filter === 'all' ? '#1a1a1a' : '#a3a3a3',
          }}
          onClick={() => setFilter('all')}
        >
          All
        </button>
        {ALL_EVENT_TYPES.map((type) => (
          <button
            key={type}
            style={{
              ...styles.filterBtn,
              background: filter === type ? '#fbbf24' : 'transparent',
              color: filter === type ? '#1a1a1a' : '#a3a3a3',
            }}
            onClick={() => setFilter(type)}
          >
            {type === 'genesis' && '🧬'}
            {type === 'task' && '📋'}
            {type === 'trust' && '🤝'}
            {type === 'artifact' && '📄'}
            {type === 'alert' && '⚠️'}
            {' '}
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </button>
        ))}
      </div>

      {/* Auto-scroll toggle */}
      <div style={styles.controls}>
        <label style={styles.toggleLabel}>
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={() => setAutoScroll(!autoScroll)}
            style={{ marginRight: 6 }}
          />
          Auto-scroll
        </label>
      </div>

      {/* Error banner */}
      {error && (
        <div style={styles.errorBanner}>
          ⚠️ Connection error: {error}
        </div>
      )}

      {/* Event list */}
      <div style={styles.eventList} ref={scrollRef}>
        {filtered.length === 0 && (
          <div style={styles.empty}>
            {events.length === 0
              ? '⏳ Waiting for events…'
              : 'No events match the current filter.'}
          </div>
        )}
        {filtered.map((event) => (
          <TimelineEntry key={event.id} event={event} />
        ))}
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
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    borderBottom: '1px solid #333',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 700,
    color: '#fbbf24',
  },
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    display: 'inline-block',
  },
  statusText: {
    color: '#a3a3a3',
  },
  count: {
    color: '#6b7280',
    fontSize: '12px',
    marginLeft: '8px',
  },
  filterBar: {
    display: 'flex',
    gap: '6px',
    padding: '8px 16px',
    borderBottom: '1px solid #2a2a2a',
    flexWrap: 'wrap',
  },
  filterBtn: {
    border: '1px solid #3a3a3a',
    borderRadius: '4px',
    padding: '4px 10px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 500,
    transition: 'all 0.15s',
  },
  controls: {
    display: 'flex',
    justifyContent: 'flex-end',
    padding: '4px 16px',
    borderBottom: '1px solid #2a2a2a',
  },
  toggleLabel: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '12px',
    color: '#a3a3a3',
    cursor: 'pointer',
  },
  errorBanner: {
    background: 'rgba(239,68,68,0.15)',
    color: '#fca5a5',
    padding: '6px 16px',
    fontSize: '13px',
    borderBottom: '1px solid rgba(239,68,68,0.3)',
  },
  eventList: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px 16px',
  },
  empty: {
    textAlign: 'center',
    color: '#525252',
    marginTop: '60px',
    fontSize: '15px',
  },
};

export default Timeline;
