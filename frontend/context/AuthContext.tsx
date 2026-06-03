import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { login as loginAPI, setTokens, clearTokens } from '../services/api';

const ACCESS_KEY = 'rasperify_access_token';
const REFRESH_KEY = 'rasperify_refresh_token';
const USERNAME_KEY = 'rasperify_username';

interface AuthContextType {
  isAuthenticated: boolean;
  username: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const restore = async () => {
      try {
        const [access, refresh, storedUser] = await AsyncStorage.multiGet([
          ACCESS_KEY,
          REFRESH_KEY,
          USERNAME_KEY,
        ]);
        const accessToken = access[1];
        const refreshToken = refresh[1];
        if (accessToken && refreshToken) {
          setTokens(accessToken, refreshToken);
          setIsAuthenticated(true);
          setUsername(storedUser[1]);
        }
      } catch {
        // storage unavailable — start unauthenticated
      } finally {
        setIsLoading(false);
      }
    };
    restore();
  }, []);

  const login = useCallback(async (user: string, password: string) => {
    const res = await loginAPI(user, password);
    await AsyncStorage.multiSet([
      [ACCESS_KEY, res.access_token],
      [REFRESH_KEY, res.refresh_token],
      [USERNAME_KEY, user],
    ]);
    setIsAuthenticated(true);
    setUsername(user);
  }, []);

  const logout = useCallback(async () => {
    await AsyncStorage.multiRemove([ACCESS_KEY, REFRESH_KEY, USERNAME_KEY]);
    clearTokens();
    setIsAuthenticated(false);
    setUsername(null);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, username, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
