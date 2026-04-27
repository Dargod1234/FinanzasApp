import hashlib
import hmac
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com/v20.0"


def verify_webhook_signature(request) -> bool:
    """Verifica la firma HMAC-SHA256 del webhook de Meta."""
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not signature.startswith('sha256='):
        return False
    expected_sig = hmac.new(
        settings.META_APP_SECRET.encode('utf-8'),
        request.body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature[7:], expected_sig)


def _send_message(phone_number: str, payload: dict) -> bool:
    """Envía un mensaje vía Meta Cloud API."""
    url = f"{META_API_BASE}/{settings.META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        **payload,
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info(f"Meta API OK — respuesta: {response.text}")
            return True
        else:
            logger.error(f"Error enviando mensaje: {response.status_code} — {response.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"Error de conexión con Meta API: {e}")
        return False


def send_text_message(phone_number: str, text: str) -> bool:
    """Envía un mensaje de texto simple."""
    return _send_message(phone_number, {
        "type": "text",
        "text": {"body": text}
    })


def send_template_confirmation(phone_number: str, transaction) -> bool:
    """
    Envía una plantilla de utilidad (Utility) para confirmar la transacción.
    """
    # Formateo exacto para que coincida con las muestras de Meta
    monto_formateado = f"{transaction.get_monto_decimal():,.0f}"
    entidad = str(transaction.entidad).upper()
    categoria = str(transaction.categoria).replace('_', ' ').title()

    payload = {
        "type": "template",
        "template": {
            "name": "confirmacion_gasto",
            "language": {"code": "es"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": monto_formateado},
                        {"type": "text", "text": entidad},
                        {"type": "text", "text": categoria},
                    ]
                }
            ]
        }
    }
    return _send_message(phone_number, payload)


def send_interactive_buttons(phone_number: str, body: str,
                              buttons: list, header: str = None) -> bool:
    """
    Envía un mensaje interactivo con botones.
    Máximo 3 botones por mensaje (limitación de Meta).

    buttons = [
        {"id": "confirm_yes", "title": "✅ Correcto"},
        {"id": "confirm_no", "title": "❌ Incorrecto"},
    ]
    """
    interactive = {
        "type": "button",
        "body": {"text": body},
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {"id": btn["id"], "title": btn["title"][:20]}  # Max 20 chars
                }
                for btn in buttons[:3]  # Max 3 botones
            ]
        }
    }

    if header:
        interactive["header"] = {"type": "text", "text": header}

    return _send_message(phone_number, {
        "type": "interactive",
        "interactive": interactive
    })


def download_media(media_id: str) -> bytes | None:
    """
    Descarga una imagen de WhatsApp.
    Paso 1: Obtener URL del media.
    Paso 2: Descargar el archivo.
    Con retry y backoff exponencial (3 intentos: 2s/4s/8s).
    """
    headers = {"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"}

    # Paso 1: Obtener URL
    try:
        url_response = requests.get(
            f"{META_API_BASE}/{media_id}",
            headers=headers,
            timeout=10
        )
        if url_response.status_code != 200:
            logger.error(f"Error obteniendo URL de media: {url_response.text}")
            return None

        media_url = url_response.json().get('url')
        if not media_url:
            return None
    except requests.RequestException as e:
        logger.error(f"Error conectando a Meta para URL de media: {e}")
        return None

    # Paso 2: Descargar imagen con retry
    import time
    for attempt, delay in enumerate([2, 4, 8]):
        try:
            download_response = requests.get(
                media_url,
                headers=headers,
                timeout=30
            )
            if download_response.status_code == 200:
                return download_response.content
            else:
                logger.warning(
                    f"Intento {attempt + 1}/3 descargando media: {download_response.status_code}"
                )
        except requests.RequestException as e:
            logger.warning(f"Intento {attempt + 1}/3 error descargando imagen: {e}")

        if attempt < 2:
            time.sleep(delay)

    logger.error(f"Falló descarga de media {media_id} tras 3 intentos")
    return None
