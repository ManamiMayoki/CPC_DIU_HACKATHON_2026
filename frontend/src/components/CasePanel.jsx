import { useEffect, useState } from 'react';
import { FolderPlus, FolderOpen, Eye, EyeOff, IdCard } from 'lucide-react';
import { fetchCases, fetchProfile, openCase, revealProfile } from '../services/api';

/**
 * Shown under the network graph for the selected account: the account holder's KYC profile
 * (masked; a compliance officer can reveal it with a reason) and the button that turns the
 * alert into a case. Render it with key={account_id} so its state resets per account.
 */
export default function CasePanel({ account, user, onOpenCaseView }) {
  const accountId = account?.account_id;
  const [profile, setProfile] = useState(null);
  const [canReveal, setCanReveal] = useState(false);
  const [activeCase, setActiveCase] = useState(null);
  const [note, setNote] = useState('');
  const [reason, setReason] = useState('');
  const [askReason, setAskReason] = useState(false);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!accountId) return undefined;
    let cancelled = false;
    fetchProfile(accountId).then((res) => {
      if (cancelled || !res.success) return;
      setProfile(res.profile);
      setCanReveal(Boolean(res.can_reveal));
    });
    fetchCases().then((res) => {
      if (cancelled || !res.success) return;
      const match = res.cases.filter((c) => c.account_id === accountId);
      setActiveCase(match.find((c) => !c.disposition) || match[0] || null);
    });
    return () => {
      cancelled = true;
    };
  }, [accountId]);

  if (!account) return null;

  const handleOpen = async () => {
    setBusy(true);
    const res = await openCase(accountId, note);
    setBusy(false);
    if (res.success || res.case) {
      setActiveCase(res.case);
      setMessage(res.success ? `Case ${res.case.case_id} opened.` : res.error);
      setNote('');
    } else {
      setMessage(res.error);
    }
  };

  const handleReveal = async () => {
    setBusy(true);
    const res = await revealProfile(accountId, reason);
    setBusy(false);
    if (res.success) {
      setProfile(res.profile);
      setAskReason(false);
      setMessage('Personal data revealed. The reveal and your reason were written to the audit log.');
    } else {
      setMessage(res.error);
    }
  };

  const field = (label, value) => (
    <div>
      <div style={{ fontSize: '0.66rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: '0.88rem', color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>{value ?? '-'}</div>
    </div>
  );

  return (
    <div className="glass-panel" style={{ padding: '24px 28px', borderRadius: '20px', display: 'grid', gridTemplateColumns: 'minmax(0, 1.1fr) minmax(0, 1fr)', gap: '28px' }}>
      {/* KYC profile */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <IdCard size={18} color="var(--accent-cyan)" />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#FFFFFF' }}>Account holder (KYC)</h3>
          {profile && (
            <span style={{ fontSize: '0.66rem', fontFamily: 'var(--font-mono)', padding: '2px 8px', borderRadius: '6px', background: profile.masked ? 'rgba(56, 189, 248, 0.15)' : 'rgba(239, 68, 68, 0.18)', color: profile.masked ? '#38BDF8' : '#EF4444' }}>
              {profile.masked ? 'PII MASKED' : 'PII REVEALED'}
            </span>
          )}
        </div>
        {profile ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '14px' }}>
            {field('Name', profile.holder_name)}
            {field('Mobile', profile.phone)}
            {field('National ID', profile.national_id)}
            {field('Account type', profile.account_tier)}
            {field('KYC level', profile.kyc_level)}
            {field('District', profile.district)}
          </div>
        ) : (
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No KYC profile on file for this account.</div>
        )}

        {profile?.masked && (
          <div style={{ marginTop: '14px' }}>
            {!canReveal && (
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <EyeOff size={13} /> Only a compliance officer can reveal personal data.
              </div>
            )}
            {canReveal && !askReason && (
              <button type="button" className="btn-secondary" style={{ fontSize: '0.8rem', padding: '6px 14px' }} onClick={() => setAskReason(true)}>
                <Eye size={14} />
                <span>Reveal personal data</span>
              </button>
            )}
            {canReveal && askReason && (
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <input className="input-fintech" style={{ flex: 1, minWidth: '220px', fontSize: '0.82rem' }} placeholder="Reason (recorded in the audit log)" value={reason} onChange={(e) => setReason(e.target.value)} />
                <button type="button" className="btn-primary" disabled={busy || reason.trim().length < 10} style={{ fontSize: '0.8rem', padding: '6px 14px' }} onClick={handleReveal}>
                  Confirm reveal
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Case action */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <FolderOpen size={18} color="var(--primary-neon)" />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#FFFFFF' }}>Case</h3>
        </div>
        {activeCase ? (
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#FFFFFF', fontSize: '0.95rem' }}>{activeCase.case_id}</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '4px 0 12px' }}>
              Status <strong style={{ color: '#FFFFFF' }}>{activeCase.status.replace(/_/g, ' ')}</strong> · priority {activeCase.priority} · assigned to {activeCase.assignee} · {activeCase.notes.length} note(s)
            </div>
            <button type="button" className="btn-primary" style={{ fontSize: '0.82rem', padding: '7px 16px' }} onClick={() => onOpenCaseView(activeCase.case_id)}>
              <FolderOpen size={14} />
              <span>Open case file</span>
            </button>
            {activeCase.disposition && user?.permissions?.includes('case:create') && (
              <button type="button" className="btn-secondary" disabled={busy} style={{ fontSize: '0.82rem', padding: '7px 16px', marginLeft: '8px' }} onClick={handleOpen}>
                <FolderPlus size={14} />
                <span>Open a new case</span>
              </button>
            )}
          </div>
        ) : (
          <div>
            <textarea
              className="input-fintech"
              rows={2}
              placeholder="First note (optional): what made you open this case?"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              style={{ width: '100%', fontSize: '0.84rem', resize: 'vertical', marginBottom: '10px' }}
            />
            <button type="button" className="btn-primary" disabled={busy} style={{ fontSize: '0.84rem', padding: '8px 18px' }} onClick={handleOpen}>
              <FolderPlus size={15} />
              <span>Open case for {accountId}</span>
            </button>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '8px' }}>
              The current risk score, patterns and evidence are frozen into the case file.
            </div>
          </div>
        )}
        {message && <div role="status" style={{ marginTop: '12px', fontSize: '0.8rem', color: '#A7F3D0' }}>{message}</div>}
      </div>
    </div>
  );
}
