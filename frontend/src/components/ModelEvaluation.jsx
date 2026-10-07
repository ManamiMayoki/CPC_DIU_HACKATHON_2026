import { useEffect, useState } from 'react';
import { BarChart3, AlertTriangle } from 'lucide-react';
import { fetchEvaluation } from '../services/api';

const pct = (v, digits = 1) => (v === null || v === undefined ? 'n/a' : `${(100 * v).toFixed(digits)}%`);
const BAR = '#38BDF8'; // one hue for every magnitude bar; text stays in text colours

const FAMILY_LABELS = {
  transactional: 'Transactional',
  temporal: 'Temporal',
  graph: 'Graph and flow tracing',
  neighbourhood: '2-hop neighbourhood',
  account_type: 'Account type',
};

function Panel({ title, subtitle, children }) {
  return (
    <div className="glass-panel" style={{ borderRadius: '18px', padding: '24px 26px', marginBottom: '22px' }}>
      <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#FFFFFF' }}>{title}</h3>
      {subtitle && <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '4px 0 16px', maxWidth: '900px' }}>{subtitle}</p>}
      {children}
    </div>
  );
}

function Tile({ value, label, note }) {
  return (
    <div className="glass-panel" style={{ borderRadius: '14px', padding: '16px 18px', minWidth: 0 }}>
      <div style={{ fontSize: '1.7rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>{value}</div>
      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>{label}</div>
      {note && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>{note}</div>}
    </div>
  );
}

/** Horizontal magnitude bar with the value written beside it. */
function ValueBar({ value, max = 1, text }) {
  const width = Math.max(0, Math.min(100, (100 * value) / (max || 1)));
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '150px' }} title={text}>
      <div style={{ flex: 1, height: '10px', background: 'rgba(255, 255, 255, 0.06)', borderRadius: '4px' }}>
        <div style={{ width: `${width}%`, height: '100%', background: BAR, borderRadius: '0 4px 4px 0' }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#FFFFFF', minWidth: '48px', textAlign: 'right' }}>{text}</span>
    </div>
  );
}

/** Table cell shaded by a 0-1 value (single hue, light to strong) with the number always visible. */
function HeatCell({ value }) {
  const v = value ?? 0;
  return (
    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: '#FFFFFF', background: `rgba(56, 189, 248, ${0.06 + 0.5 * v})`, borderLeft: '2px solid var(--surface-card)' }}>
      {pct(value, 0)}
    </td>
  );
}

const th = { padding: '10px 12px', fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right', whiteSpace: 'nowrap' };
const thLeft = { ...th, textAlign: 'left' };
const td = { padding: '9px 12px', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: '#E2E8F0', textAlign: 'right' };
const tdLeft = { ...td, textAlign: 'left', fontFamily: 'var(--font-body)', color: '#FFFFFF' };
const row = { borderBottom: '1px solid rgba(255, 255, 255, 0.05)' };

export default function ModelEvaluation() {
  const [results, setResults] = useState(undefined);

  useEffect(() => {
    fetchEvaluation().then(setResults);
  }, []);

  if (results === undefined) {
    return <div style={{ padding: '60px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading evaluation results…</div>;
  }
  const model = results?.model_evaluation;
  const bench = results?.benchmark;
  if (!model) {
    return <div style={{ padding: '60px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>No evaluation results found. Run <code>python -m ml.evaluation</code>.</div>;
  }

  const ds = model.dataset;
  const cmp = model.model_comparison;
  const best = cmp.gbm_graph;
  const rules = cmp.rules_baseline;
  const work = model.workload;
  const typologyModels = ['rules_baseline', 'graph_detectors', 'isolation_forest', 'gbm_tabular', 'gbm_graph'];
  const maxImportance = Math.max(...model.feature_importance.top_features.map((f) => f.importance));
  const biasModels = [['rules_baseline', 'Rules'], ['phase1_composite', 'Phase 1 score'], ['cygnus_composite', 'Current Cygnus score'], ['gbm_graph_no_account_type', 'GBM + graph, no account type'], ['gbm_graph', 'GBM + graph']];

  return (
    <section style={{ maxWidth: '1440px', margin: '0 auto', padding: '36px 24px' }}>
      <div style={{ marginBottom: '22px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--accent-cyan)', fontSize: '0.74rem', fontFamily: 'var(--font-mono)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>
          <BarChart3 size={14} />
          <span>Measured on held-out synthetic networks</span>
        </div>
        <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>Model Evaluation</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px', maxWidth: '900px' }}>{ds.description}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '14px', marginBottom: '22px' }}>
        <Tile value={ds.test_transactions_total.toLocaleString()} label="test transactions" note={`${ds.test_accounts_total.toLocaleString()} accounts, ${ds.test_suspicious_total} suspicious`} />
        <Tile value={best.pr_auc.mean.toFixed(3)} label="PR-AUC, graph model" note={`rules only: ${rules.pr_auc.mean.toFixed(3)}`} />
        <Tile value={pct(best.precision.mean)} label="precision" note={`rules only: ${pct(rules.precision.mean)}`} />
        <Tile value={pct(best.recall.mean)} label="recall" note={`rules only: ${pct(rules.recall.mean)}`} />
        <Tile value={pct(best.false_positive_rate.mean, 2)} label="false-positive rate" note={`rules only: ${pct(rules.false_positive_rate.mean, 2)}`} />
        <Tile value={pct(work.alert_reduction_at_equal_recall, 0)} label="fewer alerts at equal recall" note="graph model vs rules" />
      </div>

      <Panel title="Model comparison" subtitle="Mean over the held-out networks. PR-AUC is the headline because suspicious accounts are rare; it does not depend on the alert threshold.">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={row}>
                <th style={thLeft}>Model</th><th style={thLeft}>Type</th><th style={thLeft}>PR-AUC</th>
                <th style={th}>Precision</th><th style={th}>Recall</th><th style={th}>F1</th><th style={th}>False-positive rate</th><th style={th}>Alerts / 1,000 accounts</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(cmp).map(([name, m]) => (
                <tr key={name} style={{ ...row, background: name === 'gbm_graph' ? 'rgba(56, 189, 248, 0.07)' : 'transparent' }}>
                  <td style={tdLeft}>{m.label}</td>
                  <td style={{ ...tdLeft, color: 'var(--text-secondary)', fontSize: '0.78rem' }}>{m.kind}</td>
                  <td style={{ ...td, minWidth: '200px' }}><ValueBar value={m.pr_auc.mean} text={m.pr_auc.mean.toFixed(3)} /></td>
                  <td style={td}>{pct(m.precision.mean)}</td>
                  <td style={td}>{pct(m.recall.mean)}</td>
                  <td style={td}>{m.f1.mean.toFixed(3)}</td>
                  <td style={td}>{pct(m.false_positive_rate.mean, 2)}</td>
                  <td style={td}>{m.alerts_per_1000_accounts.mean.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Recall by typology: where graph intelligence catches what rules miss" subtitle={`Share of suspicious accounts of each typology that get an alert. Rules miss ${model.graph_vs_rules.missed_by_rules} of ${model.graph_vs_rules.suspicious_accounts} suspicious accounts; the graph model catches ${model.graph_vs_rules.of_those_caught_by_gbm_graph} of those.`}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={row}>
                <th style={thLeft}>Typology</th><th style={th}>Accounts</th>
                {typologyModels.map((m) => <th key={m} style={th}>{cmp[m].label}</th>)}
              </tr>
            </thead>
            <tbody>
              {Object.entries(model.recall_by_typology).map(([key, t]) => (
                <tr key={key} style={row}>
                  <td style={tdLeft}>{t.label}</td>
                  <td style={td}>{t.accounts}</td>
                  {typologyModels.map((m) => <HeatCell key={m} value={t.recall[m]} />)}
                </tr>
              ))}
              <tr style={row}>
                <td style={tdLeft}>Evasive variants (built to stay under rule thresholds)</td>
                <td style={td}>{model.recall_evasive_vs_plain.evasive_accounts}</td>
                {typologyModels.map((m) => <HeatCell key={m} value={model.recall_evasive_vs_plain.evasive[m]} />)}
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '22px' }}>
        <Panel title="What drives the model" subtitle={model.feature_importance.method}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              {model.feature_importance.top_features.slice(0, 12).map((f) => (
                <tr key={f.feature} style={row}>
                  <td style={{ ...tdLeft, fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{f.feature}</td>
                  <td style={{ ...tdLeft, color: 'var(--text-muted)', fontSize: '0.74rem' }}>{FAMILY_LABELS[f.family] || f.family}</td>
                  <td style={td}><ValueBar value={f.importance} max={maxImportance} text={f.importance.toFixed(3)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <div>
          <Panel title="What each feature family adds" subtitle="Same model, trained with more feature families each time. PR-AUC on the held-out networks.">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {model.feature_ablation.map((a) => (
                  <tr key={a.features} style={row}>
                    <td style={tdLeft}>{a.features}</td>
                    <td style={{ ...td, color: 'var(--text-muted)' }}>{a.n_features} features</td>
                    <td style={td}><ValueBar value={a.pr_auc_mean} text={a.pr_auc_mean.toFixed(3)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>

          <Panel title="Analyst workload" subtitle={`Assumes ${work.assumption_minutes_per_alert} minutes of review per alert. That is an assumption, not a pilot measurement.`}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr style={row}><th style={thLeft}> </th><th style={th}>Alerts</th><th style={th}>True positives</th><th style={th}>Analyst hours</th><th style={th}>Minutes per true positive</th></tr></thead>
              <tbody>
                <tr style={row}><td style={tdLeft}>Rules only</td><td style={td}>{work.rules.alerts.toLocaleString()}</td><td style={td}>{work.rules.true_positives}</td><td style={td}>{work.rules.analyst_hours.toFixed(0)}</td><td style={td}>{work.minutes_of_review_per_true_positive.rules.toFixed(0)}</td></tr>
                <tr style={row}><td style={tdLeft}>Graph model</td><td style={td}>{work.gbm_graph_at_operating_point.alerts.toLocaleString()}</td><td style={td}>{work.gbm_graph_at_operating_point.true_positives}</td><td style={td}>{work.gbm_graph_at_operating_point.analyst_hours.toFixed(0)}</td><td style={td}>{work.minutes_of_review_per_true_positive.gbm_graph.toFixed(0)}</td></tr>
              </tbody>
            </table>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '12px' }}>
              With the same number of alerts as the rules, the graph model reaches {pct(work.recall_gbm_at_rules_alert_budget)} recall (rules: {pct(work.rules.recall)}).
            </p>
          </Panel>
        </div>
      </div>

      <Panel title="Unseen typology test" subtitle="Each typology is removed from training in turn, then the model is tested on it. This asks whether the model can catch a laundering structure it has never seen.">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr style={row}><th style={thLeft}>Typology held out</th><th style={th}>Accounts</th><th style={th}>Graph model, never trained on it</th><th style={th}>Graph model, trained on it</th><th style={th}>IsolationForest</th><th style={th}>Graph detectors</th><th style={th}>Rules</th></tr></thead>
            <tbody>
              {Object.entries(model.unseen_typology).map(([key, t]) => (
                <tr key={key} style={row}>
                  <td style={tdLeft}>{t.label}</td><td style={td}>{t.accounts}</td>
                  <HeatCell value={t.recall_when_never_trained_on_it} /><HeatCell value={t.recall_when_trained_on_it} />
                  <HeatCell value={t.recall_isolation_forest} /><HeatCell value={t.recall_graph_detectors} /><HeatCell value={t.recall_rules} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {model.context_detectors && (
        <Panel title="Risk-area account takeover and hundi detectors" subtitle={model.context_detectors.note}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr style={row}><th style={thLeft}>Detector</th><th style={th}>True cases</th><th style={th}>Flagged</th><th style={th}>Precision</th><th style={th}>Recall</th><th style={th}>False-positive rate</th></tr></thead>
              <tbody>
                {['location_anomaly', 'takeover_collector', 'hundi_operator', 'hundi_funder'].map((key) => {
                  const d = model.context_detectors[key];
                  return (
                    <tr key={key} style={row}>
                      <td style={tdLeft}>{d.label}</td><td style={td}>{d.true_cases}</td><td style={td}>{d.flagged}</td>
                      <td style={td}>{pct(d.precision)}</td><td style={td}>{pct(d.recall)}</td><td style={td}>{pct(d.false_positive_rate, 3)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <ul style={{ margin: '14px 0 0', paddingLeft: '18px', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            <li>Customers who live in a risk area: {model.context_detectors.location_anomaly.legitimate_lookalikes.risk_area_residents_flagged} of {model.context_detectors.location_anomaly.legitimate_lookalikes.risk_area_residents.toLocaleString()} flagged.</li>
            <li>Customers who only visited a risk area: {model.context_detectors.location_anomaly.legitimate_lookalikes.risk_area_visitors_flagged} of {model.context_detectors.location_anomaly.legitimate_lookalikes.risk_area_visitors.toLocaleString()} flagged.</li>
            <li>Agents doing licensed remittance payout: {model.context_detectors.hundi_operator.legitimate_lookalikes.licensed_remittance_agents_flagged} of {model.context_detectors.hundi_operator.legitimate_lookalikes.licensed_remittance_agents} flagged.</li>
          </ul>
        </Panel>
      )}

      <Panel title="Bias check across account tiers" subtitle="False-positive rate: the share of legitimate accounts of each tier that get an alert. The check found that the Phase 1 score flagged almost every legitimate agent; the current score is tier-aware. District is never a model input.">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr style={row}><th style={thLeft}>Tier</th><th style={th}>Legitimate accounts</th>{biasModels.map(([, label]) => <th key={label} style={th}>{label}</th>)}</tr></thead>
            <tbody>
              {Object.entries(model.bias.by_account_tier).map(([tier, r]) => (
                <tr key={tier} style={row}>
                  <td style={{ ...tdLeft, textTransform: 'capitalize' }}>{tier}</td><td style={td}>{r.legitimate_accounts.toLocaleString()}</td>
                  {biasModels.map(([key]) => <td key={key} style={td}>{pct(r.false_positive_rate[key], 2)}</td>)}
                </tr>
              ))}
              <tr style={row}>
                <td style={tdLeft}>Largest gap between tiers</td><td style={td} />
                {biasModels.map(([key]) => <td key={key} style={{ ...td, color: '#FFFFFF', fontWeight: 700 }}>{model.bias.false_positive_rate_gap_between_tiers[key] ? `${model.bias.false_positive_rate_gap_between_tiers[key].gap_percentage_points.toFixed(2)} pts` : 'n/a'}</td>)}
              </tr>
            </tbody>
          </table>
        </div>
        <ul style={{ margin: '14px 0 0', paddingLeft: '18px', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          {Object.entries(model.bias.by_district_legitimate_personal_accounts).map(([name, r]) => (
            <li key={name}>
              {cmp[name]?.label || name}, by district ({r.districts} districts): false-positive rate {pct(r.min_false_positive_rate, 2)} to {pct(r.max_false_positive_rate, 2)}, chi-square p = {r.chi_square_p_value === null ? 'n/a' : r.chi_square_p_value.toFixed(3)} ({r.independent_of_district ? 'no evidence it depends on district' : 'depends on district'}).
            </li>
          ))}
        </ul>
      </Panel>

      {bench && (
        <Panel title="Throughput and latency" subtitle={`Measured on ${bench.machine}. ${bench.note}`}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr style={row}><th style={thLeft}>Path</th><th style={th}>Transactions</th><th style={th}>Accounts</th><th style={th}>Seconds</th><th style={thLeft}>Transactions / second</th></tr></thead>
              <tbody>
                {bench.scoring_path.map((r) => (
                  <tr key={`s${r.transactions}`} style={row}><td style={tdLeft}>Scoring path</td><td style={td}>{r.transactions.toLocaleString()}</td><td style={td}>{r.accounts.toLocaleString()}</td><td style={td}>{r.total_seconds.toFixed(2)}</td>
                    <td style={td}><ValueBar value={r.transactions_per_second} max={Math.max(...bench.scoring_path.map((x) => x.transactions_per_second))} text={Math.round(r.transactions_per_second).toLocaleString()} /></td></tr>
                ))}
                {bench.full_pipeline.map((r) => (
                  <tr key={`f${r.transactions}`} style={row}><td style={tdLeft}>Full pipeline with evidence text</td><td style={td}>{r.transactions.toLocaleString()}</td><td style={td}>{r.accounts.toLocaleString()}</td><td style={td}>{r.total_seconds.toFixed(2)}</td>
                    <td style={td}><ValueBar value={r.transactions_per_second} max={Math.max(...bench.scoring_path.map((x) => x.transactions_per_second))} text={Math.round(r.transactions_per_second).toLocaleString()} /></td></tr>
                ))}
              </tbody>
            </table>
          </div>
          {bench.api_latency && (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '18px' }}>
              <thead><tr style={row}><th style={thLeft}>API endpoint ({bench.api_latency.requests_per_endpoint} requests each)</th><th style={th}>p50 ms</th><th style={th}>p95 ms</th><th style={th}>p99 ms</th></tr></thead>
              <tbody>
                {bench.api_latency.endpoints.map((e) => (
                  <tr key={e.endpoint} style={row}><td style={{ ...tdLeft, fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{e.endpoint}</td><td style={td}>{e.p50_ms.toFixed(1)}</td><td style={td}>{e.p95_ms.toFixed(1)}</td><td style={td}>{e.p99_ms.toFixed(1)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      )}

      <Panel title="Limitations">
        <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.65 }}>
          {model.limitations.map((item) => (
            <li key={item}><AlertTriangle size={12} color="#F59E0B" style={{ verticalAlign: '-1px', marginRight: '6px' }} />{item}</li>
          ))}
        </ul>
      </Panel>
    </section>
  );
}
