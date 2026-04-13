import type { CategoryInfo } from '../types';

export const CATEGORIES: Record<string, CategoryInfo> = {
  alimentacion: {
    id: 'alimentacion',
    label: 'Alimentación',
    icon: '🍔',
    color: '#F59E0B',
  },
  transporte: {
    id: 'transporte',
    label: 'Transporte',
    icon: '🚗',
    color: '#3B82F6',
  },
  servicios: {
    id: 'servicios',
    label: 'Servicios',
    icon: '💡',
    color: '#8B5CF6',
  },
  salud: {
    id: 'salud',
    label: 'Salud',
    icon: '🏥',
    color: '#EC4899',
  },
  entretenimiento: {
    id: 'entretenimiento',
    label: 'Entretenimiento',
    icon: '🎮',
    color: '#14B8A6',
  },
  educacion: {
    id: 'educacion',
    label: 'Educación',
    icon: '📚',
    color: '#6366F1',
  },
  hogar: {
    id: 'hogar',
    label: 'Hogar',
    icon: '🏠',
    color: '#F97316',
  },
  ropa: {
    id: 'ropa',
    label: 'Ropa',
    icon: '👕',
    color: '#A855F7',
  },
  tecnologia: {
    id: 'tecnologia',
    label: 'Tecnología',
    icon: '💻',
    color: '#06B6D4',
  },
  ahorro: {
    id: 'ahorro',
    label: 'Ahorro',
    icon: '🏦',
    color: '#10B981',
  },
  deudas: {
    id: 'deudas',
    label: 'Deudas',
    icon: '💳',
    color: '#EF4444',
  },
  transferencia: {
    id: 'transferencia',
    label: 'Transferencia',
    icon: '👤',
    color: '#64748B',
  },
  sin_categorizar: {
    id: 'sin_categorizar',
    label: 'Sin Categorizar',
    icon: '❓',
    color: '#94A3B8',
  },
};

export function getCategoryInfo(categoryId: string): CategoryInfo {
  return CATEGORIES[categoryId] || CATEGORIES.sin_categorizar;
}
