/**
 * Dungeon.tsx — simple working layout.
 *
 * Canvas left (flex: 1), sidebar right (fixed 300px).
 */
import React from 'react';
import DungeonCanvas from '../game/DungeonCanvas';
import QuestBoard from '../game/panels/QuestBoard';
import OsMeters from '../game/panels/OsMeters';
import AgentList from '../game/panels/AgentList';
import LogStream from '../game/panels/LogStream';

const Dungeon: React.FC = () => {
  return (
    <div style={layout.container}>
      <div style={layout.canvasWrapper}>
        <DungeonCanvas />
      </div>
      <div style={layout.sidebar}>
        <QuestBoard />
        <OsMeters />
        <AgentList />
        <LogStream />
      </div>
    </div>
  );
};

const layout: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    width: '100%',
    height: '100%',
    background: '#0d0d14',
    overflow: 'hidden',
  },
  canvasWrapper: {
    flex: 1,
    position: 'relative',
    minWidth: 0,
  },
  sidebar: {
    width: 300,
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    padding: 8,
    borderLeft: '1px solid #2a2a3a',
    background: '#12121a',
    overflowY: 'auto',
  },
};

export default Dungeon;
