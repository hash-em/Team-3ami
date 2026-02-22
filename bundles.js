export const BUNDLES = [
  { label: 'Basic Starter',  color: '#64748b', bg: '#f1f5f9', tier: 'Entry'    },
  { label: 'Basic Plus',     color: '#0ea5e9', bg: '#e0f2fe', tier: 'Entry'    },
  { label: 'Essential',      color: '#2563eb', bg: '#dbeafe', tier: 'Standard' },
  { label: 'Standard',       color: '#1d4ed8', bg: '#dbeafe', tier: 'Standard' },
  { label: 'Standard Pro',   color: '#7c3aed', bg: '#ede9fe', tier: 'Standard' },
  { label: 'Premium',        color: '#b45309', bg: '#fef3c7', tier: 'Premium'  },
  { label: 'Premium Plus',   color: '#d97706', bg: '#fef9c3', tier: 'Premium'  },
  { label: 'Elite',          color: '#b91c1c', bg: '#fee2e2', tier: 'Elite'    },
  { label: 'Elite Max',      color: '#9d174d', bg: '#fce7f3', tier: 'Elite'    },
  { label: 'Platinum',       color: '#0b1f3a', bg: '#e8f1fb', tier: 'Platinum' },
];

export const getBundle = (n) => BUNDLES[n] ?? BUNDLES[0];

export function BundleChip({ value }) {
  const b = getBundle(value);
  return (
    <span
      className="bundle-chip"
      style={{ background: b.bg, color: b.color }}
    >
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: b.color, display: 'inline-block', flexShrink: 0,
      }} />
      {value} · {b.label}
    </span>
  );
}
