import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from './axios_client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true); // checking existing session

  // ── Bootstrap: restore session from localStorage ──────────────────────────
  useEffect(() => {
    const accessToken = localStorage.getItem('access_token');
    const storedUser  = localStorage.getItem('user');

    if (accessToken && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.clear();
      }
    }
    setLoading(false);
  }, []);

  // ── Login ─────────────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    const { data } = await authApi.login({ email, password });

    localStorage.setItem('access_token',  data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user',          JSON.stringify(data.user));

    setUser(data.user);
    return data.user;
  }, []);

  // ── Register ──────────────────────────────────────────────────────────────
  const register = useCallback(async (userData) => {
    const { data } = await authApi.register(userData);

    localStorage.setItem('access_token',  data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user',          JSON.stringify(data.user));

    setUser(data.user);
    return data.user;
  }, []);

  // ── Logout ────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    try {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) await authApi.logout(refresh);
    } catch {
      // Ignore errors on logout
    } finally {
      localStorage.clear();
      setUser(null);
    }
  }, []);

  // ── Update local user state (after profile edit) ──────────────────────────
  const updateUser = useCallback((updatedUser) => {
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}