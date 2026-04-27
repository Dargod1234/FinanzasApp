import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .meta_api import verify_webhook_signature
from .message_handler import handle_incoming_message
from .throttling import WhatsAppUserThrottle
from users.models import User

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == 'GET':
        return verify_webhook(request)
    elif request.method == 'POST':
        return receive_message(request)


def verify_webhook(request):
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')

    if mode == 'subscribe' and token == settings.META_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verificado correctamente")
        return HttpResponse(challenge, status=200)

    logger.warning(f"Verificación de webhook fallida: token={token}")
    return HttpResponse('Forbidden', status=403)


def receive_message(request):
    if not verify_webhook_signature(request):
        logger.warning("Firma de webhook inválida — posible spoofing")
        return HttpResponse('Invalid signature', status=403)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)

    try:
        entry = body.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        if not messages:
            # Notificación de estado (delivered, read), ignorar
            return HttpResponse('OK', status=200)

        message = messages[0]
        phone_number = message.get('from', '')
        message_id = message.get('id', '')
        message_type = message.get('type', '')

        # Rate limiting — verificar ANTES de cualquier procesamiento
        if not WhatsAppUserThrottle.is_allowed(phone_number):
            from .meta_api import send_text_message
            send_text_message(
                phone_number,
                "⏳ Has enviado muchos mensajes. Intenta de nuevo en unos minutos."
            )
            return HttpResponse('OK', status=200)

        # Crear usuario si no existe — el task Celery hace .get(), no get_or_create
        user, created = User.objects.get_or_create(
            phone_number=f"+{phone_number}",
            defaults={'username': f"+{phone_number}"}
        )

        if created:
            from .meta_api import send_text_message
            send_text_message(
                phone_number,
                "👋 ¡Hola! Soy tu asistente de Finanzas App.\n\n"
                "Envíame una foto de tu comprobante de pago (Nequi, Daviplata o Bancolombia) "
                "y yo registro el gasto automáticamente.\n\n"
                "También puedes preguntarme:\n"
                "• \"¿Cuánto he gastado este mes?\"\n"
                "• \"¿Cuál es mi ahorro?\"\n"
                "• \"Resumen\""
            )
            return HttpResponse('OK', status=200)

        if message_type == 'image':
            # ASYNC: despachar a Celery y retornar 200 OK inmediatamente a Meta
            from whatsapp.tasks import process_whatsapp_image
            process_whatsapp_image.delay(
                phone_number=phone_number,
                message_id=message_id,
                message_data_json=json.dumps(message),
            )
        else:
            # SÍNCRONO: texto y botones son < 1s, no necesitan async
            handle_incoming_message(
                user=user,
                phone_number=phone_number,
                message_id=message_id,
                message_type=message_type,
                message_data=message,
            )

    except (IndexError, KeyError) as e:
        logger.error(f"Error parseando webhook: {e}")

    # SIEMPRE responder 200 a Meta (si no, reenvía el mensaje)
    return HttpResponse('OK', status=200)
