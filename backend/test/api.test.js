/**
 * Backend tests: authentication, role-based access, PII masking, the hash-chained audit log
 * and the case workflow. Run with `npm test` in backend/ (Node's built-in test runner).
 */
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cygnus-test-'));
process.env.CYGNUS_DATA_DIR = dataDir;
process.env.CYGNUS_DEMO_MODE = 'true';
process.env.CYGNUS_ANALYST_PASSWORD = 'test-analyst-pass';
process.env.CYGNUS_ADMIN_PASSWORD = 'test-admin-pass';

const { app, audit } = require('../src/server');
const { AuditLog } = require('../src/audit');
const { maskProfile, maskPhone, maskNid, maskName } = require('../src/privacy');
const { esc } = require('../src/report');

let server;
let base;
const tokens = {};

async function call(method, url, { token, body } = {}) {
  const res = await fetch(base + url, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* html */ }
  return { status: res.status, json, text };
}

before(async () => {
  server = app.listen(0);
  await new Promise((resolve) => server.once('listening', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
  for (const role of ['analyst', 'admin']) {
    const res = await call('POST', '/api/auth/demo', { body: { role } });
    tokens[role] = res.json.token;
  }
});

after(() => {
  server.close();
  fs.rmSync(dataDir, { recursive: true, force: true });
});

test('health is public, data endpoints need a session', async () => {
  assert.equal((await call('GET', '/api/health')).status, 200);
  assert.equal((await call('GET', '/api/pipeline')).status, 401);
  assert.equal((await call('GET', '/api/accounts')).status, 401);
  assert.equal((await call('GET', '/api/cases')).status, 401);
  assert.equal((await call('GET', '/api/accounts', { token: 'not.a-real-token' })).status, 401);
});

test('password sign-in works, wrong passwords are rejected and audited', async () => {
  const ok = await call('POST', '/api/auth/login', { body: { username: 'analyst', password: 'test-analyst-pass' } });
  assert.equal(ok.status, 200);
  assert.equal(ok.json.user.role, 'analyst');
  const bad = await call('POST', '/api/auth/login', { body: { username: 'analyst', password: 'nope' } });
  assert.equal(bad.status, 401);
  assert.ok(audit.list({ action: 'AUTH_FAILED' }).length >= 1);
});

test('repeated failed sign-ins lock the account temporarily', async () => {
  let last;
  for (let i = 0; i < 6; i += 1) {
    last = await call('POST', '/api/auth/login', { body: { username: 'admin', password: `wrong-${i}` } });
  }
  assert.equal(last.status, 429);
});

test('a tampered token is rejected', async () => {
  const [payload, signature] = tokens.analyst.split('.');
  const forged = Buffer.from(JSON.stringify({ sub: 'analyst', role: 'admin', exp: 9999999999 })).toString('base64url');
  assert.equal((await call('GET', '/api/auth/me', { token: `${forged}.${signature}` })).status, 401);
  assert.equal((await call('GET', '/api/auth/me', { token: `${payload}.${signature}` })).status, 200);
});

test('analyst sees masked PII and cannot reveal it; admin reveal needs a reason and is audited', async () => {
  const masked = await call('GET', '/api/accounts/ACC_MULE_HUB/profile', { token: tokens.analyst });
  assert.equal(masked.status, 200);
  assert.equal(masked.json.profile.masked, true);
  assert.match(masked.json.profile.phone, /^01\d\*+\d{3}$/);
  assert.match(masked.json.profile.national_id, /^\*+\d{4}$/);
  assert.ok(masked.json.profile.holder_name.includes('*'));

  const denied = await call('POST', '/api/accounts/ACC_MULE_HUB/profile/reveal', { token: tokens.analyst, body: { reason: 'curious about this one' } });
  assert.equal(denied.status, 403);

  const noReason = await call('POST', '/api/accounts/ACC_MULE_HUB/profile/reveal', { token: tokens.admin, body: { reason: 'x' } });
  assert.equal(noReason.status, 400);

  const revealed = await call('POST', '/api/accounts/ACC_MULE_HUB/profile/reveal', { token: tokens.admin, body: { reason: 'Preparing STR filing for case review' } });
  assert.equal(revealed.status, 200);
  assert.equal(revealed.json.profile.masked, false);
  assert.match(revealed.json.profile.phone, /^01\d{9}$/);
  assert.equal(audit.list({ action: 'PII_REVEALED' })[0].target, 'ACC_MULE_HUB');
  assert.ok(audit.list({ action: 'ACCESS_DENIED' }).length >= 1);
});

test('the pipeline payload never contains personal data', async () => {
  const res = await call('GET', '/api/pipeline', { token: tokens.analyst });
  assert.equal(res.status, 200);
  assert.ok(!res.text.includes('national_id'));
  assert.ok(!res.text.includes('holder_name'));
});

test('masking helpers', () => {
  assert.equal(maskPhone('01712345678'), '017*****678');
  assert.equal(maskNid('1234567890'), '******7890');
  assert.equal(maskName('Rahim Ahmed'), 'R**** A****');
  assert.equal(maskProfile(null), null);
  assert.equal(esc('<script>"x"</script>'), '&lt;script&gt;&quot;x&quot;&lt;/script&gt;');
});

test('case workflow: open, note, escalate, four-eyes decision, report', async () => {
  const opened = await call('POST', '/api/cases', { token: tokens.analyst, body: { account_id: 'ACC_MULE_HUB', note: 'Hub forwards every receipt within minutes.' } });
  assert.equal(opened.status, 201);
  const id = opened.json.case.case_id;
  assert.match(id, /^CASE-\d{4}-\d{4}$/);
  assert.equal(opened.json.case.status, 'OPEN');
  assert.equal(opened.json.case.notes.length, 1);
  assert.ok(opened.json.case.snapshot.risk_score > 0);

  // one active case per account
  assert.equal((await call('POST', '/api/cases', { token: tokens.analyst, body: { account_id: 'ACC_MULE_HUB' } })).status, 409);
  assert.equal((await call('POST', '/api/cases', { token: tokens.analyst, body: { account_id: 'NO_SUCH_ACCOUNT' } })).status, 404);

  const xss = await call('POST', `/api/cases/${id}/notes`, { token: tokens.analyst, body: { text: '<img src=x onerror=alert(1)> check agent' } });
  assert.equal(xss.status, 201);
  assert.equal((await call('POST', `/api/cases/${id}/notes`, { token: tokens.analyst, body: { text: '   ' } })).status, 400);

  // analyst cannot file; must escalate
  assert.equal((await call('PATCH', `/api/cases/${id}`, { token: tokens.analyst, body: { status: 'SAR_FILED', reason: 'looks bad' } })).status, 409);
  const escalated = await call('PATCH', `/api/cases/${id}`, { token: tokens.analyst, body: { status: 'ESCALATED' } });
  assert.equal(escalated.json.case.status, 'ESCALATED');
  assert.equal((await call('PATCH', `/api/cases/${id}`, { token: tokens.analyst, body: { status: 'SAR_FILED', reason: 'looks bad' } })).status, 403);

  // admin needs a reason
  assert.equal((await call('PATCH', `/api/cases/${id}`, { token: tokens.admin, body: { status: 'SAR_FILED' } })).status, 400);
  const filed = await call('PATCH', `/api/cases/${id}`, { token: tokens.admin, body: { status: 'SAR_FILED', reason: 'Mule ring confirmed after KYC review.' } });
  assert.equal(filed.status, 200);
  assert.equal(filed.json.case.disposition, 'confirmed_suspicious');
  assert.equal(filed.json.case.decided_by, 'admin');

  // report: masked for the analyst, HTML-escaped, unmask refused for analyst
  const html = await call('GET', `/api/cases/${id}/report`, { token: tokens.analyst });
  assert.equal(html.status, 200);
  assert.ok(html.text.includes('Suspicious Transaction Report'));
  assert.ok(html.text.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert.ok(!html.text.includes('<img src=x'));
  assert.equal((await call('GET', `/api/cases/${id}/report?unmask=true`, { token: tokens.analyst })).status, 403);

  const json = await call('GET', `/api/cases/${id}/report?format=json`, { token: tokens.admin });
  assert.equal(json.json.report.subject.profile.masked, true);
  assert.ok(json.json.report.transactions.count > 0);
  assert.match(json.json.report.integrity.content_sha256, /^[0-9a-f]{64}$/);
  const unmasked = await call('GET', `/api/cases/${id}/report?format=json&unmask=true`, { token: tokens.admin });
  assert.equal(unmasked.json.report.subject.profile.masked, false);

  // labels and audit are admin-only
  assert.equal((await call('GET', '/api/cases/labels', { token: tokens.analyst })).status, 403);
  const labels = await call('GET', '/api/cases/labels', { token: tokens.admin });
  assert.deepEqual(labels.json.labels.map((l) => [l.account_id, l.label]), [['ACC_MULE_HUB', 1]]);

  const list = await call('GET', '/api/cases', { token: tokens.analyst });
  assert.equal(list.json.stats.by_status.SAR_FILED, 1);
});

test('uploading a dataset is admin-only', async () => {
  const res = await call('POST', '/api/pipeline/run', { token: tokens.analyst, body: { transactions: [{}] } });
  assert.equal(res.status, 403);
});

test('audit log: admin-only, chain verifies, tampering is detected', async () => {
  assert.equal((await call('GET', '/api/audit', { token: tokens.analyst })).status, 403);
  const res = await call('GET', '/api/audit', { token: tokens.admin });
  assert.equal(res.status, 200);
  assert.equal(res.json.integrity.valid, true);
  assert.ok(res.json.entries.length >= 10);
  const actions = new Set(res.json.entries.map((e) => e.action));
  for (const expected of ['AUTH_LOGIN', 'CASE_OPENED', 'CASE_STATUS_CHANGED', 'CASE_NOTE_ADDED', 'REPORT_EXPORTED', 'PII_REVEALED', 'ACCESS_DENIED']) {
    assert.ok(actions.has(expected), `missing audit action ${expected}`);
  }
  // no unmasked personal data in the log
  const raw = fs.readFileSync(path.join(dataDir, 'audit.jsonl'), 'utf-8');
  const profiles = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'data', 'synthetic', 'account_profiles.json'), 'utf-8'));
  const subject = profiles.ACC_MULE_HUB;
  for (const secret of [subject.phone, subject.national_id, subject.holder_name]) {
    assert.ok(!raw.includes(secret));
  }

  // edit one line on disk -> verification fails at that entry
  const lines = raw.trim().split('\n');
  const tampered = JSON.parse(lines[2]);
  tampered.actor = 'someone-else';
  lines[2] = JSON.stringify(tampered);
  const copy = path.join(dataDir, 'tampered.jsonl');
  fs.writeFileSync(copy, `${lines.join('\n')}\n`);
  const check = new AuditLog(copy).verify();
  assert.equal(check.valid, false);
  assert.equal(check.broken_at_seq, 3);

  // deleting a line is detected too
  const dropped = raw.trim().split('\n');
  dropped.splice(1, 1);
  fs.writeFileSync(copy, `${dropped.join('\n')}\n`);
  assert.equal(new AuditLog(copy).verify().valid, false);
});
