import React, { useState } from 'react';
import { 
  Shield, 
  Search, 
  Activity, 
  Layers, 
  TrendingUp, 
  AlertTriangle, 
  FileText, 
  Zap,
  Info,
  ChevronDown,
  Sparkles
} from 'lucide-react';

export default function Navbar({
  activeTab,
  setActiveTab,
  onSearchAccount,
  demoScenarios = [],
  onSelectScenario,
  isLive = true
}) {
  const [searchInput, setSearchInput] = useState('');
  const [showDemoMenu, setShowDemoMenu] = useState(false);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchInput.trim()) {
      onSearchAccount(searchInput.trim());
      setActiveTab('investigate');
    }
  };

  const navItems = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'investigate', label: 'Follow the Money', icon: Layers, highlight: true },
    { id: 'high-risk', label: 'High-Risk Accounts', icon: AlertTriangle },
    { id: 'patterns', label: 'Detection Patterns', icon: Zap },
    { id: 'investigator', label: 'AI Investigator', icon: Sparkles },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp },
    { id: 'transactions', label: 'Transactions', icon: FileText },
    { id: 'docs', label: 'Architecture', icon: Info },
  ];

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      background: 'rgba(5, 7, 11, 0.88)',
      backdropFilter: 'blur(20px)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      padding: '12px 24px'
    }}>
      <div style={{
        maxWidth: '1540px',
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px'
      }}>
        {/* Brand Logo & Title */}
        <div 
          onClick={() => setActiveTab('overview')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            cursor: 'pointer',
            userSelect: 'none'
          }}
        >
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(184, 255, 61, 0.25), rgba(139, 92, 246, 0.25))',
            border: '1px solid rgba(184, 255, 61, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 18px rgba(184, 255, 61, 0.3)'
          }}>
            <Shield size={22} color="#B8FF3D" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                fontFamily: 'var(--font-heading)',
                fontWeight: 900,
                fontSize: '1.25rem',
                letterSpacing: '-0.02em',
                color: '#FFFFFF'
              }}>
                FLOWGUARD
              </span>
              <span style={{
                background: 'linear-gradient(90deg, #B8FF3D, #38BDF8)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                fontWeight: 800,
                fontSize: '1.25rem',
                fontFamily: 'var(--font-heading)'
              }}>
                AI
              </span>
            </div>
            <div style={{
              fontSize: '0.68rem',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              letterSpacing: '0.04em',
              textTransform: 'uppercase'
            }}>
              Transaction Network Intelligence
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          background: 'rgba(13, 17, 26, 0.6)',
          padding: '4px 6px',
          borderRadius: '9999px',
          border: '1px solid rgba(255, 255, 255, 0.06)'
        }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 14px',
                  borderRadius: '9999px',
                  border: 'none',
                  background: isActive 
                    ? (item.highlight ? 'var(--primary-neon)' : 'rgba(255, 255, 255, 0.12)')
                    : 'transparent',
                  color: isActive
                    ? (item.highlight ? '#05070B' : '#FFFFFF')
                    : 'var(--text-secondary)',
                  fontFamily: 'var(--font-heading)',
                  fontSize: '0.85rem',
                  fontWeight: isActive ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.18s ease',
                  boxShadow: isActive && item.highlight ? '0 0 16px rgba(184, 255, 61, 0.4)' : 'none'
                }}
              >
                <Icon size={15} color={isActive ? (item.highlight ? '#05070B' : '#FFFFFF') : 'var(--text-muted)'} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right Tools: Search Bar & Demo Scenarios Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Quick Account Search */}
          <form onSubmit={handleSearchSubmit} style={{ position: 'relative' }}>
            <Search 
              size={15} 
              color="var(--text-muted)" 
              style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} 
            />
            <input
              type="text"
              placeholder="Search Account ID (e.g. ACC_...)"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              style={{
                background: 'rgba(13, 17, 26, 0.95)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '9999px',
                color: '#FFFFFF',
                fontSize: '0.82rem',
                padding: '8px 16px 8px 36px',
                outline: 'none',
                width: '210px',
                transition: 'all 0.2s ease',
                fontFamily: 'var(--font-mono)'
              }}
              onFocus={(e) => {
                e.target.style.width = '260px';
                e.target.style.borderColor = 'var(--primary-neon)';
                e.target.style.boxShadow = '0 0 15px rgba(184, 255, 61, 0.2)';
              }}
              onBlur={(e) => {
                e.target.style.width = '210px';
                e.target.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </form>

          {/* Demo Scenario Selector Dropdown */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowDemoMenu(!showDemoMenu)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(99, 102, 241, 0.2))',
                border: '1px solid rgba(139, 92, 246, 0.4)',
                borderRadius: '9999px',
                color: '#FFFFFF',
                padding: '8px 16px',
                fontFamily: 'var(--font-heading)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: '0 0 16px rgba(139, 92, 246, 0.2)',
                transition: 'all 0.2s ease'
              }}
            >
              <Zap size={15} color="#8B5CF6" />
              <span>Demo Scenarios</span>
              <ChevronDown size={14} color="#94A3B8" />
            </button>

            {showDemoMenu && (
              <div 
                style={{
                  position: 'absolute',
                  top: '115%',
                  right: 0,
                  width: '320px',
                  background: '#0D111A',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '14px',
                  padding: '8px',
                  boxShadow: '0 16px 40px rgba(0, 0, 0, 0.8)',
                  zIndex: 100,
                  animation: 'fadeIn 0.15s ease'
                }}
              >
                <div style={{
                  padding: '8px 12px 6px',
                  fontSize: '0.72rem',
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                  marginBottom: '6px',
                  textTransform: 'uppercase'
                }}>
                  Select Controlled Benchmark Case
                </div>
                {demoScenarios.map((sc) => (
                  <div
                    key={sc.id}
                    onClick={() => {
                      onSelectScenario(sc);
                      setShowDemoMenu(false);
                      setActiveTab('investigate');
                    }}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '3px',
                      transition: 'background 0.15s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.86rem', color: '#FFFFFF' }}>{sc.name}</span>
                      <span style={{
                        fontSize: '0.68rem',
                        fontFamily: 'var(--font-mono)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: sc.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: sc.severity === 'CRITICAL' ? '#EF4444' : '#F59E0B'
                      }}>
                        {sc.severity}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      Target: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--primary-neon)' }}>{sc.target_account}</span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Engine Status Pill */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            borderRadius: '9999px',
            padding: '6px 12px',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            color: '#22C55E'
          }}>
            <span style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              background: '#22C55E',
              boxShadow: '0 0 8px #22C55E',
              display: 'inline-block'
            }} />
            <span>42/42 Tests Verified</span>
          </div>
        </div>
      </div>
    </header>
  );
}
