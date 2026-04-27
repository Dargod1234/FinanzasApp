import logging
import time

logger = logging.getLogger(__name__)

# Claves en Django cache para estado compartido entre workers
_CACHE_KEY_STATE = "ocr_circuit_breaker:state"
_CACHE_KEY_FAILURES = "ocr_circuit_breaker:failures"
_CACHE_KEY_LAST_FAILURE = "ocr_circuit_breaker:last_failure"
_CACHE_TTL = 3600  # 1 hora — el cache se auto-limpia si el breaker nunca se resetea

# Estados posibles
STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"


class OCRCircuitBreaker:
    """
    Circuit breaker persistido en Django cache para que el estado sea compartido
    entre los múltiples workers de Gunicorn (en lugar de vivir solo en memoria).

    Compatible con cualquier backend de Django cache (db, memcached, redis, locmem).
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def _get_cache(self):
        """Importación lazy para evitar usar el cache antes de que Django esté listo."""
        from django.core.cache import cache
        return cache

    def _get_state(self) -> str:
        return self._get_cache().get(_CACHE_KEY_STATE, STATE_CLOSED)

    def _set_state(self, state: str):
        self._get_cache().set(_CACHE_KEY_STATE, state, _CACHE_TTL)

    def _get_failure_count(self) -> int:
        return self._get_cache().get(_CACHE_KEY_FAILURES, 0)

    def _get_last_failure_time(self):
        return self._get_cache().get(_CACHE_KEY_LAST_FAILURE, None)

    def can_execute(self) -> bool:
        state = self._get_state()

        if state == STATE_CLOSED:
            return True

        if state == STATE_OPEN:
            last_failure = self._get_last_failure_time()
            if last_failure and (time.time() - last_failure) >= self.recovery_timeout:
                self._set_state(STATE_HALF_OPEN)
                logger.info("Circuit breaker → HALF_OPEN (probando recuperación OCR)")
                return True
            return False

        if state == STATE_HALF_OPEN:
            return True

        return False

    def record_success(self):
        cache = self._get_cache()
        cache.set(_CACHE_KEY_FAILURES, 0, _CACHE_TTL)
        cache.set(_CACHE_KEY_STATE, STATE_CLOSED, _CACHE_TTL)
        logger.debug("Circuit breaker → CLOSED (OCR respondió OK)")

    def record_failure(self):
        cache = self._get_cache()
        cache.set(_CACHE_KEY_LAST_FAILURE, time.time(), _CACHE_TTL)

        # Incremento atómico cuando el backend lo soporta (memcached/redis)
        # Para DatabaseCache usamos get+set con tolerancia a race conditions leves
        try:
            new_count = cache.incr(_CACHE_KEY_FAILURES)
        except ValueError:
            # La clave no existe aún — inicializar
            cache.set(_CACHE_KEY_FAILURES, 1, _CACHE_TTL)
            new_count = 1

        if new_count >= self.failure_threshold:
            cache.set(_CACHE_KEY_STATE, STATE_OPEN, _CACHE_TTL)
            logger.warning(
                "Circuit breaker → OPEN (fallos=%s, umbral=%s)",
                new_count, self.failure_threshold
            )


# Singleton — la instancia ahora es stateless en memoria; el estado real vive en cache
ocr_breaker = OCRCircuitBreaker()
