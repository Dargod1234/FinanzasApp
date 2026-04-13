import random
import hashlib
from django.core.cache import cache


class OTPService:
    """
    Servicio de One-Time Password.
    MVP: Almacena OTP en cache (Redis/Memcached/DB backend).
    Producción: Usar servicio dedicado (Twilio Verify, etc.)
    """
    OTP_EXPIRY_SECONDS = 300  # 5 minutos
    MAX_ATTEMPTS = 3

    @staticmethod
    def generate_otp(phone_number: str) -> str:
        """Genera un OTP de 6 dígitos y lo almacena en cache."""
        otp = str(random.SystemRandom().randint(100000, 999999))
        cache_key = f"otp:{hashlib.sha256(phone_number.encode()).hexdigest()}"
        cache.set(cache_key, {
            'code': otp,
            'attempts': 0
        }, timeout=OTPService.OTP_EXPIRY_SECONDS)
        return otp

    @staticmethod
    def verify_otp(phone_number: str, code: str) -> bool:
        """Verifica el OTP. Retorna True si es válido."""
        cache_key = f"otp:{hashlib.sha256(phone_number.encode()).hexdigest()}"
        otp_data = cache.get(cache_key)

        if not otp_data:
            return False

        if otp_data['attempts'] >= OTPService.MAX_ATTEMPTS:
            cache.delete(cache_key)
            return False

        if otp_data['code'] == code:
            cache.delete(cache_key)  # OTP de un solo uso
            return True

        # Incrementar intentos fallidos
        otp_data['attempts'] += 1
        cache.set(cache_key, otp_data, timeout=OTPService.OTP_EXPIRY_SECONDS)
        return False
