import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { useAuth } from '../context/useAuth';
import { extractErrorMessage } from '../api/client';
import { Spinner } from '../components/common/Spinner';
import { Alert } from '../components/common/Alert';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');

    if (!email.trim()) { setError('Email is required.'); return; }
    if (!password) { setError('Password is required.'); return; }

    setIsLoading(true);
    try {
      const token = await authApi.login({ email: email.trim(), password });
      await login(token.access_token);
      navigate('/');
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-bg)',
        padding: 24,
      }}
    >
      <div style={{ width: '100%', maxWidth: 420 }} className="fade-in">
        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              width: 52,
              height: 52,
              background: 'var(--color-primary)',
              borderRadius: 14,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 26,
              marginBottom: 14,
              boxShadow: '0 8px 24px rgb(99 102 241 / 0.3)',
            }}
          >
            🎓
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Welcome back
          </h1>
          <p style={{ color: 'var(--color-muted)', marginTop: 6, fontSize: '0.9rem' }}>
            Sign in to your StudySense account
          </p>
        </div>

        {/* Card */}
        <div className="card card-pad" style={{ borderRadius: 'var(--radius-lg)' }}>
          {error && (
            <div style={{ marginBottom: 18 }}>
              <Alert message={error} onDismiss={() => setError('')} />
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div className="form-group">
                <label className="form-label" htmlFor="login-email">
                  Email address
                </label>
                <input
                  id="login-email"
                  type="email"
                  className="form-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="login-password">
                  Password
                </label>
                <input
                  id="login-password"
                  type="password"
                  className="form-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                  disabled={isLoading}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={isLoading}
                style={{ width: '100%', marginTop: 4 }}
              >
                {isLoading ? <Spinner size="sm" /> : 'Sign in'}
              </button>
            </div>
          </form>
        </div>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: '0.875rem', color: 'var(--color-muted)' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ fontWeight: 500 }}>
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
