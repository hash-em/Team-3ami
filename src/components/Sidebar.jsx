import React from 'react';
import { Shield, User, Clock, LayoutDashboard } from 'lucide-react';

const NAV = [
  { id: 'predict', label: 'New Prediction',   icon: User },
  { id: 'history', label: 'History',           icon: Clock },
  { id: 'status',  label: 'System Status',     icon: LayoutDashboard },
];

export default function Sidebar({ active, onNavigate }) {
  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-shield">
          <div className="shield-icon">
            <Shield size={20} color="#fff" strokeWidth={2} />
          </div>
          <span className="brand-name">BundleIQ</span>
        </div>
        <div className="brand-tagline">Insurance Recommender · AI</div>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Main</div>
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`nav-item ${active === id ? 'active' : ''}`}
            onClick={() => onNavigate(id)}
          >
            <Icon size={15} strokeWidth={active === id ? 2.2 : 1.8} />
            {label}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">v1.0.0 · DataQuest 2025</div>
    </aside>
  );
}
