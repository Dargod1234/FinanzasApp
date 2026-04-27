import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type {
  EncryptedTransactionPayload,
  EncryptedTransactionRecord,
  PaginatedResponse,
  Transaction,
  TransactionDetail,
} from '../types';

export function useTransactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [detail, setDetail] = useState<TransactionDetail | null>(null);
  const [encryptedRecords, setEncryptedRecords] = useState<EncryptedTransactionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);

  const loadTransactions = useCallback(async (pageNum = 1, tipo?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result: PaginatedResponse<Transaction> = await api.getTransactions(pageNum, tipo);
      if (pageNum === 1) {
        setTransactions(result.results);
      } else {
        setTransactions((prev) => [...prev, ...result.results]);
      }
      setPage(pageNum);
      setHasMore(result.next !== null);
      setTotal(result.count);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error cargando transacciones');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(async (tipo?: string) => {
    if (!hasMore || loading) return;
    await loadTransactions(page + 1, tipo);
  }, [hasMore, loading, page, loadTransactions]);

  const getDetail = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const tx = await api.getTransaction(id);
      setDetail(tx);
      return tx;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error cargando detalle');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateCategory = useCallback(async (id: number, categoria: string) => {
    try {
      await api.updateTransaction(id, { categoria });
      // Update local state
      setTransactions((prev) =>
        prev.map((tx) => (tx.id === id ? { ...tx, categoria } : tx))
      );
      if (detail && detail.id === id) {
        setDetail({ ...detail, categoria });
      }
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error actualizando categoría');
      return false;
    }
  }, [detail]);

  const deleteTransaction = useCallback(async (id: number) => {
    try {
      await api.deleteTransaction(id);
      setTransactions((prev) => prev.filter((tx) => tx.id !== id));
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error eliminando transacción');
      return false;
    }
  }, []);

  const saveEncryptedTransaction = useCallback(async (payload: EncryptedTransactionPayload) => {
    try {
      const created = await api.createEncryptedTransaction(payload);
      setEncryptedRecords((prev) => [created, ...prev]);
      return created;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error guardando transacción cifrada');
      return null;
    }
  }, []);

  return {
    transactions,
    detail,
    encryptedRecords,
    loading,
    error,
    total,
    hasMore,
    loadTransactions,
    loadMore,
    getDetail,
    updateCategory,
    deleteTransaction,
    saveEncryptedTransaction,
  };
}
