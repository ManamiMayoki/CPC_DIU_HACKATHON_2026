/**
 * Cygnus AI - API Service Layer
 * Connects frontend to Express backend with resilient fallback to pre-computed state.
 */

const API_BASE = '/api';
const SESSION_KEY = 'cygnus_session';

// ---------------------------------------------------------------------------
// Session: the token lives in sessionStorage so it is gone when the tab closes
// ---------------------------------------------------------------------------
let session = null;
try {
  session = JSON.parse(window.sessionStorage.getItem(SESSION_KEY) || 'null');
} catch {
  session = null;
}

let onUnauthorized = () => {};
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

export function getSession() {
  return session;
}

function storeSession(next) {
  session = next;
  try {
    if (next) window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(next));
    else window.sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // storage unavailable: the session still works for this page load
  }
}

export function signOut() {
  storeSession(null);
}

async function authFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (session?.token) headers.Authorization = `Bearer ${session.token}`;
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 && session) {
    storeSession(null);
    onUnauthorized();
  }
  return res;
}

async function jsonRequest(method, path, body) {
  try {
    const res = await authFetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return { success: false, status: res.status, ...data, error: data.error || `Request failed (${res.status})` };
    return data;
  } catch (err) {
    return { success: false, error: `Backend not reachable (${err.message}).` };
  }
}

export async function fetchAuthConfig() {
  try {
    const res = await fetch(`${API_BASE}/auth/config`);
    if (res.ok) return await res.json();
  } catch {
    // fall through
  }
  return { success: false, demo_mode: false, offline: true };
}

export async function signIn(username, password) {
  const data = await jsonRequest('POST', '/auth/login', { username, password });
  if (data.success) storeSession({ token: data.token, user: data.user });
  return data;
}

export async function signInDemo(role) {
  const data = await jsonRequest('POST', '/auth/demo', { role });
  if (data.success) storeSession({ token: data.token, user: data.user });
  return data;
}

// ---------------------------------------------------------------------------
// Cases, KYC profile, audit log
// ---------------------------------------------------------------------------
export const fetchCases = () => jsonRequest('GET', '/cases');
export const fetchCase = (caseId) => jsonRequest('GET', `/cases/${encodeURIComponent(caseId)}`);
export const openCase = (accountId, note) => jsonRequest('POST', '/cases', { account_id: accountId, note });
export const addCaseNote = (caseId, text) => jsonRequest('POST', `/cases/${encodeURIComponent(caseId)}/notes`, { text });
export const updateCase = (caseId, changes) => jsonRequest('PATCH', `/cases/${encodeURIComponent(caseId)}`, changes);
export const fetchProfile = (accountId) => jsonRequest('GET', `/accounts/${encodeURIComponent(accountId)}/profile`);
export const revealProfile = (accountId, reason) =>
  jsonRequest('POST', `/accounts/${encodeURIComponent(accountId)}/profile/reveal`, { reason });
export const fetchAuditLog = () => jsonRequest('GET', '/audit?limit=300');

/** Opens the printable STR/SAR draft for a case in a new tab (fetched with the session token). */
export async function openCaseReport(caseId, { unmask = false } = {}) {
  try {
    const res = await authFetch(`${API_BASE}/cases/${encodeURIComponent(caseId)}/report${unmask ? '?unmask=true' : ''}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { success: false, error: err.error || 'Could not build the report.' };
    }
    const html = await res.text();
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    const opened = window.open(url, '_blank', 'noopener');
    if (!opened) {
      const link = document.createElement('a');
      link.href = url;
      link.download = `STR-DRAFT-${caseId}.html`;
      link.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    return { success: true };
  } catch (err) {
    return { success: false, error: `Backend not reachable (${err.message}).` };
  }
}

export async function fetchEvaluation() {
  try {
    const res = await fetch('/data/evaluation.json');
    if (res.ok) return await res.json();
  } catch {
    // fall through
  }
  return null;
}

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) return await res.json();
  } catch {
    // fall through to the offline default below
  }
  return { status: 'offline', accounts_cached: 0 };
}

export async function fetchInitialData() {
  // 1. Try live backend
  try {
    const res = await authFetch(`${API_BASE}/pipeline`);
    if (res.ok) {
      const data = await res.json();
      if (data && data.nodes && data.nodes.length > 0) {
        return data;
      }
    }
  } catch (err) {
    console.warn('[Cygnus API] Backend /api/pipeline not responding, using local fallback:', err.message);
  }

  // 2. Fallback to public initial state
  try {
    const res = await fetch('/data/initial_state.json');
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error('[Cygnus API] Fallback file read error:', err.message);
  }

  throw new Error('Unable to load transaction network data from backend or local fallback.');
}

export async function fetchAccountNetwork(accountId, hops = 1) {
  try {
    const res = await authFetch(`${API_BASE}/network/${encodeURIComponent(accountId)}?hops=${hops}`);
    if (res.ok) {
      return await res.json();
    }
    const errData = await res.json().catch(() => ({}));
    return {
      success: false,
      error: errData.error || `Account '${accountId}' not found in transaction network.`,
    };
  } catch (err) {
    return {
      success: false,
      error: `Network error connecting to backend: ${err.message}`,
    };
  }
}

export async function fetchAccountDetails(accountId) {
  try {
    const res = await authFetch(`${API_BASE}/accounts/${encodeURIComponent(accountId)}`);
    if (res.ok) return await res.json();
  } catch {
    // fall through to the offline default below
  }
  return { success: false, error: 'Account not found' };
}

export async function fetchInvestigation(accountId) {
  try {
    const res = await authFetch(`${API_BASE}/investigate/${encodeURIComponent(accountId)}`);
    if (res.ok) return await res.json();
    const errData = await res.json().catch(() => ({}));
    return { success: false, error: errData.error || 'Investigation request failed' };
  } catch (err) {
    return { success: false, error: `Backend not reachable (${err.message}); showing the offline briefing.` };
  }
}

export async function runCustomPipeline(transactions) {
  const res = await authFetch(`${API_BASE}/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transactions }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || 'Pipeline execution failed');
  }
  return await res.json();
}
