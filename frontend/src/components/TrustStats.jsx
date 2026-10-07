import {
  Activity,
  Users,
  Network,
  AlertTriangle,
  Zap,
  TrendingUp,
  ShieldAlert
} from 'lucide-react';

export default function TrustStats({ stats }) {
  const statItems = [
    {
      id: 'transactions',
      label: 'Transactions Analyzed',
      value: (stats?.total_transactions ?? 0).toLocaleString(),
      subtext: 'Synthetic & peer-to-peer volume',
      icon: Activity,
      color: '#B8FF3D',
      badge: 'LIVE INGESTION',
    },
    {
      id: 'accounts',
      label: 'Accounts Monitored',
      value: stats?.total_accounts ?? 0,
      subtext: 'Entities in active graph topology',
      icon: Users,
      color: '#38BDF8',
      badge: 'DIRECTED NODES',
    },
    {
      id: 'networks',
      label: 'Suspicious Networks',
      value: stats?.suspicious_networks ?? 0,
      subtext: 'Strongly connected & cycle groups',
      icon: Network,
      color: '#8B5CF6',
      badge: 'TOPOLOGY CLUSTERS',
    },
    {
      id: 'high-risk',
      label: 'Elevated Risk Accounts',
      value: (stats?.high_risk_accounts ?? 0) + (stats?.medium_risk_accounts ?? 0),
      subtext: `${stats?.high_risk_accounts ?? 0} High/Critical / ${stats?.medium_risk_accounts ?? 0} Medium`,
      icon: AlertTriangle,
      color: '#EF4444',
      badge: 'FLAGGED ENTITIES',
    },
    {
      id: 'patterns',
      label: 'Detection Patterns',
      value: `${stats?.active_detection_patterns ?? 0} / 7`,
      subtext: 'Fan-In, Fan-Out, Rapid, Chains, Cycles, Structuring, Clusters',
      icon: Zap,
      color: '#F59E0B',
      badge: 'MEMBER 2 ALGORITHMS',
    },
    {
      id: 'avg-risk',
      label: 'Average Risk Score',
      value: stats?.average_risk_score != null ? stats.average_risk_score.toFixed(1) : '0.0',
      subtext: '0–100 Explainable Composite scale',
      icon: TrendingUp,
      color: '#A855F7',
      badge: 'ISOLATION FOREST + GRAPH',
    },
  ];

  return (
    <section style={{
      maxWidth: '1360px',
      margin: '0 auto',
      padding: '40px 24px',
      position: 'relative'
    }}>
      {/* Section Header */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        marginBottom: '28px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        paddingBottom: '16px'
      }}>
        <div>
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
            <ShieldAlert size={14} color="#B8FF3D" />
            <span>REAL-TIME PIPELINE METRICS</span>
          </div>
          <h2 style={{
            fontSize: '1.85rem',
            fontWeight: 800,
            color: '#FFFFFF',
            letterSpacing: '-0.02em'
          }}>
            Financial Network Intelligence
          </h2>
        </div>

        <div style={{
          fontSize: '0.82rem',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
          textAlign: 'right'
        }}>
          Direct Grounding • <span style={{ color: '#22C55E' }}>Zero Hallucinations</span>
        </div>
      </div>

      {/* Grid of 6 Statistics Cards (AgroTrade inspired) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px'
      }}>
        {statItems.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.id}
              className="glass-panel glass-panel-hover"
              style={{
                padding: '22px 20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                position: 'relative',
                overflow: 'hidden',
                borderRadius: '16px',
                border: '1px solid rgba(255, 255, 255, 0.07)'
              }}
            >
              {/* Subtle top color bar */}
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '3px',
                background: `linear-gradient(90deg, ${item.color}, transparent)`
              }} />

              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '10px',
                    background: `${item.color}18`,
                    border: `1px solid ${item.color}40`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Icon size={18} color={item.color} />
                  </div>

                  <span style={{
                    fontSize: '0.62rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-muted)',
                    background: 'rgba(255, 255, 255, 0.04)',
                    padding: '3px 8px',
                    borderRadius: '6px',
                    border: '1px solid rgba(255, 255, 255, 0.06)'
                  }}>
                    {item.badge}
                  </span>
                </div>

                <div style={{
                  fontSize: '2.2rem',
                  fontWeight: 900,
                  fontFamily: 'var(--font-heading)',
                  color: '#FFFFFF',
                  lineHeight: 1.1,
                  marginBottom: '4px'
                }}>
                  {item.value}
                </div>

                <div style={{
                  fontSize: '0.88rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  marginBottom: '4px'
                }}>
                  {item.label}
                </div>
              </div>

              <div style={{
                fontSize: '0.74rem',
                color: 'var(--text-muted)',
                lineHeight: 1.4,
                marginTop: '10px',
                paddingTop: '8px',
                borderTop: '1px solid rgba(255, 255, 255, 0.05)'
              }}>
                {item.subtext}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
