import { useState } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { useProfile } from '../../hooks/useProfile';
import { useAuth } from '../../hooks/useAuth';
import { formatCurrency } from '../utils/format';

export function Profile() {
  const navigate = useNavigate();
  const { profile, loading, updateProfile } = useProfile();
  const { phone, logout } = useAuth();
  const formattedPhone = phone
    ? `+57 ${phone.slice(0, 3)} ${phone.slice(3, 6)} ${phone.slice(6)}`
    : '+57 ---';

  const salary = parseFloat(profile?.salario_mensual || '0') || 0;
  const budget = parseFloat(profile?.presupuesto_mensual || '0') || 0;
  const cutDay = profile?.dia_corte || 1;

  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [editField, setEditField] = useState<'salary' | 'budget' | null>(null);
  const [editValue, setEditValue] = useState('');

  const openEdit = (field: 'salary' | 'budget') => {
    setEditField(field);
    setEditValue(field === 'salary' ? String(salary) : String(budget));
  };

  const handleSave = async () => {
    const num = parseInt(editValue.replace(/\D/g, '')) || 0;
    const data = editField === 'salary'
      ? { salario_mensual: String(num) }
      : { presupuesto_mensual: String(num) };
    const success = await updateProfile(data);
    setEditField(null);
    if (success) {
      toast.success('Configuración guardada');
    } else {
      toast.error('Error guardando');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const handleExport = () => {
    toast.success('Datos exportados en CSV');
  };

  const displayEdit = editValue
    ? '$' + (parseInt(editValue.replace(/\D/g, '')) || 0).toLocaleString('en-US')
    : '';

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen bg-[#F8FAFC]">
        <div className="px-5 pt-14 pb-8 text-center" style={{ background: 'linear-gradient(180deg, #EEF2FF 0%, #F8FAFC 100%)' }}>
          <div className="w-20 h-20 rounded-full mx-auto mb-3 bg-[#E2E8F0] animate-pulse" />
          <div className="h-5 w-32 mx-auto bg-[#E2E8F0] rounded animate-pulse mb-2" />
          <div className="h-4 w-40 mx-auto bg-[#E2E8F0] rounded animate-pulse" />
        </div>
        <div className="px-4 space-y-4">
          <div className="h-40 bg-[#E2E8F0] rounded-2xl animate-pulse" />
          <div className="h-24 bg-[#E2E8F0] rounded-2xl animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#F8FAFC]">
      {/* Header */}
      <div
        className="px-5 pt-14 pb-8 text-center"
        style={{ background: 'linear-gradient(180deg, #EEF2FF 0%, #F8FAFC 100%)' }}
      >
        {/* Avatar */}
        <div
          className="w-20 h-20 rounded-full mx-auto mb-3 flex items-center justify-center text-3xl font-bold text-white shadow-lg"
          style={{ background: 'linear-gradient(135deg, #6366F1 0%, #7C3AED 100%)' }}
        >
          J
        </div>
        <p className="text-[#0F172A] font-bold text-lg">Finanzas App</p>
        <p className="text-[#64748B] text-sm">{formattedPhone}</p>
      </div>

      <div className="flex flex-col gap-4 px-4 pb-8">
        {/* Financial Plan Card */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-[#F8FAFC]">
            <p className="text-[#0F172A] font-bold text-sm">💼 Mi Plan Financiero</p>
          </div>

          {/* Salary */}
          <button
            onClick={() => openEdit('salary')}
            className="w-full flex items-center justify-between px-4 py-4 active:bg-[#F8FAFC] transition-colors border-b border-[#F8FAFC]"
          >
            <div className="text-left">
              <p className="text-[#94A3B8] text-xs mb-0.5">Salario mensual</p>
              <p className="text-[#0F172A] font-semibold text-sm">{formatCurrency(salary)}</p>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" strokeWidth="2.5">
              <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </button>

          {/* Budget */}
          <button
            onClick={() => openEdit('budget')}
            className="w-full flex items-center justify-between px-4 py-4 active:bg-[#F8FAFC] transition-colors border-b border-[#F8FAFC]"
          >
            <div className="text-left">
              <p className="text-[#94A3B8] text-xs mb-0.5">Presupuesto mensual</p>
              <p className="text-[#0F172A] font-semibold text-sm">{formatCurrency(budget)}</p>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" strokeWidth="2.5">
              <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </button>

          {/* Cut Day */}
          <div className="flex items-center justify-between px-4 py-4">
            <div>
              <p className="text-[#94A3B8] text-xs mb-0.5">Día de pago</p>
              <p className="text-[#0F172A] font-semibold text-sm">Día {cutDay} de cada mes</p>
            </div>
            <span className="text-2xl">📅</span>
          </div>
        </div>

        {/* Stats Card */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-[#F8FAFC]">
            <p className="text-[#0F172A] font-bold text-sm">📊 Estadísticas</p>
          </div>
          <div className="grid grid-cols-3 divide-x divide-[#F8FAFC]">
            <StatItem value="—" label="Transacciones" />
            <StatItem value="—" label="Meses activo" />
            <StatItem value="—" label="Confianza IA" color="#10B981" />
          </div>
        </div>

        {/* About */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-[#F8FAFC]">
            <p className="text-[#0F172A] font-bold text-sm">ℹ️ Cuenta</p>
          </div>
          <div className="px-4 py-3.5 flex items-center justify-between border-b border-[#F8FAFC]">
            <p className="text-[#64748B] text-sm">Versión</p>
            <span className="text-xs bg-[#EEF2FF] text-[#6366F1] font-medium px-2 py-0.5 rounded-full">1.0.0 MVP</span>
          </div>
          <div className="px-4 py-3.5 flex items-center justify-between">
            <p className="text-[#64748B] text-sm">Plan</p>
            <span className="text-xs bg-[#ECFDF5] text-[#10B981] font-medium px-2 py-0.5 rounded-full">✨ Gratuito</span>
          </div>
        </div>

        {/* Actions */}
        <button
          onClick={handleExport}
          className="w-full py-3.5 rounded-xl border-2 border-[#6366F1] text-[#6366F1] font-medium text-sm transition-colors active:bg-[#EEF2FF]"
        >
          📥 Exportar datos (CSV)
        </button>

        <button
          onClick={() => setShowLogoutModal(true)}
          className="w-full py-3 text-[#EF4444] font-medium text-sm transition-colors active:bg-[#FEF2F2] rounded-xl"
        >
          Cerrar sesión
        </button>
      </div>

      {/* Edit Bottom Sheet */}
      {editField && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center"
          onClick={() => setEditField(null)}
        >
          <div className="absolute inset-0 bg-black/50" />
          <div
            className="relative w-full max-w-[390px] bg-white rounded-t-2xl pb-8 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            style={{ animation: 'slideUp 0.25s ease-out' }}
          >
            <div className="flex justify-center pt-3 pb-4">
              <div className="w-10 h-1 bg-[#CBD5E1] rounded-full" />
            </div>
            <p className="text-[#0F172A] font-bold text-base px-5 mb-4">
              Editar {editField === 'salary' ? 'salario mensual' : 'presupuesto mensual'}
            </p>
            <div className="px-5 mb-5">
              <div
                className="flex items-center border-2 border-[#6366F1] rounded-xl px-4 py-4 bg-white"
                style={{ boxShadow: '0 0 0 3px rgba(99,102,241,0.1)' }}
              >
                <input
                  type="tel"
                  autoFocus
                  value={displayEdit}
                  onChange={(e) => setEditValue(e.target.value.replace(/\D/g, ''))}
                  placeholder="$0"
                  className="flex-1 outline-none bg-transparent text-[#0F172A] font-semibold text-xl placeholder:text-[#CBD5E1] placeholder:font-normal"
                />
                <span className="text-[#94A3B8] text-sm ml-2">COP</span>
              </div>
            </div>
            <div className="flex gap-3 px-5">
              <button
                onClick={() => setEditField(null)}
                className="flex-1 py-3.5 rounded-xl border-2 border-[#E2E8F0] text-[#64748B] font-medium text-sm"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                className="flex-1 py-3.5 rounded-xl bg-[#6366F1] text-white font-medium text-sm"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Logout Confirmation */}
      {showLogoutModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-6">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowLogoutModal(false)} />
          <div className="relative w-full max-w-[320px] bg-white rounded-2xl p-6 shadow-2xl text-center">
            <div className="text-4xl mb-3">👋</div>
            <h2 className="text-[#0F172A] font-bold text-lg mb-1">¿Cerrar sesión?</h2>
            <p className="text-[#64748B] text-sm mb-6">Tendrás que ingresar tu número de nuevo</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowLogoutModal(false)}
                className="flex-1 py-3 rounded-xl border-2 border-[#E2E8F0] text-[#64748B] font-medium text-sm"
              >
                Cancelar
              </button>
              <button
                onClick={handleLogout}
                className="flex-1 py-3 rounded-xl bg-[#EF4444] text-white font-medium text-sm"
              >
                Cerrar sesión
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

function StatItem({ value, label, color }: { value: string; label: string; color?: string }) {
  return (
    <div className="flex flex-col items-center py-4 px-2">
      <p className="font-bold text-xl mb-0.5" style={{ color: color || '#0F172A' }}>{value}</p>
      <p className="text-[#94A3B8] text-xs text-center">{label}</p>
    </div>
  );
}
