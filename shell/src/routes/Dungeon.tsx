/**
 * Dungeon.tsx — 16:9 layout with square canvas + scrollable panel sidebar.
 *
 * Layout (16:9 centered):
 *   ┌───────────────────────────────────────────────┐
 *   │ ┌──────────┐ ┌──────────────────────────────┐ │
 *   │ │          │ │  🎯 QuestBoard               │ │
 *   │ │  SQUARE  │ │  ⚙️ OS Meters                │ │
 *   │ │  CANVAS  │ │  👤 AgentList                │ │
 *   │ │  1:1     │ │  📜 LogStream (max 180px)    │ │
 *   │ │          │ │                               │ │
 *   │ └──────────┘ └──────────────────────────────┘ │
 *   └───────────────────────────────────────────────┘
 */
import React from 'react';
import DungeonCanvas from '../game/DungeonCanvas';
import QuestBoard from '../game/panels/QuestBoard';
import OsMeters from '../game/panels/OsMeters';
import AgentList from '../game/panels/AgentList';
import LogStream from '../game/panels/LogStream';

const Dungeon: React.FC = () => {
  return (
    <div style={layout.outer}>
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
    </div>
  );
};

const layout: Record<string, React.CSSProperties> = {
  outer: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#0d0d14',
    overflow: 'hidden',
  },
  container: {
    display: 'flex',
    aspectRatio: '16 / 9',
    maxWidth: '100%',
    maxHeight: '100%',
    background: '#0d0d14',
    borderRadius: 8,
    overflow: 'hidden',
    border: '1px solid #1a1a2a',
  },
  canvasWrapper: {
    flex: '0 0 auto',
    height: '100%',
    aspectRatio: '1 / 1',
    position: 'relative',
    minWidth: 0,
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
