/** Spinner — inline loading indicator */
export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const cls =
    size === 'sm' ? 'spinner spinner-sm' : size === 'lg' ? 'spinner' : 'spinner';
  return <div className={cls} role="status" aria-label="Loading" />;
}

/** Full-page loading overlay */
export function PageLoader() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        flexDirection: 'column',
        gap: 16,
        background: 'var(--color-bg)',
      }}
    >
      <Spinner />
      <span style={{ fontSize: '0.875rem', color: 'var(--color-muted)' }}>
        Loading…
      </span>
    </div>
  );
}

/** Skeleton block */
export function Skeleton({ width, height }: { width?: string | number; height?: string | number }) {
  return (
    <div
      className="skeleton"
      style={{ width: width ?? '100%', height: height ?? 16 }}
    />
  );
}

/** Section of skeletons */
export function SkeletonCard() {
  return (
    <div className="card card-pad" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Skeleton height={20} width="60%" />
      <Skeleton height={14} width="80%" />
      <Skeleton height={14} width="40%" />
    </div>
  );
}
