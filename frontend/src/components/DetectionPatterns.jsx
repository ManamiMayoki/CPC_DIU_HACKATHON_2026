import {
  Zap,
  ArrowDownLeft,
  ArrowUpRight,
  Repeat,
  GitCommit,
  Share2,
  Users,
  Layers,
  ArrowRight
} from 'lucide-react';

export default function DetectionPatterns({ patternsSummary = [], onInvestigateAccount }) {
  // Pattern icon mapping
  const getIcon = (id) => {
    switch (id) {
      case 'fan_in': return ArrowDownLeft;
      case 'fan_out': return ArrowUpRight;
      case 'rapid_movement': return Zap;
      case 'transaction_chain': return GitCommit;
      case 'circular_flow': return Repeat;
      case 'coordinated_network': return Users;
      case 'structuring': return Layers;
      default: return Share2;
    }
  };

  const getSeverityBadge = (sev) => {
    switch (sev) {
      case 'CRITICAL':
        return <span className="badge-risk badge-risk-critical">CRITICAL</span>;
      case 'HIGH':
        return <span className="badge-risk badge-risk-high">HIGH</span>;
      case 'MEDIUM':
        return <span className="badge-risk badge-risk-medium">MEDIUM</span>;
      default:
        return <span className="badge-risk badge-risk-low">LOW</span>;
    }
  };

  return (
    <section style={{ maxWidth: '1440px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Section Header */}
      <div style={{ marginBottom: '28px' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          color: 'var(--primary-neon)',
          fontSize: '0.74rem',
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: '6px'
        }}>
          <Zap size={14} color="#B8FF3D" />
          <span>MEMBER 2 TOPOLOGY ALGORITHMS</span>
        </div>
        <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
          Suspicious Transaction Patterns
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '750px', marginTop: '4px' }}>
          Algorithmic topological discovery engineered to detect multi-account layering, dispersion, rapid forwarding, 
          closed circular loops, and coordinated clusters across NetworkX graphs.
        </p>
      </div>

      {/* Grid of Detection Pattern Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
        gap: '20px'
      }}>
        {patternsSummary.map((pat) => {
          const Icon = getIcon(pat.id);
          const isDetected = pat.status === 'Detected';
          const flagged = pat.flagged_accounts || [];

          return (
            <div
              key={pat.id}
              className="glass-panel glass-panel-hover"
              style={{
                padding: '24px',
                borderRadius: '18px',
                border: isDetected ? '1px solid rgba(255, 255, 255, 0.12)' : '1px solid rgba(255, 255, 255, 0.05)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                position: 'relative'
              }}
            >
              <div>
                {/* Header: Icon, Title, Status & Severity */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: '12px',
                      background: isDetected ? 'rgba(184, 255, 61, 0.12)' : 'rgba(255, 255, 255, 0.04)',
                      border: isDetected ? '1px solid rgba(184, 255, 61, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: isDetected ? '0 0 16px rgba(184, 255, 61, 0.2)' : 'none'
                    }}>
                      <Icon size={20} color={isDetected ? 'var(--primary-neon)' : 'var(--text-muted)'} />
                    </div>

                    <div>
                      <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFFFFF' }}>
                        {pat.name}
                      </h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                        <span style={{
                          width: '7px',
                          height: '7px',
                          borderRadius: '50%',
                          background: isDetected ? '#22C55E' : '#64748B',
                          boxShadow: isDetected ? '0 0 8px #22C55E' : 'none'
                        }} />
                        <span style={{
                          fontSize: '0.74rem',
                          fontFamily: 'var(--font-mono)',
                          color: isDetected ? '#22C55E' : 'var(--text-muted)',
                          fontWeight: 600
                        }}>
                          {pat.status}
                        </span>
                      </div>
                    </div>
                  </div>

                  {getSeverityBadge(pat.severity)}
                </div>

                {/* Description */}
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '16px' }}>
                  {pat.description}
                </p>

                {/* Affected Entities Metric */}
                <div style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  marginBottom: '16px'
                }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    AFFECTED ACCOUNTS
                  </span>
                  <span style={{
                    fontSize: '1rem',
                    fontWeight: 800,
                    fontFamily: 'var(--font-mono)',
                    color: isDetected ? 'var(--primary-neon)' : '#FFFFFF'
                  }}>
                    {pat.affected_accounts_count} accounts involved
                  </span>
                </div>

                {/* Flagged Accounts Pill List */}
                {flagged.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '8px' }}>
                      CLICK ENTITY TO INVESTIGATE:
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', maxHeight: '110px', overflowY: 'auto' }}>
                      {flagged.map((accId) => (
                        <button
                          key={accId}
                          onClick={() => onInvestigateAccount && onInvestigateAccount(accId)}
                          style={{
                            background: 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            borderRadius: '6px',
                            color: '#FFFFFF',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.75rem',
                            padding: '3px 8px',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            transition: 'all 0.15s ease'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = 'var(--primary-neon)';
                            e.currentTarget.style.color = 'var(--primary-neon)';
                            e.currentTarget.style.background = 'rgba(184, 255, 61, 0.1)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                            e.currentTarget.style.color = '#FFFFFF';
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                          }}
                        >
                          <span>{accId}</span>
                          <ArrowRight size={10} />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Bottom Quick Investigate Link */}
              {flagged.length > 0 && (
                <div style={{ marginTop: '18px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <button
                    onClick={() => onInvestigateAccount && onInvestigateAccount(flagged[0])}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--primary-neon)',
                      fontSize: '0.82rem',
                      fontFamily: 'var(--font-heading)',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: 0
                    }}
                  >
                    <span>Investigate Primary Hub ({flagged[0]})</span>
                    <ArrowRight size={14} />
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
