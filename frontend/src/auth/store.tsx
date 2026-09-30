import { api } from '@/api/client';
import type { User } from '@/api/types';
import { tokenStore } from '@/auth/token-store';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react';

interface AuthState {
  user: User | null;
  loading: boolean;
  isTeacher: boolean;
  isStudent: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        if (await tokenStore.access()) {
          setUser(await api.me());
        }
      } catch {
        await tokenStore.clear();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    await api.login(username, password);
    setUser(await api.me());
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      isTeacher: user?.role === 'teacher' || user?.role === 'admin',
      isStudent: user?.role === 'student',
      login,
      logout,
    }),
    [user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
