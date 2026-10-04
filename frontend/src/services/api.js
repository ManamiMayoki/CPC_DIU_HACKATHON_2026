/**
 * FlowGuard AI - API Service Layer
 * Connects frontend to Express backend with resilient fallback to pre-computed state.
 */

const API_BASE = '/api';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) return await res.json();
  } catch (_) {}
  return { status: 'offline', accounts_cached: 57 };
}

export async function fetchInitialData() {
  // 1. Try live backend
  try {
    const res = await fetch(`${API_BASE}/pipeline`);
    if (res.ok) {
      const data = await res.json();
      if (data && data.nodes && data.nodes.length > 0) {
        return data;
      }
    }
  } catch (err) {
    console.warn('[FlowGuard API] Backend /api/pipeline not responding, using local fallback:', err.message);
  }

  // 2. Fallback to public initial state
  try {
    const res = await fetch('/data/initial_state.json');
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error('[FlowGuard API] Fallback file read error:', err.message);
  }

  throw new Error('Unable to load transaction network data from backend or local fallback.');
}

export async function fetchAccountNetwork(accountId, hops = 1) {
  try {
    const res = await fetch(`${API_BASE}/network/${encodeURIComponent(accountId)}?hops=${hops}`);
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
    const res = await fetch(`${API_BASE}/accounts/${encodeURIComponent(accountId)}`);
    if (res.ok) return await res.json();
  } catch (_) {}
  return { success: false, error: 'Account not found' };
}

export async function runCustomPipeline(transactions) {
  const res = await fetch(`${API_BASE}/pipeline/run`, {
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
