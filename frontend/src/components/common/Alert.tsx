/** Alert / error banner */
interface AlertProps {
  type?: 'error' | 'success' | 'warning' | 'info';
  message: string;
  onDismiss?: () => void;
}

const typeClass = {
  error: 'alert-error',
  success: 'alert-success',
  warning: 'alert-warning',
  info: 'alert-info',
};

const typeIcon = {
  error: '⚠',
  success: '✓',
  warning: '⚑',
  info: 'ℹ',
};

export function Alert({ type = 'error', message, onDismiss }: AlertProps) {
  return (
    <div
      className={`alert ${typeClass[type]}`}
      role="alert"
      style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}
    >
      <span style={{ flexShrink: 0 }}>{typeIcon[type]}</span>
      <span style={{ flex: 1 }}>{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="btn btn-ghost btn-sm"
          style={{ padding: '0 4px', lineHeight: 1 }}
          aria-label="Dismiss"
        >
          ✕
        </button>
      )}
    </div>
  );
}

/** Empty state */
interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-state-icon">{icon}</div>}
      <div className="empty-state-title">{title}</div>
      {description && <div className="empty-state-desc">{description}</div>}
      {action && <div style={{ marginTop: 8 }}>{action}</div>}
    </div>
  );
}
