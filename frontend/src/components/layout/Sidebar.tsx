import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: '⌂', end: true },
  { to: '/documents', label: 'Study Material', icon: '📄', end: false },
  { to: '/chat', label: 'Ask StudySense', icon: '💬', end: false },
  { to: '/quizzes', label: 'Quizzes', icon: '✎', end: false },
  { to: '/analytics', label: 'Analytics', icon: '📊', end: false },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <>
      {/* Overlay for mobile */}
      <div
        className={`sidebar-overlay ${isOpen ? 'sidebar-open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`} aria-label="Main navigation">
        {/* Logo */}
        <div
          style={{
            padding: '20px 20px 16px',
            borderBottom: '1px solid var(--color-border)',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              marginBottom: 2,
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                background: 'var(--color-primary)',
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 16,
                flexShrink: 0,
              }}
            >
              🎓
            </div>
            <span
              style={{
                fontWeight: 700,
                fontSize: '1rem',
                letterSpacing: '-0.02em',
                color: 'var(--color-text)',
              }}
            >
              StudySense
            </span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-muted)', paddingLeft: 42 }}>
            AI Study Assistant
          </div>
        </div>

        {/* Navigation */}
        <nav
          style={{
            flex: 1,
            padding: '12px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            overflowY: 'auto',
          }}
        >
          {NAV_ITEMS.map(({ to, label, icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 8,
                fontSize: '0.875rem',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--color-primary)' : 'var(--color-text)',
                background: isActive ? 'var(--color-primary-light)' : 'transparent',
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              })}
            >
              <span style={{ fontSize: '1rem', width: 20, textAlign: 'center' }}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User / Logout */}
        <div
          style={{
            padding: '14px 16px',
            borderTop: '1px solid var(--color-border)',
            flexShrink: 0,
          }}
        >
          {user && (
            <div style={{ marginBottom: 10 }}>
              <div
                style={{
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--color-text)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {user.username}
              </div>
              <div
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-muted)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {user.email}
              </div>
            </div>
          )}
          <button className="btn btn-ghost btn-sm" onClick={handleLogout} style={{ width: '100%' }}>
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}

/** Top bar with hamburger for mobile and page title. */
interface TopBarProps {
  title: string;
  onMenuClick: () => void;
  actions?: React.ReactNode;
}

export function TopBar({ title, onMenuClick, actions }: TopBarProps) {
  return (
    <div className="top-bar">
      <button
        className="btn btn-ghost btn-sm"
        onClick={onMenuClick}
        aria-label="Open menu"
        style={{ display: 'none' }}
        id="sidebar-menu-btn"
      >
        ☰
      </button>
      <div className="top-bar-title" style={{ flex: 1 }}>
        {title}
      </div>
      {actions && <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>{actions}</div>}
    </div>
  );
}

/** Full authenticated shell — sidebar + content area. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="main-content" id="main-content">
        {children}
      </main>

      {/* Mobile menu trigger injected via CSS */}
      <style>{`
        @media (max-width: 768px) {
          #sidebar-menu-btn { display: flex !important; }
        }
      `}</style>
    </div>
  );
}
