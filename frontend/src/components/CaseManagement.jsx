import { useCallback, useEffect, useState } from 'react';
import { FolderOpen, FileText, MessageSquarePlus, ArrowRight, ShieldCheck, RefreshCw } from 'lucide-react';
import { addCaseNote, fetchCases, openCaseReport, updateCase } from '../services/api';

const STATUS_COLORS = {
  OPEN: '#38BDF8',
  IN_REVIEW: '#8B5CF6',
  ESCALATED: '#F59E0B',
  SAR_FILED: '#EF4444',
  CLOSED_FALSE_POSITIVE: '#22C55E',
};
const STATUS_LABELS = {
  OPEN: 'Open',
  IN_REVIEW: 'In review',
  ESCALATED: 'Escalated',
  SAR_FILED: 'STR filed',
  CLOSED_FALSE_POSITIVE: 'Closed: false positive',
};
const DECISIONS = ['SAR_FILED', 'CLOSED_FALSE_POSITIVE'];

function StatusBadge({ status }) {
  const color = STATUS_COLORS[status] || '#94A3B8';
  return (
    <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', fontWeight: 700, padding: '3px 8px', borderRadius: '6px', background: `${color}26`, color }}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

/**
 * Case management workspace: the queue on the left, the selected case file on the right.
 * Analysts work a case up to "Escalated"; only a compliance officer can file or close it.
 */
export default function CaseManagement({ user, initialCaseId, onInvestigateAccount }) {
  const [cases, setCases] = useState([]);
  const [stats, setStats] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [selectedId, setSelectedId] = useState(initialCaseId || null);
  const [noteText, setNoteText] = useState('');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  const canDecide = user?.permissions?.includes('case:decide');
  const canUnmask = user?.permissions?.includes('pii:reveal');

  const load = useCallback(async () => {
    const res = await fetchCases();
    if (!res.success) {
      setMessage({ ok: false, text: res.error });
      return;
    }
    setCases(res.cases);
    setStats(res.stats);
    setWorkflow(res.workflow);
    setSelectedId((current) => current || res.cases[0]?.case_id || null);
  }, []);

  useEffect(() => {
    // Initial fetch; load() sets state when the response arrives.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const selected = cases.find((c) => c.case_id === selectedId) || null;

  const run = async (action, successText) => {
    setBusy(true);
    const res = await action();
    setBusy(false);
    setMessage({ ok: Boolean(res.success), text: res.success ? successText : res.error });
    if (res.success) await load();
    return res;
  };

  const handleNote = async () => {
    const res = await run(() => addCaseNote(selected.case_id, noteText), 'Note added.');
    if (res.success) setNoteText('');
  };

  const handleStatus = async (status) => {
    const res = await run(
      () => updateCase(selected.case_id, { status, reason }),
      `Case moved to ${STATUS_LABELS[status]}.`
    );
    if (res.success) setReason('');
  };

  const handleReport = (unmask) => run(() => openCaseReport(selected.case_id, { unmask }), 'Report opened in a new tab. Use Print to save it as PDF.');

  const nextStatuses = selected && workflow ? workflow.transitions[selected.status] || [] : [];

  return (
    <section style={{ maxWidth: '1480px', margin: '0 auto', padding: '36px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '22px' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--primary-neon)', fontSize: '0.74rem', fontFamily: 'var(--font-mono)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>
            <FolderOpen size={14} />
            <span>Analyst workflow</span>
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>Case Management</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px', maxWidth: '760px' }}>
            Alert, case, notes, escalation, decision, report. The model ranks and explains; a person decides, and the decision is kept as a label for retraining.
          </p>
        </div>
        {stats && (
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {[['Active', stats.active], ['STR filed', stats.by_status.SAR_FILED], ['False positive', stats.by_status.CLOSED_FALSE_POSITIVE], ['Total', stats.total]].map(([label, value]) => (
              <div key={label} className="glass-panel" style={{ padding: '10px 16px', borderRadius: '12px', textAlign: 'center', minWidth: '92px' }}>
                <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>{value}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>{label}</div>
              </div>
            ))}
            <button type="button" className="btn-secondary" onClick={load} style={{ padding: '8px 14px', fontSize: '0.8rem', alignSelf: 'center' }}>
              <RefreshCw size={14} />
              <span>Refresh</span>
            </button>
          </div>
        )}
      </div>

      {message && (
        <div role="status" style={{ marginBottom: '16px', padding: '10px 14px', borderRadius: '10px', fontSize: '0.85rem', background: message.ok ? 'rgba(34, 197, 94, 0.12)' : 'rgba(239, 68, 68, 0.12)', color: message.ok ? '#86EFAC' : '#FCA5A5', border: `1px solid ${message.ok ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}` }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '380px minmax(0, 1fr)', gap: '22px', alignItems: 'start' }}>
        {/* Queue */}
        <div className="glass-panel" style={{ borderRadius: '18px', overflow: 'hidden' }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Case queue ({cases.length})
          </div>
          {cases.length === 0 && (
            <div style={{ padding: '22px 18px', fontSize: '0.86rem', color: 'var(--text-muted)' }}>
              No cases yet. Open one from an account in Follow the Money.
            </div>
          )}
          {cases.map((c) => (
            <button
              key={c.case_id}
              type="button"
              onClick={() => { setSelectedId(c.case_id); setMessage(null); }}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '14px 18px', border: 'none', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', background: c.case_id === selectedId ? 'rgba(184, 255, 61, 0.08)' : 'transparent', cursor: 'pointer', color: '#FFFFFF' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.86rem' }}>{c.case_id}</span>
                <StatusBadge status={c.status} />
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.title}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                {c.priority} · {c.snapshot.risk_level} {Number(c.snapshot.risk_score).toFixed(1)} · {c.assignee}
              </div>
            </button>
          ))}
        </div>

        {/* Case file */}
        {selected ? (
          <div className="glass-panel" style={{ borderRadius: '18px', padding: '26px 28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <h3 style={{ fontSize: '1.3rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>{selected.case_id}</h3>
                  <StatusBadge status={selected.status} />
                  <span className={`badge-risk badge-risk-${String(selected.snapshot.risk_level).toLowerCase()}`}>{selected.snapshot.risk_level}</span>
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '6px' }}>{selected.title}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.76rem', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                  Opened {new Date(selected.created_at).toLocaleString()} by {selected.created_by} · priority {selected.priority} · assigned to {selected.assignee}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button type="button" className="btn-secondary" style={{ fontSize: '0.8rem', padding: '7px 14px' }} onClick={() => onInvestigateAccount(selected.account_id)}>
                  <span>View network</span>
                  <ArrowRight size={13} />
                </button>
                <button type="button" className="btn-primary" disabled={busy} style={{ fontSize: '0.8rem', padding: '7px 14px' }} onClick={() => handleReport(false)}>
                  <FileText size={14} />
                  <span>Export STR draft</span>
                </button>
                {canUnmask && (
                  <button type="button" className="btn-secondary" disabled={busy} style={{ fontSize: '0.8rem', padding: '7px 14px' }} onClick={() => handleReport(true)}>
                    <span>Export with PII</span>
                  </button>
                )}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '24px', marginTop: '22px' }}>
              <div>
                <h4 style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Risk picture at case open</h4>
                <div style={{ fontSize: '0.86rem', color: '#E2E8F0', lineHeight: 1.55 }}>
                  <div><strong>{selected.snapshot.typology || 'Suspicious activity'}</strong> on account <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--primary-neon)' }}>{selected.account_id}</span></div>
                  <div style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Score {Number(selected.snapshot.risk_score).toFixed(1)} / 100 · patterns: {(selected.snapshot.patterns || []).map((p) => p.replace(/_/g, ' ')).join(', ') || 'none'}
                  </div>
                  {selected.snapshot.summary && <p style={{ marginTop: '8px', color: 'var(--text-secondary)' }}>{selected.snapshot.summary}</p>}
                </div>
                <ul style={{ margin: '10px 0 0', paddingLeft: '18px', fontSize: '0.82rem', color: '#CBD5E1', lineHeight: 1.5 }}>
                  {(selected.snapshot.evidence || []).slice(0, 5).map((ev) => <li key={ev}>{ev}</li>)}
                </ul>
              </div>

              <div>
                <h4 style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Timeline</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '240px', overflowY: 'auto' }}>
                  {selected.timeline.map((event, i) => (
                    <div key={`${event.at}-${i}`} style={{ fontSize: '0.8rem', borderLeft: '2px solid rgba(184, 255, 61, 0.5)', paddingLeft: '10px' }}>
                      <div style={{ color: '#FFFFFF' }}>{event.event}{event.reason ? `: ${event.reason}` : ''}</div>
                      <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>{new Date(event.at).toLocaleString()} · {event.by} ({event.role})</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Notes */}
            <h4 style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', margin: '24px 0 8px' }}>Analyst notes ({selected.notes.length})</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {selected.notes.map((n) => (
                <div key={n.id} style={{ background: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px', padding: '10px 14px' }}>
                  <div style={{ fontSize: '0.86rem', color: '#F1F5F9', whiteSpace: 'pre-wrap' }}>{n.text}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>{n.by} ({n.role}) · {new Date(n.at).toLocaleString()}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
              <textarea className="input-fintech" rows={2} placeholder="Add a note: what you checked, what you found" value={noteText} onChange={(e) => setNoteText(e.target.value)} style={{ flex: 1, fontSize: '0.84rem', resize: 'vertical' }} />
              <button type="button" className="btn-secondary" disabled={busy || !noteText.trim()} style={{ fontSize: '0.8rem', padding: '8px 14px', alignSelf: 'flex-start' }} onClick={handleNote}>
                <MessageSquarePlus size={14} />
                <span>Add note</span>
              </button>
            </div>

            {/* Workflow actions */}
            <h4 style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', margin: '24px 0 8px' }}>Move the case</h4>
            {selected.disposition && (
              <div style={{ fontSize: '0.84rem', color: '#E2E8F0', marginBottom: '10px' }}>
                Decision: <strong>{selected.disposition.replace(/_/g, ' ')}</strong> by {selected.decided_by}. Reason: {selected.disposition_reason}
              </div>
            )}
            <input className="input-fintech" placeholder="Reason (required to file or close)" value={reason} onChange={(e) => setReason(e.target.value)} style={{ width: '100%', fontSize: '0.84rem', marginBottom: '10px' }} />
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
              {nextStatuses.map((status) => {
                const isDecision = DECISIONS.includes(status) || DECISIONS.includes(selected.status);
                const locked = isDecision && !canDecide;
                return (
                  <button
                    key={status}
                    type="button"
                    disabled={busy || locked || (DECISIONS.includes(status) && !reason.trim())}
                    title={locked ? 'Only a compliance officer can file, close or reopen a case' : ''}
                    onClick={() => handleStatus(status)}
                    style={{ padding: '8px 14px', borderRadius: '9999px', fontSize: '0.8rem', fontWeight: 700, cursor: locked ? 'not-allowed' : 'pointer', border: `1px solid ${STATUS_COLORS[status]}`, background: `${STATUS_COLORS[status]}1F`, color: STATUS_COLORS[status], opacity: locked ? 0.45 : 1 }}
                  >
                    {isDecision && <ShieldCheck size={13} style={{ verticalAlign: '-2px', marginRight: '5px' }} />}
                    {STATUS_LABELS[status]}
                  </button>
                );
              })}
              {!canDecide && (
                <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Filing and closing need a compliance officer. Escalate the case to hand it over.</span>
              )}
            </div>
          </div>
        ) : (
          <div className="glass-panel" style={{ borderRadius: '18px', padding: '40px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Select a case from the queue.
          </div>
        )}
      </div>
    </section>
  );
}
