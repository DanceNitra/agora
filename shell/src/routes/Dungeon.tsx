/**
 * Dungeon.tsx — route page: split layout with PixiJS canvas + dashboard panels.
 *
 * Layout:
 *   ┌──────────────────────────┬──────────────────────┐
 *   │                          │ 📋 QuestBoard        │
 *   │     PixiJS Dungeon       │ ⚙️ OS Meters         │
 *   │                          │ 👤 Agent List         │
 *   │                          │ 📜 Event Log          │
 *   └──────────────────────────┴──────────────────────┘
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
      {/* Left: PixiJS canvas */}
      <div style={layout.canvas}>
        <DungeonCanvas />
      </div>

      {/* Right: Dashboard panels */}
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
  canvas: {
    flex: 1,
    minWidth: 0,
    position: 'relative',
  },
  sidebar: {
    width: 260,
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    padding: 8,
    borderLeft: '1px solid #2a2a3a',
    background: '#12121a',
    overflowY: 'auto',
    scrollbarWidth: 'thin',
    scrollbarColor: '#3a3a4a transparent',
  },
};

export default Dungeon;
