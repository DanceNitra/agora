/**
 * QuestBoard.tsx — shows active quests from world.ts Zustand store.
 */
import React from 'react';
import { useWorldStore } from '../../state/world';

const QuestBoard: React.FC = () => {
  const quests = useWorldStore((s) => s.quests);
  const tick = useWorldStore((s) => s.tick);

  return (
    <div style={panelStyles.container}>
      <div style={panelStyles.header}>
        <span>🎯 Quests</span>
        <span style={panelStyles.tick}>#{tick}</span>
      </div>
      {quests.length === 0 ? (
        <div style={panelStyles.empty}>No active quests</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {quests.map((q, i) => (
            <div key={i} style={panelStyles.questRow}>
              <span style={panelStyles.npc}>{q.npcName}</span>
              <span style={panelStyles.questTitle}>{q.activeQuestTitle}</span>
              <span style={panelStyles.questStatus(q.questStatus)}>
                {q.questStatus}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const panelStyles: Record<string, React.CSSProperties | ((v: string) => React.CSSProperties)> = {
  container: {
    background: 'rgba(20,20,30,0.85)',
    border: '1px solid #3a3a4a',
    borderRadius: 8,
    padding: 10,
    backdropFilter: 'blur(4px)',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    fontSize: 13, fontWeight: 600, color: '#d4d4d4', marginBottom: 8,
    borderBottom: '1px solid #3a3a4a', paddingBottom: 6,
  },
  tick: { fontSize: 11, color: '#6b7280', fontFamily: 'monospace' },
  empty: { fontSize: 12, color: '#525252', fontStyle: 'italic', padding: 8, textAlign: 'center' },
  questRow: {
    display: 'flex', flexDirection: 'column', gap: 2,
    padding: '6px 8px', background: 'rgba(42,42,52,0.6)', borderRadius: 6,
    border: '1px solid #2a2a3a',
  },
  npc: { fontSize: 11, color: '#88ccff', fontWeight: 600 },
  questTitle: { fontSize: 12, color: '#d4d4d4' },
  questStatus: (v: string): React.CSSProperties => ({
    fontSize: 10, color: v === 'active' ? '#22c55e' : v === 'completed' ? '#88ccff' : '#eab308',
    fontWeight: 600, textTransform: 'uppercase',
  }),
};

export default QuestBoard;
