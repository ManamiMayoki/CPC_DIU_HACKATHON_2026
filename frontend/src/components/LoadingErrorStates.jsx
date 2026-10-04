import React from 'react';
import { Activity, AlertTriangle, Search, RefreshCw } from 'lucide-react';

export function LoadingState({ message = 'Analyzing transaction network...' }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '400px',
      padding: '40px',
      textAlign: 'center'
    }}>
      {/* High-tech scanning radar ring */}
      <div style={{ position: 'relative', width: '72px', height: '72px', marginBottom: '20px' }}>
        <div style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          border: '2px solid rgba(184, 255, 61, 0.2)',
        }} />
        <div style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          border: '2px solid transparent',
          borderTopColor: 'var(--primary-neon)',
          animation: 'spin 1s linear infinite'
        }} />
        <div style={{
          position: 'absolute',
          inset: '18px',
          borderRadius: '50%',
          background: 'rgba(184, 255, 61, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <Activity size={18} color="var(--primary-neon)" />
        </div>
      </div>

      <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF' }}>
        {message}
      </h3>
      <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '6px', fontFamily: 'var(--font-mono)' }}>
        Evaluating NetworkX topology & Isolation Forest decision boundaries...
      </p>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export function EmptyState({ message = 'No suspicious network found.', onReset }) {
  return (
    <div className="glass-panel" style={{
      maxWidth: '560px',
      margin: '60px auto',
      padding: '40px',
      textAlign: 'center',
      borderRadius: '20px'
    }}>
      <div style={{
        width: '56px',
        height: '56px',
        borderRadius: '16px',
        background: 'rgba(255, 255, 255, 0.04)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 16px'
      }}>
        <Search size={24} color="var(--text-muted)" />
      </div>

      <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '8px' }}>
        {message}
      </h3>
      <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '20px' }}>
        The query returned zero matching entities in the active transaction graph. 
        Verify the Account ID or choose from our pre-configured demo scenarios.
      </p>

      {onReset && (
        <button onClick={onReset} className="btn-secondary" style={{ padding: '10px 24px', fontSize: '0.88rem' }}>
          <span>Reset to Baseline</span>
        </button>
      )}
    </div>
  );
}

export function ErrorState({ message = 'Unable to analyze the transaction network.', onRetry }) {
  return (
    <div className="glass-panel" style={{
      maxWidth: '560px',
      margin: '60px auto',
      padding: '40px',
      textAlign: 'center',
      borderRadius: '20px',
      border: '1px solid rgba(239, 68, 68, 0.3)'
    }}>
      <div style={{
        width: '56px',
        height: '56px',
        borderRadius: '16px',
        background: 'rgba(239, 68, 68, 0.15)',
        border: '1px solid rgba(239, 68, 68, 0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 16px'
      }}>
        <AlertTriangle size={24} color="#EF4444" />
      </div>

      <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '8px' }}>
        {message}
      </h3>
      <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '20px' }}>
        A system error occurred while processing the transaction pipeline. 
        Raw inputs have been validated and internal exceptions were gracefully caught.
      </p>

      {onRetry && (
        <button onClick={onRetry} className="btn-primary" style={{ padding: '10px 24px', fontSize: '0.88rem' }}>
          <RefreshCw size={15} />
          <span>Retry Analysis</span>
        </button>
      )}
    </div>
  );
}
