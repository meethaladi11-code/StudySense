/**
 * AuthContext — provides user state, login, logout, and registration.
 * JWT is stored in localStorage under 'ss_token'.
 */

import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { authApi } from '../api/auth';
import type { UserResponse } from '../types/api';
import { AuthContext } from './authContextDef';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(() => !!localStorage.getItem('ss_token'));

  // On mount, try to restore session from stored token
  useEffect(() => {
    const token = localStorage.getItem('ss_token');
    if (!token) return;

    let ignore = false;
    authApi
      .me()
      .then((u) => {
        if (!ignore) setUser(u);
      })
      .catch(() => {
        // Token invalid / expired — clear it
        localStorage.removeItem('ss_token');
        if (!ignore) setUser(null);
      })
      .finally(() => {
        if (!ignore) setIsLoading(false);
      });

    return () => {
      ignore = true;
    };
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
