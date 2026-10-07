import { Zap } from 'lucide-react';

export default function DemoScenarioBar({
  scenarios = [],
  activeScenarioId,
  onSelectScenario
}) {
  return (
    <div className="glass-panel" style={{
      maxWidth: '1440px',
      margin: '0 auto 24px',
      padding: '16px 20px',
      borderRadius: '16px',
      border: '1px solid rgba(139, 92, 246, 0.35)',
      background: 'linear-gradient(90deg, rgba(13, 17, 26, 0.95), rgba(18, 24, 38, 0.95))',
      boxShadow: '0 8px 30px rgba(0, 0, 0, 0.4)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        {/* Left Label */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'rgba(184, 255, 61, 0.15)',
            border: '1px solid rgba(184, 255, 61, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Zap size={16} color="var(--primary-neon)" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--primary-neon)', fontWeight: 700 }}>
              HACKATHON JUDGE DEMO MODE
            </div>
            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#FFFFFF' }}>
              Select Controlled Test Topology
            </div>
          </div>
        </div>

        {/* Horizontal Scenario Buttons */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap'
        }}>
          {scenarios.map((sc) => {
            const isActive = activeScenarioId === sc.id;
            return (
              <button
                key={sc.id}
                onClick={() => onSelectScenario(sc)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 14px',
                  borderRadius: '9999px',
                  border: isActive ? '1px solid var(--primary-neon)' : '1px solid rgba(255, 255, 255, 0.1)',
                  background: isActive ? 'rgba(184, 255, 61, 0.18)' : 'rgba(255, 255, 255, 0.03)',
                  color: isActive ? 'var(--primary-neon)' : '#FFFFFF',
                  fontFamily: 'var(--font-heading)',
                  fontSize: '0.8rem',
                  fontWeight: isActive ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.18s ease',
                  boxShadow: isActive ? '0 0 16px rgba(184, 255, 61, 0.25)' : 'none'
                }}
              >
                <span style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: sc.severity === 'CRITICAL' ? '#EF4444' : sc.severity === 'HIGH' ? '#EF4444' : sc.severity === 'MEDIUM' ? '#F59E0B' : '#22C55E'
                }} />
                <span>{sc.name.split(' ')[0]}</span>
                <span style={{
                  fontSize: '0.68rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                  marginLeft: '2px'
                }}>
                  ({sc.target_account})
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
