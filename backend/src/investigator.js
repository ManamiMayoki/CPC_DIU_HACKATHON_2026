/**
 * AI Investigator narrative.
 *
 * Every account already carries a rule-based briefing built by ml/investigator.py from its
 * computed evidence. When Claude API credentials are configured (ANTHROPIC_API_KEY), this
 * module asks Claude to rewrite that briefing as an analyst-style case narrative, using only
 * the facts the pipeline produced. Without credentials, or if the call fails, the rule-based
 * briefing is returned unchanged, so the demo works fully offline.
 */
const Anthropic = require('@anthropic-ai/sdk');

const MODEL = process.env.CLAUDE_MODEL || 'claude-opus-5-5';

const BRIEFING_SCHEMA = {
  type: 'object',
  properties: {
    headline: { type: 'string' },
    typology: { type: 'string' },
    summary: { type: 'string' },
    key_findings: { type: 'array', items: { type: 'string' } },
    next_steps: { type: 'array', items: { type: 'string' } },
  },
  required: ['headline', 'typology', 'summary', 'key_findings', 'next_steps'],
  additionalProperties: false,
};

const SYSTEM_PROMPT = `You are a financial-crime analyst at a Bangladeshi mobile financial services (MFS) provider.
You write short case briefings that help a compliance officer decide what to review first.

Use only the facts in the case data you are given: the risk score, detected patterns, evidence,
metrics and the draft briefing. Do not invent amounts, accounts, dates, names or events. Amounts are in BDT.
The data is synthetic and the scores are risk indicators, not proof of wrongdoing, so write
"indicates" or "is consistent with" rather than stating that a crime happened.

Write plain English a non-specialist can follow. The summary is 2 to 4 sentences. Give 3 to 6 key findings,
each one sentence citing a concrete number from the data. Give 3 to 6 next steps an MFS investigator can
actually take (KYC/NID, device or SIM linkage, agent cash-out records, transaction holds under internal
policy, a Suspicious Transaction Report to BFIU when warranted). Match the urgency to the risk level.`;

let client = null;
const cache = new Map();

function hasCredentials() {
  return Boolean(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN);
}

function getClient() {
  if (!client) {
    client = new Anthropic({ timeout: 45 * 1000, maxRetries: 1 });
  }
  return client;
}

function buildCaseData(account) {
  return {
    account_id: account.account_id,
    risk_score: account.risk_score,
    risk_level: account.risk_level,
    is_ml_anomaly: account.is_anomaly,
    patterns: account.patterns || [],
    scoring_breakdown: account.scoring_breakdown || {},
    evidence: account.evidence || [],
    graph_features: account.graph_features || {},
    behaviour_features: account.ml_features || {},
    draft_briefing: account.investigation || null,
  };
}

/**
 * Returns { investigation, source, note } for an account report from the pipeline.
 * source is "claude" when Claude wrote the narrative, otherwise "rule-based".
 */
async function investigateAccount(account, cacheKey) {
  const ruleBased = account.investigation || null;
  const fallback = (note) => ({ investigation: ruleBased, source: 'rule-based', note });

  if (!hasCredentials()) {
    return fallback('Claude narrative is off: set ANTHROPIC_API_KEY on the backend to enable it.');
  }
  if (cache.has(cacheKey)) {
    return cache.get(cacheKey);
  }

  try {
    const response = await getClient().beta.messages.create({
      model: MODEL,
      max_tokens: 4000,
      betas: ['server-side-fallback-2026-07-01'],
      fallbacks: 'default',
      output_config: {
        effort: 'low',
        format: { type: 'json_schema', schema: BRIEFING_SCHEMA },
      },
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: 'user',
          content: `Write the case briefing for this account.\n\n<case_data>\n${JSON.stringify(buildCaseData(account), null, 2)}\n</case_data>`,
        },
      ],
    });

    if (response.stop_reason === 'refusal') {
      return fallback('Claude declined this request, so the rule-based briefing is shown.');
    }
    if (response.stop_reason === 'max_tokens') {
      return fallback('Claude ran out of output space, so the rule-based briefing is shown.');
    }

    const text = response.content
      .filter((block) => block.type === 'text')
      .map((block) => block.text)
      .join('');
    const narrative = JSON.parse(text);

    const result = {
      investigation: {
        ...(ruleBased || {}),
        ...narrative,
        account_id: account.account_id,
        related_accounts: ruleBased?.related_accounts || [],
        caveat: ruleBased?.caveat ||
          'Generated from synthetic data and computed metrics. These are risk indicators, not proof of wrongdoing.',
        generated_by: 'claude',
      },
      source: 'claude',
      note: null,
    };
    cache.set(cacheKey, result);
    return result;
  } catch (err) {
    let reason = 'the Claude API call failed';
    if (err instanceof Anthropic.AuthenticationError) reason = 'the Claude API key was rejected';
    else if (err instanceof Anthropic.RateLimitError) reason = 'the Claude API rate limit was reached';
    else if (err instanceof Anthropic.APIConnectionError) reason = 'the Claude API could not be reached';
    else if (err instanceof Anthropic.APIError) reason = `the Claude API returned an error (${err.status})`;
    else if (err instanceof SyntaxError) reason = 'Claude returned a reply that could not be parsed';
    console.warn(`[AI Investigator] Falling back to rule-based briefing: ${reason}.`, err.message);
    return fallback(`Showing the rule-based briefing because ${reason}.`);
  }
}

function clearInvestigationCache() {
  cache.clear();
}

module.exports = { investigateAccount, clearInvestigationCache, hasCredentials, MODEL };
