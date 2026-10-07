import { useState } from 'react';
import {
  Sparkles,
  FileCheck,
  Copy,
  Check,
  AlertCircle,
  ChevronRight,
  ListChecks,
  Loader2,
  Link2,
  Info
} from 'lucide-react';
import { fetchInvestigation } from '../services/api';

export default function AIInvestigator({ selectedAccount, accounts = [], onSelectAccount }) {
  const [copied, setCopied] = useState(false);
  // Claude narratives fetched this session, keyed by account id
  const [narratives, setNarratives] = useState({});
  const [loadingId, setLoadingId] = useState(null);

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

  // Fallback for data produced before briefings existed: tier-based guidance only
  const getTierRecommendation = () => {
    if (level === 'CRITICAL' || level === 'HIGH') {
      return 'Escalate for priority review: verify the KYC of linked wallets and review the detected patterns before deciding on a hold or an STR.';
    }
    if (level === 'MEDIUM') {
      return 'Enhanced due diligence: monitor the account and review again if similar activity repeats.';
    }
    return 'Routine monitoring: no network pattern needs action.';
  };

  const fetched = narratives[target.account_id];
  const briefing = fetched?.investigation || target.investigation || null;
  const source = briefing?.generated_by === 'claude' ? 'claude' : 'rule-based';
  const findings = briefing?.key_findings?.length ? briefing.key_findings : evidence;
  const nextSteps = briefing?.next_steps?.length ? briefing.next_steps : [getTierRecommendation()];
  const related = briefing?.related_accounts || [];
  const knownIds = new Set(accounts.map((a) => a.account_id));
  const isLoading = loadingId === target.account_id;

  const handleGenerateNarrative = async () => {
    const accountId = target.account_id;
    setLoadingId(accountId);
    const res = await fetchInvestigation(accountId);
    setNarratives((prev) => ({
      ...prev,
      [accountId]: res.success
        ? { investigation: res.investigation, note: res.note }
        : { investigation: null, note: res.error },
    }));
    setLoadingId(null);
  };

  // Export or copy case report
  const handleCopyReport = () => {
    const reportText = `CYGNUS AI - TRANSACTION INTELLIGENCE CASE FILE
Generated: ${new Date().toISOString()}
Target Account: ${target.account_id}
Composite Risk Score: ${score.toFixed(1)} / 100 (${level} RISK)
Typology: ${briefing?.typology || 'Not assessed'}
Anomaly Classification: ${target.is_anomaly ? 'Isolation Forest Outlier' : 'Statistical Inlier'}
Detected Patterns: ${patterns.join(', ') || 'None'}
Briefing Source: ${source === 'claude' ? 'Claude narrative grounded in pipeline evidence' : 'Rule-based, built from pipeline evidence'}

SUMMARY:
${briefing?.summary || 'No briefing available.'}

KEY FINDINGS:
${findings.map(e => `- ${e}`).join('\n')}

RECOMMENDED NEXT STEPS:
${nextSteps.map((e, i) => `${i + 1}. ${e}`).join('\n')}

LINKED ACCOUNTS: ${related.join(', ') || 'None'}

DECOMPOSED METRICS:
- ML Anomaly Score: ${target.scoring_breakdown?.ml_component ?? 'N/A'}
- Graph Pattern Score: ${target.scoring_breakdown?.graph_component ?? 'N/A'}
- Behavioral Score: ${target.scoring_breakdown?.behavioral_component ?? 'N/A'}

NOTE: ${briefing?.caveat || 'Risk indicators for prioritisation, not proof of wrongdoing.'}
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
            <span>EVIDENCE-GROUNDED CASE BRIEFING</span>
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            AI Forensic Investigator
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
            Every finding and next step below is built from this account's detected patterns, transaction metrics and Isolation Forest score.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <button
            onClick={handleGenerateNarrative}
            disabled={isLoading}
            className="btn-primary"
            style={{ padding: '10px 20px', fontSize: '0.86rem', opacity: isLoading ? 0.7 : 1 }}
          >
            {isLoading ? <Loader2 size={16} className="spin" /> : <Sparkles size={16} />}
            <span>{isLoading ? 'Writing narrative...' : 'Generate AI Narrative'}</span>
          </button>
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
              {briefing?.typology && briefing.typology !== 'No suspicious typology'
                ? briefing.typology
                : 'Why is this account flagged?'}
            </h3>
            <span style={{
              marginLeft: 'auto',
              fontSize: '0.68rem',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              padding: '4px 10px',
              borderRadius: '999px',
              color: source === 'claude' ? '#C4B5FD' : 'var(--primary-neon)',
              border: `1px solid ${source === 'claude' ? 'rgba(139, 92, 246, 0.5)' : 'rgba(184, 255, 61, 0.4)'}`,
              whiteSpace: 'nowrap'
            }}>
              {source === 'claude' ? 'CLAUDE NARRATIVE' : 'RULE-BASED BRIEFING'}
            </span>
          </div>

          {briefing?.summary && (
            <p style={{ fontSize: '0.95rem', color: '#E2E8F0', lineHeight: 1.6, marginBottom: '20px' }}>
              {briefing.summary}
            </p>
          )}

          {fetched?.note && (
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '10px',
              padding: '10px 12px',
              marginBottom: '20px'
            }}>
              <Info size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
              <span>{fetched.note}</span>
            </div>
          )}

          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '10px' }}>
            KEY FINDINGS
          </div>

          {/* Auditable Grounded Evidence List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '32px' }}>
            {findings.length > 0 ? (
              findings.map((item, idx) => (
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

          {/* Recommended Next Steps */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(99, 102, 241, 0.08))',
            borderRadius: '16px',
            padding: '20px 24px',
            border: '1px solid rgba(139, 92, 246, 0.35)',
            boxShadow: '0 0 25px rgba(139, 92, 246, 0.1)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <ListChecks size={18} color="#8B5CF6" />
              <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: '#FFFFFF', letterSpacing: '0.02em' }}>
                Recommended Next Steps
              </h4>
            </div>
            <ol style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {nextSteps.map((step, idx) => (
                <li key={idx} style={{ fontSize: '0.88rem', color: 'var(--text-primary)', lineHeight: 1.55 }}>
                  {step}
                </li>
              ))}
            </ol>
          </div>

          {related.length > 0 && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '10px' }}>
                <Link2 size={13} />
                <span>LINKED ACCOUNTS</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {related.map((accId) => (
                  <button
                    key={accId}
                    onClick={() => knownIds.has(accId) && onSelectAccount && onSelectAccount(accId)}
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.75rem',
                      padding: '5px 10px',
                      borderRadius: '8px',
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#E2E8F0',
                      cursor: knownIds.has(accId) ? 'pointer' : 'default'
                    }}
                  >
                    {accId}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginTop: '20px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <FileCheck size={14} style={{ flexShrink: 0, marginTop: '1px' }} />
            <span>{briefing?.caveat || 'Risk indicators for prioritisation, not proof of wrongdoing.'}</span>
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
