import React, { useState, useEffect, useRef, useCallback } from 'react';
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

function parseWsMessage(data: string): TimelineEvent | null {
  try {
    const parsed = JSON.parse(data);

    // Agent interactions (new ESS Protocol events)
    if (parsed.type === 'interaction' && parsed.payload) {
      const p = parsed.payload;
      return {
        id: `int-${p.agent_id}-${p.partner_id}-${parsed.timestamp}`,
        type: 'trust',
        agentName: p.agent_id,
        message: `${p.outcome === 'cooperate' ? '🤝' : '⚔️'} ${p.agent_id} → ${p.partner_id}: ${p.outcome} (trust: ${p.trust}) on ${p.task}`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }

    // Agent thoughts (LLM-powered events)
    if (parsed.type === 'agent_thought' && parsed.payload) {
      const p = parsed.payload;
      return {
        id: `thought-${p.agent_id}-${parsed.timestamp}`,
        type: 'genesis',
        agentName: p.role || p.agent_id || 'unknown',
        message: `💭 [${p.tier}] ${p.agent_id}: ${p.action} — ${(p.insight || '').substring(0, 120)}`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }

    // Stigmergy insights (every 5 ticks)
    if (parsed.type === 'stigmergy_insight' && parsed.payload) {
      const p = parsed.payload;
      const bestList = Object.entries(p.best_agents || {}).map(
        ([tt, ba]: [string, any]) => `${tt}: ${ba.agent_id?.slice(0, 8)} (score: ${ba.score})`
      ).join(', ');
      return {
        id: `stig-${p.tick}`,
        type: 'genesis',
        agentName: 'System',
        message: `📊 Stigmergy insight tick #${p.tick}: ${bestList || 'no clear leaders yet'}`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }

    // Heartbeat
    if (parsed.type === 'heartbeat' && parsed.payload) {
      const p = parsed.payload;
      return {
        id: `hb-${p.tick}`,
        type: 'trust',
        agentName: 'System',
        message: `💓 Tick #${p.tick} — ${p.agents} agents, energy: ${p.total_energy?.toFixed(0) || '?'}`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }

    // Task pipeline events
    if (parsed.type === 'task_posted' && parsed.payload) {
      const p = parsed.payload;
      return {
        id: `tp-${p.task_id}`,
        type: 'task',
        agentName: 'System',
        message: `📋 Task posted: "${p.title}" (${p.task_type}, dif=${p.difficulty})`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }
    if (parsed.type === 'task_assigned' && parsed.payload) {
      const p = parsed.payload;
      return {
        id: `ta-${p.task_id}`,
        type: 'task',
        agentName: p.agent_id || '?',
        message: `📌 ${p.role}: ${p.title || '?'} → ${p.agent_id || '?'} (bid=${p.bid_amount})`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }
    if (parsed.type === 'task_completed' && parsed.payload) {
      const p = parsed.payload;
      return {
        id: `tc-${p.task_id}`,
        type: 'artifact',
        agentName: p.agent_id || '?',
        message: `✅ ${p.title || '?'} — +${p.reward_energy || 0}⚡ +${((p.trust_boost || 0) * 100).toFixed(1)}% trust`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }

    // Agent lifecycle events
    if (parsed.type === 'agent_died' && parsed.payload) {
      const p = parsed.payload;
      return {
        id: `die-${p.agent_id}-${parsed.timestamp}`,
        type: 'alert',
        agentName: p.agent_id || '?',
        message: `💀 Agent died: ${p.agent_id} (${p.role || '?'}) gen=${p.generation || 0} total_deaths=${p.total_deaths || 0}`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }
    if (parsed.type === 'agent_reborn' && parsed.payload) {
      const p = parsed.payload;
      return {
        id: `reb-${p.agent_id}-${parsed.timestamp}`,
        type: 'genesis',
        agentName: p.agent_id || '?',
        message: `✨ Agent reborn: ${p.agent_id} (${p.role}) gen=${p.new_generation} ⚡${p.starting_energy} trust=${p.starting_trust}`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: p,
      };
    }

    // Old tick events (fallback)
    if (parsed.type === 'tick' && parsed.payload) {
      return {
        id: `tick-${parsed.payload.agent_id}-${parsed.timestamp}`,
        type: 'task',
        agentName: parsed.payload.role || parsed.payload.agent_id?.slice(0, 8) || 'unknown',
        message: `Tick — trust: ${parsed.payload.trust?.toFixed(3)}, energy: ${parsed.payload.energy}`,
        timestamp: parsed.timestamp || new Date().toISOString(),
        details: parsed.payload,
      };
    }

    return null;
  } catch {
    return null;
  }
}

const Timeline: React.FC = () => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // WebSocket connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };

      ws.onclose = () => {
        setConnected(false);
        setError('WebSocket disconnected — reconnecting…');
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onmessage = (evt) => {
        const event = parseWsMessage(evt.data);
        if (event) {
          setEvents((prev) => {
            if (prev.some((e) => e.id === event.id)) return prev;
            return [...prev, event].slice(-500);
          });
        }
      };
    };

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

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
      <div style={styles.header}>
        <h2 style={styles.title}>⏱ Timeline</h2>
        <div style={styles.statusRow}>
          <span style={{ ...styles.dot, background: connected ? '#22c55e' : '#ef4444' }} />
          <span style={styles.statusText}>{connected ? 'Live' : 'Disconnected'}</span>
          <span style={styles.count}>{events.length} events</span>
        </div>
      </div>

      <div style={styles.filterBar}>
        <button
          style={{ ...styles.filterBtn, background: filter === 'all' ? '#fbbf24' : 'transparent', color: filter === 'all' ? '#1a1a1a' : '#a3a3a3' }}
          onClick={() => setFilter('all')}
        >All</button>
        {ALL_EVENT_TYPES.map((type) => (
          <button
            key={type}
            style={{ ...styles.filterBtn, background: filter === type ? '#fbbf24' : 'transparent', color: filter === type ? '#1a1a1a' : '#a3a3a3' }}
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

      <div style={styles.controls}>
        <label style={styles.toggleLabel}>
          <input type="checkbox" checked={autoScroll} onChange={() => setAutoScroll(!autoScroll)} style={{ marginRight: 6 }} />
          Auto-scroll
        </label>
      </div>

      {error && <div style={styles.errorBanner}>⚠️ {error}</div>}

      <div style={styles.eventList} ref={scrollRef}>
        {filtered.length === 0 && (
          <div style={styles.empty}>
            {events.length === 0 ? '⏳ Waiting for events from WebSocket…' : 'No events match the current filter.'}
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
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#1a1a1a', color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif", overflow: 'hidden' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid #333' },
  title: { margin: 0, fontSize: '18px', fontWeight: 700, color: '#fbbf24' },
  statusRow: { display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' },
  dot: { width: 10, height: 10, borderRadius: '50%', display: 'inline-block' },
  statusText: { color: '#a3a3a3' },
  count: { color: '#6b7280', fontSize: '12px', marginLeft: '8px' },
  filterBar: { display: 'flex', gap: '6px', padding: '8px 16px', borderBottom: '1px solid #2a2a2a', flexWrap: 'wrap' },
  filterBtn: { border: '1px solid #3a3a3a', borderRadius: '4px', padding: '4px 10px', cursor: 'pointer', fontSize: '12px', fontWeight: 500, transition: 'all 0.15s' },
  controls: { display: 'flex', justifyContent: 'flex-end', padding: '4px 16px', borderBottom: '1px solid #2a2a2a' },
  toggleLabel: { display: 'flex', alignItems: 'center', fontSize: '12px', color: '#a3a3a3', cursor: 'pointer' },
  errorBanner: { background: 'rgba(239,68,68,0.15)', color: '#fca5a5', padding: '6px 16px', fontSize: '13px', borderBottom: '1px solid rgba(239,68,68,0.3)' },
  eventList: { flex: 1, overflowY: 'auto', padding: '8px 16px' },
  empty: { textAlign: 'center', color: '#525252', marginTop: '60px', fontSize: '15px' },
};

export default Timeline;
