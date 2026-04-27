import json
import logging

from celery import shared_task
from django.core.cache import cache

from users.models import User

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL = 3600  # 1 hora


@shared_task(bind=True, max_retries=1, default_retry_delay=15)
def process_whatsapp_image(self, phone_number: str, message_id: str, message_data_json: str):
    """
    Task Celery para procesar imágenes de comprobantes de WhatsApp.
    Desacoplado del webhook para responder 200 OK a Meta inmediatamente.
    """
    idempotency_key = f"wa_processing:{message_id}"
    if cache.get(idempotency_key):
        logger.info("Task duplicado detectado para message_id=%s, ignorando.", message_id)
        return {"status": "duplicate_task", "message_id": message_id}

    cache.set(idempotency_key, True, timeout=IDEMPOTENCY_TTL)

    try:
        message_data = json.loads(message_data_json)

        user = User.objects.get(phone_number=f"+{phone_number}")

        from whatsapp.message_handler import handle_image_message
        handle_image_message(user, phone_number, message_id, message_data)

    except User.DoesNotExist:
        logger.error("Usuario no encontrado para phone_number=%s", phone_number)
    except Exception as exc:
        logger.error("Error en process_whatsapp_image: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
