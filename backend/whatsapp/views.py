import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .meta_api import verify_webhook_signature
from .message_handler import handle_incoming_message

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    """
    Endpoint del webhook de WhatsApp.
    GET: Verificación inicial de Meta.
    POST: Mensajes entrantes.
    """
    if request.method == 'GET':
        return verify_webhook(request)
    elif request.method == 'POST':
        return receive_message(request)


def verify_webhook(request):
    """
    Meta envía un GET con hub.challenge para verificar el webhook.
    Debemos responder con el challenge si el token coincide.
    """
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')

    if mode == 'subscribe' and token == settings.META_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verificado correctamente")
        return HttpResponse(challenge, status=200)

    logger.warning(f"Verificación de webhook fallida: token={token}")
    return HttpResponse('Forbidden', status=403)


def receive_message(request):
    """
    Recibe y procesa mensajes entrantes de WhatsApp.
    Meta siempre espera 200 OK — el procesamiento real es síncrono en MVP.
    """
    # Verificar firma HMAC
    if not verify_webhook_signature(request):
        logger.warning("Firma de webhook inválida — posible spoofing")
        return HttpResponse('Invalid signature', status=403)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)

    # Extraer datos del mensaje
    try:
        entry = body.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        if not messages:
            # Es una notificación de estado (delivered, read), ignorar
            return HttpResponse('OK', status=200)

        message = messages[0]
        phone_number = message.get('from', '')
        message_id = message.get('id', '')
        message_type = message.get('type', '')

        # Procesar el mensaje según su tipo
        handle_incoming_message(
            phone_number=phone_number,
            message_id=message_id,
            message_type=message_type,
            message_data=message,
        )

    except (IndexError, KeyError) as e:
        logger.error(f"Error parseando webhook: {e}")

    # SIEMPRE responder 200 a Meta (si no, reenvía el mensaje)
    return HttpResponse('OK', status=200)
