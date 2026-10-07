/**
 * Suspicious Transaction Report (STR/SAR) draft for one case.
 *
 * Builds a self-contained, printable HTML document (and the same content as JSON) from the
 * case record, the frozen risk snapshot, the linked transactions and the analyst notes. It is
 * a draft to help a compliance officer prepare a filing; it is not an official BFIU form and
 * nothing is submitted anywhere.
 */
const crypto = require('crypto');

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function money(value) {
  return `BDT ${Number(value || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
}

/** Transactions that touch the subject account, newest first, from the aggregated graph edges. */
function linkedTransactions(accountId, edges = [], limit = 60) {
  const rows = [];
  for (const edge of edges) {
    if (edge.source !== accountId && edge.target !== accountId) continue;
    const txs = edge.transactions?.length
      ? edge.transactions
      : [{ transaction_id: edge.transaction_id, amount: edge.amount, timestamp: edge.timestamp }];
    for (const tx of txs) {
      rows.push({
        transaction_id: tx.transaction_id || edge.transaction_id,
        timestamp: tx.timestamp || edge.timestamp,
        direction: edge.source === accountId ? 'OUT' : 'IN',
        counterparty: edge.source === accountId ? edge.target : edge.source,
        amount: Number(tx.amount || 0),
      });
    }
  }
  rows.sort((a, b) => String(b.timestamp).localeCompare(String(a.timestamp)));
  return rows.slice(0, limit);
}

function buildReport({ caseRecord, account, profile, edges, generatedBy, auditHead }) {
  const transactions = linkedTransactions(caseRecord.account_id, edges);
  const totalIn = transactions.filter((t) => t.direction === 'IN').reduce((s, t) => s + t.amount, 0);
  const totalOut = transactions.filter((t) => t.direction === 'OUT').reduce((s, t) => s + t.amount, 0);
  const snapshot = caseRecord.snapshot || {};
  const report = {
    report_type: 'Suspicious Transaction Report (draft)',
    report_reference: `STR-DRAFT-${caseRecord.case_id}`,
    generated_at: new Date().toISOString(),
    generated_by: { username: generatedBy.username, role: generatedBy.role },
    case: {
      case_id: caseRecord.case_id,
      title: caseRecord.title,
      status: caseRecord.status,
      priority: caseRecord.priority,
      opened_at: caseRecord.created_at,
      opened_by: caseRecord.created_by,
      assignee: caseRecord.assignee,
      disposition: caseRecord.disposition,
      disposition_reason: caseRecord.disposition_reason,
      decided_by: caseRecord.decided_by,
      decided_at: caseRecord.decided_at,
    },
    subject: { account_id: caseRecord.account_id, profile: profile || null },
    suspicion: {
      typology: snapshot.typology,
      headline: snapshot.headline,
      summary: snapshot.summary,
      detected_patterns: snapshot.patterns || [],
      evidence: snapshot.evidence || [],
      related_accounts: snapshot.related_accounts || [],
    },
    risk: {
      score_at_case_open: snapshot.risk_score,
      level_at_case_open: snapshot.risk_level,
      ml_anomaly_flag: snapshot.is_anomaly,
      scoring_breakdown: snapshot.scoring_breakdown || {},
      current_score: account?.risk_score ?? null,
      current_level: account?.risk_level ?? null,
    },
    transactions: {
      count: transactions.length,
      total_incoming: Number(totalIn.toFixed(2)),
      total_outgoing: Number(totalOut.toFixed(2)),
      items: transactions,
    },
    recommended_actions: snapshot.next_steps || [],
    analyst_notes: caseRecord.notes,
    timeline: caseRecord.timeline,
    integrity: { audit_log_head_hash: auditHead },
    disclaimer:
      'Draft prepared by Cygnus AI from synthetic data to support a human reviewer. Risk scores are '
      + 'indicators, not proof of wrongdoing. Not an official BFIU/goAML form; nothing has been submitted.',
  };
  report.integrity.content_sha256 = crypto.createHash('sha256').update(JSON.stringify(report)).digest('hex');
  return report;
}

function list(items) {
  if (!items?.length) return '<p class="muted">None recorded.</p>';
  return `<ul>${items.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>`;
}

function renderHtml(report) {
  const p = report.subject.profile;
  const breakdown = report.risk.scoring_breakdown;
  const profileRows = p
    ? `
      <tr><th>Account holder</th><td>${esc(p.holder_name)}</td><th>Mobile number</th><td>${esc(p.phone)}</td></tr>
      <tr><th>National ID</th><td>${esc(p.national_id)}</td><th>Account type</th><td>${esc(p.account_tier)}</td></tr>
      <tr><th>KYC level</th><td>${esc(p.kyc_level)}</td><th>District</th><td>${esc(p.district)}</td></tr>
      <tr><th>Account age</th><td>${esc(p.account_age_days)} days</td><th>Personal data</th><td>${p.masked ? 'Masked' : 'Unmasked (reveal recorded in audit log)'}</td></tr>`
    : '<tr><td colspan="4" class="muted">No KYC profile on file for this account.</td></tr>';
  const txRows = report.transactions.items
    .map(
      (t) => `<tr><td>${esc(t.timestamp)}</td><td>${esc(t.transaction_id)}</td><td>${esc(t.direction)}</td>`
        + `<td>${esc(t.counterparty)}</td><td class="num">${esc(money(t.amount))}</td></tr>`
    )
    .join('');
  const noteRows = report.analyst_notes.length
    ? report.analyst_notes
      .map((n) => `<tr><td>${esc(n.at)}</td><td>${esc(n.by)} (${esc(n.role)})</td><td>${esc(n.text)}</td></tr>`)
      .join('')
    : '<tr><td colspan="3" class="muted">No notes.</td></tr>';
  const timelineRows = report.timeline
    .map((t) => `<tr><td>${esc(t.at)}</td><td>${esc(t.by)} (${esc(t.role)})</td><td>${esc(t.event)}${t.reason ? ` - ${esc(t.reason)}` : ''}</td></tr>`)
    .join('');

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${esc(report.report_reference)}</title>
<style>
  body { font-family: Georgia, 'Times New Roman', serif; color: #111; max-width: 860px; margin: 32px auto; padding: 0 24px; line-height: 1.45; }
  h1 { font-size: 22px; margin-bottom: 2px; }
  h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .06em; border-bottom: 2px solid #111; padding-bottom: 4px; margin-top: 28px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
  th, td { border: 1px solid #bbb; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { background: #f1f1f1; width: 18%; }
  .num { text-align: right; white-space: nowrap; }
  .muted { color: #666; }
  .banner { border: 2px solid #b91c1c; color: #b91c1c; padding: 8px 12px; font-weight: bold; font-size: 13px; margin: 14px 0; }
  .hash { font-family: 'Courier New', monospace; font-size: 11px; word-break: break-all; }
  .print { margin: 16px 0; padding: 8px 16px; font-size: 14px; cursor: pointer; }
  @media print { .print { display: none; } body { margin: 0; } }
</style>
</head>
<body>
<button class="print" onclick="window.print()">Print / Save as PDF</button>
<h1>Suspicious Transaction Report - Draft</h1>
<div class="muted">Reference ${esc(report.report_reference)} &middot; generated ${esc(report.generated_at)} by ${esc(report.generated_by.username)} (${esc(report.generated_by.role)})</div>
<div class="banner">CONFIDENTIAL - DRAFT FOR COMPLIANCE REVIEW. Synthetic demonstration data. Not submitted to any authority.</div>

<h2>1. Case</h2>
<table>
  <tr><th>Case ID</th><td>${esc(report.case.case_id)}</td><th>Status</th><td>${esc(report.case.status)}</td></tr>
  <tr><th>Title</th><td colspan="3">${esc(report.case.title)}</td></tr>
  <tr><th>Priority</th><td>${esc(report.case.priority)}</td><th>Assigned to</th><td>${esc(report.case.assignee)}</td></tr>
  <tr><th>Opened</th><td>${esc(report.case.opened_at)} by ${esc(report.case.opened_by)}</td><th>Decision</th><td>${report.case.disposition ? `${esc(report.case.disposition)} by ${esc(report.case.decided_by)} at ${esc(report.case.decided_at)}` : 'Pending'}</td></tr>
  ${report.case.disposition_reason ? `<tr><th>Decision reason</th><td colspan="3">${esc(report.case.disposition_reason)}</td></tr>` : ''}
</table>

<h2>2. Subject of the report</h2>
<table>
  <tr><th>Account ID</th><td colspan="3">${esc(report.subject.account_id)}</td></tr>
  ${profileRows}
</table>

<h2>3. Reason for suspicion</h2>
<table>
  <tr><th>Typology</th><td>${esc(report.suspicion.typology || 'Not classified')}</td></tr>
  <tr><th>Detected patterns</th><td>${esc(report.suspicion.detected_patterns.join(', ') || 'None')}</td></tr>
  <tr><th>Related accounts</th><td>${esc(report.suspicion.related_accounts.join(', ') || 'None')}</td></tr>
</table>
<p>${esc(report.suspicion.summary || '')}</p>
<strong>Evidence</strong>
${list(report.suspicion.evidence)}

<h2>4. Risk assessment</h2>
<table>
  <tr><th>Score at case open</th><td>${esc(report.risk.score_at_case_open)} / 100 (${esc(report.risk.level_at_case_open)})</td><th>ML anomaly flag</th><td>${report.risk.ml_anomaly_flag ? 'Yes' : 'No'}</td></tr>
  <tr><th>ML component</th><td>${esc(breakdown.ml_component ?? '-')}</td><th>Graph component</th><td>${esc(breakdown.graph_component ?? '-')}</td></tr>
  <tr><th>Behavioural component</th><td>${esc(breakdown.behavioral_component ?? '-')}</td><th>Current score</th><td>${esc(report.risk.current_score ?? '-')} (${esc(report.risk.current_level ?? '-')})</td></tr>
</table>

<h2>5. Transactions involving the subject</h2>
<table>
  <tr><th>Transactions listed</th><td>${esc(report.transactions.count)}</td><th>Total in / out</th><td>${esc(money(report.transactions.total_incoming))} / ${esc(money(report.transactions.total_outgoing))}</td></tr>
</table>
<table>
  <tr><th>Time</th><th>Transaction</th><th>Direction</th><th>Counterparty</th><th>Amount</th></tr>
  ${txRows || '<tr><td colspan="5" class="muted">No transactions found.</td></tr>'}
</table>

<h2>6. Recommended next steps</h2>
${list(report.recommended_actions)}

<h2>7. Analyst notes</h2>
<table><tr><th>Time</th><th>Author</th><th>Note</th></tr>${noteRows}</table>

<h2>8. Case timeline</h2>
<table><tr><th>Time</th><th>Actor</th><th>Event</th></tr>${timelineRows}</table>

<h2>9. Integrity</h2>
<p class="hash">Report content SHA-256: ${esc(report.integrity.content_sha256)}<br>Audit log head at export: ${esc(report.integrity.audit_log_head_hash)}</p>
<p class="muted">${esc(report.disclaimer)}</p>
</body>
</html>`;
}

module.exports = { buildReport, renderHtml, linkedTransactions, esc };
