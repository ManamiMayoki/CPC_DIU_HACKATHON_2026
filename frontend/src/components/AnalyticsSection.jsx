import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { TrendingUp, BarChart2, PieChart as PieIcon } from 'lucide-react';

// Custom Dark Tooltip
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'rgba(13, 17, 26, 0.95)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        padding: '10px 14px',
        borderRadius: '10px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.8rem'
      }}>
        <div style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>{label}</div>
        {payload.map((entry, index) => (
          <div key={`item-${index}`} style={{ color: entry.color || '#FFFFFF', fontWeight: 700 }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function AnalyticsSection({ analytics = {}, riskDistribution = {} }) {
  // Volume Timeline Data
  const volumeData = analytics.volume_timeline && analytics.volume_timeline.length > 0
    ? analytics.volume_timeline
    : [];

  // Risk Distribution Data
  const riskPieData = [
    { name: 'Low Risk', value: riskDistribution.LOW ?? 0, color: '#22C55E' },
    { name: 'Medium Risk', value: riskDistribution.MEDIUM ?? 0, color: '#F59E0B' },
    { name: 'High Risk', value: riskDistribution.HIGH ?? 0, color: '#EF4444' },
    { name: 'Critical Risk', value: riskDistribution.CRITICAL ?? 0, color: '#DC2626' },
  ].filter(d => d.value > 0);

  // Pattern Frequency Data
  const patternData = analytics.pattern_frequency && analytics.pattern_frequency.length > 0
    ? analytics.pattern_frequency
    : [];

  return (
    <section style={{ maxWidth: '1440px', margin: '0 auto', padding: '36px 24px' }}>
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
          <TrendingUp size={14} color="#B8FF3D" />
          <span>FUTURISTIC ANALYTICS (INSPIRED BY AGROTRADE)</span>
        </div>
        <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
          Network & Financial Analytics
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
          Real-time transaction volume telemetry, risk score distributions, and pattern frequency metrics.
        </p>
      </div>

      {/* Grid of Analytics Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '24px', marginBottom: '24px' }}>
        {/* Chart 1: Volume Over Time (Glowing Trading Curve style) */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: '18px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                background: 'rgba(56, 189, 248, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <TrendingUp size={18} color="#38BDF8" />
              </div>
              <div>
                <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#FFFFFF' }}>Transaction Volume Over Time</h4>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Chronological monetary movement (BDT)</span>
              </div>
            </div>

            <div style={{
              fontSize: '0.74rem',
              fontFamily: 'var(--font-mono)',
              color: 'var(--primary-neon)',
              background: 'rgba(184, 255, 61, 0.1)',
              padding: '4px 10px',
              borderRadius: '9999px',
              border: '1px solid rgba(184, 255, 61, 0.3)'
            }}>
              LIVE FLOW
            </div>
          </div>

          <div style={{ width: '100%', height: '280px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={volumeData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                <defs>
                  <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.45} />
                    <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="time" 
                  stroke="#475569" 
                  fontSize={11} 
                  tickLine={false} 
                  fontFamily="var(--font-mono)" 
                />
                <YAxis 
                  stroke="#475569" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false} 
                  fontFamily="var(--font-mono)" 
                />
                <Tooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="volume" 
                  name="Volume (BDT)" 
                  stroke="#38BDF8" 
                  strokeWidth={2.5} 
                  fillOpacity={1} 
                  fill="url(#volumeGradient)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Risk Score Distribution (Donut Chart) */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: '18px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              background: 'rgba(245, 158, 11, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <PieIcon size={18} color="#F59E0B" />
            </div>
            <div>
              <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#FFFFFF' }}>Risk Tier Distribution</h4>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Low, Medium, High & Critical Accounts</span>
            </div>
          </div>

          <div style={{ width: '100%', height: '280px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={95}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {riskPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend 
                  verticalAlign="bottom" 
                  iconType="circle"
                  wrapperStyle={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }} 
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Chart 3: Detection Pattern Frequency (Horizontal Bar Chart) */}
      <div className="glass-panel" style={{ padding: '24px', borderRadius: '18px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div style={{
            width: '34px',
            height: '34px',
            borderRadius: '8px',
            background: 'rgba(184, 255, 61, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <BarChart2 size={18} color="#B8FF3D" />
          </div>
          <div>
            <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#FFFFFF' }}>Detection Pattern Frequency</h4>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Number of accounts flagged per topology detector</span>
          </div>
        </div>

        <div style={{ width: '100%', height: '240px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={patternData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <XAxis dataKey="pattern" stroke="#475569" fontSize={11} tickLine={false} fontFamily="var(--font-mono)" />
              <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} fontFamily="var(--font-mono)" />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" name="Flagged Accounts" fill="#B8FF3D" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
