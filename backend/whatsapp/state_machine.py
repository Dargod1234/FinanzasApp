from enum import Enum
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    QUERYING = "querying"


class ConversationManager:
    """
    Gestiona el estado de conversación por usuario.
    Usa cache para persistir estado entre requests.
    TTL de 30 minutos — si el usuario no responde, vuelve a IDLE.
    """
    STATE_TTL = 1800  # 30 minutos

    @staticmethod
    def _cache_key(phone_number: str) -> str:
        return f"wa_state:{phone_number}"

    @staticmethod
    def get_state(phone_number: str) -> dict:
        """Obtiene el estado actual de la conversación."""
        key = ConversationManager._cache_key(phone_number)
        state_data = cache.get(key)
        if state_data is None:
            return {
                'state': ConversationState.IDLE.value,
                'pending_transaction_id': None,
                'context': {}
            }
        return state_data

    @staticmethod
    def set_state(phone_number: str, state: ConversationState,
                  pending_transaction_id: int = None, context: dict = None):
        """Actualiza el estado de la conversación."""
        key = ConversationManager._cache_key(phone_number)
        state_data = {
            'state': state.value,
            'pending_transaction_id': pending_transaction_id,
            'context': context or {}
        }
        cache.set(key, state_data, timeout=ConversationManager.STATE_TTL)
        logger.info(f"Estado actualizado: {phone_number} → {state.value}")

    @staticmethod
    def reset(phone_number: str):
        """Vuelve al estado IDLE."""
        ConversationManager.set_state(phone_number, ConversationState.IDLE)
