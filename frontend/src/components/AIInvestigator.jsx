import React, { useState } from 'react';
import { 
  Sparkles, 
  ShieldAlert, 
  FileCheck, 
  Download, 
  Copy, 
  Check, 
  AlertCircle, 
  ExternalLink,
  ChevronRight,
  TrendingDown
} from 'lucide-react';

export default function AIInvestigator({ selectedAccount, accounts = [], onSelectAccount }) {
  const [copied, setCopied] = useState(false);

  // If no account is explicitly selected, pick the highest risk one
  const target = selectedAccount || accounts[0];

  if (!target) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', margin: '30px auto', maxWidth: '800px' }}>
        <Sparkles size={36} color="var(--primary-neon)" style={{ margin: '0 auto 16px' }} />
        <h3 style={{ fontSize: '1.25rem', color: '#FFFFFF' }}>AI Investigator Ready</h3>
        <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
          Select an account from the network or accounts list to inspect auditable machine learning evidence.
        </p>
      </div>
    );
  }

  const evidence = target.evidence || [];
  const patterns = target.patterns || [];
  const score = target.risk_score || 0;
  const level = target.risk_level || 'LOW';

  // Construct grounded investigator recommendation based strictly on data
  const getRecommendation = () => {
    if (level === 'CRITICAL' || level === 'HIGH') {
      return 'Immediate Case Escalation Recommended: Cross-reference recipient account ownership, hold outbound clearing on rapid passthrough routes, and request originator KYC documentation for coordinated cycle participation.';
    }
    if (level === 'MEDIUM') {
      return 'Enhanced Due Diligence (EDD): Monitor 24-hour transaction velocity, verify business legitimacy of incoming peer funds, and flag further cycle layering attempts.';
    }
    return 'Routine Monitoring: Behavior conforms within standard statistical thresholds. Maintain baseline anomaly surveillance.';
  };

  const recommendation = getRecommendation();

  // Export or copy case report
  const handleCopyReport = () => {
    const reportText = `FLOWGUARD AI - TRANSACTION INTELLIGENCE CASE FILE
Generated: ${new Date().toISOString()}
Target Account: ${target.account_id}
Composite Risk Score: ${score.toFixed(1)} / 100 (${level} RISK)
Anomaly Classification: ${target.is_anomaly ? 'Isolation Forest Outlier' : 'Statistical Inlier'}
Detected Patterns: ${patterns.join(', ') || 'None'}

GROUNDED AUDIT EVIDENCE:
${evidence.map(e => `• ${e}`).join('\n')}

INVESTIGATOR RECOMMENDATION:
${recommendation}

DECOMPOSED METRICS:
- ML Anomaly Score: ${target.scoring_breakdown?.ml_component || 'N/A'}
- Graph Pattern Score: ${target.scoring_breakdown?.graph_component || 'N/A'}
- Behavioral Score: ${target.scoring_breakdown?.behavioral_component || 'N/A'}
`;
    navigator.clipboard.writeText(reportText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <section style={{ maxWidth: '1440px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '28px', flexWrap: 'wrap', gap: '16px' }}>
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
            <Sparkles size={14} color="#B8FF3D" />
            <span>MEMBER 3 EVIDENCE INFERENCE ENGINE</span>
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            AI Forensic Investigator
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
            Explainable AI diagnostic statements generated from topological cycles, velocity spikes, and Isolation Forest outliers.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={handleCopyReport} className="btn-secondary" style={{ padding: '10px 20px', fontSize: '0.86rem' }}>
            {copied ? <Check size={16} color="#22C55E" /> : <Copy size={16} />}
            <span>{copied ? 'Case File Copied!' : 'Copy Case Report'}</span>
          </button>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '24px' }}>
        {/* Left Column: Why is this network suspicious? */}
        <div className="glass-panel" style={{ padding: '32px', borderRadius: '20px', border: '1px solid rgba(184, 255, 61, 0.25)' }}>
          {/* Target Profile Bar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: '20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            marginBottom: '24px'
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                CASE SUBJECT ENTITY
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 900, fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>
                {target.account_id}
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                COMPOSITE SCORE
              </div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: 900,
                fontFamily: 'var(--font-mono)',
                color: level === 'CRITICAL' || level === 'HIGH' ? '#EF4444' : level === 'MEDIUM' ? '#F59E0B' : '#22C55E'
              }}>
                {score.toFixed(1)} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>/ 100</span>
              </div>
            </div>
          </div>

          {/* Prominent Question Headline */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <AlertCircle size={18} color="#EF4444" />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF' }}>
              Why is this network suspicious?
            </h3>
          </div>

          {/* Auditable Grounded Evidence List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '32px' }}>
            {evidence.length > 0 ? (
              evidence.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                    padding: '14px 16px',
                    borderRadius: '12px',
                    background: 'rgba(255, 255, 255, 0.025)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    borderLeft: '4px solid var(--primary-neon)'
                  }}
                >
                  <span style={{
                    color: 'var(--primary-neon)',
                    fontWeight: 900,
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.85rem'
                  }}>
                    {String(idx + 1).padStart(2, '0')}.
                  </span>
                  <span style={{ fontSize: '0.9rem', color: '#F1F5F9', lineHeight: 1.5 }}>
                    {item}
                  </span>
                </div>
              ))
            ) : (
              <div style={{ padding: '16px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '10px', color: 'var(--text-muted)' }}>
                No active anomalies detected for this entity.
              </div>
            )}
          </div>

          {/* Investigator Recommendation Card */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(99, 102, 241, 0.08))',
            borderRadius: '16px',
            padding: '20px 24px',
            border: '1px solid rgba(139, 92, 246, 0.35)',
            boxShadow: '0 0 25px rgba(139, 92, 246, 0.1)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <FileCheck size={18} color="#8B5CF6" />
              <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: '#FFFFFF', letterSpacing: '0.02em' }}>
                Investigator Recommendation
              </h4>
            </div>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
              {recommendation}
            </p>
          </div>
        </div>

        {/* Right Column: Other High Risk Cases to Inspect */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="glass-panel" style={{ padding: '24px', borderRadius: '20px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '14px' }}>
              High-Risk Accounts for Review
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {accounts.slice(0, 7).map((acc) => {
                const isSelected = acc.account_id === target.account_id;
                return (
                  <div
                    key={acc.account_id}
                    onClick={() => onSelectAccount && onSelectAccount(acc.account_id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: isSelected ? 'rgba(184, 255, 61, 0.12)' : 'rgba(255, 255, 255, 0.025)',
                      border: isSelected ? '1px solid var(--primary-neon)' : '1px solid rgba(255, 255, 255, 0.06)',
                      cursor: 'pointer',
                      transition: 'all 0.18s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.025)';
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>
                        {acc.account_id}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {acc.patterns?.length > 0 ? acc.patterns.join(', ') : 'Standard Baseline'}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span className={`badge-risk badge-risk-${acc.risk_level.toLowerCase()}`}>
                        {acc.risk_score.toFixed(1)}
                      </span>
                      <ChevronRight size={14} color="var(--text-muted)" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
