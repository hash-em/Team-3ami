import React, { useState } from 'react';
import Sidebar    from './components/Sidebar';
import PredictPage from './pages/PredictPage';
import HistoryPage from './pages/HistoryPage';
import StatusPage  from './pages/StatusPage';

const PAGES = {
  predict: { Component: PredictPage, title: 'New Prediction' },
  history: { Component: HistoryPage, title: 'Prediction History' },
  status:  { Component: StatusPage,  title: 'System Status'      },
};

export default function App() {
  const [active, setActive] = useState('predict');
  const { Component, title } = PAGES[active] || PAGES.predict;

  return (
    <div className="app-shell">
      <Sidebar active={active} onNavigate={setActive} />

      <div className="main">
        {/* Top bar */}
        <header className="topbar">
          <span className="topbar-title">{title}</span>
          <div className="topbar-right">
            <div className="status-dot" />
            <span className="status-label">API Online</span>
          </div>
        </header>

        <main className="main-body">
          <Component />
        </main>
      </div>
    </div>
  );
}
