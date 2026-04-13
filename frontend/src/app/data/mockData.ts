export interface Transaction {
  id: string;
  emoji: string;
  name: string;
  category: string;
  bank: string;
  date: string;
  amount: number; // negative = gasto, positive = ingreso
  confidence: number; // 0-1
  reference: string;
  time: string;
  status: 'confirmed' | 'pending' | 'rejected';
}

export const mockTransactions: Transaction[] = [
  {
    id: '1',
    emoji: '🍔',
    name: 'Rappi Colombia',
    category: 'Alimentación',
    bank: 'Nequi',
    date: '7 abr',
    amount: -45000,
    confidence: 0.95,
    reference: 'TXN-20240407-001',
    time: '12:34',
    status: 'confirmed',
  },
  {
    id: '2',
    emoji: '🚗',
    name: 'Uber',
    category: 'Transporte',
    bank: 'Daviplata',
    date: '6 abr',
    amount: -23500,
    confidence: 0.91,
    reference: 'TXN-20240406-002',
    time: '09:15',
    status: 'confirmed',
  },
  {
    id: '3',
    emoji: '🏠',
    name: 'Almacenes Éxito',
    category: 'Hogar',
    bank: 'Bancolombia',
    date: '5 abr',
    amount: -187000,
    confidence: 0.88,
    reference: 'TXN-20240405-003',
    time: '16:50',
    status: 'confirmed',
  },
  {
    id: '4',
    emoji: '💡',
    name: 'EPM Medellín',
    category: 'Servicios',
    bank: 'Bancolombia',
    date: '4 abr',
    amount: -95000,
    confidence: 0.75,
    reference: 'TXN-20240404-004',
    time: '08:00',
    status: 'confirmed',
  },
  {
    id: '5',
    emoji: '🎮',
    name: 'Netflix',
    category: 'Entretenimiento',
    bank: 'Nequi',
    date: '3 abr',
    amount: -38900,
    confidence: 0.97,
    reference: 'TXN-20240403-005',
    time: '00:01',
    status: 'confirmed',
  },
  {
    id: '6',
    emoji: '💰',
    name: 'Empresa XYZ',
    category: 'Ingreso',
    bank: 'Bancolombia',
    date: '1 abr',
    amount: 4500000,
    confidence: 0.99,
    reference: 'TXN-20240401-006',
    time: '07:30',
    status: 'confirmed',
  },
];

export const mockCategories = [
  { name: 'Alimentación', amount: 680000, color: '#6366F1' },
  { name: 'Transporte', amount: 420000, color: '#10B981' },
  { name: 'Hogar', amount: 510000, color: '#F59E0B' },
  { name: 'Entretenimiento', amount: 320000, color: '#EF4444' },
  { name: 'Otros', amount: 220000, color: '#94A3B8' },
];

export const allCategories = [
  { emoji: '🍔', name: 'Alimentación' },
  { emoji: '🚗', name: 'Transporte' },
  { emoji: '🏠', name: 'Hogar' },
  { emoji: '💡', name: 'Servicios' },
  { emoji: '🎮', name: 'Entretenimiento' },
  { emoji: '💰', name: 'Ingreso' },
  { emoji: '🛍️', name: 'Compras' },
  { emoji: '💊', name: 'Salud' },
  { emoji: '📦', name: 'Otros' },
];

export const mockProfile = {
  phone: '+57 300 123 4567',
  name: 'Juan',
  salary: 4500000,
  budget: 3000000,
  cutDay: 1,
  totalTransactions: 47,
  monthsUsing: 3,
  aiConfidence: 94,
};
