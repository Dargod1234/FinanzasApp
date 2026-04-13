import { useState, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import type { Profile } from '../types';

export function useProfile() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const p = await api.getProfile();
      setProfile(p);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error cargando perfil');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const updateProfile = useCallback(async (data: Partial<Profile>) => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateProfile(data);
      setProfile(updated);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error guardando perfil');
      return false;
    } finally {
      setSaving(false);
    }
  }, []);

  return { profile, loading, saving, error, reload: load, updateProfile };
}
