import { useNavigate } from 'react-router';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { useDashboard } from '../../hooks/useDashboard';
import { formatCurrency, getBudgetColor } from '../utils/format';
import { getCategoryInfo } from '../../constants/categories';

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number }> }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-[#E2E8F0] rounded-lg px-3 py-2 shadow-sm text-xs">
        <p className="font-medium text-[#0F172A]">{payload[0].name}</p>
        <p className="text-[#64748B]">{formatCurrency(payload[0].value)}</p>
      </div>
    );
  }
  return null;
};

export function Dashboard() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useDashboard();

  if (loading) {
    return (
      <div className="flex flex-col pb-6">
        <div className="px-5 pt-14 pb-6" style={{ background: 'linear-gradient(180deg, #EEF2FF 0%, #F8FAFC 100%)' }}>
          <div className="h-6 w-32 bg-[#E2E8F0] rounded animate-pulse mb-2" />
          <div className="h-8 w-48 bg-[#E2E8F0] rounded animate-pulse" />
        </div>
        <div className="px-4 space-y-4 mt-2">
          <div className="h-40 bg-[#E2E8F0] rounded-2xl animate-pulse" />
          <div className="h-24 bg-[#E2E8F0] rounded-2xl animate-pulse" />
          <div className="h-64 bg-[#E2E8F0] rounded-2xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-6 text-center">
        <span className="text-4xl mb-4">😕</span>
        <p className="text-[#EF4444] mb-4">{error || 'Error desconocido'}</p>
        <button
          onClick={reload}
          className="px-6 py-2 rounded-xl text-white font-medium"
          style={{ backgroundColor: '#6366F1' }}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const salaryNum = parseFloat(data.salario) || 0;
  const gastosNum = parseFloat(data.total_gastos) || 0;
  const ahorroNum = parseFloat(data.ahorro_real) || 0;
  const presupuestoNum = parseFloat(data.presupuesto) || 0;
  const porcentaje = Math.min(data.progreso_presupuesto, 100);
  const progressColor = getBudgetColor(porcentaje);

  // Build chart data from gastos_por_categoria
  const categoryChartData = Object.entries(data.gastos_por_categoria).map(([key, value]) => {
    const info = getCategoryInfo(key);
    return {
      name: info.label,
      amount: parseFloat(value) || 0,
      color: info.color,
    };
  });

  return (
    <div className="flex flex-col pb-6">
      {/* Header */}
      <div
        className="px-5 pt-14 pb-6"
        style={{ background: 'linear-gradient(180deg, #EEF2FF 0%, #F8FAFC 100%)' }}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[#6366F1] text-sm font-medium">Buenos días 👋</p>
            <h1 className="text-[#0F172A] font-bold text-2xl">Dashboard</h1>
          </div>
          <div
            className="w-11 h-11 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-md"
            style={{ background: 'linear-gradient(135deg, #6366F1 0%, #818CF8 100%)' }}
          >
            U
          </div>
        </div>
      </div>

      {/* Savings Card */}
      <div className="px-4 -mt-2">
        <div
          className="rounded-2xl p-5 shadow-lg"
          style={{ background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 60%, #6366F1 100%)' }}
        >
          <p className="text-indigo-200 text-sm mb-1">Ahorro del mes</p>
          <p
            className="font-bold text-4xl mb-4"
            style={{ color: ahorroNum >= 0 ? '#86EFAC' : '#FCA5A5' }}
          >
            {formatCurrency(ahorroNum)}
          </p>
          <div className="flex items-center gap-4">
            <div>
              <p className="text-indigo-300 text-xs mb-0.5">Salario</p>
              <p className="text-white font-semibold text-sm">{formatCurrency(salaryNum)}</p>
            </div>
            <div className="w-px h-8 bg-indigo-400/50" />
            <div>
              <p className="text-indigo-300 text-xs mb-0.5">Gastos</p>
              <p className="text-white font-semibold text-sm">{formatCurrency(gastosNum)}</p>
            </div>
            <div className="w-px h-8 bg-indigo-400/50" />
            <div>
              <p className="text-indigo-300 text-xs mb-0.5">Presupuesto</p>
              <p className="text-white font-semibold text-sm">{formatCurrency(presupuestoNum)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Budget Progress */}
      <div className="mx-4 mt-4 bg-white rounded-2xl p-4 shadow-sm border border-[#F1F5F9]">
        <div className="flex justify-between items-center mb-3">
          <p className="text-[#0F172A] font-semibold text-sm">Presupuesto mensual</p>
          <span
            className="text-xs font-bold px-2 py-0.5 rounded-full"
            style={{
              backgroundColor: progressColor + '20',
              color: progressColor,
            }}
          >
            {porcentaje}%
          </span>
        </div>
        <div className="h-2.5 bg-[#F1F5F9] rounded-full overflow-hidden mb-2">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${porcentaje}%`, backgroundColor: progressColor }}
          />
        </div>
        <div className="flex justify-between">
          <p className="text-[#64748B] text-xs">
            Has usado el {porcentaje}% de tu presupuesto
          </p>
          <p className="text-[#64748B] text-xs">
            Quedan {formatCurrency(presupuestoNum - gastosNum)}
          </p>
        </div>
      </div>

      {/* Category Chart */}
      {categoryChartData.length > 0 && (
        <div className="mx-4 mt-4 bg-white rounded-2xl p-4 shadow-sm border border-[#F1F5F9]">
          <p className="text-[#0F172A] font-semibold text-sm mb-1">Gastos por Categoría</p>
          <ResponsiveContainer width="100%" height={190}>
            <PieChart>
              <Pie
                data={categoryChartData}
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={78}
                dataKey="amount"
                nameKey="name"
                paddingAngle={3}
                startAngle={90}
                endAngle={-270}
              >
                {categoryChartData.map((cat, i) => (
                  <Cell key={i} fill={cat.color} strokeWidth={0} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-1">
            {categoryChartData.map((cat) => (
              <div key={cat.name} className="flex items-center gap-2">
                <div
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: cat.color }}
                />
                <div className="min-w-0">
                  <p className="text-[#0F172A] text-xs font-medium truncate">{cat.name}</p>
                  <p className="text-[#64748B] text-xs">{formatCurrency(cat.amount)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {data.transacciones_count === 0 && (
        <div className="mx-4 mt-4 bg-white rounded-2xl p-6 shadow-sm border border-[#F1F5F9] text-center">
          <span className="text-4xl mb-3 block">📸</span>
          <p className="text-[#0F172A] font-semibold mb-1">¡Bienvenido!</p>
          <p className="text-[#64748B] text-sm">Envía tu primer comprobante por WhatsApp para empezar</p>
        </div>
      )}

      {/* View All Transactions */}
      {data.transacciones_count > 0 && (
        <div className="mx-4 mt-4">
          <button
            onClick={() => navigate('/app/transactions')}
            className="w-full py-3 rounded-xl border-2 border-[#E2E8F0] text-[#6366F1] font-medium text-sm"
          >
            Ver {data.transacciones_count} transacciones →
          </button>
        </div>
      )}

      {/* WhatsApp Button */}
      <div className="mx-4 mt-4">
        <a
          href="https://wa.me/573001234567?text=Hola%2C%20quiero%20registrar%20un%20gasto"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2.5 w-full py-4 rounded-2xl text-white font-semibold text-base shadow-md transition-opacity active:opacity-90"
          style={{ backgroundColor: '#25D366' }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
          </svg>
          📸 Registrar gasto vía WhatsApp
        </a>
      </div>
    </div>
  );
}