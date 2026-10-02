import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import { PageLoader } from '../common/Spinner';

/** Wraps protected routes — redirects to /login if unauthenticated. */
export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <PageLoader />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}

/** Wraps auth routes — redirects to dashboard if already logged in. */
export function GuestRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <PageLoader />;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <Outlet />;
}
