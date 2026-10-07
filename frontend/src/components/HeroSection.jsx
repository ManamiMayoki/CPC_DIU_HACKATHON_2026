import { useEffect, useRef } from 'react';
import { ArrowRight, Shield, Zap, Activity, Lock, Layers } from 'lucide-react';

export default function HeroSection({
  stats,
  nodes = [],
  onStartInvestigation,
  onExploreNetwork,
  onSelectAccount
}) {
  const canvasRef = useRef(null);

  // Highest-risk account in the current dataset drives the "flagged" card
  const topNode = nodes.reduce(
    (best, n) => (!best || (n.risk_score ?? 0) > (best.risk_score ?? 0) ? n : best),
    null
  );
  const topId = topNode?.id || 'ACC_MULE_HUB';

  // Animated Network Canvas on Hero background/foreground
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    // Use actual nodes from project data or fallback sample
    const sampleNodes = nodes.length > 0 ? nodes.slice(0, 22) : [
      { id: 'ACC_MULE_HUB', risk_score: 97.1, risk_level: 'CRITICAL', patterns: ['fan_in', 'rapid_movement', 'structuring'] },
      { id: 'ACC_MULE_CASHOUT', risk_score: 95.2, risk_level: 'CRITICAL', patterns: ['structuring'] },
      { id: 'ACC_STRUCT_SRC', risk_score: 60.0, risk_level: 'MEDIUM', patterns: ['structuring'] },
      { id: 'ACC_FANIN_HUB', risk_score: 60.0, risk_level: 'MEDIUM', patterns: ['fan_in'] },
      { id: 'ACC_FANOUT_HUB', risk_score: 60.0, risk_level: 'MEDIUM', patterns: ['fan_out'] },
      { id: 'ACC_CYCLE_B', risk_score: 44.4, risk_level: 'MEDIUM', patterns: ['circular_flow'] },
      { id: 'ACC_COORD_00', risk_score: 40.0, risk_level: 'MEDIUM', patterns: ['coordinated_network'] },
      { id: 'ACC_NORM_004', risk_score: 18.2, risk_level: 'LOW', patterns: [] },
      { id: 'ACC_NORM_021', risk_score: 22.1, risk_level: 'LOW', patterns: [] },
    ];

    // Position particles in a spherical/orbital layout
    const width = canvas.width = canvas.parentElement.clientWidth;
    const height = canvas.height = canvas.parentElement.clientHeight;

    const centerX = width * 0.52;
    const centerY = height * 0.52;
    const radius = Math.min(width, height) * 0.38;

    const particles = sampleNodes.map((node, i) => {
      const angle = (i / sampleNodes.length) * Math.PI * 2;
      const r = radius * (0.45 + (i % 3) * 0.28);
      return {
        ...node,
        x: centerX + Math.cos(angle) * r,
        y: centerY + Math.sin(angle) * r,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        baseX: centerX + Math.cos(angle) * r,
        baseY: centerY + Math.sin(angle) * r,
        size: node.patterns?.length > 0 ? 11 : 7,
        color: node.risk_level === 'CRITICAL' ? '#EF4444' 
          : node.risk_level === 'HIGH' ? '#EF4444' 
          : node.risk_level === 'MEDIUM' ? '#F59E0B' 
          : '#64748B',
      };
    });

    // Particle flow packets along edges
    const flowPackets = [];
    for (let i = 0; i < 16; i++) {
      flowPackets.push({
        sourceIdx: Math.floor(Math.random() * particles.length),
        targetIdx: Math.floor(Math.random() * particles.length),
        progress: Math.random(),
        speed: 0.006 + Math.random() * 0.008,
      });
    }

    let time = 0;

    const render = () => {
      time += 0.02;
      ctx.clearRect(0, 0, width, height);

      // Draw subtle orbital arc grid (Velopay world network motif)
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(184, 255, 61, 0.05)';
      ctx.lineWidth = 1;
      ctx.arc(centerX, centerY + radius * 0.8, radius * 1.5, Math.PI * 1.1, Math.PI * 1.9);
      ctx.stroke();

      ctx.beginPath();
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.06)';
      ctx.arc(centerX, centerY + radius * 0.9, radius * 1.8, Math.PI * 1.15, Math.PI * 1.85);
      ctx.stroke();

      // Draw connected edges
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < radius * 0.95) {
            const hasSuspicious = particles[i].patterns?.length > 0 || particles[j].patterns?.length > 0;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);

            if (hasSuspicious) {
              ctx.strokeStyle = `rgba(245, 158, 11, ${0.35 - (dist / (radius * 0.95)) * 0.25})`;
              ctx.lineWidth = 1.6;
            } else {
              ctx.strokeStyle = `rgba(184, 255, 61, ${0.16 - (dist / (radius * 0.95)) * 0.12})`;
              ctx.lineWidth = 0.9;
            }
            ctx.stroke();
          }
        }
      }

      // Draw flowing packets
      flowPackets.forEach((p) => {
        p.progress += p.speed;
        if (p.progress >= 1) {
          p.progress = 0;
          p.sourceIdx = Math.floor(Math.random() * particles.length);
          p.targetIdx = Math.floor(Math.random() * particles.length);
        }

        const s = particles[p.sourceIdx];
        const t = particles[p.targetIdx];
        if (!s || !t) return;

        const curX = s.x + (t.x - s.x) * p.progress;
        const curY = s.y + (t.y - s.y) * p.progress;

        ctx.beginPath();
        ctx.arc(curX, curY, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = '#B8FF3D';
        ctx.shadowColor = '#B8FF3D';
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // Draw nodes
      particles.forEach((p, idx) => {
        p.x = p.baseX + Math.sin(time + idx) * 8;
        p.y = p.baseY + Math.cos(time + idx * 0.7) * 8;

        const isSuspicious = p.patterns && p.patterns.length > 0;

        // Glow ring for suspicious nodes
        if (isSuspicious) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size + 6 + Math.sin(time * 3 + idx) * 3, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.4)';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = isSuspicious ? 16 : 8;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Inner core
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 0.45, 0, Math.PI * 2);
        ctx.fillStyle = '#FFFFFF';
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [nodes]);

  return (
    <section style={{
      position: 'relative',
      minHeight: '88vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden',
      padding: '40px 24px',
      background: 'radial-gradient(circle at 50% 20%, rgba(184, 255, 61, 0.08) 0%, rgba(139, 92, 246, 0.06) 35%, transparent 75%)'
    }}>
      {/* Background Interactive Network Canvas */}
      <div style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 1,
        opacity: 0.85
      }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
      </div>

      <div style={{
        position: 'relative',
        zIndex: 10,
        maxWidth: '1360px',
        width: '100%',
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: '1.15fr 0.85fr',
        gap: '40px',
        alignItems: 'center'
      }}>
        {/* Left Column: Bold Hero Typography & CTAs */}
        <div>
          {/* Eyebrow Pill */}
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(184, 255, 61, 0.1)',
            border: '1px solid rgba(184, 255, 61, 0.35)',
            borderRadius: '9999px',
            padding: '6px 16px',
            marginBottom: '24px'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: 'var(--primary-neon)',
              boxShadow: '0 0 10px var(--primary-neon)'
            }} />
            <span style={{
              color: 'var(--primary-neon)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase'
            }}>
              AI-POWERED TRANSACTION NETWORK INTELLIGENCE
            </span>
          </div>

          {/* Large Bold Headline */}
          <h1 style={{
            fontSize: 'clamp(3rem, 6.5vw, 5.2rem)',
            fontWeight: 900,
            lineHeight: 1.02,
            letterSpacing: '-0.04em',
            color: '#FFFFFF',
            marginBottom: '24px'
          }}>
            FOLLOW THE <br />
            <span style={{
              background: 'linear-gradient(90deg, #B8FF3D 0%, #A3E635 40%, #38BDF8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '0 0 40px rgba(184, 255, 61, 0.35)'
            }}>
              MONEY.
            </span>
          </h1>

          {/* Subheading */}
          <p style={{
            fontSize: 'clamp(1.05rem, 1.4vw, 1.25rem)',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
            maxWidth: '560px',
            marginBottom: '36px'
          }}>
            Detect suspicious transaction networks before they become financial threats. 
            Cygnus AI applies topological graph algorithms and explainable machine learning 
            to uncover hidden layering, rapid movement, and coordinated illicit networks.
          </p>

          {/* Call to Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <button
              onClick={onStartInvestigation}
              className="btn-primary"
              style={{ fontSize: '1.05rem', padding: '14px 32px' }}
            >
              <span>Start Investigation</span>
              <ArrowRight size={18} />
            </button>

            <button
              onClick={onExploreNetwork}
              className="btn-secondary"
              style={{ fontSize: '1.05rem', padding: '14px 28px' }}
            >
              <Layers size={18} color="var(--primary-neon)" />
              <span>Explore Network</span>
            </button>
          </div>

          {/* Micro Trust Indicators */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '24px',
            marginTop: '44px',
            paddingTop: '24px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={16} color="#B8FF3D" />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                40/40/20 Multi-Signal Grounding
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Lock size={16} color="#8B5CF6" />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Deterministic Reproducibility
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={16} color="#38BDF8" />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Zero Fake Scores
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Floating Glassmorphism Intelligence Cards (Velopay Inspired) */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '18px',
          position: 'relative'
        }}>
          {/* Card 1: Live Network Monitor Card */}
          <div 
            onClick={() => onSelectAccount && onSelectAccount(topId)}
            className="glass-panel glass-panel-hover" 
            style={{
              padding: '24px',
              border: '1px solid rgba(184, 255, 61, 0.35)',
              boxShadow: '0 0 35px rgba(184, 255, 61, 0.12)',
              cursor: 'pointer'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: '#22C55E',
                  boxShadow: '0 0 10px #22C55E'
                }} />
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  LIVE NETWORK STATUS
                </span>
              </div>
              <span className={`badge-risk badge-risk-${(topNode?.risk_level || 'critical').toLowerCase()}`}>{topNode?.risk_level || 'FLAGGED'} ALERT</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '6px' }}>
              <span style={{ fontSize: '2.5rem', fontWeight: 900, fontFamily: 'var(--font-heading)', color: '#FFFFFF' }}>
                {stats?.total_accounts ?? 0}
              </span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                Monitored Accounts
              </span>
            </div>

            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Continuously parsing directed edges across peer-to-peer and merchant volumes.
            </p>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 14px',
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '10px',
              border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Top Alert: <strong style={{ color: 'var(--primary-neon)', fontFamily: 'var(--font-mono)' }}>{topId}</strong>
              </span>
              <span style={{ fontSize: '0.82rem', color: '#EF4444', fontWeight: 600 }}>
                Risk: {topNode ? `${Number(topNode.risk_score).toFixed(1)}/100` : 'n/a'}
              </span>
            </div>
          </div>

          {/* Card 2: Rapid Movement Passthrough Alert (Velopay transfer comparison motif) */}
          <div 
            onClick={() => onSelectAccount && onSelectAccount('ACC_RAPID_MID')}
            className="glass-panel glass-panel-hover" 
            style={{
              padding: '22px',
              border: '1px solid rgba(139, 92, 246, 0.3)',
              boxShadow: '0 0 30px rgba(139, 92, 246, 0.1)',
              cursor: 'pointer'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Zap size={16} color="#8B5CF6" />
                <span style={{ fontSize: '0.76rem', fontFamily: 'var(--font-mono)', color: '#8B5CF6', fontWeight: 600 }}>
                  RAPID MOVEMENT DETECTED
                </span>
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Latency: 300s
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: '12px' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Incoming Transfer</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>৳5,000.00</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--primary-neon)', fontFamily: 'var(--font-mono)' }}>ACC_RAPID_IN</div>
              </div>

              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <ArrowRight size={16} color="#EF4444" />
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Outgoing Forward (95%)</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#EF4444', fontFamily: 'var(--font-mono)' }}>৳4,750.00</div>
                <div style={{ fontSize: '0.68rem', color: '#EF4444', fontFamily: 'var(--font-mono)' }}>ACC_RAPID_OUT</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
