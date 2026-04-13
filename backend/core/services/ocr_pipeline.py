import logging
from .gemini_service import get_gemini_service
from .ocr_validator import validate_ocr_response
from .category_engine import infer_category
from .transaction_classifier import classify_transaction_type
from transactions.services import TransactionService

logger = logging.getLogger(__name__)


def process_receipt_image(
    user,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    whatsapp_message_id: str = None
) -> dict:
    """
    Pipeline completo:
    1. Enviar imagen a Gemini → obtener JSON
    2. Validar y normalizar respuesta
    3. Clasificar tipo de transacción
    4. Inferir categoría
    5. Verificar duplicados
    6. Crear Transaction en DB

    Returns:
        dict con 'status' y datos relevantes
    """
    # Paso 1: Gemini OCR
    logger.info(f"Procesando imagen para user={user.id}, mime={mime_type}")
    gemini = get_gemini_service()
    raw_result = gemini.extract_from_image(image_bytes, mime_type)

    # Paso 2: Validar
    validated = validate_ocr_response(raw_result)
    if 'error' in validated:
        logger.warning(f"OCR error: {validated['error']} — {validated.get('message')}")
        return validated

    # Paso 3: Clasificar tipo
    validated['tipo'] = classify_transaction_type(
        validated,
        user_name=user.get_full_name() or None
    )

    # Paso 4: Categorizar
    if not validated.get('categoria') or validated['categoria'] == 'sin_categorizar':
        validated['categoria'] = infer_category(
            validated.get('destinatario', ''),
            validated.get('descripcion', '')
        )

    # Paso 5 y 6: Dedup + Crear
    result = TransactionService.create_from_ocr(
        user=user,
        ocr_data=validated,
        whatsapp_message_id=whatsapp_message_id
    )

    logger.info(f"Pipeline resultado: {result['status']} para user={user.id}")
    return result
