import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { useTransactions } from '../../hooks/useTransactions';
import { getCategoryInfo } from '../../constants/categories';
import { formatCurrency, formatDateShort, getAmountColor } from '../utils/format';
import type { Transaction } from '../../types';

type FilterTab = 'todos' | 'gasto' | 'ingreso';

export function Transactions() {
  const navigate = useNavigate();
  const { transactions, loading, error, total, hasMore, loadTransactions, loadMore } = useTransactions();
  const [activeTab, setActiveTab] = useState<FilterTab>('todos');

  useEffect(() => {
    loadTransactions(1, activeTab === 'todos' ? undefined : activeTab);
  }, [activeTab, loadTransactions]);

  const tabs: { key: FilterTab; label: string }[] = [
    { key: 'todos', label: 'Todos' },
    { key: 'gasto', label: 'Gastos' },
    { key: 'ingreso', label: 'Ingresos' },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-[#F8FAFC]">
      {/* Header */}
      <div className="px-5 pt-14 pb-4 bg-white border-b border-[#E2E8F0]">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-[#0F172A] font-bold text-xl">Transacciones</h1>
          <span className="text-[#64748B] text-sm">{total} total</span>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 bg-[#F8FAFC] p-1 rounded-xl">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className="flex-1 py-2 rounded-lg text-sm font-medium transition-all"
              style={{
                backgroundColor: activeTab === tab.key ? '#6366F1' : 'transparent',
                color: activeTab === tab.key ? 'white' : '#64748B',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Transaction List */}
      <div className="flex-1 px-4 mt-3">
        {loading && transactions.length === 0 ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="bg-white rounded-xl p-4 animate-pulse flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-[#E2E8F0]" />
                <div className="flex-1">
                  <div className="h-4 w-32 bg-[#E2E8F0] rounded mb-2" />
                  <div className="h-3 w-24 bg-[#E2E8F0] rounded" />
                </div>
                <div className="h-4 w-20 bg-[#E2E8F0] rounded" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20">
            <span className="text-4xl mb-4">😕</span>
            <p className="text-[#EF4444] text-sm mb-4">{error}</p>
            <button
              onClick={() => loadTransactions(1, activeTab === 'todos' ? undefined : activeTab)}
              className="px-5 py-2.5 rounded-xl text-white text-sm font-medium"
              style={{ backgroundColor: '#6366F1' }}
            >
              Reintentar
            </button>
          </div>
        ) : transactions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <span className="text-5xl">📭</span>
            <p className="text-[#64748B] text-center text-sm">
              Aún no tienes transacciones.
              <br />Envía tu primer comprobante por WhatsApp 📸
            </p>
            <a
              href="https://wa.me/573001234567"
              target="_blank"
              rel="noopener noreferrer"
              className="px-5 py-2.5 rounded-xl text-white text-sm font-medium"
              style={{ backgroundColor: '#25D366' }}
            >
              Abrir WhatsApp
            </a>
          </div>
        ) : (
          <>
            <div className="bg-white rounded-2xl border border-[#F1F5F9] overflow-hidden shadow-sm">
              {transactions.map((tx, index) => (
                <TransactionItem
                  key={tx.id}
                  tx={tx}
                  isLast={index === transactions.length - 1}
                  onClick={() => navigate(`/transaction/${tx.id}`)}
                />
              ))}
            </div>
            {hasMore && (
              <button
                onClick={() => loadMore(activeTab === 'todos' ? undefined : activeTab)}
                disabled={loading}
                className="w-full py-3 mt-3 rounded-xl border-2 border-[#E2E8F0] text-[#6366F1] font-medium text-sm"
              >
                {loading ? 'Cargando...' : 'Cargar más'}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function TransactionItem({
  tx,
  isLast,
  onClick,
}: {
  tx: Transaction;
  isLast: boolean;
  onClick: () => void;
}) {
  const [pressed, setPressed] = useState(false);
  const lowConfidence = tx.confianza_ia < 0.8;
  const catInfo = getCategoryInfo(tx.categoria);
  const montoNum = parseFloat(tx.monto_display) || 0;

  return (
    <button
      onClick={onClick}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      onTouchStart={() => setPressed(true)}
      onTouchEnd={() => setPressed(false)}
      className="w-full flex items-center gap-3 px-4 py-3.5 text-left transition-colors"
      style={{
        backgroundColor: pressed ? '#F8FAFC' : 'white',
        borderBottom: isLast ? 'none' : '1px solid #F1F5F9',
      }}
    >
      {/* Icon */}
      <div className="w-11 h-11 rounded-xl bg-[#F8FAFC] flex items-center justify-center text-2xl flex-shrink-0">
        {catInfo.icon}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-[#0F172A] text-sm font-semibold truncate">{tx.destinatario}</p>
          {lowConfidence && (
            <span className="text-xs px-1.5 py-0.5 rounded-md bg-[#FEF3C7] text-[#92400E] font-medium whitespace-nowrap">
              ⚠️ Verificar
            </span>
          )}
        </div>
        <p className="text-[#94A3B8] text-xs">{catInfo.label} · {tx.entidad}</p>
      </div>

      {/* Amount + Date */}
      <div className="flex flex-col items-end gap-0.5 flex-shrink-0">
        <p
          className="text-sm font-semibold"
          style={{ color: getAmountColor(tx.tipo) }}
        >
          {tx.tipo === 'ingreso' ? '+' : '-'}{formatCurrency(montoNum)}
        </p>
        <p className="text-[#94A3B8] text-xs">{formatDateShort(tx.fecha_transaccion)}</p>
      </div>

      {/* Chevron */}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="ml-1">
        <path d="M9 18l6-6-6-6" />
      </svg>
    </button>
  );
}
