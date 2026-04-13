import { useState } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { useProfile } from '../../hooks/useProfile';
import { formatCOP } from '../utils/format';

export function Onboarding() {
  const navigate = useNavigate();
  const { updateProfile } = useProfile();
  const [step, setStep] = useState(0);
  const [salaryDigits, setSalaryDigits] = useState('');
  const [budgetDigits, setBudgetDigits] = useState('');
  const [cutDay, setCutDay] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const salary = parseInt(salaryDigits) || 0;
  const budget = parseInt(budgetDigits) || 0;
  const suggestedBudget = Math.round(salary * 0.67);

  const handleSalaryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const digits = e.target.value.replace(/\D/g, '').slice(0, 10);
    setSalaryDigits(digits);
  };

  const handleBudgetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const digits = e.target.value.replace(/\D/g, '').slice(0, 10);
    setBudgetDigits(digits);
  };

  const handleNext = () => {
    if (step < 2) {
      setStep(step + 1);
    } else {
      finishOnboarding();
    }
  };

  const finishOnboarding = async () => {
    setSaving(true);
    const success = await updateProfile({
      salario_mensual: String(salary || 4500000),
      presupuesto_mensual: String(budget || 3000000),
      dia_corte: cutDay || 1,
      onboarding_completed: true,
    });
    setSaving(false);
    if (success) {
      navigate('/app');
    } else {
      toast.error('Error guardando configuración. Intenta de nuevo.');
    }
  };

  const handleSkip = async () => {
    setSaving(true);
    await updateProfile({ onboarding_completed: true });
    setSaving(false);
    navigate('/app');
  };

  const canNext = step === 0
    ? salary > 0
    : step === 1
    ? budget > 0
    : cutDay !== null;

  const salaryDisplay = salary > 0 ? '$' + salary.toLocaleString('en-US') : '';
  const budgetDisplay = budget > 0 ? '$' + budget.toLocaleString('en-US') : '';

  return (
    <div className="flex flex-col min-h-screen px-6 py-8 bg-[#F8FAFC]">
      {/* Progress Dots */}
      <div className="flex items-center justify-center gap-2 mt-6 mb-8">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="rounded-full transition-all duration-300"
            style={{
              width: i === step ? 24 : 8,
              height: 8,
              backgroundColor: i <= step ? '#6366F1' : '#E2E8F0',
            }}
          />
        ))}
      </div>

      {/* Step 0 - Salary */}
      {step === 0 && (
        <div className="flex-1 flex flex-col">
          <div className="flex justify-center mb-8">
            <div className="w-24 h-24 rounded-full bg-[#EEF2FF] flex items-center justify-center">
              <span className="text-5xl">💼</span>
            </div>
          </div>
          <h1 className="text-[#0F172A] font-bold text-2xl text-center mb-2">
            ¿Cuál es tu salario mensual?
          </h1>
          <p className="text-[#64748B] text-sm text-center mb-8">
            Esto nos ayuda a calcular tu ahorro real
          </p>
          <div className="mb-2">
            <div
              className="flex items-center border-2 rounded-xl px-4 py-4 bg-white"
              style={{ borderColor: salary > 0 ? '#6366F1' : '#E2E8F0' }}
            >
              <input
                type="tel"
                value={salaryDisplay}
                onChange={handleSalaryChange}
                placeholder="$0"
                className="flex-1 outline-none bg-transparent text-[#0F172A] font-semibold text-xl placeholder:text-[#CBD5E1] placeholder:font-normal"
              />
              <span className="text-[#94A3B8] text-sm ml-2">COP</span>
            </div>
          </div>
        </div>
      )}

      {/* Step 1 - Budget */}
      {step === 1 && (
        <div className="flex-1 flex flex-col">
          <div className="flex justify-center mb-8">
            <div className="w-24 h-24 rounded-full bg-[#ECFDF5] flex items-center justify-center">
              <span className="text-5xl">🐷</span>
            </div>
          </div>
          <h1 className="text-[#0F172A] font-bold text-2xl text-center mb-2">
            ¿Cuánto quieres gastar máximo al mes?
          </h1>
          <p className="text-[#64748B] text-sm text-center mb-8">
            Te avisaremos cuando estés cerca del límite
          </p>
          <div className="mb-2">
            <div
              className="flex items-center border-2 rounded-xl px-4 py-4 bg-white"
              style={{ borderColor: budget > 0 ? '#6366F1' : '#E2E8F0' }}
            >
              <input
                type="tel"
                value={budgetDisplay}
                onChange={handleBudgetChange}
                placeholder="$0"
                className="flex-1 outline-none bg-transparent text-[#0F172A] font-semibold text-xl placeholder:text-[#CBD5E1] placeholder:font-normal"
              />
              <span className="text-[#94A3B8] text-sm ml-2">COP</span>
            </div>
          </div>
          {salary > 0 && (
            <div className="flex items-center gap-1.5 mt-2">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="#10B981">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
              <p className="text-[#10B981] text-xs">
                Sugerido: {formatCOP(suggestedBudget)} (67% de tu salario)
              </p>
            </div>
          )}
        </div>
      )}

      {/* Step 2 - Cut Day */}
      {step === 2 && (
        <div className="flex-1 flex flex-col">
          <div className="flex justify-center mb-8">
            <div className="w-24 h-24 rounded-full bg-[#FEF3C7] flex items-center justify-center">
              <span className="text-5xl">📅</span>
            </div>
          </div>
          <h1 className="text-[#0F172A] font-bold text-2xl text-center mb-2">
            ¿Qué día te pagan?
          </h1>
          <p className="text-[#64748B] text-sm text-center mb-6">
            Así calculamos tu ciclo financiero mensual
          </p>
          <div className="grid grid-cols-7 gap-2">
            {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
              <button
                key={day}
                onClick={() => setCutDay(day)}
                className="aspect-square rounded-lg flex items-center justify-center text-sm font-medium transition-all"
                style={{
                  backgroundColor: cutDay === day ? '#6366F1' : '#F1F5F9',
                  color: cutDay === day ? 'white' : '#0F172A',
                }}
              >
                {day}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-auto pt-6 flex flex-col gap-3">
        <button
          onClick={handleNext}
          disabled={!canNext || saving}
          className="w-full py-4 rounded-xl font-semibold text-base transition-all"
          style={{
            backgroundColor: canNext && !saving ? '#6366F1' : '#C7D2FE',
            color: canNext && !saving ? 'white' : '#94A3B8',
            cursor: canNext && !saving ? 'pointer' : 'not-allowed',
          }}
        >
          {saving ? 'Guardando...' : step === 2 ? 'Comenzar 🚀' : 'Siguiente'}
        </button>
        <button
          onClick={handleSkip}
          className="text-[#94A3B8] text-sm text-center py-2"
        >
          Configurar después
        </button>
      </div>
    </div>
  );
}
