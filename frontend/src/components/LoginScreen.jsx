import { useEffect, useState } from 'react';
import { Shield, UserCheck, ShieldCheck, Lock, WifiOff } from 'lucide-react';
import { fetchAuthConfig, signIn, signInDemo } from '../services/api';

/**
 * Sign-in gate. Analysts and compliance officers get different permissions (see backend auth.js).
 * In demo mode the two one-click buttons sign in without a password; the form is for real accounts.
 */
export default function LoginScreen({ onSignedIn, onOfflinePreview }) {
  const [config, setConfig] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchAuthConfig().then(setConfig);
  }, []);

  const finish = (result) => {
    setBusy(false);
    if (result.success) onSignedIn(result.user);
    else setError(result.error || 'Sign-in failed.');
  };

  const handleDemo = async (role) => {
    setBusy(true);
    setError('');
    finish(await signInDemo(role));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) return;
    setBusy(true);
    setError('');
    finish(await signIn(username, password));
  };

  const roleCard = (role, Icon, title, lines, color) => (
    <button
      type="button"
      disabled={busy}
      onClick={() => handleDemo(role)}
      style={{
        flex: 1,
        textAlign: 'left',
        background: 'rgba(255, 255, 255, 0.03)',
        border: `1px solid ${color}55`,
        borderRadius: '14px',
        padding: '18px',
        cursor: busy ? 'wait' : 'pointer',
        color: '#FFFFFF',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <Icon size={18} color={color} />
        <span style={{ fontWeight: 800, fontSize: '0.98rem' }}>{title}</span>
      </div>
      <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.55 }}>
        {lines.map((line) => <li key={line}>{line}</li>)}
      </ul>
    </button>
  );

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-dark)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '640px', borderRadius: '20px', padding: '36px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
          <Shield size={28} color="#B8FF3D" />
          <h1 style={{ fontSize: '1.7rem', fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.02em' }}>CYGNUS AI</h1>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', marginBottom: '24px' }}>
          Sign in to the investigation workspace. What you can see and do depends on your role, and every action is written to the audit log.
        </p>

        {config?.offline && (
          <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.4)', borderRadius: '12px', padding: '14px', marginBottom: '18px' }}>
            <WifiOff size={18} color="#F59E0B" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ fontSize: '0.84rem', color: '#FDE68A' }}>
              The backend is not reachable, so sign-in, cases and the audit log are unavailable.
              <button type="button" onClick={onOfflinePreview} className="btn-secondary" style={{ display: 'block', marginTop: '10px', fontSize: '0.8rem', padding: '6px 14px' }}>
                Open read-only preview with saved data
              </button>
            </div>
          </div>
        )}

        {config?.demo_mode && (
          <>
            <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>
              Demo sign-in
            </div>
            <div style={{ display: 'flex', gap: '14px', marginBottom: '24px', flexWrap: 'wrap' }}>
              {roleCard('analyst', UserCheck, 'AML Analyst', ['Investigate accounts', 'Open cases, add notes, escalate', 'Personal data stays masked'], '#38BDF8')}
              {roleCard('admin', ShieldCheck, 'Compliance Officer', ['Everything an analyst can do', 'File or close cases', 'Reveal personal data with a reason', 'Read and verify the audit log'], '#B8FF3D')}
            </div>
          </>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>
            Sign in with an account
          </div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <input className="input-fintech" style={{ flex: 1, minWidth: '160px' }} placeholder="Username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
            <input className="input-fintech" style={{ flex: 1, minWidth: '160px' }} placeholder="Password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="submit" className="btn-primary" disabled={busy || !username || !password} style={{ padding: '8px 18px' }}>
              <Lock size={14} />
              <span>Sign in</span>
            </button>
          </div>
        </form>

        {error && (
          <div role="alert" style={{ marginTop: '16px', color: '#FCA5A5', fontSize: '0.85rem' }}>{error}</div>
        )}

        <p style={{ marginTop: '22px', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
          Synthetic data only. Risk scores are indicators for a human reviewer, not proof of wrongdoing.
        </p>
      </div>
    </div>
  );
}
