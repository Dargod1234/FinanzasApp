import logging
import re

from .ocr_local import OCRLocalService
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
    1. Enviar imagen a OCR local → obtener texto plano
    2. Extraer campos por heuristica/regex
    3. Validar y normalizar respuesta
    4. Clasificar tipo de transacción
    5. Inferir categoría
    6. Verificar duplicados
    7. Crear Transaction en DB

    Returns:
        dict con 'status' y datos relevantes
    """
    # Paso 1: OCR local
    logger.info(f"Procesando imagen para user={user.id}, mime={mime_type}")
    ocr_text = OCRLocalService.extract_text(image_bytes, mime_type)
    if ocr_text is None:
        return {
            "error": "service_unavailable",
            "message": "Servicio OCR no disponible o sin respuesta valida.",
        }
    if not ocr_text.strip():
        return {
            "error": "low_quality",
            "message": "No se pudo extraer texto legible del comprobante.",
        }

    if not _looks_like_receipt(ocr_text):
        logger.info("OCR devolvio texto sin patron de comprobante para user=%s", user.id)
        return {
            "error": "not_a_receipt",
            "message": "La imagen no parece un comprobante bancario.",
        }

    raw_result = _extract_receipt_fields(ocr_text)

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


def _looks_like_receipt(ocr_text: str) -> bool:
    lowered = ocr_text.lower()
    markers = [
        "comprobante",
        "transaccion",
        "referencia",
        "nequi",
        "daviplata",
        "bancolombia",
        "pago",
        "transferencia",
    ]
    marker_match = any(marker in lowered for marker in markers)
    has_numeric_signal = bool(re.search(r"\d{4,}", ocr_text))
    return marker_match and has_numeric_signal


def _extract_receipt_fields(ocr_text: str) -> dict:
    lowered = ocr_text.lower()

    entidad = "otro"
    if "nequi" in lowered:
        entidad = "nequi"
    elif "daviplata" in lowered:
        entidad = "daviplata"
    elif "bancolombia" in lowered:
        entidad = "bancolombia"

    monto = _extract_amount(ocr_text)
    referencia = _extract_reference(ocr_text)
    fecha = _extract_date(ocr_text)
    destinatario = _extract_labeled_value(ocr_text, ["destinatario", "para", "recibe"]) or ""
    emisor = _extract_labeled_value(ocr_text, ["emisor", "de", "origen", "envia"]) or ""
    descripcion = _extract_labeled_value(ocr_text, ["concepto", "descripcion", "detalle"]) or ""

    return {
        "monto": monto,
        "referencia_bancaria": referencia,
        "fecha_transaccion": fecha,
        "entidad": entidad,
        "tipo": "gasto",
        "destinatario": destinatario,
        "emisor": emisor,
        "descripcion": descripcion,
        "confianza": 0.55,
        "raw_response": ocr_text,
    }


def _extract_amount(ocr_text: str):
    labeled = re.search(
        r"(?im)(?:monto|valor|total|pagado|importe)\s*[:$-]?\s*([0-9][0-9\s\.,]{2,})",
        ocr_text,
    )
    if labeled:
        return _to_numeric_string(labeled.group(1))

    candidates = re.findall(r"\$?\s*([0-9][0-9\.,]{3,})", ocr_text)
    if not candidates:
        return None
    normalized = [_to_numeric_string(candidate) for candidate in candidates]
    normalized = [value for value in normalized if value]
    if not normalized:
        return None
    return max(normalized, key=lambda value: int(value))


def _extract_reference(ocr_text: str) -> str:
    match = re.search(
        r"(?im)(?:referencia|id(?:\s+de)?\s+transaccion|n(?:ro|umero)?\s*comprobante|aprobacion)\s*[:#-]?\s*([a-z0-9-]{4,})",
        ocr_text,
    )
    if match:
        return match.group(1).strip().upper()
    return ""


def _extract_date(ocr_text: str) -> str:
    patterns = [
        r"(?i)\b(\d{4}-\d{2}-\d{2}[ t]\d{2}:\d{2}(?::\d{2})?)\b",
        r"(?i)\b(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\b",
        r"(?i)\b(\d{2}/\d{2}/\d{4})\b",
        r"(?i)\b(\d{4}-\d{2}-\d{2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, ocr_text)
        if match:
            return match.group(1)
    return ""


def _extract_labeled_value(ocr_text: str, labels) -> str:
    for label in labels:
        pattern = rf"(?im){label}\s*[:\-]\s*(.+)$"
        match = re.search(pattern, ocr_text)
        if match:
            return match.group(1).strip()
    return ""


def _to_numeric_string(raw_value: str):
    digits = re.sub(r"[^0-9]", "", raw_value)
    return digits if digits else None
