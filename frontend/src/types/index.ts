// === Auth ===
export interface AuthResponse {
  access: string;
  refresh: string;
  is_new_user: boolean;
  onboarding_completed: boolean;
}

// === Profile ===
export interface Profile {
  salario_mensual: string | null;
  presupuesto_mensual: string | null;
  dia_corte: number;
  onboarding_completed: boolean;
}

// === Transaction ===
export type TransactionType = 'gasto' | 'ingreso' | 'transferencia_propia';
export type TransactionStatus = 'pending' | 'confirmed' | 'rejected' | 'needs_review' | 'error';
export type BankEntity = 'nequi' | 'daviplata' | 'bancolombia' | 'otro';

export interface Transaction {
  id: number;
  tipo: TransactionType;
  entidad: BankEntity;
  categoria: string;
  destinatario: string;
  fecha_transaccion: string;
  descripcion: string;
  estado: TransactionStatus;
  confianza_ia: number;
  monto_display: string;
  created_at: string;
}

export interface TransactionDetail extends Transaction {
  image_url?: string;
  referencia_bancaria: string;
}

// === Dashboard ===
export interface DashboardSummary {
  ciclo: {
    inicio: string;
    fin: string;
  };
  salario: string;
  presupuesto: string;
  total_gastos: string;
  total_ingresos: string;
  ahorro_real: string;
  progreso_presupuesto: number;
  gastos_por_categoria: Record<string, string>;
  transacciones_count: number;
}

// === Categories ===
export interface CategoryInfo {
  id: string;
  label: string;
  icon: string;
  color: string;
}

// === API ===
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail?: string;
  message?: string;
  [key: string]: unknown;
}
