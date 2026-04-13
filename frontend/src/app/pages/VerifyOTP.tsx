import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../../hooks/useAuth';
import { maskPhone } from '../utils/format';

type OtpState = 'idle' | 'loading' | 'error';

export function VerifyOTP() {
  const navigate = useNavigate();
  const { phone, verifyOtp, requestOtp } = useAuth();
  const [otp, setOtp] = useState(Array(6).fill(''));
  const [state, setState] = useState<OtpState>('idle');
  const [timeLeft, setTimeLeft] = useState(60);
  const [canResend, setCanResend] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  useEffect(() => {
    if (timeLeft <= 0) {
      setCanResend(true);
      return;
    }
    const t = setTimeout(() => setTimeLeft((v) => v - 1), 1000);
    return () => clearTimeout(t);
  }, [timeLeft]);

  const handleChange = (index: number, value: string) => {
    if (state === 'loading') return;
    const digit = value.replace(/\D/g, '').slice(-1);
    const newOtp = [...otp];
    newOtp[index] = digit;
    setOtp(newOtp);
    setState('idle');

    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-validate when all 6 are filled
    if (digit && index === 5) {
      const fullCode = [...newOtp.slice(0, 5), digit].join('');
      verifyCode(fullCode);
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
    if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
    if (e.key === 'ArrowRight' && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      const newOtp = pasted.split('');
      setOtp(newOtp);
      inputRefs.current[5]?.focus();
      verifyCode(pasted);
    }
    e.preventDefault();
  };

  const verifyCode = async (code: string) => {
    setState('loading');
    const response = await verifyOtp(code);
    if (response) {
      if (response.is_new_user || !response.onboarding_completed) {
        navigate('/onboarding');
      } else {
        navigate('/app');
      }
    } else {
      setState('error');
      setOtp(Array(6).fill(''));
      setTimeout(() => inputRefs.current[0]?.focus(), 50);
    }
  };

  const handleResend = async () => {
    setTimeLeft(60);
    setCanResend(false);
    setOtp(Array(6).fill(''));
    setState('idle');
    await requestOtp(phone);
    setTimeout(() => inputRefs.current[0]?.focus(), 50);
  };

  const isError = state === 'error';
  const isLoading = state === 'loading';

  return (
    <div className="flex flex-col min-h-screen px-6 py-8 bg-[#F8FAFC]">
      {/* Header */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-1 text-[#64748B] mb-8 -ml-1 mt-4"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M12 5l-7 7 7 7" />
        </svg>
        <span className="text-sm">Volver</span>
      </button>

      {/* Icon */}
      <div className="flex justify-center mb-6">
        <div className="w-20 h-20 rounded-full bg-[#EEF2FF] flex items-center justify-center">
          <span className="text-4xl">💬</span>
        </div>
      </div>

      {/* Title */}
      <div className="text-center mb-8">
        <h1 className="text-[#0F172A] font-bold text-2xl mb-2">
          Código de verificación
        </h1>
        <p className="text-[#64748B] text-sm leading-relaxed">
          Enviamos un código de 6 dígitos al
          <br />
          <span className="font-medium">{maskPhone(phone)}</span>
        </p>
      </div>

      {/* OTP Inputs */}
      <div className="flex justify-center gap-3 mb-4" onPaste={handlePaste}>
        {otp.map((digit, i) => (
          <input
            key={i}
            ref={(el) => { inputRefs.current[i] = el; }}
            type="tel"
            inputMode="numeric"
            maxLength={1}
            value={digit}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            disabled={isLoading}
            className="w-12 h-14 text-center text-xl font-semibold rounded-xl border-2 outline-none transition-all bg-white text-[#0F172A]"
            style={{
              borderColor: isError
                ? '#EF4444'
                : focusedIndex === i || digit
                ? '#6366F1'
                : '#E2E8F0',
              boxShadow: isError && digit
                ? '0 0 0 3px rgba(239,68,68,0.1)'
                : focusedIndex === i
                ? '0 0 0 3px rgba(99,102,241,0.1)'
                : undefined,
              backgroundColor: isError ? '#FEF2F2' : 'white',
            }}
            onFocus={() => setFocusedIndex(i)}
            onBlur={() => setFocusedIndex(-1)}
          />
        ))}
      </div>

      {/* Error message */}
      {isError && (
        <p className="text-center text-[#EF4444] text-sm mb-4">
          Código incorrecto. Intenta de nuevo.
        </p>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center gap-2 mb-4">
          <svg className="animate-spin w-5 h-5 text-[#6366F1]" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-[#64748B] text-sm">Verificando...</span>
        </div>
      )}

      {/* Timer / Resend */}
      <div className="flex justify-center mb-8">
        {canResend ? (
          <button
            onClick={handleResend}
            className="text-[#6366F1] text-sm font-medium underline"
          >
            Reenviar código
          </button>
        ) : (
          <p className="text-[#94A3B8] text-sm">
            Reenviar código en{' '}
            <span className="font-medium text-[#64748B]">
              0:{String(timeLeft).padStart(2, '0')}
            </span>
          </p>
        )}
      </div>

      {/* Change number */}
      <p className="text-center text-[#94A3B8] text-sm mt-auto pt-4">
        ¿Número incorrecto?{' '}
        <button
          onClick={() => navigate('/')}
          className="text-[#6366F1] underline font-medium"
        >
          Cambiar
        </button>
      </p>
    </div>
  );
}