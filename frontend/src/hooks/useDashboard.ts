import { useState, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import type { DashboardSummary } from '../types';

export function useDashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await api.getDashboardSummary();
      setData(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error cargando dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, reload: load };
}
