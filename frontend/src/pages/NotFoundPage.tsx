import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-bg)',
        flexDirection: 'column',
        gap: 16,
        textAlign: 'center',
        padding: 24,
      }}
    >
      <div style={{ fontSize: '4rem', lineHeight: 1 }}>🔍</div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Page not found</h1>
      <p style={{ color: 'var(--color-muted)', maxWidth: 340 }}>
        The page you're looking for doesn't exist or may have moved.
      </p>
      <Link to="/" className="btn btn-primary" style={{ marginTop: 8 }}>
        Go to Dashboard
      </Link>
    </div>
  );
}
