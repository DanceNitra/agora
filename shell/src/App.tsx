import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import Timeline from './routes/Timeline';
import Graph from './routes/Graph';
import Dashboard from './routes/Dashboard';
import GodConsole from './routes/GodConsole';
import Arena from './routes/Arena';
import Artifacts from './routes/Artifacts';
import { AgentProvider } from './context/AgentContext';
import AgentDetailPanel from './components/AgentDetailPanel';
import LiveIndicator from './components/LiveIndicator';

const navItems = [
  { path: '/dashboard', label: '📊 Dashboard' },
  { path: '/timeline', label: '📜 Timeline' },
  { path: '/graph', label: '🕸️ Graph' },
  { path: '/artifacts', label: '📦 Artifacts' },
  { path: '/god-console', label: '⚡ God Console' },
  { path: '/arena', label: '🧬 Arena' },
];

const App: React.FC = () => {
  return (
    <AgentProvider>
      <div className="flex h-screen w-screen bg-gray-900 text-white">
        {/* Sidebar */}
        <aside className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
          <div className="p-4 text-lg font-bold border-b border-gray-700 flex items-center justify-between">
            <span>🏛️ Agora</span>
            <LiveIndicator />
          </div>
          <nav className="flex-1 p-2 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `block px-3 py-2 rounded-md text-sm transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* Main content area */}
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/timeline" element={<Timeline />} />
            <Route path="/graph" element={<Graph />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/god-console" element={<GodConsole />} />
            <Route path="/arena" element={<Arena />} />
            <Route path="/artifacts" element={<Artifacts />} />
          </Routes>
        </main>

        {/* Floating agent detail panel */}
        <AgentDetailPanel />
      </div>
    </AgentProvider>
  );
};

export default App;
