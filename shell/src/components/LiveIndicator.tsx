import React from 'react';
import { useAgent } from '../context/AgentContext';

const LiveIndicator: React.FC = () => {
  const { wsConnected, liveAgents } = useAgent();

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%',
        background: wsConnected ? '#22c55e' : '#ef4444',
        display: 'inline-block',
        boxShadow: wsConnected
          ? '0 0 6px rgba(34,197,94,0.6)'
          : '0 0 6px rgba(239,68,68,0.4)',
      }} />
      <span style={{ fontSize: 11, color: '#6b7280' }}>
        {wsConnected ? `${liveAgents.length} agents` : 'offline'}
      </span>
    </div>
  );
};

export default LiveIndicator;
