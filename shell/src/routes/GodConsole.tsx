import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useGodCommands } from '../hooks/useGodCommands';

const COMMANDS = [
  '!status',
  '!agents',
  '!spawn',
  '!shutdown',
  '!broadcast',
  '!metrics',
  '!config',
  '!log',
  '!reset',
  '!help',
];

interface HistoryEntry {
  command: string;
  output: string;
  timestamp: Date;
}

const suggestionsFromCommand = (cmd: string): string[] => {
  if (!cmd.startsWith('!')) return [];
  return COMMANDS.filter((c) => c.startsWith(cmd));
};

const GodConsole: React.FC = () => {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedSuggestion, setSelectedSuggestion] = useState(-1);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsLog, setWsLog] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const historyEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { sendCommand } = useGodCommands();

  // WebSocket connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/god/ws`;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (evt) => {
        setWsLog((prev) => [...prev.slice(-199), evt.data]);
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
    historyEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, wsLog]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setInput(val);
      setSuggestions(suggestionsFromCommand(val));
      setSelectedSuggestion(-1);
    },
    [],
  );

  const executeCommand = useCallback(
    async (cmd: string) => {
      const trimmed = cmd.trim();
      if (!trimmed) return;

      setHistory((prev) => [
        ...prev,
        { command: trimmed, output: '⏳ Sending…', timestamp: new Date() },
      ]);
      setInput('');
      setSuggestions([]);

      try {
        const result = await sendCommand(trimmed);
        setHistory((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = {
            ...copy[copy.length - 1],
            output: result.output ?? result.error ?? '(empty response)',
          };
          return copy;
        });
      } catch (err: any) {
        setHistory((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = {
            ...copy[copy.length - 1],
            output: `❌ ${err.message ?? String(err)}`,
          };
          return copy;
        });
      }
    },
    [sendCommand],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (selectedSuggestion >= 0 && suggestions[selectedSuggestion]) {
          executeCommand(suggestions[selectedSuggestion]);
        } else {
          executeCommand(input);
        }
        return;
      }

      if (e.key === 'ArrowDown' && suggestions.length > 0) {
        e.preventDefault();
        setSelectedSuggestion((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : 0,
        );
        return;
      }

      if (e.key === 'ArrowUp' && suggestions.length > 0) {
        e.preventDefault();
        setSelectedSuggestion((prev) =>
          prev > 0 ? prev - 1 : suggestions.length - 1,
        );
        return;
      }

      // Tab completion
      if (e.key === 'Tab' && suggestions.length > 0) {
        e.preventDefault();
        const pick = selectedSuggestion >= 0 ? suggestions[selectedSuggestion] : suggestions[0];
        setInput(pick + ' ');
        setSuggestions([]);
        setSelectedSuggestion(-1);
      }

      if (e.key === 'Escape') {
        setSuggestions([]);
        setSelectedSuggestion(-1);
      }
    },
    [input, suggestions, selectedSuggestion, executeCommand],
  );

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.title}>⛁ God Console</span>
        <span
          style={{
            ...styles.badge,
            background: wsConnected ? '#22c55e' : '#ef4444',
          }}
        >
          {wsConnected ? '● LIVE' : '○ DISCONNECTED'}
        </span>
      </div>

      {/* History output */}
      <div style={styles.outputArea}>
        {history.map((entry, idx) => (
          <div key={idx} style={styles.historyRow}>
            <span style={styles.prompt}>&gt;</span>
            <span style={styles.commandText}>{entry.command}</span>
            <br />
            <span style={styles.outputText}>{entry.output}</span>
            <span style={styles.timestamp}>
              {entry.timestamp.toLocaleTimeString()}
            </span>
          </div>
        ))}

        {/* Real-time WS log */}
        {wsLog.length > 0 && (
          <div style={styles.wsSection}>
            <div style={styles.wsLabel}>📡 Live feed</div>
            {wsLog.map((msg, i) => (
              <div key={i} style={styles.wsLine}>
                {msg}
              </div>
            ))}
          </div>
        )}
        <div ref={historyEndRef} />
      </div>

      {/* Input row with suggestions */}
      <div style={styles.inputArea}>
        {suggestions.length > 0 && (
          <div style={styles.suggestionsDropdown}>
            {suggestions.map((s, i) => (
              <div
                key={s}
                style={{
                  ...styles.suggestionItem,
                  background:
                    i === selectedSuggestion
                      ? 'rgba(251,191,36,0.25)'
                      : 'transparent',
                }}
                onMouseDown={() => {
                  setInput(s + ' ');
                  setSuggestions([]);
                  inputRef.current?.focus();
                }}
              >
                {s}
              </div>
            ))}
          </div>
        )}
        <span style={styles.prompt}>&gt;</span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="Type a command…"
          style={styles.input}
        />
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
    fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
    fontSize: '14px',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 16px',
    background: '#2a2a2a',
    borderBottom: '1px solid #3a3a3a',
  },
  title: {
    color: '#fbbf24',
    fontWeight: 700,
    fontSize: '16px',
  },
  badge: {
    padding: '2px 10px',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '11px',
    fontWeight: 600,
  },
  outputArea: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 16px',
  },
  historyRow: {
    marginBottom: '10px',
    lineHeight: 1.5,
  },
  prompt: {
    color: '#fbbf24',
    marginRight: '8px',
    fontWeight: 700,
  },
  commandText: {
    color: '#fbbf24',
    fontWeight: 600,
  },
  outputText: {
    color: '#a3a3a3',
    whiteSpace: 'pre-wrap',
    display: 'block',
    marginLeft: '14px',
  },
  timestamp: {
    color: '#525252',
    fontSize: '11px',
    marginLeft: '12px',
  },
  wsSection: {
    marginTop: '16px',
    borderTop: '1px dashed #3a3a3a',
    paddingTop: '8px',
  },
  wsLabel: {
    color: '#22d3ee',
    fontSize: '12px',
    fontWeight: 600,
    marginBottom: '4px',
  },
  wsLine: {
    color: '#6b7280',
    fontSize: '12px',
    lineHeight: 1.4,
  },
  inputArea: {
    display: 'flex',
    alignItems: 'center',
    padding: '10px 16px',
    background: '#2a2a2a',
    borderTop: '1px solid #3a3a3a',
    position: 'relative',
  },
  input: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#d4d4d4',
    fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
    fontSize: '14px',
  },
  suggestionsDropdown: {
    position: 'absolute',
    bottom: '100%',
    left: '16px',
    right: '16px',
    background: '#2a2a2a',
    border: '1px solid #3a3a3a',
    borderRadius: '4px 4px 0 0',
    maxHeight: '160px',
    overflowY: 'auto',
  },
  suggestionItem: {
    padding: '6px 12px',
    cursor: 'pointer',
    color: '#fbbf24',
    fontSize: '13px',
  },
};

export default GodConsole;
