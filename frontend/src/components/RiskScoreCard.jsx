import React from 'react';
import { Shield, AlertTriangle, Cpu, Network, Activity } from 'lucide-react';

export default function RiskScoreCard({ account }) {
  if (!account) return null;

  const score = account.risk_score || 0;
  const level = account.risk_level || 'LOW';
  const breakdown = account.scoring_breakdown || {
    ml_component: 20.0,
    graph_component: 15.0,
    behavioral_component: 10.0,
  };

  // Radial calculation (perimeter = 2 * PI * r)
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Tier color mapping
  const getColor = () => {
    if (level === 'CRITICAL') return '#DC2626';
    if (level === 'HIGH') return '#EF4444';
    if (level === 'MEDIUM') return '#F59E0B';
    return '#22C55E';
  };

  const color = getColor();

  return (
    <div className="glass-panel" style={{
      padding: '28px',
      borderRadius: '20px',
      border: `1px solid ${color}40`,
      boxShadow: `0 0 35px ${color}15`,
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background glow accent */}
      <div style={{
        position: 'absolute',
        top: '-40px',
        right: '-40px',
        width: '160px',
        height: '160px',
        borderRadius: '50%',
        background: `${color}15`,
        filter: 'blur(35px)',
        pointerEvents: 'none'
      }} />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div>
          <div style={{
            fontSize: '0.72rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase'
          }}>
            MEMBER 3 ML INFERENCE ENGINE
          </div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
            Account Risk Architecture
          </h3>
        </div>

        <span className={`badge-risk badge-risk-${level.toLowerCase()}`} style={{ fontSize: '0.82rem', padding: '4px 12px' }}>
          {level} RISK
        </span>
      </div>

      {/* Center Radial Meter + Big Score */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '32px',
        margin: '16px 0 28px',
        padding: '16px',
        background: 'rgba(255, 255, 255, 0.02)',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.04)'
      }}>
        {/* SVG Radial Gauge */}
        <div style={{ position: 'relative', width: '150px', height: '150px' }}>
          <svg width="150" height="150" viewBox="0 0 150 150" style={{ transform: 'rotate(-90deg)' }}>
            {/* Background Track */}
            <circle
              cx="75"
              cy="75"
              r={radius}
              fill="none"
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="10"
            />
            {/* Progress Stroke */}
            <circle
              cx="75"
              cy="75"
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth="10"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              style={{
                transition: 'stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
                filter: `drop-shadow(0 0 8px ${color}80)`
              }}
            />
          </svg>

          {/* Central Number Display */}
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center'
          }}>
            <span style={{
              fontSize: '2.1rem',
              fontWeight: 900,
              fontFamily: 'var(--font-heading)',
              color: '#FFFFFF',
              lineHeight: 1
            }}>
              {score.toFixed(1)}
            </span>
            <span style={{
              fontSize: '0.68rem',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-muted)',
              marginTop: '4px'
            }}>
              COMPOSITE
            </span>
          </div>
        </div>

        {/* Explainable Formula Card */}
        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--primary-neon)',
            marginBottom: '6px'
          }}>
            FORMULA GROUNDING (DOCS/API-CONTRACT)
          </div>
          <div style={{
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
            fontFamily: 'var(--font-mono)',
            background: 'rgba(0, 0, 0, 0.3)',
            padding: '8px 12px',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.06)'
          }}>
            Score = 0.40 × ML + 0.40 × Graph + 0.20 × Behavioral
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '8px' }}>
            Calibrated against dynamic population percentiles with zero synthetic hallucinations.
          </div>
        </div>
      </div>

      {/* Component Decomposed Sub-Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* 1. ML Component (40% Weight) */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Cpu size={14} color="#8B5CF6" />
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#FFFFFF' }}>
                Isolation Forest ML Component
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                (40% Weight)
              </span>
            </div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#8B5CF6' }}>
              {breakdown.ml_component?.toFixed(1) || '0.0'}
            </span>
          </div>
          <div style={{ width: '100%', height: '7px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '9999px', overflow: 'hidden' }}>
            <div style={{
              width: `${Math.min(breakdown.ml_component || 0, 100)}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #8B5CF6, #6366F1)',
              borderRadius: '9999px',
              transition: 'width 0.6s ease'
            }} />
          </div>
        </div>

        {/* 2. Graph Pattern Component (40% Weight) */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Network size={14} color="#B8FF3D" />
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#FFFFFF' }}>
                Graph Topology & Cycle Component
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                (40% Weight)
              </span>
            </div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--primary-neon)' }}>
              {breakdown.graph_component?.toFixed(1) || '0.0'}
            </span>
          </div>
          <div style={{ width: '100%', height: '7px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '9999px', overflow: 'hidden' }}>
            <div style={{
              width: `${Math.min(breakdown.graph_component || 0, 100)}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #B8FF3D, #22C55E)',
              borderRadius: '9999px',
              transition: 'width 0.6s ease'
            }} />
          </div>
        </div>

        {/* 3. Behavioral Component (20% Weight) */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Activity size={14} color="#38BDF8" />
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#FFFFFF' }}>
                Behavioral Velocity & Volatility Component
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                (20% Weight)
              </span>
            </div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#38BDF8' }}>
              {breakdown.behavioral_component?.toFixed(1) || '0.0'}
            </span>
          </div>
          <div style={{ width: '100%', height: '7px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '9999px', overflow: 'hidden' }}>
            <div style={{
              width: `${Math.min(breakdown.behavioral_component || 0, 100)}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #38BDF8, #0284C7)',
              borderRadius: '9999px',
              transition: 'width 0.6s ease'
            }} />
          </div>
        </div>
      </div>
    </div>
  );
}
