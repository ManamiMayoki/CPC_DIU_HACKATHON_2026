import { useState } from 'react';
import { Search, ArrowRight, ShieldAlert } from 'lucide-react';

export default function HighRiskAccounts({ accounts = [], onInvestigateAccount }) {
  const [filterTier, setFilterTier] = useState('ALL'); // ALL, CRITICAL, HIGH, MEDIUM, LOW
  const [searchTerm, setSearchTerm] = useState('');

  // Filter accounts
  const filtered = accounts.filter((acc) => {
    const matchesTier = filterTier === 'ALL' || acc.risk_level === filterTier;
    const matchesSearch = !searchTerm || acc.account_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesTier && matchesSearch;
  });

  return (
    <section style={{ maxWidth: '1440px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            color: 'var(--risk-high)',
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: '6px'
          }}>
            <ShieldAlert size={14} color="#EF4444" />
            <span>MEMBER 3 POPULATION-CALIBRATED TIERS</span>
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            Elevated Risk Accounts
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
            Rank-ordered directory of entities prioritized by the multi-signal composite score (ML + Graph + Behavioral).
          </p>
        </div>

        {/* Filter & Search Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Risk Tier Buttons */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'rgba(255, 255, 255, 0.04)',
            padding: '3px',
            borderRadius: '9999px',
            border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((tier) => (
              <button
                key={tier}
                onClick={() => setFilterTier(tier)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '9999px',
                  border: 'none',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                  background: filterTier === tier ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                  color: filterTier === tier ? '#FFFFFF' : 'var(--text-secondary)',
                  fontWeight: filterTier === tier ? 700 : 500,
                  transition: 'all 0.15s ease'
                }}
              >
                {tier}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div style={{ position: 'relative' }}>
            <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Filter Account ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-fintech"
              style={{ width: '180px', padding: '6px 14px 6px 32px', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}
            />
          </div>
        </div>
      </div>

      {/* Table Container */}
      <div className="glass-panel" style={{ borderRadius: '18px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>ACCOUNT ID</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>RISK SCORE</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>RISK LEVEL</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>DETECTED PATTERNS</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>TRANSACTIONS</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>FINANCIAL FLOW</th>
              <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 30).map((acc) => {
              const patterns = acc.patterns || [];
              const mlFeats = acc.ml_features || {};
              const inAmount = mlFeats.total_incoming || 0;
              const outAmount = mlFeats.total_outgoing || 0;

              return (
                <tr
                  key={acc.account_id}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  {/* Account ID */}
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#FFFFFF', fontSize: '0.9rem' }}>
                      {acc.account_id}
                    </span>
                  </td>

                  {/* Risk Score */}
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 800,
                      fontSize: '1rem',
                      color: acc.risk_level === 'CRITICAL' ? '#DC2626' :
                        acc.risk_level === 'HIGH' ? '#EF4444' :
                        acc.risk_level === 'MEDIUM' ? '#F59E0B' : '#22C55E'
                    }}>
                      {acc.risk_score.toFixed(1)}
                    </span>
                  </td>

                  {/* Risk Level Badge */}
                  <td style={{ padding: '14px 20px' }}>
                    <span className={`badge-risk badge-risk-${acc.risk_level.toLowerCase()}`}>
                      {acc.risk_level}
                    </span>
                  </td>

                  {/* Detected Patterns */}
                  <td style={{ padding: '14px 20px' }}>
                    {patterns.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {patterns.map((p) => (
                          <span
                            key={p}
                            style={{
                              background: 'rgba(245, 158, 11, 0.15)',
                              color: '#F59E0B',
                              fontSize: '0.68rem',
                              fontFamily: 'var(--font-mono)',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontWeight: 600
                            }}
                          >
                            {p.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Standard</span>
                    )}
                  </td>

                  {/* Transactions Count */}
                  <td style={{ padding: '14px 20px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {mlFeats.transaction_count || 1} transfers
                  </td>

                  {/* Financial Flow */}
                  <td style={{ padding: '14px 20px', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                    <span style={{ color: '#22C55E' }}>+৳{inAmount.toLocaleString()}</span>
                    <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>/</span>
                    <span style={{ color: '#EF4444' }}>-৳{outAmount.toLocaleString()}</span>
                  </td>

                  {/* Action */}
                  <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                    <button
                      onClick={() => onInvestigateAccount && onInvestigateAccount(acc.account_id)}
                      className="btn-primary"
                      style={{ padding: '6px 14px', fontSize: '0.78rem' }}
                    >
                      <span>Investigate</span>
                      <ArrowRight size={13} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
