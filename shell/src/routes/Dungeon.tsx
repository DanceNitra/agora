/**
 * Dungeon.tsx — route page: square canvas + scrollable panel sidebar.
 *
 * Layout:
 *   ┌───────────────────────┬──────────────────────────────┐
 *   │                       │  🎯 QuestBoard               │
 *   │   SQUARE CANVAS       │  ⚙️ OS Meters                │
 *   │   (height × height)   │  👤 AgentList                │
 *   │                       │  📜 LogStream (max 180px)    │
 *   └───────────────────────┴──────────────────────────────┘
 *
 * Canvas is always square (height = width), fills the full height.
 * Sidebar takes the remaining width, scrollable.
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
      {/* Left: Square canvas */}
      <div style={layout.canvasWrapper}>
        <div style={layout.canvasInner}>
          <DungeonCanvas />
        </div>
      </div>

      {/* Right: Scrollable panels */}
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
    height: '100%',
    aspectRatio: '1 / 1',
    flexShrink: 0,
    position: 'relative',
  },
  canvasInner: {
    position: 'absolute',
    inset: 0,
  },
  sidebar: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    padding: 8,
    borderLeft: '1px solid #2a2a3a',
    background: '#12121a',
    overflowY: 'auto',
    scrollbarWidth: 'thin',
    scrollbarColor: '#3a3a4a transparent',
  },
};

export default Dungeon;
