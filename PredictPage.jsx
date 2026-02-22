import React, { useState } from 'react';
import { Zap, User, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import { predictSingle } from '../services/api';
import { BundleChip, getBundle } from '../utils/bundles';

// ── Field definitions grouped by section ──────────────────
const SECTIONS = [
  {
    title: 'Demographics & Financials',
    fields: [
      { name: 'User_ID',                label: 'User ID',               type: 'text',   ph: 'USR_000001' },
      { name: 'Estimated_Annual_Income', label: 'Annual Income (USD)',   type: 'number', ph: '60000' },
      { name: 'Employment_Status',      label: 'Employment Status',     type: 'select',
        opts: ['Employed', 'Self-Employed', 'Unemployed', 'Retired', 'Student'] },
      { name: 'Region_Code',            label: 'Region Code',           type: 'text',   ph: 'R01' },
      { name: 'Adult_Dependents',       label: 'Adult Dependents',      type: 'number', ph: '1' },
      { name: 'Child_Dependents',       label: 'Child Dependents',      type: 'number', ph: '0' },
      { name: 'Infant_Dependents',      label: 'Infant Dependents',     type: 'number', ph: '0' },
    ],
  },
  {
    title: 'Risk Profile & History',
    fields: [
      { name: 'Existing_Policyholder',         label: 'Existing Policyholder',         type: 'select', opts: ['0','1'] },
      { name: 'Previous_Claims_Filed',         label: 'Previous Claims Filed',         type: 'number', ph: '0' },
      { name: 'Years_Without_Claims',          label: 'Years Without Claims',          type: 'number', ph: '3' },
      { name: 'Previous_Policy_Duration_Months', label: 'Prior Policy Duration (mo)',  type: 'number', ph: '12' },
      { name: 'Policy_Cancelled_Post_Purchase', label: 'Policy Cancelled Post-Purchase', type: 'select', opts: ['0','1'] },
    ],
  },
  {
    title: 'Policy Preferences',
    fields: [
      { name: 'Deductible_Tier',         label: 'Deductible Tier',          type: 'select', opts: ['Low','Medium','High'] },
      { name: 'Payment_Schedule',        label: 'Payment Schedule',         type: 'select', opts: ['Monthly','Quarterly','Annual'] },
      { name: 'Vehicles_on_Policy',      label: 'Vehicles on Policy',       type: 'number', ph: '1' },
      { name: 'Custom_Riders_Requested', label: 'Custom Riders Requested',  type: 'number', ph: '0' },
      { name: 'Grace_Period_Extensions', label: 'Grace Period Extensions',  type: 'number', ph: '0' },
    ],
  },
  {
    title: 'Broker & Acquisition',
    fields: [
      { name: 'Broker_Agency_Type', label: 'Broker Agency Type',  type: 'select', opts: ['Independent','Captive','Online','Direct'] },
      { name: 'Acquisition_Channel', label: 'Acquisition Channel', type: 'select', opts: ['Referral','Online','Agent','Broker','Direct Mail'] },
    ],
  },
];

const DEFAULTS = SECTIONS.flatMap(s => s.fields).reduce((acc, f) => {
  acc[f.name] = f.opts ? f.opts[0] : '';
  return acc;
}, {});

// ── Component ──────────────────────────────────────────────
export default function PredictPage() {
  const [form,    setForm]    = useState(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState(null);
  const [error,   setError]   = useState(null);

  const handleChange = (e) =>
    setForm(p => ({ ...p, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await predictSingle(form);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Prediction failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => { setForm(DEFAULTS); setResult(null); setError(null); };

  const bundle = result?.prediction?.Purchased_Coverage_Bundle;
  const bInfo  = bundle != null ? getBundle(bundle) : null;

  return (
    <div className="fade-up">
      <div className="page-header">
        <h1 className="page-title">New Prediction</h1>
        <p className="page-sub">Enter client details to receive an insurance bundle recommendation</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 28, alignItems: 'start' }}>

        {/* ── Form ── */}
        <form onSubmit={handleSubmit}>
          {SECTIONS.map(({ title, fields }) => (
            <div className="card" key={title} style={{ marginBottom: 20 }}>
              <div className="form-section-title">{title}</div>
              <div className="form-grid">
                {fields.map(f => (
                  <div className="field" key={f.name}>
                    <label htmlFor={f.name}>{f.label}</label>
                    {f.type === 'select' ? (
                      <select id={f.name} name={f.name} value={form[f.name]} onChange={handleChange}>
                        {f.opts.map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : (
                      <input
                        id={f.name}
                        name={f.name}
                        type={f.type}
                        value={form[f.name]}
                        onChange={handleChange}
                        placeholder={f.ph}
                        min={f.type === 'number' ? 0 : undefined}
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          {error && (
            <div className="alert alert-error" style={{ marginBottom: 16 }}>
              <AlertCircle size={15} />{error}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12 }}>
            <button type="submit" className="btn btn-primary" disabled={loading}
              style={{ flex: 1, justifyContent: 'center', padding: 14 }}>
              {loading
                ? <><div className="spinner" /> Analysing…</>
                : <><Zap size={16} /> Predict Bundle</>}
            </button>
            <button type="button" className="btn btn-ghost" onClick={handleReset}>
              <RefreshCw size={15} /> Reset
            </button>
          </div>
        </form>

        {/* ── Result Panel ── */}
        <div className="result-panel">
          <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'rgba(255,255,255,0.35)',
            textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 16 }}>
            Recommendation
          </div>

          {!result && !loading && (
            <div className="result-empty">
              <User size={40} style={{ display: 'block', margin: '0 auto 12px' }} />
              <div style={{ fontSize: 13 }}>Awaiting client data</div>
            </div>
          )}

          {loading && (
            <div style={{ textAlign: 'center', padding: '48px 0' }}>
              <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3, margin: '0 auto 14px' }} />
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)' }}>Processing…</div>
            </div>
          )}

          {result && bInfo && (
            <div key={bundle}>
              {/* Big bundle circle */}
              <div
                className="bundle-circle"
                style={{ background: bInfo.color + '22', borderColor: bInfo.color + '66', color: bInfo.color }}
              >
                {bundle}
              </div>
              <div className="bundle-name">{bInfo.label}</div>
              <div className="bundle-sub">{bInfo.tier} Tier · Bundle {bundle}</div>

              {/* Meta */}
              <div className="result-meta">
                {[
                  ['Client',    result.prediction.User_ID],
                  ['Latency',   `${result.durationMs} ms`],
                  ['Session ID', result.historyId?.slice(0, 8) + '…'],
                ].map(([k, v]) => (
                  <div className="result-meta-row" key={k}>
                    <span className="key">{k}</span>
                    <span className="val" style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{v}</span>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 16 }}>
                <div className="alert alert-success" style={{
                  background: 'rgba(22,163,74,0.15)', border: '1px solid rgba(22,163,74,0.3)', color: '#4ade80'
                }}>
                  <CheckCircle size={14} /> Prediction complete
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
