/**
 * AuthContext — provides user state, login, logout, and registration.
 * JWT is stored in localStorage under 'ss_token'.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { authApi } from '../api/auth';
import type { UserResponse } from '../types/api';

interface AuthContextValue {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, try to restore session from stored token
  useEffect(() => {
    const token = localStorage.getItem('ss_token');
    if (!token) {
      setIsLoading(false);
      return;
    }
    authApi
      .me()
      .then((u) => setUser(u))
      .catch(() => {
        // Token invalid / expired — clear it
        localStorage.removeItem('ss_token');
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (token: string) => {
    localStorage.setItem('ss_token', token);
    const u = await authApi.me();
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('ss_token');
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      login,
      logout,
    }),
    [user, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
