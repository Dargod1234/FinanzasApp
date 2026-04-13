import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { api } from '../services/api';
import { setTokens, clearTokens, isAuthenticated } from '../utils/storage';
import type { AuthResponse } from '../types';

interface AuthContextType {
  phone: string;
  setPhone: (p: string) => void;
  loading: boolean;
  error: string | null;
  authenticated: boolean;
  requestOtp: (phoneNumber: string) => Promise<boolean>;
  verifyOtp: (otpCode: string) => Promise<AuthResponse | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    isAuthenticated().then(setAuthenticated);
  }, []);

  const requestOtp = useCallback(async (phoneDigits: string) => {
    setLoading(true);
    setError(null);
    try {
      const fullPhone = `+57${phoneDigits}`;
      setPhone(phoneDigits);
      await api.requestOtp(fullPhone);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error enviando OTP');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const verifyOtp = useCallback(async (otpCode: string): Promise<AuthResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const fullPhone = `+57${phone}`;
      const response = await api.phoneAuth(fullPhone, otpCode);
      await setTokens(response.access, response.refresh);
      setAuthenticated(true);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Código incorrecto');
      return null;
    } finally {
      setLoading(false);
    }
  }, [phone]);

  const logout = useCallback(async () => {
    await clearTokens();
    setAuthenticated(false);
    setPhone('');
  }, []);

  return (
    <AuthContext.Provider
      value={{ phone, setPhone, loading, error, authenticated, requestOtp, verifyOtp, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
