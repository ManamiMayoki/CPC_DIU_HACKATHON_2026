import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import TrustStats from './components/TrustStats';
import FollowTheMoney from './components/FollowTheMoney';
import RiskScoreCard from './components/RiskScoreCard';
import DetectionPatterns from './components/DetectionPatterns';
import AIInvestigator from './components/AIInvestigator';
import AnalyticsSection from './components/AnalyticsSection';
import HighRiskAccounts from './components/HighRiskAccounts';
import TransactionLedger from './components/TransactionLedger';
import DemoScenarioBar from './components/DemoScenarioBar';
import ArchitectureModal from './components/ArchitectureModal';
import { LoadingState, ErrorState } from './components/LoadingErrorStates';
import { fetchInitialData, fetchAccountNetwork } from './services/api';
import { Shield, Sparkles, Layers, ArrowRight } from 'lucide-react';

export default function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const [activeTab, setActiveTab] = useState('overview');
  const [selectedAccountId, setSelectedAccountId] = useState('ACC_FANIN_HUB');
  const [activeScenarioId, setActiveScenarioId] = useState('FAN_IN');

  // Load initial data
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchInitialData();
      setData(payload);
      if (payload.top_risk_accounts && payload.top_risk_accounts.length > 0) {
        setSelectedAccountId(payload.top_risk_accounts[0].account_id);
      }
    } catch (err) {
      console.error('Failed to load initial data:', err);
      setError(err.message || 'Unable to connect to FlowGuard detection pipeline.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Handle Account Selection for Investigation
  const handleSelectAccount = (accountId) => {
    setSelectedAccountId(accountId);
    // Find if account belongs to a scenario
    const matchedScenario = data?.demo_scenarios?.find(
      s => s.target_account.toLowerCase() === accountId.toLowerCase()
    );
    if (matchedScenario) {
      setActiveScenarioId(matchedScenario.id);
    }
  };

  // Handle Quick Investigation Action
  const handleInvestigateAccount = (accountId) => {
    handleSelectAccount(accountId);
    setActiveTab('investigate');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Handle Scenario Switch from Demo Bar
  const handleSelectScenario = (scenario) => {
    setActiveScenarioId(scenario.id);
    handleSelectAccount(scenario.target_account);
    setActiveTab('investigate');
  };

  if (loading) {
    return <LoadingState message="Initializing FlowGuard AI Detection Pipeline..." />;
  }

  if (error && !data) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  const selectedAccount = data?.accounts?.find(
    a => a.account_id.toLowerCase() === (selectedAccountId || '').toLowerCase()
  ) || data?.accounts?.[0];

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-dark)', color: '#FFFFFF', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation Bar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onSearchAccount={handleInvestigateAccount}
        demoScenarios={data?.demo_scenarios || []}
        onSelectScenario={handleSelectScenario}
      />

      {/* Main Content Area */}
      <main style={{ flex: 1, paddingBottom: '60px' }}>
        {/* VIEW 1: Overview / Landing Hero & Live Stats */}
        {activeTab === 'overview' && (
          <>
            <HeroSection
              stats={data?.stats}
              nodes={data?.nodes || []}
              edges={data?.edges || []}
              onStartInvestigation={() => setActiveTab('investigate')}
              onExploreNetwork={() => {
                setActiveTab('investigate');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              onSelectAccount={handleInvestigateAccount}
            />

            <TrustStats
              stats={data?.stats}
              riskDistribution={data?.risk_distribution}
            />

            <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '0 24px 32px' }}>
              <DemoScenarioBar
                scenarios={data?.demo_scenarios || []}
                activeScenarioId={activeScenarioId}
                onSelectScenario={handleSelectScenario}
              />
            </div>

            {/* Quick Preview of Detection Patterns on Landing */}
            <DetectionPatterns
              patternsSummary={data?.patterns_summary || []}
              onInvestigateAccount={handleInvestigateAccount}
            />

            {/* Quick Preview of High-Risk Accounts */}
            <HighRiskAccounts
              accounts={data?.accounts || []}
              onInvestigateAccount={handleInvestigateAccount}
            />
          </>
        )}

        {/* VIEW 2: Follow the Money (Investigation Dashboard - CORE FEATURE) */}
        {activeTab === 'investigate' && (
          <div style={{ paddingTop: '24px' }}>
            {/* Header */}
            <div style={{ maxWidth: '1480px', margin: '0 auto 20px', padding: '0 24px' }}>
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
                <Layers size={14} color="#B8FF3D" />
                <span>PRIMARY INVESTIGATION WORKSPACE</span>
              </div>
              <h2 style={{ fontSize: '2.2rem', fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.03em' }}>
                Follow the Money
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.98rem', maxWidth: '680px', marginTop: '4px' }}>
                Analyze transaction networks and identify suspicious money movement across multi-hop directed graphs.
              </p>
            </div>

            {/* Demo Scenario Quick Selector */}
            <div style={{ maxWidth: '1480px', margin: '0 auto 20px', padding: '0 24px' }}>
              <DemoScenarioBar
                scenarios={data?.demo_scenarios || []}
                activeScenarioId={activeScenarioId}
                onSelectScenario={handleSelectScenario}
              />
            </div>

            {/* Interactive Network Graph */}
            <FollowTheMoney
              initialNodes={data?.nodes || []}
              initialEdges={data?.edges || []}
              selectedAccountId={selectedAccountId}
              onSelectAccount={handleSelectAccount}
              demoScenarios={data?.demo_scenarios || []}
              onSelectScenario={handleSelectScenario}
            />

            {/* Risk Card & AI Investigator Side-by-Side Underneath */}
            <div style={{
              maxWidth: '1480px',
              margin: '32px auto 0',
              padding: '0 24px',
              display: 'grid',
              gridTemplateColumns: '440px 1fr',
              gap: '24px'
            }}>
              <RiskScoreCard account={selectedAccount} />
              
              <div className="glass-panel" style={{ padding: '28px', borderRadius: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                  <Sparkles size={18} color="var(--primary-neon)" />
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#FFFFFF' }}>
                    AI Investigator Findings for {selectedAccount?.account_id}
                  </h3>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
                  {selectedAccount?.evidence && selectedAccount.evidence.length > 0 ? (
                    selectedAccount.evidence.map((ev, i) => (
                      <div
                        key={i}
                        style={{
                          fontSize: '0.86rem',
                          color: '#F1F5F9',
                          lineHeight: 1.5,
                          padding: '10px 14px',
                          background: 'rgba(255, 255, 255, 0.03)',
                          borderRadius: '10px',
                          borderLeft: '3px solid var(--primary-neon)'
                        }}
                      >
                        {ev}
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: '0.86rem', color: 'var(--text-muted)' }}>
                      No topological or statistical anomalies detected.
                    </div>
                  )}
                </div>

                <button
                  onClick={() => setActiveTab('investigator')}
                  className="btn-secondary"
                  style={{ fontSize: '0.84rem', padding: '8px 18px' }}
                >
                  <span>Open Full Forensic Investigator View</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 3: High Risk Accounts Directory */}
        {activeTab === 'high-risk' && (
          <HighRiskAccounts
            accounts={data?.accounts || []}
            onInvestigateAccount={handleInvestigateAccount}
          />
        )}

        {/* VIEW 4: Detection Patterns Showcase */}
        {activeTab === 'patterns' && (
          <DetectionPatterns
            patternsSummary={data?.patterns_summary || []}
            onInvestigateAccount={handleInvestigateAccount}
          />
        )}

        {/* VIEW 5: Dedicated AI Forensic Investigator */}
        {activeTab === 'investigator' && (
          <AIInvestigator
            selectedAccount={selectedAccount}
            accounts={data?.accounts || []}
            onSelectAccount={handleSelectAccount}
          />
        )}

        {/* VIEW 6: Futuristic Analytics Section */}
        {activeTab === 'analytics' && (
          <AnalyticsSection
            analytics={data?.analytics || {}}
            riskDistribution={data?.risk_distribution || {}}
            stats={data?.stats || {}}
          />
        )}

        {/* VIEW 7: Transaction Ledger Table */}
        {activeTab === 'transactions' && (
          <TransactionLedger
            transactions={data?.transactions_sample || []}
            onInvestigateAccount={handleInvestigateAccount}
          />
        )}

        {/* VIEW 8: Architecture & Contract Transparency */}
        {activeTab === 'docs' && (
          <ArchitectureModal />
        )}
      </main>

      {/* Global Footer */}
      <footer style={{
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        padding: '32px 24px',
        background: 'rgba(5, 7, 11, 0.95)',
        fontSize: '0.8rem',
        color: 'var(--text-muted)'
      }}>
        <div style={{
          maxWidth: '1440px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Shield size={18} color="var(--primary-neon)" />
            <span style={{ fontWeight: 700, color: '#FFFFFF' }}>FLOWGUARD AI</span>
            <span>— AI-Powered Transaction Network Intelligence</span>
          </div>

          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>
            CPC DIU HACKATHON 2026 • MEMBER 1 + 2 + 3 INTEGRATED • ZERO SYNTHETIC HALLUCINATIONS
          </div>
        </div>
      </footer>
    </div>
  );
}
