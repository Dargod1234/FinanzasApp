import hashlib
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
        "daviplata", "bancolombia", "davivienda", "banco de bogota",
        "bbva", "avvillas", "pse", "pago", "transferencia", "exitoso",
        "aprobado", "aprobacion", "recibo", "voucher",
    ]
    marker_match = any(marker in lowered for marker in markers)
    has_numeric_signal = bool(re.search(r"\d{4,}", ocr_text))
    return marker_match and has_numeric_signal


def _extract_receipt_fields(ocr_text: str) -> dict:
    lowered = ocr_text.lower()

    # Identificación de entidad con patrones específicos y más robustos
    if any(x in lowered for x in ["nequi", "movimiento exitoso", "¡listo!", "listo!"]):
        entidad = "nequi"
    elif any(x in lowered for x in ["daviplata", "aprobacion", "aprobación"]):
        entidad = "daviplata"
    elif any(x in lowered for x in ["bancolombia", "transferencia procesada", "valor enviado", "sucursal virtual"]):
        entidad = "bancolombia"
    else:
        entidad = "otro"

    monto_raw, monto_source = _extract_amount_with_source(ocr_text, entidad)
    referencia = _extract_reference(ocr_text, entidad)
    fecha = _extract_date(ocr_text)
    destinatario = _extract_labeled_value(ocr_text, ["destinatario", "para", "recibe", "a:"])
    emisor = _extract_labeled_value(ocr_text, ["emisor", "de", "origen", "desde:"])
    descripcion = _extract_labeled_value(ocr_text, ["concepto", "descripcion", "descripción", "detalle", "mensaje"])

    confianza = _calculate_confidence(
        entidad=entidad,
        monto_raw=monto_raw,
        monto_source=monto_source,
        referencia=referencia,
        fecha=fecha,
        destinatario=destinatario,
    )

    return {
        "monto": monto_raw,
        "referencia_bancaria": referencia,
        "fecha_transaccion": fecha,
        "entidad": entidad,
        "tipo": "gasto",
        "destinatario": destinatario,
        "emisor": emisor,
        "descripcion": descripcion,
        "confianza": confianza,
        "raw_response": ocr_text,
    }


# ── Confianza real ──────────────────────────────────────────────────────────

def _calculate_confidence(
    entidad: str,
    monto_raw,
    monto_source: str,
    referencia: str,
    fecha: str,
    destinatario: str,
) -> float:
    """
    Calcula un score de confianza real basado en la calidad de los campos extraídos.

    Componentes del score (máx 1.0):
    - 0.35  Monto extraído con patrón primario (labeled)
    - 0.20  Monto extraído con fallback numérico
    - 0.20  Entidad identificada específicamente (no 'otro')
    - 0.20  Referencia bancaria encontrada
    - 0.15  Fecha encontrada
    - 0.10  Destinatario encontrado
    """
    score = 0.0

    # Monto: el campo más crítico
    if monto_raw:
        if monto_source == "labeled":
            score += 0.35
        else:
            score += 0.20

    # Entidad identificada
    if entidad != "otro":
        score += 0.20

    # Referencia bancaria
    if referencia:
        score += 0.20

    # Fecha
    if fecha:
        score += 0.15

    # Destinatario
    if destinatario:
        score += 0.10

    return round(min(max(score, 0.0), 1.0), 4)


# ── Monto ───────────────────────────────────────────────────────────────────

def _extract_amount_with_source(ocr_text: str, entidad: str) -> tuple:
    """
    Retorna (monto_string, source) donde source es 'labeled' o 'fallback'.
    """
    # Patrones específicos por entidad primero
    entity_patterns = {
        "nequi": r"(?im)(?:enviaste?|recibiste?|valor|monto)\s*[:$\-\s]*\s*([0-9]{1,3}(?:[\.,]\d{3})*(?:[,\.]\d{1,2})?)",
        "daviplata": r"(?im)(?:monto|valor|total)\s*[:\$\-\s]*\s*([0-9]{1,3}(?:[\.,]\d{3})*(?:[,\.]\d{1,2})?)",
        "bancolombia": r"(?im)(?:valor enviado|valor|monto|total)\s*[:$\-\s]*\s*([0-9]{1,3}(?:[\.,]\d{3})*(?:[,\.]\d{1,2})?)",
    }

    if entidad in entity_patterns:
        match = re.search(entity_patterns[entidad], ocr_text)
        if match:
            cleaned = _to_numeric_string(match.group(1))
            if cleaned:
                return cleaned, "labeled"

    # Patrón genérico con etiquetas
    generic_pattern = r"(?im)(?:monto|valor|total|pagado|importe|cantidad|pago)\s*[:$\-\s]*\s*([0-9]{1,3}(?:[\.,]\d{3})*(?:[,\.]\d{1,2})?)"
    labeled = re.search(generic_pattern, ocr_text)
    if labeled:
        cleaned = _to_numeric_string(labeled.group(1))
        if cleaned:
            return cleaned, "labeled"

    # Fallback: número con separadores de miles más grande
    candidates = re.findall(r"\$?\s*([0-9]{1,3}(?:\.\d{3})+)", ocr_text)
    if candidates:
        normalized = [_to_numeric_string(c) for c in candidates]
        best = max(normalized, key=lambda v: int(v) if v else 0)
        if best:
            return best, "fallback"

    return None, "none"


def _extract_amount(ocr_text: str):
    amount, _ = _extract_amount_with_source(ocr_text, "otro")
    return amount


# ── Referencia ──────────────────────────────────────────────────────────────

def _extract_reference(ocr_text: str, entidad: str = "otro") -> str:
    """
    Extrae referencia bancaria con patrones específicos por entidad.
    """
    entity_patterns = {
        "nequi": r"(?im)(?:referencia|id|n[uú]mero)\s*[:#\-\s]*\s*([a-z0-9]{6,20})",
        "daviplata": r"(?im)(?:aprobaci[oó]n|referencia|c[oó]digo)\s*[:#\-\s]*\s*([a-z0-9]{6,20})",
        "bancolombia": r"(?im)(?:comprobante|referencia|id\s*transacci[oó]n)\s*[:#\-\s]*\s*([a-z0-9]{6,20})",
    }

    if entidad in entity_patterns:
        match = re.search(entity_patterns[entidad], ocr_text)
        if match:
            return match.group(1).strip().upper()

    # Patrón genérico
    generic = re.search(
        r"(?im)(?:referencia|id|comprobante|aprobaci[oó]n|nro|n[uú]mero)\s*[:#\-\s]*\s*([a-z0-9]{6,20})",
        ocr_text,
    )
    if generic:
        return generic.group(1).strip().upper()

    return ""


# ── Fecha ───────────────────────────────────────────────────────────────────

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


# ── Campos etiquetados ───────────────────────────────────────────────────────

def _extract_labeled_value(ocr_text: str, labels) -> str:
    for label in labels:
        pattern = rf"(?im){label}\s*[:\-]\s*(.+)$"
        match = re.search(pattern, ocr_text)
        if match:
            return match.group(1).strip()
    return ""


# ── Normalización numérica ───────────────────────────────────────────────────

def _to_numeric_string(raw_value: str):
    """
    Convierte una cadena con monto colombiano a string de entero (sin decimales).

    Casos manejados:
      "$ 50.000"        → "50000"
      "1.200.000"       → "1200000"
      "1.200.000,00"    → "1200000"   (coma decimal al final → se descarta)
      "50,000"          → "50000"     (sin punto de miles → ambiguo, se asume miles)
      "1.200.000,50"    → "1200000"   (centavos → se descarta, Colombia usa enteros)
    """
    if not raw_value:
        return None

    # Eliminar símbolo de moneda y espacios
    value = re.sub(r"[\$\s]", "", raw_value).strip()

    if not value:
        return None

    # Formato colombiano estándar: puntos como miles, coma como decimal
    # Ej: "1.200.000,50" o "50.000"
    if re.match(r"^[0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{1,2})?$", value):
        # Eliminar puntos de miles y parte decimal con coma
        value = re.sub(r"\.", "", value)
        value = re.sub(r",[0-9]+$", "", value)
        return value if value.isdigit() else None

    # Formato con coma como miles y punto como decimal (poco común en Colombia)
    # Ej: "50,000.00" → tratar como 50000
    if re.match(r"^[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{1,2})?$", value):
        value = re.sub(r",", "", value)
        value = re.sub(r"\.[0-9]+$", "", value)
        return value if value.isdigit() else None

    # Solo dígitos (ya limpio)
    digits = re.sub(r"[^0-9]", "", value)
    return digits if digits else None


def _generate_fallback_reference(ocr_text: str, entidad: str) -> str:
    """
    Genera una referencia interna basada en hash cuando no se puede extraer.
    Usa los primeros 200 caracteres del texto OCR + entidad para generar hash único.
    """
    seed = f"{entidad}:{ocr_text[:200]}"
    return "INT-" + hashlib.sha1(seed.encode()).hexdigest()[:12].upper()
