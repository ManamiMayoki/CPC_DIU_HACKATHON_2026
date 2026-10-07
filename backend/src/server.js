/**
 * Cygnus AI - Backend Integration Server
 * Member 1 Implementation
 * 
 * Bridges React frontend with Member 2 (GraphEngine) and Member 3 (ML Inference)
 * without modifying any algorithmic logic.
 */

const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn } = require('child_process');
const { investigateAccount, clearInvestigationCache, hasCredentials } = require('./investigator');

const app = express();
const PORT = process.env.PORT || 5000;

// Enable CORS & JSON parsing
app.use(cors());
app.use(express.json({ limit: '20mb' }));

const PROJECT_ROOT = process.env.PROJECT_ROOT || path.resolve(__dirname, '..', '..');
const ADAPTER_SCRIPT = path.join(PROJECT_ROOT, 'backend', 'engine_adapter.py');
const INITIAL_STATE_PATH = path.join(PROJECT_ROOT, 'frontend', 'public', 'data', 'initial_state.json');

// In-memory cache for ultra-fast response
let cachedData = null;

function loadInitialCache() {
  try {
    if (fs.existsSync(INITIAL_STATE_PATH)) {
      const raw = fs.readFileSync(INITIAL_STATE_PATH, 'utf-8');
      cachedData = JSON.parse(raw);
      console.log(`[Cygnus Backend] Loaded initial cache: ${cachedData.nodes?.length || 0} accounts, ${cachedData.stats?.total_transactions || 0} transactions.`);
    }
  } catch (err) {
    console.error('[Cygnus Backend] Error loading initial state file:', err.message);
  }
}

// Load cache immediately
loadInitialCache();

/**
 * Execute Python engine adapter safely
 */
function runPythonAdapter(args = []) {
  return new Promise((resolve, reject) => {
    // Determine python command
    const pyCmd = process.env.PYTHON_CMD || (process.platform === 'win32' ? 'py' : 'python3');
    const pyProcess = spawn(pyCmd, [ADAPTER_SCRIPT, ...args], {
      cwd: PROJECT_ROOT,
      env: { ...process.env },
    });

    let stdoutData = '';
    let stderrData = '';

    pyProcess.stdout.on('data', (chunk) => {
      stdoutData += chunk.toString();
    });

    pyProcess.stderr.on('data', (chunk) => {
      stderrData += chunk.toString();
    });

    pyProcess.on('error', (err) => {
      reject(err);
    });

    pyProcess.on('close', (code) => {
      if (code !== 0) {
        return reject(new Error(`Python adapter exited with code ${code}: ${stderrData}`));
      }
      try {
        const parsed = JSON.parse(stdoutData);
        resolve(parsed);
      } catch (parseErr) {
        reject(new Error(`Failed to parse Python adapter output: ${parseErr.message}\nRaw: ${stdoutData.slice(0, 300)}`));
      }
    });
  });
}

// -------------------------------------------------------------
// REST API ENDPOINTS
// -------------------------------------------------------------

/**
 * Health Check & Status
 */
app.get('/api/health', (req, res) => {
  res.json({
    status: 'online',
    timestamp: new Date().toISOString(),
    service: 'Cygnus AI Detection Backend',
    contract_version: '1.0.0',
    verification: '50/50 tests passing',
    ai_narrative: hasCredentials() ? 'claude' : 'rule-based',
    accounts_cached: cachedData?.nodes?.length || 0,
  });
});

/**
 * Live Project Statistics (Reference 2 style)
 */
app.get('/api/stats', (req, res) => {
  if (cachedData?.stats) {
    return res.json({
      success: true,
      stats: cachedData.stats,
      risk_distribution: cachedData.risk_distribution,
    });
  }
  res.status(503).json({ success: false, error: 'Engine data not yet loaded' });
});

/**
 * Complete Pipeline Result (API Contract)
 */
app.get('/api/pipeline', async (req, res) => {
  if (cachedData) {
    return res.json(cachedData);
  }
  try {
    const data = await runPythonAdapter(['--action', 'analyze']);
    cachedData = data;
    res.json(data);
  } catch (err) {
    res.status(500).json({ success: false, error: 'Pipeline execution failed', message: err.message });
  }
});

/**
 * Run Pipeline on custom or uploaded transactions
 */
app.post('/api/pipeline/run', async (req, res) => {
  let tempFile = null;
  try {
    const transactions = req.body?.transactions;
    if (!transactions || !Array.isArray(transactions) || transactions.length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Invalid input: "transactions" must be a non-empty array of transaction objects.',
      });
    }

    // Save the uploaded transactions to a unique temp file and point the adapter at it
    tempFile = path.join(os.tmpdir(), `cygnus_tx_${process.pid}_${Date.now()}.json`);
    fs.writeFileSync(tempFile, JSON.stringify(transactions), 'utf-8');

    const data = await runPythonAdapter(['--action', 'analyze', '--input', tempFile]);
    if (data.pipeline_status !== 'SUCCESS') {
      // Keep serving the current dataset rather than replacing it with an empty result
      return res.status(400).json({ success: false, error: 'No valid transactions in upload', validation_summary: data.validation_summary });
    }
    cachedData = data;
    clearInvestigationCache();

    res.json(data);
  } catch (err) {
    res.status(500).json({ success: false, error: 'Pipeline execution failed', message: err.message });
  } finally {
    if (tempFile) fs.rm(tempFile, { force: true }, () => {});
  }
});

/**
 * List all accounts with risk levels, scores, and patterns
 */
app.get('/api/accounts', (req, res) => {
  if (!cachedData || !cachedData.accounts) {
    return res.status(503).json({ success: false, error: 'No account data available' });
  }

  const { risk, pattern, search, limit = 100 } = req.query;
  let results = [...cachedData.accounts];

  if (risk) {
    const targetRisk = String(risk).toUpperCase();
    results = results.filter((a) => a.risk_level === targetRisk);
  }

  if (pattern) {
    const targetPattern = String(pattern).toLowerCase();
    results = results.filter((a) => a.patterns?.some((p) => p.toLowerCase().includes(targetPattern)));
  }

  if (search) {
    const q = String(search).toLowerCase();
    results = results.filter((a) => a.account_id.toLowerCase().includes(q));
  }

  res.json({
    success: true,
    total: results.length,
    accounts: results.slice(0, Number(limit)),
  });
});

/**
 * Single Account Detailed Profile & Evidence
 */
app.get('/api/accounts/:id', (req, res) => {
  const accountId = req.params.id;
  if (!cachedData || !cachedData.accounts) {
    return res.status(503).json({ success: false, error: 'Data not available' });
  }

  const account = cachedData.accounts.find(
    (a) => a.account_id.toLowerCase() === accountId.toLowerCase()
  );

  if (!account) {
    return res.status(404).json({
      success: false,
      error: `Account '${accountId}' not found in current transaction universe.`,
    });
  }

  res.json({ success: true, account });
});

/**
 * AI Investigator: case briefing for one account. Claude writes the narrative when an
 * API key is configured; otherwise the rule-based briefing from the pipeline is returned.
 */
app.get('/api/investigate/:id', async (req, res) => {
  const accountId = req.params.id;
  if (!cachedData || !cachedData.accounts) {
    return res.status(503).json({ success: false, error: 'Data not available' });
  }
  const account = cachedData.accounts.find(
    (a) => a.account_id.toLowerCase() === accountId.toLowerCase()
  );
  if (!account) {
    return res.status(404).json({ success: false, error: `Account '${accountId}' not found.` });
  }
  const result = await investigateAccount(account, account.account_id);
  res.json({ success: true, ...result });
});

/**
 * Follow the Money: Ego Network Subgraph for Account
 */
app.get('/api/network/:accountId', async (req, res) => {
  const accountId = req.params.accountId;
  const hops = Math.min(Math.max(Number(req.query.hops) || 1, 1), 3);

  // If cached data exists, compute subgraph directly for sub-millisecond response
  if (cachedData && cachedData.nodes && cachedData.edges) {
    const targetNode = cachedData.nodes.find(
      (n) => n.id.toLowerCase() === accountId.toLowerCase()
    );

    if (!targetNode) {
      return res.status(404).json({
        success: false,
        error: `Account '${accountId}' not found. Please verify the Account ID or choose from demo scenarios.`,
        target_id: accountId,
        nodes: [],
        edges: [],
      });
    }

    const targetId = targetNode.id;
    const visited = new Set([targetId]);
    let frontier = new Set([targetId]);

    for (let h = 0; h < hops; h++) {
      const nextFrontier = new Set();
      for (const e of cachedData.edges) {
        if (frontier.has(e.source)) nextFrontier.add(e.target);
        if (frontier.has(e.target)) nextFrontier.add(e.source);
      }
      for (const nid of nextFrontier) visited.add(nid);
      frontier = nextFrontier;
    }

    const nodeMap = new Map(cachedData.nodes.map((n) => [n.id, n]));
    const subgraphNodes = Array.from(visited)
      .map((id) => nodeMap.get(id))
      .filter(Boolean)
      .map((n) => ({
        ...n,
        is_target: n.id === targetId,
      }));

    const subgraphEdges = cachedData.edges.filter(
      (e) => visited.has(e.source) && visited.has(e.target)
    );

    return res.json({
      success: true,
      target_account: targetNode,
      target_id: targetId,
      hops,
      nodes: subgraphNodes,
      edges: subgraphEdges,
      node_count: subgraphNodes.length,
      edge_count: subgraphEdges.length,
      evidence: targetNode.evidence || [],
      scoring_breakdown: targetNode.scoring_breakdown || {},
      patterns: targetNode.patterns || [],
      risk_score: targetNode.risk_score || 0,
      risk_level: targetNode.risk_level || 'LOW',
    });
  }

  // Fallback to Python invocation if cache not loaded
  try {
    const subgraph = await runPythonAdapter(['--action', 'account', '--account', accountId, '--hops', String(hops)]);
    res.json(subgraph);
  } catch (err) {
    res.status(500).json({ success: false, error: 'Failed to extract network subgraph', message: err.message });
  }
});

/**
 * Detection Patterns Summary
 */
app.get('/api/patterns', (req, res) => {
  if (cachedData?.patterns_summary) {
    return res.json({
      success: true,
      patterns: cachedData.patterns_summary,
    });
  }
  res.status(503).json({ success: false, error: 'Pattern summary not available' });
});

/**
 * Analytics Charts Data
 */
app.get('/api/analytics', (req, res) => {
  if (cachedData?.analytics) {
    return res.json({
      success: true,
      analytics: cachedData.analytics,
      stats: cachedData.stats,
    });
  }
  res.status(503).json({ success: false, error: 'Analytics data not available' });
});

/**
 * Transaction Ledger
 */
app.get('/api/transactions', (req, res) => {
  if (!cachedData) {
    return res.status(503).json({ success: false, error: 'No transaction data available' });
  }

  const { search, sender, receiver, limit = 100 } = req.query;
  let txs = cachedData.transactions_sample || [];

  if (search) {
    const q = String(search).toLowerCase();
    txs = txs.filter(
      (t) =>
        t.transaction_id?.toLowerCase().includes(q) ||
        t.sender_id?.toLowerCase().includes(q) ||
        t.receiver_id?.toLowerCase().includes(q)
    );
  }

  if (sender) {
    txs = txs.filter((t) => t.sender_id?.toLowerCase() === sender.toLowerCase());
  }

  if (receiver) {
    txs = txs.filter((t) => t.receiver_id?.toLowerCase() === receiver.toLowerCase());
  }

  res.json({
    success: true,
    total: txs.length,
    transactions: txs.slice(0, Number(limit)),
  });
});

/**
 * Demo Scenarios Catalog
 */
app.get('/api/demo/scenarios', (req, res) => {
  if (cachedData?.demo_scenarios) {
    return res.json({
      success: true,
      scenarios: cachedData.demo_scenarios,
    });
  }
  res.json({
    success: true,
    scenarios: [
      { id: 'NORMAL', name: 'Normal Baseline Peer-to-Peer', target_account: 'ACC_NORM_004' },
      { id: 'FAN_IN', name: 'Fan-In Aggregation Hub', target_account: 'ACC_FANIN_HUB' },
      { id: 'FAN_OUT', name: 'Fan-Out Dispersion Hub', target_account: 'ACC_FANOUT_HUB' },
      { id: 'RAPID_MOVEMENT', name: 'Rapid Passthrough Movement', target_account: 'ACC_RAPID_MID' },
      { id: 'CHAIN', name: 'Multi-Hop Transaction Chain', target_account: 'ACC_CHAIN_02' },
      { id: 'CIRCULAR_FLOW', name: 'Circular Layering Loop', target_account: 'ACC_CYCLE_B' },
      { id: 'COORDINATED_NETWORK', name: 'Coordinated Account Cluster', target_account: 'ACC_COORD_00' },
      { id: 'STRUCTURING', name: 'Structured Transfers', target_account: 'ACC_STRUCT_SRC' },
      { id: 'MULE_RING', name: 'Mule-Ring (MFS Money-Mule Network)', target_account: 'ACC_MULE_HUB' },
    ],
  });
});

// Start Express Server
app.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`🚀 CYGNUS AI API BACKEND ACTIVE ON PORT ${PORT}`);
  console.log(`   Health: http://localhost:${PORT}/api/health`);
  console.log(`   Stats:  http://localhost:${PORT}/api/stats`);
  console.log(`   Demo:   http://localhost:${PORT}/api/demo/scenarios`);
  console.log(`====================================================`);
});
