/**
 * Case management: the analyst workflow that sits on top of detection.
 *
 * alert (risky account) -> case OPEN -> IN_REVIEW -> ESCALATED -> decision by a compliance
 * officer: SAR_FILED or CLOSED_FALSE_POSITIVE. The model never decides; a person does, and the
 * decision is kept as a label that can feed retraining.
 *
 * Cases are stored in one JSON file so the prototype has no database dependency.
 */
const fs = require('fs');
const path = require('path');

const STATUSES = ['OPEN', 'IN_REVIEW', 'ESCALATED', 'SAR_FILED', 'CLOSED_FALSE_POSITIVE'];
const DECISION_STATUSES = ['SAR_FILED', 'CLOSED_FALSE_POSITIVE'];

// from -> allowed next statuses
const TRANSITIONS = {
  OPEN: ['IN_REVIEW', 'ESCALATED', 'CLOSED_FALSE_POSITIVE'],
  IN_REVIEW: ['ESCALATED', 'OPEN', 'CLOSED_FALSE_POSITIVE'],
  ESCALATED: ['SAR_FILED', 'CLOSED_FALSE_POSITIVE', 'IN_REVIEW'],
  SAR_FILED: ['IN_REVIEW'],
  CLOSED_FALSE_POSITIVE: ['IN_REVIEW'],
};

const PRIORITY_BY_RISK = { CRITICAL: 'P1', HIGH: 'P2', MEDIUM: 'P3', LOW: 'P4' };

class CaseError extends Error {
  constructor(status, message, extra = {}) {
    super(message);
    this.status = status;
    this.extra = extra;
  }
}

function cleanText(value, maxLength) {
  return String(value ?? '').replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '').trim().slice(0, maxLength);
}

class CaseStore {
  constructor(filePath) {
    this.filePath = filePath;
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    this.cases = [];
    this.counter = 0;
    if (fs.existsSync(filePath)) {
      try {
        const saved = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        this.cases = saved.cases || [];
        this.counter = saved.counter || this.cases.length;
      } catch (err) {
        console.error('[Cygnus Cases] Could not read case file, starting empty:', err.message);
      }
    }
  }

  save() {
    const tmp = `${this.filePath}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify({ counter: this.counter, cases: this.cases }, null, 2), 'utf-8');
    fs.renameSync(tmp, this.filePath);
  }

  list({ status, account_id: accountId, assignee } = {}) {
    let results = [...this.cases];
    if (status) results = results.filter((c) => c.status === String(status).toUpperCase());
    if (accountId) results = results.filter((c) => c.account_id.toLowerCase() === String(accountId).toLowerCase());
    if (assignee) results = results.filter((c) => c.assignee === assignee);
    return results.sort((a, b) => (a.priority === b.priority
      ? b.created_at.localeCompare(a.created_at)
      : a.priority.localeCompare(b.priority)));
  }

  get(caseId) {
    const found = this.cases.find((c) => c.case_id.toLowerCase() === String(caseId).toLowerCase());
    if (!found) throw new CaseError(404, `Case '${caseId}' not found.`);
    return found;
  }

  findActiveForAccount(accountId) {
    return this.cases.find(
      (c) => c.account_id === accountId && !DECISION_STATUSES.includes(c.status)
    );
  }

  /** Opens a case from an account, freezing the risk picture the analyst saw at that moment. */
  open(account, user, { title, note } = {}) {
    const existing = this.findActiveForAccount(account.account_id);
    if (existing) {
      throw new CaseError(409, `Account ${account.account_id} already has an active case (${existing.case_id}).`, {
        case: existing,
      });
    }
    this.counter += 1;
    const now = new Date().toISOString();
    const investigation = account.investigation || {};
    const record = {
      case_id: `CASE-${new Date().getFullYear()}-${String(this.counter).padStart(4, '0')}`,
      account_id: account.account_id,
      title: cleanText(title, 160) || `${investigation.typology || 'Suspicious activity'} - ${account.account_id}`,
      status: 'OPEN',
      priority: PRIORITY_BY_RISK[account.risk_level] || 'P4',
      created_by: user.username,
      assignee: user.username,
      created_at: now,
      updated_at: now,
      decided_at: null,
      decided_by: null,
      disposition: null,
      disposition_reason: null,
      snapshot: {
        risk_score: account.risk_score,
        risk_level: account.risk_level,
        is_anomaly: account.is_anomaly,
        patterns: account.patterns || [],
        scoring_breakdown: account.scoring_breakdown || {},
        evidence: account.evidence || [],
        typology: investigation.typology || null,
        headline: investigation.headline || null,
        summary: investigation.summary || null,
        next_steps: investigation.next_steps || [],
        related_accounts: investigation.related_accounts || [],
        ml_features: account.ml_features || {},
      },
      notes: [],
      timeline: [{ at: now, by: user.username, role: user.role, event: 'Case opened', status: 'OPEN' }],
    };
    this.cases.push(record);
    if (cleanText(note, 4000)) this.addNote(record.case_id, user, note, { skipSave: true });
    this.save();
    return record;
  }

  addNote(caseId, user, text, { skipSave = false } = {}) {
    const record = this.get(caseId);
    const body = cleanText(text, 4000);
    if (!body) throw new CaseError(400, 'A note cannot be empty.');
    const now = new Date().toISOString();
    const note = { id: `N${record.notes.length + 1}`, at: now, by: user.username, role: user.role, text: body };
    record.notes.push(note);
    record.updated_at = now;
    record.timeline.push({ at: now, by: user.username, role: user.role, event: 'Note added' });
    if (!skipSave) this.save();
    return note;
  }

  /** Moves a case along the workflow. `canDecide` says whether this user may make the final decision. */
  changeStatus(caseId, user, nextStatus, { reason, canDecide = false } = {}) {
    const record = this.get(caseId);
    const target = String(nextStatus || '').toUpperCase();
    if (!STATUSES.includes(target)) {
      throw new CaseError(400, `Unknown status '${nextStatus}'. Use one of: ${STATUSES.join(', ')}.`);
    }
    if (target === record.status) return record;
    if (!TRANSITIONS[record.status].includes(target)) {
      throw new CaseError(409, `A case cannot move from ${record.status} to ${target}.`, {
        allowed: TRANSITIONS[record.status],
      });
    }
    const isDecision = DECISION_STATUSES.includes(target);
    const isReopen = DECISION_STATUSES.includes(record.status);
    if ((isDecision || isReopen) && !canDecide) {
      throw new CaseError(403, 'Only a compliance officer can file, close or reopen a case. Escalate it instead.');
    }
    const why = cleanText(reason, 2000);
    if (isDecision && !why) {
      throw new CaseError(400, 'A written reason is required to file or close a case.');
    }
    const now = new Date().toISOString();
    const previous = record.status;
    record.status = target;
    record.updated_at = now;
    if (isDecision) {
      record.decided_at = now;
      record.decided_by = user.username;
      record.disposition = target === 'SAR_FILED' ? 'confirmed_suspicious' : 'false_positive';
      record.disposition_reason = why;
    } else if (isReopen) {
      record.decided_at = null;
      record.decided_by = null;
      record.disposition = null;
      record.disposition_reason = null;
    }
    record.timeline.push({
      at: now, by: user.username, role: user.role, event: `Status ${previous} -> ${target}`, status: target, reason: why || undefined,
    });
    this.save();
    return record;
  }

  assign(caseId, user, assignee) {
    const record = this.get(caseId);
    const name = cleanText(assignee, 64);
    if (!name) throw new CaseError(400, 'assignee is required.');
    const now = new Date().toISOString();
    record.assignee = name;
    record.updated_at = now;
    record.timeline.push({ at: now, by: user.username, role: user.role, event: `Assigned to ${name}` });
    this.save();
    return record;
  }

  stats() {
    const byStatus = Object.fromEntries(STATUSES.map((s) => [s, 0]));
    const decisionHours = [];
    for (const c of this.cases) {
      byStatus[c.status] = (byStatus[c.status] || 0) + 1;
      if (c.decided_at) decisionHours.push((new Date(c.decided_at) - new Date(c.created_at)) / 3600000);
    }
    const decided = byStatus.SAR_FILED + byStatus.CLOSED_FALSE_POSITIVE;
    return {
      total: this.cases.length,
      by_status: byStatus,
      active: this.cases.length - decided,
      decided,
      confirmed_rate: decided ? Number((byStatus.SAR_FILED / decided).toFixed(3)) : null,
      average_hours_to_decision: decisionHours.length
        ? Number((decisionHours.reduce((a, b) => a + b, 0) / decisionHours.length).toFixed(2))
        : null,
    };
  }

  /** Human decisions as training labels (the feedback loop for supervised retraining). */
  labels() {
    return this.cases
      .filter((c) => c.disposition)
      .map((c) => ({
        account_id: c.account_id,
        label: c.disposition === 'confirmed_suspicious' ? 1 : 0,
        disposition: c.disposition,
        case_id: c.case_id,
        decided_by: c.decided_by,
        decided_at: c.decided_at,
        model_risk_score: c.snapshot.risk_score,
        model_risk_level: c.snapshot.risk_level,
      }));
  }
}

module.exports = { CaseStore, CaseError, STATUSES, TRANSITIONS, DECISION_STATUSES };
