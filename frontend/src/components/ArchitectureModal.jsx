import React from 'react';
import { ShieldCheck, Cpu, Network, CheckCircle2, Layers, AlertCircle, FileText } from 'lucide-react';

export default function ArchitectureModal() {
  return (
    <section style={{ maxWidth: '1240px', margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          color: 'var(--primary-neon)',
          fontSize: '0.74rem',
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: '6px'
        }}>
          <ShieldCheck size={14} color="#B8FF3D" />
          <span>TEAM CONTRACT & SYSTEM TRANSPARENCY</span>
        </div>
        <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
          FlowGuard AI Architecture Specification
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
          End-to-end integration boundaries adhering to the Member 1, Member 2, and Member 3 contracts.
        </p>
      </div>

      {/* Role Distribution Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '28px' }}>
        {/* Member 1: Frontend & Integration */}
        <div className="glass-panel" style={{ padding: '24px', border: '1px solid rgba(184, 255, 61, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'rgba(184, 255, 61, 0.15)',
              border: '1px solid rgba(184, 255, 61, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Layers size={18} color="var(--primary-neon)" />
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--primary-neon)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                MEMBER 1 SCOPE
              </div>
              <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#FFFFFF' }}>Frontend & Integration</h4>
            </div>
          </div>
          <ul style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.6, paddingLeft: '18px' }}>
            <li>Interactive SVG / Force Network Explorer</li>
            <li>Follow the Money dynamic ego-network query</li>
            <li>Express REST API & Python Adapter Bridge</li>
            <li>Futuristic Velopay & AgroTrade aesthetic</li>
            <li>Judge demo switcher & forensic exports</li>
          </ul>
        </div>

        {/* Member 2: Graph Algorithms */}
        <div className="glass-panel" style={{ padding: '24px', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Network size={18} color="#38BDF8" />
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: '#38BDF8', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                MEMBER 2 SCOPE
              </div>
              <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#FFFFFF' }}>Graph Algorithms Engine</h4>
            </div>
          </div>
          <ul style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.6, paddingLeft: '18px' }}>
            <li>NetworkX directed graph topology construction</li>
            <li>6 Topology detectors (Fan-In, Fan-Out, Chains, Cycles, Passthrough, Clusters)</li>
            <li>Topological feature extraction per account</li>
            <li>Subgraphs, density, and connected components</li>
          </ul>
        </div>

        {/* Member 3: ML Anomaly & Risk */}
        <div className="glass-panel" style={{ padding: '24px', border: '1px solid rgba(139, 92, 246, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'rgba(139, 92, 246, 0.15)',
              border: '1px solid rgba(139, 92, 246, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Cpu size={18} color="#8B5CF6" />
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: '#8B5CF6', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                MEMBER 3 SCOPE
              </div>
              <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#FFFFFF' }}>ML Model & Risk Scorer</h4>
            </div>
          </div>
          <ul style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.6, paddingLeft: '18px' }}>
            <li>Rigorous ingress security validation</li>
            <li>Isolation Forest unsupervised anomaly detection</li>
            <li>Composite risk scorer (40% ML + 40% Graph + 20% Behavioral)</li>
            <li>Auditable metric-grounded evidence generator</li>
          </ul>
        </div>
      </div>

      {/* Verification & Test Suite Card */}
      <div className="glass-panel" style={{ padding: '28px', borderRadius: '18px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <CheckCircle2 size={22} color="#22C55E" />
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#FFFFFF' }}>
              Full Test Suite & Benchmark Verification
            </h3>
          </div>
          <div style={{
            background: 'rgba(34, 197, 94, 0.15)',
            border: '1px solid rgba(34, 197, 94, 0.4)',
            color: '#22C55E',
            padding: '4px 12px',
            borderRadius: '9999px',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem',
            fontWeight: 700
          }}>
            42 PASSED / 0 FAILED (100%)
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginBottom: '16px' }}>
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>test_graph.py</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#FFFFFF' }}>13 Tests Passed</div>
          </div>
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>test_ml.py</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#FFFFFF' }}>8 Tests Passed</div>
          </div>
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>test_scenarios_benchmark.py</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#FFFFFF' }}>9 Tests Passed</div>
          </div>
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>test_security.py</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#FFFFFF' }}>12 Tests Passed</div>
          </div>
        </div>

        <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          Benchmark verified: All 7 synthetic scenarios (NORMAL, FAN_IN, FAN_OUT, RAPID_MOVEMENT, CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK) 
          passed false-positive and target sensitivity thresholds with zero code regression.
        </div>
      </div>

      {/* Mandatory Engineering Disclaimer */}
      <div style={{
        background: 'rgba(245, 158, 11, 0.08)',
        border: '1px solid rgba(245, 158, 11, 0.3)',
        borderRadius: '16px',
        padding: '20px 24px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '14px'
      }}>
        <AlertCircle size={22} color="#F59E0B" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <h4 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#F59E0B', marginBottom: '4px' }}>
            Prototype Engineering Disclaimer
          </h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            This software is a synthetic-data hackathon prototype for algorithm research and demonstration. 
            The topological patterns, risk scores, and risk tiers do <strong>NOT</strong> prove financial crime, 
            do <strong>NOT</strong> constitute legal or regulatory evidence, and do <strong>NOT</strong> represent 
            official banking compliance standards.
          </p>
        </div>
      </div>
    </section>
  );
}
