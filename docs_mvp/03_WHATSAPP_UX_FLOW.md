# 03 — WHATSAPP UX FLOW (Integración Bot WhatsApp)

> **Proyecto:** Finanzas App  
> **Versión:** 1.0.0 (MVP)  
> **Última actualización:** 2026-04-07  
> **Referencia:** [00_SISTEMA_Y_RESILIENCIA.md](./00_SISTEMA_Y_RESILIENCIA.md) | [01_BACKEND_EVOLUTIVO.md](./01_BACKEND_EVOLUTIVO.md) | [02_IA_OCR_MAESTRO.md](./02_IA_OCR_MAESTRO.md)

---

## 1. Máquina de Estados de Conversación

### 1.1 Diagrama de Estados

```
                    ┌──────────┐
                    │          │
         ┌─────────►   IDLE   ◄──────────────────────┐
         │          │          │                       │
         │          └────┬─────┘                       │
         │               │                             │
         │    Usuario envía imagen                     │
         │    o mensaje de texto                       │
         │               │                             │
         │          ┌────▼──────┐                      │
         │          │           │                      │
         │          │PROCESSING │──── Error IA ────────┤
         │          │           │     (responder        │
         │          └────┬──────┘      y volver         │
         │               │             a IDLE)          │
         │    Extracción exitosa                        │
         │               │                             │
         │    ┌──────────▼───────────┐                 │
         │    │                      │                 │
         │    │ PENDING_CONFIRMATION │                 │
         │    │                      │                 │
         │    └──────┬──────┬───────┘                 │
         │           │      │                          │
         │     ✅ OK │      │ ❌ Incorrecto           │
         │           │      │                          │
         │     ┌─────▼──┐  ┌▼───────────┐             │
         │     │CONFIRMED│  │  REJECTED  │             │
         │     │(guardado)│  │(descartado)│             │
         │     └─────┬──┘  └─────┬──────┘             │
         │           │           │                     │
         └───────────┴───────────┴─────────────────────┘
                    (Vuelven a IDLE)

    ESTADO PARALELO (siempre activo):
    ┌──────────────┐
    │   QUERYING   │  ← Usuario pregunta por texto:
    │              │    "¿Cuánto he gastado?"
    │              │    → Responder con datos del dashboard
    └──────────────┘    → Volver a IDLE
```

### 1.2 Implementación de la Máquina de Estados

```python
# backend/whatsapp/state_machine.py

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
    Usa cache (Redis) para persistir estado entre requests.
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
```

---

## 2. Webhook de WhatsApp

### 2.1 Vista Principal del Webhook

```python
# backend/whatsapp/views.py

import json
import logging
import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .state_machine import ConversationManager, ConversationState
from .message_handler import handle_incoming_message
from .meta_api import verify_webhook_signature

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

    if mode == 'subscribe' and token == settings.META_VERIFY_TOKEN:
        logger.info("Webhook verificado correctamente")
        return HttpResponse(challenge, status=200)

    logger.warning(f"Verificación de webhook fallida: token={token}")
    return HttpResponse('Forbidden', status=403)


def receive_message(request):
    """
    Recibe y procesa mensajes entrantes de WhatsApp.
    Meta siempre espera 200 OK — el procesamiento real es asíncrono en MVP.
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
```

### 2.2 URLs del Webhook

```python
# backend/whatsapp/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.webhook, name='whatsapp-webhook'),
]
```

---

## 3. Handler de Mensajes

```python
# backend/whatsapp/message_handler.py

import logging
from django.conf import settings

from .state_machine import ConversationManager, ConversationState
from .meta_api import (
    send_text_message,
    send_interactive_buttons,
    download_media,
)
from core.services.ocr_pipeline import process_receipt_image
from users.models import User
from transactions.models import Transaction

logger = logging.getLogger(__name__)


def handle_incoming_message(phone_number: str, message_id: str,
                            message_type: str, message_data: dict):
    """
    Dispatcher principal. Enruta el mensaje según su tipo.
    """
    # Obtener o crear usuario
    user, created = User.objects.get_or_create(
        phone_number=f"+{phone_number}",
        defaults={'username': f"+{phone_number}"}
    )

    if created:
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
        return

    # Obtener estado actual de la conversación
    conv_state = ConversationManager.get_state(phone_number)
    current_state = conv_state['state']

    # ── Tipo: IMAGEN ──
    if message_type == 'image':
        handle_image_message(user, phone_number, message_id, message_data)

    # ── Tipo: RESPUESTA A BOTÓN INTERACTIVO ──
    elif message_type == 'interactive':
        handle_button_response(user, phone_number, message_data, conv_state)

    # ── Tipo: TEXTO ──
    elif message_type == 'text':
        text_body = message_data.get('text', {}).get('body', '').strip()
        handle_text_message(user, phone_number, text_body)

    # ── Tipo NO SOPORTADO ──
    else:
        handle_unsupported(phone_number, message_type)


def handle_image_message(user, phone_number, message_id, message_data):
    """Procesa una imagen de comprobante."""
    # Cambiar estado a PROCESSING
    ConversationManager.set_state(phone_number, ConversationState.PROCESSING)

    try:
        # Descargar imagen de Meta
        image_info = message_data.get('image', {})
        media_id = image_info.get('id')
        mime_type = image_info.get('mime_type', 'image/jpeg')

        image_bytes = download_media(media_id)
        if image_bytes is None:
            send_text_message(
                phone_number,
                "⚠️ No pude descargar la imagen. ¿Puedes enviarla de nuevo?"
            )
            ConversationManager.reset(phone_number)
            return

        # Procesar con pipeline OCR
        result = process_receipt_image(
            user=user,
            image_bytes=image_bytes,
            mime_type=mime_type,
            whatsapp_message_id=message_id,
        )

        # Manejar resultado
        if 'error' in result:
            error_messages = {
                'not_a_receipt': "🤔 Eso no parece un comprobante de pago.\n"
                                "Envíame la captura de pantalla de tu transferencia.",
                'low_quality': "📸 La imagen no es clara.\n"
                              "¿Puedes enviar otra foto del comprobante?",
                'service_unavailable': "⏳ El servicio de procesamiento no está disponible.\n"
                                      "Tu imagen será procesada cuando se restablezca.",
                'validation_failed': "⚠️ No pude extraer todos los datos necesarios.\n"
                                    "Intenta con una captura más completa del comprobante.",
            }
            msg = error_messages.get(result['error'],
                                     "❌ Hubo un error procesando tu comprobante. Intenta de nuevo.")
            send_text_message(phone_number, msg)
            ConversationManager.reset(phone_number)
            return

        if result['status'] == 'duplicate':
            send_text_message(phone_number, f"📋 {result['message']}")
            ConversationManager.reset(phone_number)
            return

        if result['status'] == 'created':
            transaction = result['transaction']
            # Enviar confirmación con botones
            send_confirmation_buttons(phone_number, transaction)
            ConversationManager.set_state(
                phone_number,
                ConversationState.PENDING_CONFIRMATION,
                pending_transaction_id=transaction.id
            )

    except Exception as e:
        logger.error(f"Error procesando imagen: {e}", exc_info=True)
        send_text_message(
            phone_number,
            "❌ Ocurrió un error inesperado. Intenta de nuevo en unos momentos."
        )
        ConversationManager.reset(phone_number)


def handle_button_response(user, phone_number, message_data, conv_state):
    """Procesa la respuesta a un botón interactivo."""
    interactive = message_data.get('interactive', {})
    button_reply = interactive.get('button_reply', {})
    button_id = button_reply.get('id', '')

    transaction_id = conv_state.get('pending_transaction_id')

    if not transaction_id:
        send_text_message(phone_number, "No hay una transacción pendiente de confirmar.")
        ConversationManager.reset(phone_number)
        return

    try:
        transaction = Transaction.objects.get(id=transaction_id, user=user)
    except Transaction.DoesNotExist:
        send_text_message(phone_number, "No encontré la transacción. Envía el comprobante de nuevo.")
        ConversationManager.reset(phone_number)
        return

    if button_id == 'confirm_yes':
        transaction.estado = 'confirmed'
        transaction.save(update_fields=['estado', 'updated_at'])
        monto = transaction.get_monto_decimal()
        send_text_message(
            phone_number,
            f"✅ ¡Registrado!\n\n"
            f"💰 ${monto:,.0f} COP\n"
            f"📁 {transaction.categoria.replace('_', ' ').title()}\n"
            f"🏦 {transaction.get_entidad_display()}\n\n"
            f"📊 Revisa tu dashboard en la app para ver tu progreso."
        )

    elif button_id == 'confirm_no':
        transaction.estado = 'rejected'
        transaction.save(update_fields=['estado', 'updated_at'])
        send_text_message(
            phone_number,
            "❌ Transacción descartada.\n"
            "Si quieres, envía otra foto del comprobante."
        )

    ConversationManager.reset(phone_number)


def handle_text_message(user, phone_number, text):
    """
    Procesa mensajes de texto.
    Detecta consultas rápidas sobre estado financiero.
    """
    text_lower = text.lower()

    # Detectar intención de consulta
    query_keywords = {
        'resumen': 'summary',
        'cuánto he gastado': 'gastos',
        'cuanto he gastado': 'gastos',
        'mi gasto': 'gastos',
        'mis gastos': 'gastos',
        'ahorro': 'ahorro',
        'mi ahorro': 'ahorro',
        'presupuesto': 'presupuesto',
        'ayuda': 'help',
        'help': 'help',
        'hola': 'greeting',
    }

    intent = None
    for keyword, intent_type in query_keywords.items():
        if keyword in text_lower:
            intent = intent_type
            break

    if intent == 'help' or intent == 'greeting':
        send_text_message(
            phone_number,
            "👋 ¡Hola! Puedo ayudarte con:\n\n"
            "📸 *Envía una foto* de un comprobante para registrar un gasto\n"
            "💬 *Pregúntame:*\n"
            "  • \"Resumen\" — ver tu resumen financiero\n"
            "  • \"¿Cuánto he gastado?\" — total de gastos del mes\n"
            "  • \"Mi ahorro\" — cuánto has ahorrado\n"
        )
        return

    if intent in ['summary', 'gastos', 'ahorro', 'presupuesto']:
        send_financial_summary(user, phone_number, intent)
        return

    # Si no se detectó intención, asumir que quiere ayuda
    send_text_message(
        phone_number,
        "🤔 No entendí tu mensaje.\n\n"
        "Puedes:\n"
        "📸 Enviar una *foto de un comprobante*\n"
        "💬 Escribir *\"Resumen\"* para ver tu estado financiero\n"
        "❓ Escribir *\"Ayuda\"* para ver todas las opciones"
    )


def handle_unsupported(phone_number, message_type):
    """Responde a tipos de mensaje no soportados."""
    unsupported_messages = {
        'document': "📄 No puedo procesar documentos.\n"
                    "Envíame una *imagen* (foto o captura de pantalla) del comprobante.",
        'video': "🎥 No puedo procesar videos.\n"
                "Envíame una *imagen* del comprobante.",
        'audio': "🎤 No proceso mensajes de voz.\n"
                "Envíame una *foto* del comprobante o escríbeme tu consulta.",
        'sticker': "No proceso stickers 😄\n"
                  "Envíame una *foto* de tu comprobante.",
        'location': "📍 No necesito tu ubicación.\n"
                   "Envíame una *foto* de tu comprobante.",
    }
    msg = unsupported_messages.get(
        message_type,
        "No puedo procesar ese tipo de mensaje.\n"
        "Envíame una *imagen* de tu comprobante o escríbeme una consulta."
    )
    send_text_message(phone_number, msg)


def send_confirmation_buttons(phone_number: str, transaction):
    """Envía mensaje interactivo con botones de confirmación."""
    monto = transaction.get_monto_decimal()
    body_text = (
        f"📋 *Comprobante procesado:*\n\n"
        f"💰 Monto: *${monto:,.0f} COP*\n"
        f"🏦 Entidad: {transaction.get_entidad_display()}\n"
        f"📁 Categoría: {transaction.categoria.replace('_', ' ').title()}\n"
        f"👤 Destinatario: {transaction.destinatario or 'N/A'}\n"
        f"🔢 Ref: {transaction.referencia_bancaria}\n\n"
        f"¿Los datos son correctos?"
    )

    send_interactive_buttons(
        phone_number=phone_number,
        body=body_text,
        buttons=[
            {"id": "confirm_yes", "title": "✅ Correcto"},
            {"id": "confirm_no", "title": "❌ Incorrecto"},
        ]
    )


def send_financial_summary(user, phone_number, intent):
    """Envía resumen financiero por WhatsApp."""
    from decimal import Decimal
    from django.utils import timezone

    profile = user.profile
    now = timezone.now()

    # Calcular inicio del ciclo
    dia_corte = profile.dia_corte
    if now.day >= dia_corte:
        cycle_start = now.replace(day=dia_corte, hour=0, minute=0, second=0, microsecond=0)
    else:
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        cycle_start = now.replace(year=prev_year, month=prev_month, day=dia_corte,
                                  hour=0, minute=0, second=0, microsecond=0)

    transactions = Transaction.objects.filter(
        user=user,
        estado='confirmed',
        fecha_transaccion__gte=cycle_start,
    )

    total_gastos = Decimal('0')
    total_ingresos = Decimal('0')
    for t in transactions:
        monto = t.get_monto_decimal()
        if t.tipo == 'gasto':
            total_gastos += monto
        elif t.tipo == 'ingreso':
            total_ingresos += monto

    salario = profile.get_salario_decimal()
    presupuesto = profile.get_presupuesto_decimal()
    ahorro = salario - total_gastos + total_ingresos

    if not profile.onboarding_completed:
        send_text_message(
            phone_number,
            "⚙️ Aún no has configurado tu salario y presupuesto.\n"
            "Descarga la app y completa el onboarding para ver tu resumen completo."
        )
        return

    progreso = (total_gastos / presupuesto * 100) if presupuesto > 0 else 0
    barra = "🟩" * int(progreso / 10) + "⬜" * (10 - int(progreso / 10))

    msg = (
        f"📊 *Resumen Financiero*\n"
        f"📅 Ciclo: {cycle_start.strftime('%d/%m')} - {now.strftime('%d/%m/%Y')}\n\n"
        f"💵 Salario: ${salario:,.0f}\n"
        f"📉 Gastos: ${total_gastos:,.0f}\n"
        f"📈 Ingresos: ${total_ingresos:,.0f}\n"
        f"💰 *Ahorro: ${ahorro:,.0f}*\n\n"
        f"🎯 Presupuesto: ${presupuesto:,.0f}\n"
        f"{barra} {progreso:.0f}%\n\n"
        f"📱 Abre la app para ver el detalle completo."
    )
    send_text_message(phone_number, msg)
```

---

## 4. API de Meta (Envío de Mensajes)

```python
# backend/whatsapp/meta_api.py

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

    # Paso 2: Descargar imagen
    try:
        download_response = requests.get(
            media_url,
            headers=headers,
            timeout=30
        )
        if download_response.status_code == 200:
            return download_response.content
        else:
            logger.error(f"Error descargando media: {download_response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"Error descargando imagen: {e}")
        return None
```

---

## 5. Interactive Messages — Referencia de Meta API

### 5.1 Botones de Respuesta (Reply Buttons)

```json
// Estructura que Meta espera para botones
{
  "messaging_product": "whatsapp",
  "to": "573001234567",
  "type": "interactive",
  "interactive": {
    "type": "button",
    "header": {
      "type": "text",
      "text": "Comprobante Procesado"
    },
    "body": {
      "text": "💰 Monto: $150,000 COP\n🏦 Nequi\n📁 Alimentación\n\n¿Es correcto?"
    },
    "footer": {
      "text": "Finanzas App"
    },
    "action": {
      "buttons": [
        {
          "type": "reply",
          "reply": {
            "id": "confirm_yes",
            "title": "✅ Correcto"
          }
        },
        {
          "type": "reply",
          "reply": {
            "id": "confirm_no",
            "title": "❌ Incorrecto"
          }
        }
      ]
    }
  }
}
```

### 5.2 Restricciones de Meta API

| Restricción                        | Límite                    |
|------------------------------------|---------------------------|
| Botones por mensaje                | Máximo 3                  |
| Caracteres en título de botón      | Máximo 20                 |
| Caracteres en body                 | Máximo 1024               |
| Caracteres en header               | Máximo 60                 |
| Caracteres en footer               | Máximo 60                 |
| Mensajes por segundo (throttle)    | 80 msg/s (Business tier)  |
| Ventana de conversación            | 24 horas desde último msg del usuario |

### 5.3 Regla de 24 Horas

Meta requiere que el usuario inicie la conversación. El bot solo puede responder dentro de una **ventana de 24 horas** desde el último mensaje del usuario. Para iniciar conversación fuera de esta ventana, se necesitan **Templates de Mensaje** pre-aprobados.

```python
# Para MVP: solo respondemos a mensajes del usuario (reactivo)
# Para V2: configurar templates para notificaciones proactivas:
#   - "Tu resumen semanal está listo 📊"
#   - "Llevas el 80% de tu presupuesto 🎯"
```

---

## 6. Fallbacks y Manejo de Errores de Conversación

### 6.1 Tabla de Fallbacks

| Escenario                              | Respuesta del Bot                                        |
|----------------------------------------|----------------------------------------------------------|
| Usuario envía PDF                      | "📄 No puedo procesar documentos. Envíame una *imagen*." |
| Usuario envía audio/video              | "🎤 Solo proceso imágenes. Envía una *foto* del comprobante." |
| Usuario envía sticker                  | "Envíame una *foto* de tu comprobante 😄"                |
| Usuario envía ubicación                | "📍 No necesito ubicación. Envía una *foto* del comprobante." |
| Gemini API caída                       | "⏳ El servicio no está disponible. Intenta en unos minutos." |
| Imagen no es comprobante               | "🤔 Eso no parece un comprobante bancario."              |
| Comprobante duplicado                  | "📋 Este comprobante ya fue registrado el [fecha]."      |
| Texto no reconocido                    | "🤔 No entendí. Escribe *Ayuda* para ver las opciones."  |
| Error inesperado del servidor          | "❌ Ocurrió un error. Intenta de nuevo."                  |
| Botón respondido sin transacción activa| "No hay transacción pendiente. Envía un nuevo comprobante."|

### 6.2 Rate Limiting por Usuario

```python
# backend/whatsapp/throttling.py

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
```

---

## 7. Ejemplo Completo: Flujo Conversacional

```
USUARIO: [Envía imagen de comprobante Nequi]

BOT (procesando...):

BOT: 📋 *Comprobante procesado:*

     💰 Monto: *$85,000 COP*
     🏦 Entidad: Nequi
     📁 Categoría: Alimentación
     👤 Destinatario: Rappi Colombia
     🔢 Ref: NQ9876543210

     ¿Los datos son correctos?

     [✅ Correcto]  [❌ Incorrecto]

USUARIO: [Presiona ✅ Correcto]

BOT: ✅ ¡Registrado!

     💰 $85,000 COP
     📁 Alimentación
     🏦 Nequi 

     📊 Revisa tu dashboard en la app para ver tu progreso.

--- (más tarde) ---

USUARIO: ¿Cuánto he gastado este mes?

BOT: 📊 *Resumen Financiero*
     📅 Ciclo: 01/04 - 07/04/2026

     💵 Salario: $4,500,000
     📉 Gastos: $1,235,000
     📈 Ingresos: $0
     💰 *Ahorro: $3,265,000*

     🎯 Presupuesto: $3,000,000
     🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 41%

     📱 Abre la app para ver el detalle completo.
```

---

## 8. Configuración de Webhook en Meta Dashboard

```markdown
### Pasos para configurar el Webhook:

1. Ir a https://developers.facebook.com → Tu App → WhatsApp → Configuration
2. En "Webhook":
   - Callback URL: https://api.finanzasapp.co/api/whatsapp/webhook/
   - Verify Token: (usar el valor de META_VERIFY_TOKEN de .env)
   - Suscribir al campo: `messages`
3. En "Phone Numbers":
   - Registrar el número de WhatsApp Business
   - Generar un Access Token permanente (System User Token recomendado)
4. Probar con la herramienta "Test" del dashboard de Meta

### Ngrok para desarrollo local:
ngrok http 8000
# Usar la URL de ngrok como Callback URL temporalmente
```

---

*Este documento sigue la [Regla de Oro](./00_SISTEMA_Y_RESILIENCIA.md#61-regla-de-oro). Cambios en el flujo conversacional deben documentarse aquí y en el log de decisiones.*
