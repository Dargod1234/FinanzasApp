import { useState } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { useAuth } from '../../hooks/useAuth';
import { formatPhone } from '../utils/format';

export function Login() {
  const navigate = useNavigate();
  const { requestOtp, loading } = useAuth();
  const [digits, setDigits] = useState('');
  const [touched, setTouched] = useState(false);

  const isValid = digits.length === 10;
  const showError = touched && !isValid && digits.length > 0;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, '').slice(0, 10);
    setDigits(raw);
  };

  const handleContinue = async () => {
    if (!isValid || loading) return;
    const success = await requestOtp(digits);
    if (success) {
      navigate('/verify');
    } else {
      toast.error('Error enviando código. Intenta de nuevo.');
    }
  };

  const displayValue = formatPhone(digits);

  return (
    <div className="flex flex-col min-h-screen px-6 py-8 bg-[#F8FAFC]">
      {/* Logo */}
      <div className="flex flex-col items-center mt-8 mb-6">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mb-3 shadow-lg"
          style={{ background: 'linear-gradient(135deg, #6366F1 0%, #818CF8 100%)' }}
        >
          <span className="text-3xl">💳</span>
        </div>
        <span className="text-[#6366F1] font-bold text-xl tracking-tight">Finanzas App</span>
      </div>

      {/* Illustration */}
      <div className="flex justify-center mb-8">
        <div className="relative w-56 h-44">
          {/* Background card */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-48 h-36 bg-white rounded-2xl shadow-md flex flex-col items-center justify-center gap-2 border border-[#E2E8F0]">
              <div className="flex gap-3">
                <span className="text-3xl">📊</span>
                <span className="text-3xl">💰</span>
              </div>
              <div className="w-32 h-2 bg-[#6366F1] rounded-full opacity-30" />
              <div className="w-24 h-1.5 bg-[#10B981] rounded-full opacity-40" />
              <div className="flex gap-2 mt-1">
                <div className="w-8 h-8 bg-[#EEF2FF] rounded-lg flex items-center justify-center">
                  <span className="text-sm">📈</span>
                </div>
                <div className="w-8 h-8 bg-[#ECFDF5] rounded-lg flex items-center justify-center">
                  <span className="text-sm">🪙</span>
                </div>
                <div className="w-8 h-8 bg-[#FEF3C7] rounded-lg flex items-center justify-center">
                  <span className="text-sm">🎯</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Title */}
      <div className="text-center mb-8">
        <h1 className="text-[#0F172A] font-bold text-2xl leading-tight mb-2">
          Controla tus finanzas sin esfuerzo
        </h1>
        <p className="text-[#64748B] text-sm leading-relaxed">
          Envía fotos de tus comprobantes por WhatsApp y nosotros hacemos el resto
        </p>
      </div>

      {/* Phone Input */}
      <div className="mb-4">
        <label className="block text-[#0F172A] text-sm font-medium mb-2">
          Número de celular
        </label>
        <div
          className="flex items-center border-2 rounded-xl px-4 py-3 bg-white transition-colors"
          style={{
            borderColor: showError ? '#EF4444' : digits.length > 0 ? '#6366F1' : '#E2E8F0',
            boxShadow: digits.length > 0 && !showError ? '0 0 0 3px rgba(99,102,241,0.1)' : undefined,
          }}
        >
          <span className="text-lg mr-2">🇨🇴</span>
          <span className="text-[#64748B] text-sm font-medium mr-2">+57</span>
          <div className="w-px h-5 bg-[#E2E8F0] mr-2" />
          <input
            type="tel"
            value={displayValue}
            onChange={handleChange}
            onBlur={() => setTouched(true)}
            placeholder="300 123 4567"
            className="flex-1 outline-none bg-transparent text-[#0F172A] text-sm placeholder:text-[#94A3B8]"
          />
        </div>
        {showError && (
          <p className="text-[#EF4444] text-xs mt-1.5">
            Ingresa un número válido de 10 dígitos
          </p>
        )}
      </div>

      {/* CTA Button */}
      <button
        onClick={handleContinue}
        disabled={!isValid || loading}
        className="w-full py-4 rounded-xl text-white font-semibold text-base transition-all"
        style={{
          backgroundColor: isValid && !loading ? '#6366F1' : '#C7D2FE',
          color: isValid && !loading ? 'white' : '#94A3B8',
          cursor: isValid && !loading ? 'pointer' : 'not-allowed',
        }}
      >
        {loading ? 'Enviando...' : 'Continuar'}
      </button>

      {/* Legal */}
      <p className="text-center text-[#94A3B8] text-xs mt-6 leading-relaxed">
        Al continuar, aceptas los{' '}
        <span className="text-[#6366F1] underline cursor-pointer">Términos de Servicio</span>
        {' '}y la{' '}
        <span className="text-[#6366F1] underline cursor-pointer">Política de Privacidad</span>
      </p>
    </div>
  );
}
