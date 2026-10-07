import { useCallback, useEffect, useState } from 'react';
import { ScrollText, ShieldCheck, ShieldAlert, RefreshCw } from 'lucide-react';
import { fetchAuditLog } from '../services/api';

const ACTION_COLORS = {
  ACCESS_DENIED: '#EF4444',
  AUTH_FAILED: '#EF4444',
  AUTH_LOCKED: '#EF4444',
  PII_REVEALED: '#F59E0B',
  REPORT_EXPORTED: '#8B5CF6',
  CASE_STATUS_CHANGED: '#38BDF8',
  CASE_OPENED: '#38BDF8',
};

/**
 * Compliance-officer view of the append-only audit log. Each entry carries the hash of the
 * one before it; "Verify chain" recomputes every hash from the file on the server.
 */
export default function AuditLog() {
  const [entries, setEntries] = useState([]);
  const [integrity, setIntegrity] = useState(null);
  const [error, setError] = useState('');
  const [checkedAt, setCheckedAt] = useState(null);

  const load = useCallback(async () => {
    const res = await fetchAuditLog();
    if (!res.success) {
      setError(res.error);
      return;
    }
    setError('');
    setEntries(res.entries);
    setIntegrity(res.integrity);
    setCheckedAt(new Date());
  }, []);

  useEffect(() => {
    // Initial fetch; load() sets state when the response arrives.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  return (
    <section style={{ maxWidth: '1440px', margin: '0 auto', padding: '36px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '22px' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--accent-cyan)', fontSize: '0.74rem', fontFamily: 'var(--font-mono)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>
            <ScrollText size={14} />
            <span>Compliance officer only</span>
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>Audit Log</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px', maxWidth: '760px' }}>
            Append-only and hash-chained: every entry stores the SHA-256 hash of the previous one, so an edited or deleted line breaks the chain. No unmasked personal data is written here.
          </p>
        </div>
        <button type="button" className="btn-primary" onClick={load} style={{ padding: '8px 18px', fontSize: '0.84rem' }}>
          <RefreshCw size={14} />
          <span>Verify chain</span>
        </button>
      </div>

      {error && <div role="alert" style={{ color: '#FCA5A5', fontSize: '0.9rem', marginBottom: '16px' }}>{error}</div>}

      {integrity && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '14px 18px', borderRadius: '14px', marginBottom: '18px', background: integrity.valid ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.12)', border: `1px solid ${integrity.valid ? 'rgba(34, 197, 94, 0.35)' : 'rgba(239, 68, 68, 0.4)'}` }}>
          {integrity.valid ? <ShieldCheck size={22} color="#22C55E" /> : <ShieldAlert size={22} color="#EF4444" />}
          <div>
            <div style={{ fontWeight: 800, color: integrity.valid ? '#86EFAC' : '#FCA5A5', fontSize: '0.95rem' }}>
              {integrity.valid ? `Chain intact: ${integrity.entries} entries verified` : `Chain broken at entry ${integrity.broken_at_seq}`}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}>
              head {integrity.head_hash}{checkedAt ? ` · checked ${checkedAt.toLocaleTimeString()}` : ''}
            </div>
          </div>
        </div>
      )}

      <div className="glass-panel" style={{ borderRadius: '18px', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
              {['#', 'Time', 'Actor', 'Role', 'Action', 'Target', 'Details', 'Hash'].map((h) => (
                <th key={h} style={{ padding: '12px 14px', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.seq} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', fontSize: '0.8rem' }}>
                <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{e.seq}</td>
                <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{new Date(e.timestamp).toLocaleString()}</td>
                <td style={{ padding: '10px 14px', color: '#FFFFFF' }}>{e.actor}</td>
                <td style={{ padding: '10px 14px', color: 'var(--text-secondary)' }}>{e.role}</td>
                <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: ACTION_COLORS[e.action] || '#B8FF3D' }}>{e.action}</td>
                <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', color: '#E2E8F0' }}>{e.target || '-'}</td>
                <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', maxWidth: '320px' }}>
                  {Object.entries(e.details || {}).map(([k, v]) => `${k}: ${v}`).join(' · ') || '-'}
                </td>
                <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }} title={e.hash}>{e.hash.slice(0, 12)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
