from django.core.cache import cache


class WhatsAppUserThrottle:
    """
    Limita mensajes por usuario para prevenir abuso.
    Max 30 mensajes por hora por usuario.
    """
    MAX_MESSAGES_PER_HOUR = 30

    @staticmethod
    def is_allowed(phone_number: str) -> bool:
        key = f"wa_throttle:{phone_number}"
        count = cache.get(key, 0)
        if count >= WhatsAppUserThrottle.MAX_MESSAGES_PER_HOUR:
            return False
        cache.set(key, count + 1, timeout=3600)
        return True
