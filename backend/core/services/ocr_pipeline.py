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
    """
    logger.info(f"Procesando imagen para user={user.id}, mime={mime_type}")
    
    # Paso 1: OCR local
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

    # Validación visual básica
    if not _looks_like_receipt(ocr_text):
        logger.info("OCR devolvio texto sin patron de comprobante para user=%s", user.id)
        return {
            "error": "not_a_receipt",
            "message": "La imagen no parece un comprobante bancario.",
        }

    # Paso 2: Extracción de campos
    raw_result = _extract_receipt_fields(ocr_text)

    # Paso 3: Validar y normalizar (Maneja montos y fechas)
    validated = validate_ocr_response(raw_result)
    if 'error' in validated:
        logger.warning(f"OCR error: {validated['error']} — {validated.get('message')}")
        return validated

    # Paso 4: Clasificar tipo (Ingreso/Gasto)
    validated['tipo'] = classify_transaction_type(
        validated,
        user_name=user.get_full_name() or None
    )

    # Paso 5: Categorizar automáticamente
    if not validated.get('categoria') or validated['categoria'] == 'sin_categorizar':
        validated['categoria'] = infer_category(
            validated.get('destinatario', ''),
            validated.get('descripcion', '')
        )

    # Paso 6 e 7: Dedup y Persistencia
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
        "comprobante", "transaccion", "referencia", "nequi", 
        "daviplata", "bancolombia", "pago", "transferencia", "exitoso"
    ]
    marker_match = any(marker in lowered for marker in markers)
    has_numeric_signal = bool(re.search(r"\d{4,}", ocr_text))
    return marker_match and has_numeric_signal


def _extract_receipt_fields(ocr_text: str) -> dict:
    lowered = ocr_text.lower()

    # Identificación de banco mejorada para PaddleOCR
    if any(x in lowered for x in ["nequi", "movimiento exitoso", "¡listo!"]):
        entidad = "nequi"
    elif any(x in lowered for x in ["daviplata", "transacción exitosa", "aprobación"]):
        entidad = "daviplata"
    elif any(x in lowered for x in ["bancolombia", "transferencia procesada", "valor enviado"]):
        entidad = "bancolombia"
    else:
        entidad = "otro"

    return {
        "monto": _extract_amount(ocr_text),
        "referencia_bancaria": _extract_reference(ocr_text),
        "fecha_transaccion": _extract_date(ocr_text),
        "entidad": entidad,
        "tipo": "gasto",
        "destinatario": _extract_labeled_value(ocr_text, ["destinatario", "para", "recibe", "a:"]),
        "emisor": _extract_labeled_value(ocr_text, ["emisor", "de", "origen", "desde:"]),
        "descripcion": _extract_labeled_value(ocr_text, ["concepto", "descripcion", "detalle", "mensaje"]),
        "confianza": 0.65,
        "raw_response": ocr_text,
    }


def _extract_amount(ocr_text: str):
    # Regex robusto para montos colombianos (ej: 50.000 o $ 1.200.000,00)
    pattern = r"(?im)(?:monto|valor|total|pagado|importe|cantidad|pago)\s*[:$\-\s]*\s*([0-9]{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)"
    labeled = re.search(pattern, ocr_text)
    
    if labeled:
        return _to_numeric_string(labeled.group(1))

    # Búsqueda secundaria de candidatos numéricos grandes
    candidates = re.findall(r"\$?\s*([0-9]{1,3}(?:\.\d{3})+)", ocr_text)
    if not candidates:
        return None
        
    normalized = [_to_numeric_string(c) for c in candidates]
    return max(normalized, key=lambda v: int(v) if v else 0)


def _extract_reference(ocr_text: str) -> str:
    # Captura referencias alfanuméricas de 6 a 15 caracteres
    match = re.search(
        r"(?im)(?:referencia|id|comprobante|aprobaci[oó]n|nro|n[uú]mero)\s*[:#\-\s]*\s*([a-z0-9]{6,15})",
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
        # Busca la etiqueta y captura hasta el final de la línea
        pattern = rf"(?im){label}\s*[:\-]\s*(.+)$"
        match = re.search(pattern, ocr_text)
        if match:
            return match.group(1).strip()
    return ""


def _to_numeric_string(raw_value: str):
    # Limpia todo lo que no sea número para dejar solo la cifra
    digits = re.sub(r"[^0-9]", "", raw_value)
    return digits if digits else None