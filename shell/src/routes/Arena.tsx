import React, { useState, useEffect, useCallback } from 'react';
import { useGodCommands } from '../hooks/useGodCommands';

interface SpawnedAgent {
  id: string;
  name: string;
  role: string;
  goal: string;
  trustScore: number;
  energyBalance: number;
  createdAt: string;
  status: 'active' | 'paused';
}

const ROLES = [
  { value: 'researcher', label: '🔬 Researcher' },
  { value: 'writer', label: '✍️ Writer' },
  { value: 'critic', label: '🔍 Critic' },
  { value: 'analyst', label: '📊 Analyst' },
  { value: 'explorer', label: '🧭 Explorer' },
];

const Arena: React.FC = () => {
  const [role, setRole] = useState('researcher');
  const [goal, setGoal] = useState('');
  const [spawning, setSpawning] = useState(false);
  const [spawnedAgents, setSpawnedAgents] = useState<SpawnedAgent[]>([]);
  const [error, setError] = useState('');
  const { sendCommand } = useGodCommands();

  // Fetch agents on mount
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const res = await fetch('/api/v1/agents/');
        if (res.ok) {
          const json = await res.json();
          if (json.agents) {
            setSpawnedAgents(json.agents.map((a: any) => ({
              id: a.agent_id,
              name: a.genome?.role || a.role,
              role: a.role,
              goal: a.genome?.instruction || '',
              trustScore: a.trust_score,
              energyBalance: a.energy_balance,
              createdAt: a.created_at,
              status: a.status,
            })));
          }
        }
      } catch { /* ignore */ }
    };
    fetchAgents();
  }, []);

  const handleSpawn = useCallback(async () => {
    if (!goal.trim()) {
      setError('Please enter a goal for the agent.');
      return;
    }
    setError('');
    setSpawning(true);

    try {
      const cmd = `!spawn ${role} "${goal.trim()}"`;
      const result = await sendCommand(cmd);
      if (!result.success) {
        setError(result.error || 'Spawn failed');
      }
      // Refresh agents list
      const res = await fetch('/api/v1/agents/');
      if (res.ok) {
        const json = await res.json();
        if (json.agents) {
          setSpawnedAgents(json.agents.map((a: any) => ({
            id: a.agent_id,
            name: a.genome?.role || a.role,
            role: a.role,
            goal: a.genome?.instruction || '',
            trustScore: a.trust_score,
            energyBalance: a.energy_balance,
            createdAt: a.created_at,
            status: a.status,
          })));
        }
      }
      setGoal('');
    } catch (err: any) {
      setError(err.message ?? 'Spawn failed');
    } finally {
      setSpawning(false);
    }
  }, [role, goal, sendCommand]);

  const isFormValid = goal.trim().length > 0 && !spawning;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🧪 Agent Arena</h2>
      <p style={styles.subtitle}>Design and spawn new agents into the Agora</p>

      <div style={styles.formCard}>
        <h3 style={styles.formTitle}>Spawn a New Agent</h3>

        <label style={styles.label}>Role</label>
        <div style={styles.roleGrid}>
          {ROLES.map((r) => (
            <button
              key={r.value}
              style={{
                ...styles.roleBtn,
                borderColor: role === r.value ? '#fbbf24' : '#3a3a3a',
                background: role === r.value ? 'rgba(251,191,36,0.12)' : '#2a2a2a',
                color: role === r.value ? '#fbbf24' : '#a3a3a3',
              }}
              onClick={() => setRole(r.value)}
            >
              {r.label}
            </button>
          ))}
        </div>

        <label style={styles.label}>Goal / Objective</label>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g. Analyze the latest market trends and produce a report…"
          rows={3}
          style={styles.textarea}
        />

        {error && <div style={styles.errorText}>{error}</div>}

        <button
          onClick={handleSpawn}
          disabled={!isFormValid}
          style={{
            ...styles.spawnBtn,
            opacity: isFormValid ? 1 : 0.4,
            cursor: isFormValid ? 'pointer' : 'not-allowed',
          }}
        >
          {spawning ? '⏳ Spawning…' : '🚀 Spawn Agent'}
        </button>
      </div>

      <div style={styles.listSection}>
        <h3 style={styles.listTitle}>
          Active Agents ({spawnedAgents.length})
        </h3>

        {spawnedAgents.length === 0 && (
          <div style={styles.emptyText}>
            No agents yet. Spawn your first agent above!
          </div>
        )}

        <div style={styles.agentList}>
          {spawnedAgents.map((agent) => (
            <div key={agent.id} style={styles.agentCard}>
              <div style={styles.agentHeader}>
                <span style={styles.agentName}>{agent.name}</span>
                <span style={{ ...styles.statusBadge, background: agent.status === 'active' ? '#22c55e' : '#eab308' }}>
                  {agent.status}
                </span>
              </div>
              <div style={styles.agentDetail}>
                <span style={styles.agentRole}>
                  {ROLES.find((r) => r.value === agent.role)?.label ?? agent.role}
                </span>
                <span style={{ marginLeft: 12, color: '#6b7280' }}>
                  Trust: {(agent.trustScore * 100).toFixed(0)}% | Energy: {agent.energyBalance.toFixed(0)}
                </span>
              </div>
              {agent.goal && <div style={styles.agentGoal}>{agent.goal}</div>}
              <div style={styles.agentTime}>
                {new Date(agent.createdAt).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', background: '#1a1a1a', color: '#d4d4d4', fontFamily: "'Inter', system-ui, sans-serif", overflowY: 'auto', padding: '0 16px 24px' },
  title: { fontSize: '18px', fontWeight: 700, color: '#fbbf24', margin: '12px 0 0' },
  subtitle: { fontSize: '13px', color: '#6b7280', margin: '4px 0 16px' },
  formCard: { background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px', padding: '16px', marginBottom: '16px' },
  formTitle: { fontSize: '15px', fontWeight: 600, color: '#d4d4d4', margin: '0 0 12px' },
  label: { display: 'block', fontSize: '12px', color: '#a3a3a3', marginBottom: '6px', fontWeight: 500 },
  roleGrid: { display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '14px' },
  roleBtn: { border: '1px solid', borderRadius: '6px', padding: '8px 14px', cursor: 'pointer', fontSize: '13px', fontWeight: 500, transition: 'all 0.15s' },
  textarea: { width: '100%', background: '#1a1a1a', border: '1px solid #3a3a3a', borderRadius: '6px', color: '#d4d4d4', padding: '10px', fontSize: '13px', fontFamily: 'inherit', resize: 'vertical', boxSizing: 'border-box', marginBottom: '10px' },
  errorText: { color: '#ef4444', fontSize: '12px', marginBottom: '8px' },
  spawnBtn: { width: '100%', padding: '12px', background: '#fbbf24', color: '#1a1a1a', border: 'none', borderRadius: '6px', fontSize: '15px', fontWeight: 700, transition: 'all 0.15s' },
  listSection: { flex: 1 },
  listTitle: { fontSize: '14px', fontWeight: 600, color: '#d4d4d4', margin: '0 0 10px' },
  emptyText: { color: '#525252', fontSize: '13px', fontStyle: 'italic', padding: '20px 0', textAlign: 'center' },
  agentList: { display: 'flex', flexDirection: 'column', gap: '8px' },
  agentCard: { background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px', padding: '12px' },
  agentHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' },
  agentName: { fontWeight: 600, color: '#fbbf24', fontSize: '14px' },
  statusBadge: { padding: '2px 8px', borderRadius: '10px', color: '#fff', fontSize: '11px', fontWeight: 600, textTransform: 'capitalize' },
  agentDetail: { marginBottom: '4px', fontSize: '12px' },
  agentRole: { color: '#a3a3a3' },
  agentGoal: { fontSize: '12px', color: '#d4d4d4', lineHeight: 1.4, marginBottom: '4px' },
  agentTime: { fontSize: '11px', color: '#525252' },
};

export default Arena;
