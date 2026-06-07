/**
 * Dungeon.tsx — route page: canvas left, LogStream right.
 */
import React from 'react';
import DungeonCanvas from '../game/DungeonCanvas';
import LogStream from '../game/panels/LogStream';

const Dungeon: React.FC = () => {
  return (
    <div style={layout.container}>
      <div style={layout.canvasWrapper}>
        <DungeonCanvas />
      </div>
      <div style={layout.sidebar}>
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
    width: 320,
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    borderLeft: '1px solid #2a2a3a',
    background: '#12121a',
  },
};

export default Dungeon;
