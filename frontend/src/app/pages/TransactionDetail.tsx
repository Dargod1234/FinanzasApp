import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { toast } from 'sonner';
import { useTransactions } from '../../hooks/useTransactions';
import { CATEGORIES, getCategoryInfo } from '../../constants/categories';
import { formatCurrency, formatDate, getAmountColor } from '../utils/format';

export function TransactionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { detail: tx, loading, error, getDetail, updateCategory, deleteTransaction } = useTransactions();

  const [showCategorySheet, setShowCategorySheet] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [imageExpanded, setImageExpanded] = useState(false);

  useEffect(() => {
    if (id) getDetail(Number(id));
  }, [id, getDetail]);

  if (loading && !tx) {
    return (
      <div className="flex flex-col min-h-screen bg-[#F8FAFC]">
        <div className="flex items-center gap-3 px-5 pt-14 pb-4 bg-white border-b border-[#E2E8F0]">
          <div className="w-9 h-9 rounded-full bg-[#E2E8F0] animate-pulse" />
          <div className="h-6 w-20 bg-[#E2E8F0] rounded animate-pulse" />
        </div>
        <div className="px-4 py-4 space-y-4">
          <div className="h-20 bg-[#E2E8F0] rounded-2xl animate-pulse" />
          <div className="h-32 bg-[#E2E8F0] rounded-2xl animate-pulse" />
          <div className="h-48 bg-[#E2E8F0] rounded-2xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !tx) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <span className="text-4xl mb-4">😕</span>
        <p className="text-[#64748B]">{error || 'Transacción no encontrada'}</p>
        <button onClick={() => navigate('/app/transactions')} className="mt-4 text-[#6366F1] text-sm underline">
          Volver
        </button>
      </div>
    );
  }

  const handleDelete = async () => {
    setShowDeleteModal(false);
    const success = await deleteTransaction(tx.id);
    if (success) {
      toast.success('Transacción eliminada');
      navigate('/app/transactions');
    } else {
      toast.error('Error eliminando transacción');
    }
  };

  const handleCategoryChange = async (newCat: string) => {
    setShowCategorySheet(false);
    const success = await updateCategory(tx.id, newCat);
    if (success) {
      toast.success('Categoría actualizada');
    } else {
      toast.error('Error actualizando categoría');
    }
  };

  const statusConfig: Record<string, { label: string; icon: string; color: string; bg: string }> = {
    confirmed: { label: 'Confirmado', icon: '✅', color: '#10B981', bg: '#ECFDF5' },
    pending: { label: 'Pendiente', icon: '⏳', color: '#F59E0B', bg: '#FEF3C7' },
    rejected: { label: 'Rechazado', icon: '❌', color: '#EF4444', bg: '#FEF2F2' },
    needs_review: { label: 'Revisar', icon: '⚠️', color: '#F59E0B', bg: '#FEF3C7' },
    error: { label: 'Error', icon: '❌', color: '#EF4444', bg: '#FEF2F2' },
  };
  const status = statusConfig[tx.estado] || statusConfig.pending;

  const montoNum = parseFloat(tx.monto_display) || 0;
  const confidencePct = Math.round(tx.confianza_ia * 100);
  const confColor = confidencePct >= 85 ? '#10B981' : confidencePct >= 70 ? '#F59E0B' : '#EF4444';
  const catInfo = getCategoryInfo(tx.categoria);
  const allCategoryEntries = Object.values(CATEGORIES);

  return (
    <div className="flex flex-col min-h-screen bg-[#F8FAFC]">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 pt-14 pb-4 bg-white border-b border-[#E2E8F0]">
        <button
          onClick={() => navigate('/app/transactions')}
          className="w-9 h-9 rounded-full bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0F172A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7" />
          </svg>
        </button>
        <h1 className="text-[#0F172A] font-bold text-lg">Detalle</h1>
      </div>

      <div className="flex-1 px-4 py-4 flex flex-col gap-4">
        {/* Receipt Image */}
        <div
          className="bg-white rounded-2xl border border-[#E2E8F0] overflow-hidden cursor-pointer shadow-sm"
          onClick={() => setImageExpanded(!imageExpanded)}
        >
          {imageExpanded ? (
            <div className="h-56 flex flex-col items-center justify-center gap-3 bg-[#F8FAFC]">
              <div className="text-center p-6 bg-white rounded-xl border border-[#E2E8F0] w-40">
                <div className="text-3xl mb-2">🧾</div>
                <div className="space-y-1.5">
                  <div className="h-2 bg-[#E2E8F0] rounded w-full" />
                  <div className="h-2 bg-[#E2E8F0] rounded w-3/4 mx-auto" />
                  <div className="h-2 bg-[#E2E8F0] rounded w-full" />
                  <div className="h-1 bg-transparent" />
                  <div className="h-2 bg-[#6366F1]/30 rounded w-1/2 mx-auto" />
                </div>
              </div>
              <p className="text-[#94A3B8] text-xs">Toca para contraer</p>
            </div>
          ) : (
            <div className="flex items-center gap-3 p-4">
              <div className="w-14 h-14 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center">
                <span className="text-2xl">🧾</span>
              </div>
              <div className="flex-1">
                <p className="text-[#0F172A] text-sm font-medium">Comprobante original</p>
                <p className="text-[#94A3B8] text-xs">Procesado por IA · {formatDate(tx.fecha_transaccion)}</p>
              </div>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" strokeWidth="2">
                <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
              </svg>
            </div>
          )}
        </div>

        {/* Amount Card */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-5 shadow-sm text-center">
          <p className="text-[#64748B] text-sm mb-1">
            {tx.tipo === 'ingreso' ? 'Ingreso' : tx.tipo === 'transferencia_propia' ? 'Transferencia' : 'Gasto'}
          </p>
          <p
            className="font-bold text-4xl mb-2"
            style={{ color: getAmountColor(tx.tipo) }}
          >
            {tx.tipo === 'ingreso' ? '+' : '-'}{formatCurrency(montoNum)}
          </p>
          <span
            className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full"
            style={{ backgroundColor: status.bg, color: status.color }}
          >
            {status.icon} {status.label}
          </span>
        </div>

        {/* Details Card */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <DetailRow icon="🏪" label="Destinatario" value={tx.destinatario} />
          <DetailRow icon="🏦" label="Entidad bancaria" value={tx.entidad} />
          <DetailRow
            icon={catInfo.icon}
            label="Categoría"
            value={catInfo.label}
            action={
              <button
                onClick={() => setShowCategorySheet(true)}
                className="text-[#6366F1] text-xs font-medium"
              >
                Cambiar
              </button>
            }
          />
          <DetailRow icon="🔢" label="Referencia" value={tx.referencia_bancaria} small />
          <DetailRow icon="📅" label="Fecha y hora" value={formatDate(tx.fecha_transaccion)} />
        </div>

        {/* AI Confidence */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-4 shadow-sm">
          <div className="flex justify-between items-center mb-2">
            <p className="text-[#0F172A] text-sm font-medium">Confianza IA</p>
            <span className="text-sm font-bold" style={{ color: confColor }}>{confidencePct}%</span>
          </div>
          <div className="h-2 bg-[#F1F5F9] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{ width: `${confidencePct}%`, backgroundColor: confColor }}
            />
          </div>
          {confidencePct < 80 && (
            <p className="text-[#F59E0B] text-xs mt-2 flex items-center gap-1">
              <span>⚠️</span> Baja confianza — verifica los datos manualmente
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 pb-4">
          <button
            onClick={() => setShowCategorySheet(true)}
            className="w-full py-3.5 rounded-xl border-2 border-[#6366F1] text-[#6366F1] font-medium text-sm transition-colors active:bg-[#EEF2FF]"
          >
            Cambiar categoría
          </button>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="w-full py-3 text-[#EF4444] font-medium text-sm transition-colors active:bg-[#FEF2F2] rounded-xl"
          >
            Eliminar transacción
          </button>
        </div>
      </div>

      {/* Category Bottom Sheet */}
      {showCategorySheet && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center"
          onClick={() => setShowCategorySheet(false)}
        >
          <div className="absolute inset-0 bg-black/50" />
          <div
            className="relative w-full max-w-[390px] bg-white rounded-t-2xl pb-8 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            style={{ animation: 'slideUp 0.25s ease-out' }}
          >
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-4">
              <div className="w-10 h-1 bg-[#CBD5E1] rounded-full" />
            </div>
            <p className="text-[#0F172A] font-bold text-base px-5 mb-4">Seleccionar categoría</p>
            {allCategoryEntries.map((cat) => (
              <button
                key={cat.id}
                onClick={() => handleCategoryChange(cat.id)}
                className="w-full flex items-center gap-3 px-5 py-3.5 active:bg-[#F8FAFC] transition-colors"
                style={{ borderBottom: '1px solid #F8FAFC' }}
              >
                <span className="text-2xl">{cat.icon}</span>
                <span
                  className="text-sm font-medium"
                  style={{ color: tx.categoria === cat.id ? '#6366F1' : '#0F172A' }}
                >
                  {cat.label}
                </span>
                {tx.categoria === cat.id && (
                  <svg className="ml-auto" width="16" height="16" viewBox="0 0 24 24" fill="#6366F1">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-6">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowDeleteModal(false)} />
          <div className="relative w-full max-w-[320px] bg-white rounded-2xl p-6 shadow-2xl text-center">
            <div className="text-4xl mb-3">🗑️</div>
            <h2 className="text-[#0F172A] font-bold text-lg mb-1">¿Eliminar transacción?</h2>
            <p className="text-[#64748B] text-sm mb-6">Esta acción no se puede deshacer</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="flex-1 py-3 rounded-xl border-2 border-[#E2E8F0] text-[#64748B] font-medium text-sm"
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                className="flex-1 py-3 rounded-xl bg-[#EF4444] text-white font-medium text-sm"
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

function DetailRow({
  icon,
  label,
  value,
  action,
  small,
}: {
  icon: string;
  label: string;
  value: string;
  action?: React.ReactNode;
  small?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3.5" style={{ borderBottom: '1px solid #F8FAFC' }}>
      <span className="text-lg w-6 flex-shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-[#94A3B8] text-xs mb-0.5">{label}</p>
        <p
          className="text-[#0F172A] font-medium truncate"
          style={{ fontSize: small ? 11 : 13 }}
        >
          {value}
        </p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
