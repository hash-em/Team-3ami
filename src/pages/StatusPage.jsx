import React, { useEffect, useState } from 'react';
import { RefreshCw, CheckCircle, AlertCircle, Server, Cpu, HardDrive, Clock } from 'lucide-react';
import { fetchHealth } from '../services/api';

export default function StatusPage() {
  const [health,  setHealth]  = useState(null);
  const [error,   setError]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const h = await fetchHealth();
      setHealth(h);
      setLastRefresh(new Date());
    } catch {
      setError('Cannot reach the API. Make sure the Node.js server is running on port 3001.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="fade-up">
      <div className="page-header" style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
        <div>
          <h1 className="page-title">System Status</h1>
          <p className="page-sub">
            Live health data from <code style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--blue)' }}>GET /api/health</code>
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={13} style={{ animation: loading ? 'spin 0.8s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: 24 }}>
          <AlertCircle size={15} />{error}
        </div>
      )}

      {!health && !error && (
        <div style={{ textAlign:'center', padding:'80px 0', color:'var(--text-3)' }}>
          <div className="spinner spinner-blue" style={{ width:32, height:32, margin:'0 auto 16px' }} />
          <div style={{ fontSize:13 }}>Checking API health…</div>
        </div>
      )}

      {health && (
        <>
          {/* Overall status banner */}
          <div style={{
            background: health.status === 'ok' ? 'var(--green-light)' : 'var(--rose-light)',
            border: `1px solid ${health.status === 'ok' ? 'rgba(22,163,74,0.25)' : 'rgba(220,38,38,0.25)'}`,
            borderRadius: 'var(--r-lg)',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginBottom: 24,
          }}>
            {health.status === 'ok'
              ? <CheckCircle size={20} color="var(--green)" />
              : <AlertCircle size={20} color="var(--rose)" />}
            <div>
              <div style={{ fontWeight:600, color: health.status === 'ok' ? 'var(--green)' : 'var(--rose)' }}>
                {health.status === 'ok' ? 'All systems operational' : 'Service degraded'}
              </div>
              <div style={{ fontSize:12, color:'var(--text-3)', fontFamily:'var(--font-mono)', marginTop:2 }}>
                {health.service} · v{health.version} · {health.timestamp}
              </div>
            </div>
            {lastRefresh && (
              <div style={{ marginLeft:'auto', fontSize:11, fontFamily:'var(--font-mono)', color:'var(--text-3)' }}>
                Refreshed {lastRefresh.toLocaleTimeString()}
              </div>
            )}
          </div>

          {/* Metric cards */}
          <div className="stats-row" style={{ marginBottom: 24 }}>
            <MetricCard icon={<Clock size={18} />} label="Uptime" value={health.uptime?.human} />
            <MetricCard icon={<HardDrive size={18} />} label="Heap Used" value={health.memory?.heapUsed} />
            <MetricCard icon={<HardDrive size={18} />} label="Heap Total" value={health.memory?.heapTotal} />
            <MetricCard icon={<Cpu size={18} />} label="Free Memory" value={health.system?.freeMemory} />
            <MetricCard icon={<Server size={18} />} label="CPU Cores" value={health.system?.cpus} />
          </div>

          {/* Model connection */}
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-title" style={{ marginBottom: 16 }}>Model Service</div>
            <div style={{ display:'flex', alignItems:'center', gap:14 }}>
              <div style={{
                width: 42, height: 42, borderRadius: 'var(--r)',
                background: health.model?.status === 'connected' ? 'var(--green-light)' : 'var(--gold-light)',
                display:'flex', alignItems:'center', justifyContent:'center',
                color: health.model?.status === 'connected' ? 'var(--green)' : 'var(--gold)',
              }}>
                <Server size={18} />
              </div>
              <div>
                <div style={{ fontWeight:600, fontSize:14, marginBottom:3 }}>
                  {health.model?.status === 'connected' ? 'Python Model Connected' : 'Demo Mode (Mock Predictions)'}
                </div>
                <div style={{ fontSize:12, color:'var(--text-3)', fontFamily:'var(--font-mono)' }}>
                  {health.model?.endpoint}
                </div>
              </div>
            </div>
            {health.model?.status !== 'connected' && (
              <div className="alert alert-info" style={{ marginTop: 16 }}>
                <AlertCircle size={14} />
                Set <code style={{ fontFamily:'var(--font-mono)' }}>PYTHON_API_URL</code> in <code style={{ fontFamily:'var(--font-mono)' }}>api/.env</code> to connect your trained model.
              </div>
            )}
          </div>

          {/* Endpoint reference */}
          <div className="card">
            <div className="card-title" style={{ marginBottom: 16 }}>API Endpoints</div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Method</th><th>Path</th><th>Description</th></tr>
                </thead>
                <tbody>
                  {[
                    ['GET',  '/api/health',         'Service health, uptime, memory, model status'],
                    ['POST', '/api/predict-single', 'Single client JSON → bundle recommendation'],
                    ['GET',  '/api/history',         'Paginated prediction history + summary stats'],
                    ['GET',  '/api/history/:id',     'Full detail for a single prediction entry'],
                  ].map(([method, path, desc]) => (
                    <tr key={path}>
                      <td>
                        <span style={{
                          padding:'2px 9px', borderRadius:4,
                          fontSize:11, fontWeight:600, fontFamily:'var(--font-mono)',
                          background: method === 'GET' ? 'var(--green-light)' : 'var(--gold-light)',
                          color:      method === 'GET' ? 'var(--green)'       : 'var(--gold)',
                        }}>{method}</span>
                      </td>
                      <td style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--blue)' }}>{path}</td>
                      <td style={{ fontSize:12, color:'var(--text-2)' }}>{desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({ icon, label, value }) {
  return (
    <div className="stat-card">
      <div style={{ color:'var(--blue)', marginBottom:8 }}>{icon}</div>
      <div className="stat-label">{label}</div>
      <div style={{ fontSize:16, fontWeight:600, color:'var(--navy)', fontFamily:'var(--font-mono)' }}>{value}</div>
    </div>
  );
}
