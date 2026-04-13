/**
 * Formatea un valor numérico como moneda colombiana.
 * Ejemplo: 2350000 → "$2,350,000"
 */
export function formatCurrency(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '$0';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(num));
}

/** @deprecated Usa formatCurrency() en su lugar */
export function formatCOP(amount: number): string {
  return formatCurrency(amount);
}

/**
 * Formatea una fecha ISO a formato legible.
 * Ejemplo: "2026-04-07T14:30:00" → "7 abr 2026, 2:30 p.m."
 */
export function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat('es-CO', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(date);
}

/**
 * Formatea solo la fecha sin hora.
 * Ejemplo: "2026-04-07T14:30:00" → "7 abr"
 */
export function formatDateShort(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat('es-CO', {
    day: 'numeric',
    month: 'short',
  }).format(date);
}

/**
 * Retorna color CSS hex según el progreso del presupuesto.
 */
export function getBudgetColor(percentage: number): string {
  if (percentage < 70) return '#10B981';
  if (percentage < 90) return '#F59E0B';
  return '#EF4444';
}

/**
 * Retorna color CSS hex según tipo de transacción.
 */
export function getAmountColor(tipo: string): string {
  switch (tipo) {
    case 'gasto': return '#EF4444';
    case 'ingreso': return '#10B981';
    case 'transferencia_propia': return '#64748B';
    default: return '#0F172A';
  }
}

export function formatPhone(digits: string): string {
  const d = digits.slice(0, 10);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)} ${d.slice(3)}`;
  return `${d.slice(0, 3)} ${d.slice(3, 6)} ${d.slice(6)}`;
}

export function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 10) return phone;
  return `+57 ${digits.slice(0, 3)} *** ${digits.slice(6)}`;
}
