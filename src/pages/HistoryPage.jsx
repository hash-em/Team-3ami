import React, { useEffect, useState, useCallback } from 'react';
import { Clock, X, RefreshCw, AlertCircle, ChevronRight } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { fetchHistory, fetchHistoryEntry } from '../services/api';
import { BundleChip, getBundle, BUNDLES } from '../utils/bundles';

export default function HistoryPage() {
  const [data,    setData]    = useState(null);
  const [error,   setError]   = useState(null);
  const [page,    setPage]    = useState(1);
  const [drawer,  setDrawer]  = useState(null);   // full entry shown in side drawer
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (p = 1) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchHistory(p, 15);
      setData(res);
      setPage(p);
    } catch {
      setError('Could not load history — is the API running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(1); }, [load]);

  const openDrawer = async (id) => {
    const entry = await fetchHistoryEntry(id).catch(() => null);
    setDrawer(entry);
  };

  // Build chart data from summary
  const chartData = data?.summary
    ? Object.entries(data.summary.bundleDistribution)
        .sort((a, b) => parseInt(a[0]) - parseInt(b[0]))
        .map(([bundle, count]) => ({
          name: `B${bundle}`,
          count,
          bundle: parseInt(bundle),
        }))
    : [];

  return (
    <div className="fade-up">
      <div className="page-header" style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
        <div>
          <h1 className="page-title">Prediction History</h1>
          <p className="page-sub">All past single-client predictions, with bundle distribution analytics</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => load(page)} disabled={loading}>
          <RefreshCw size={13} className={loading ? 'spin-anim' : ''} /> Refresh
        </button>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 24 }}><AlertCircle size={15} />{error}</div>}

      {/* ── Stats row ── */}
      {data && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-label">Total Predictions</div>
            <div className="stat-value blue">{data.summary.total.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Most Common Bundle</div>
            <div className="stat-value gold">
              {data.summary.mostCommon != null
                ? `${data.summary.mostCommon} · ${getBundle(parseInt(data.summary.mostCommon)).label}`
                : '—'}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Unique Bundles Seen</div>
            <div className="stat-value">{Object.keys(data.summary.bundleDistribution).length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">This Page</div>
            <div className="stat-value">{data.data.length}</div>
          </div>
        </div>
      )}

      {/* ── Chart + Table ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 24, alignItems: 'start' }}>

        {/* Bar chart */}
        <div className="card" style={{ padding: '22px 16px' }}>
          <div className="card-title" style={{ paddingLeft: 8, marginBottom: 16 }}>Bundle Distribution</div>
          {chartData.length === 0
            ? <div style={{ textAlign:'center', padding:'40px 0', color:'var(--text-3)', fontSize:13 }}>No data yet</div>
            : (
              <ResponsiveContainer width="100%" height={230}>
                <BarChart data={chartData} margin={{ top: 0, right: 8, bottom: 0, left: -20 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'var(--font-mono)', fill: 'var(--text-3)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fontFamily: 'var(--font-mono)', fill: 'var(--text-3)' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:8, fontSize:12 }}
                    formatter={(v, _, p) => [v, `${getBundle(p.payload.bundle).label}`]}
                    cursor={{ fill: 'var(--ice)' }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {chartData.map(d => (
                      <Cell key={d.bundle} fill={getBundle(d.bundle).color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )
          }
        </div>

        {/* Table */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border)', background: 'var(--surface2)' }}>
            <span className="card-title">Recent Predictions</span>
          </div>

          {loading && !data && (
            <div style={{ padding: 40, textAlign:'center' }}>
              <div className="spinner spinner-blue" style={{ width:28, height:28, margin:'0 auto' }} />
            </div>
          )}

          {data?.data.length === 0 && (
            <div style={{ padding: '60px 24px', textAlign:'center', color:'var(--text-3)' }}>
              <Clock size={32} style={{ margin:'0 auto 12px', display:'block', opacity:0.3 }} />
              <div style={{ fontSize: 13 }}>No predictions yet. Run one from <em>New Prediction</em>.</div>
            </div>
          )}

          {data && data.data.length > 0 && (
            <div className="table-wrap" style={{ borderRadius: 0, border: 'none' }}>
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Client ID</th>
                    <th>Bundle</th>
                    <th>Latency</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map(entry => (
                    <tr key={entry.id} style={{ cursor: 'pointer' }} onClick={() => openDrawer(entry.id)}>
                      <td style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-3)', whiteSpace:'nowrap' }}>
                        {new Date(entry.timestamp).toLocaleString()}
                      </td>
                      <td style={{ fontFamily:'var(--font-mono)', fontSize:12 }}>
                        {entry.prediction.User_ID}
                      </td>
                      <td><BundleChip value={entry.prediction.Purchased_Coverage_Bundle} /></td>
                      <td style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-3)' }}>
                        {entry.durationMs} ms
                      </td>
                      <td style={{ textAlign:'right', paddingRight: 16 }}>
                        <ChevronRight size={14} color="var(--text-3)" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div style={{ padding:'14px 24px', borderTop:'1px solid var(--border)', display:'flex', gap:8, alignItems:'center' }}>
              <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => load(page - 1)}>← Prev</button>
              <span style={{ fontSize:12, fontFamily:'var(--font-mono)', color:'var(--text-3)', flex:1, textAlign:'center' }}>
                Page {page} of {data.pages}
              </span>
              <button className="btn btn-ghost btn-sm" disabled={page >= data.pages} onClick={() => load(page + 1)}>Next →</button>
            </div>
          )}
        </div>
      </div>

      {/* ── Detail Drawer ── */}
      {drawer && (
        <div className="drawer-overlay" onClick={() => setDrawer(null)}>
          <div className="drawer" onClick={e => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <div style={{ fontSize:13, fontWeight:600, color:'var(--navy)' }}>Prediction Detail</div>
                <div style={{ fontSize:10, fontFamily:'var(--font-mono)', color:'var(--text-3)', marginTop:2 }}>{drawer.id}</div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => setDrawer(null)}>
                <X size={14} />
              </button>
            </div>

            <div className="drawer-body">
              {/* Result summary */}
              <div style={{ background:'var(--navy)', borderRadius:'var(--r-lg)', padding:'20px 24px', marginBottom:20, textAlign:'center' }}>
                <div style={{
                  width:60, height:60, borderRadius:'50%', margin:'0 auto 12px',
                  display:'flex', alignItems:'center', justifyContent:'center',
                  fontSize:24, fontWeight:700, fontFamily:'var(--font-serif)',
                  background: getBundle(drawer.prediction.Purchased_Coverage_Bundle).color + '22',
                  color: getBundle(drawer.prediction.Purchased_Coverage_Bundle).color,
                  border: `2px solid ${getBundle(drawer.prediction.Purchased_Coverage_Bundle).color}55`,
                }}>
                  {drawer.prediction.Purchased_Coverage_Bundle}
                </div>
                <div style={{ color:'#fff', fontFamily:'var(--font-serif)', fontSize:18 }}>
                  {getBundle(drawer.prediction.Purchased_Coverage_Bundle).label}
                </div>
                <div style={{ fontSize:11, color:'rgba(255,255,255,0.35)', fontFamily:'var(--font-mono)', marginTop:4 }}>
                  {new Date(drawer.timestamp).toLocaleString()} · {drawer.durationMs}ms
                </div>
              </div>

              {/* Input snapshot */}
              <div style={{ fontSize:11, fontFamily:'var(--font-mono)', color:'var(--text-3)',
                textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:12 }}>
                Client Data Snapshot
              </div>

              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
                {Object.entries(drawer.clientData)
                  .filter(([k]) => k !== 'User_ID')
                  .map(([key, val]) => (
                    <div key={key} style={{ background:'var(--surface2)', border:'1px solid var(--border)',
                      borderRadius:'var(--r)', padding:'8px 12px' }}>
                      <div style={{ fontSize:9, fontFamily:'var(--font-mono)', color:'var(--text-3)',
                        textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:3 }}>
                        {key.replace(/_/g, ' ')}
                      </div>
                      <div style={{ fontSize:12, fontWeight:500, color:'var(--text-1)' }}>
                        {val || <span style={{ color:'var(--text-3)' }}>—</span>}
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
