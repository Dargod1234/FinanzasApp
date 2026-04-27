import logging
from decimal import Decimal
from django.utils import timezone

from .state_machine import ConversationManager, ConversationState
from .meta_api import (
    send_text_message,
    send_interactive_buttons,
    send_template_confirmation,
    download_media,
)
from core.services.ocr_pipeline import process_receipt_image
from users.models import User
from transactions.models import Transaction

logger = logging.getLogger(__name__)

# ── Categorización desde texto del usuario ───────────────────────────────────

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "alimentacion": [
        "comida", "almuerzo", "desayuno", "cena", "restaurante", "mercado",
        "supermercado", "domicilio", "rappi", "ifood", "snack", "café", "cafe",
        "panaderia", "fruteria", "carniceria", "picada",
    ],
    "transporte": [
        "taxi", "uber", "bus", "metro", "transporte", "gasolina", "combustible",
        "parqueadero", "parking", "indriver", "cabify", "peaje", "pasaje",
        "moto", "bicicleta", "tren",
    ],
    "salud": [
        "salud", "medico", "médico", "farmacia", "drogueria", "medicina",
        "consulta", "eps", "clinica", "clínica", "hospital", "laboratorio",
        "dentista", "optometria", "psicólogo", "psicologo",
    ],
    "educacion": [
        "educacion", "educación", "colegio", "universidad", "curso", "libro",
        "matricula", "matrícula", "taller", "seminario", "clase", "tutor",
        "capacitacion", "capacitación",
    ],
    "entretenimiento": [
        "entretenimiento", "cine", "juego", "netflix", "spotify", "disney",
        "musica", "música", "concierto", "deporte", "gimnasio", "gym",
        "streaming", "suscripcion", "suscripción", "videojuego", "fiesta",
        "bar", "discoteca",
    ],
    "servicios": [
        "servicios", "agua", "luz", "gas", "internet", "celular", "telefono",
        "teléfono", "wifi", "recarga", "arriendo", "alquiler", "vivienda",
        "administracion", "administración", "seguros", "seguro",
    ],
    "ropa": [
        "ropa", "zapatos", "zapato", "vestido", "camisa", "pantalon",
        "pantalón", "calzado", "accesorio", "bolso", "shopping",
    ],
    "ahorro": [
        "ahorro", "ahorros", "inversion", "inversión", "fondo", "cdp",
        "depósito", "deposito",
    ],
}


def _infer_category_from_text(text: str) -> str:
    """
    Infiere una categoría a partir del texto libre enviado por el usuario
    junto al comprobante. Retorna el nombre de la categoría o '' si no hay match.
    """
    if not text:
        return ""
    lowered = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                return category
    return ""


def handle_incoming_message(user, phone_number: str, message_id: str,
                            message_type: str, message_data: dict):
    """
    Dispatcher principal. Enruta el mensaje según su tipo.
    El throttle y la creación de usuario se hacen en views.py antes de llamar aquí.
    """
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
        # Caption opcional que el usuario envía junto a la imagen
        caption = image_info.get('caption', '') or ''

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

            # Aplicar categoría desde el caption del usuario si hay coincidencia
            inferred_cat = _infer_category_from_text(caption)
            if inferred_cat and transaction.categoria == 'sin_categorizar':
                transaction.categoria = inferred_cat
                transaction.save(update_fields=['categoria'])
                logger.info("Categoría '%s' inferida del caption para tx=%s", inferred_cat, transaction.id)

            # CAMBIO: Usamos plantilla Utility en lugar de botones manuales
            # Esto optimiza costos y profesionaliza el flujo (Abril 2026)
            exito = send_template_confirmation(phone_number, transaction)
            
            if exito:
                ConversationManager.set_state(
                    phone_number,
                    ConversationState.PENDING_CONFIRMATION,
                    pending_transaction_id=transaction.id
                )
            else:
                # Fallback a botones interactivos si la plantilla falla (ej: no aprobada aún)
                send_text_message(phone_number, "✅ ¡Listo! He extraído los datos.")
                # Aquí podrías llamar a una función de botones si la tienes
                # Por ahora reseteamos si falla el envío crítico
                ConversationManager.reset(phone_number)

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
