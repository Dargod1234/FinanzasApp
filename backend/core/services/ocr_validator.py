import hashlib
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# Campos esperados y sus tipos
OCR_SCHEMA = {
    'monto': {'type': 'number', 'required': True},
    'referencia_bancaria': {'type': 'string', 'required': False},  # Generada internamente si falta
    'fecha_transaccion': {'type': 'datetime', 'required': False},
    'entidad': {'type': 'enum', 'values': ['nequi', 'daviplata', 'bancolombia', 'otro'], 'required': True},
    'tipo': {'type': 'enum', 'values': ['gasto', 'ingreso', 'transferencia_propia'], 'required': False},
    'destinatario': {'type': 'string', 'required': False},
    'emisor': {'type': 'string', 'required': False},
    'descripcion': {'type': 'string', 'required': False},
    'confianza': {'type': 'float', 'required': False},
}


def validate_ocr_response(data: dict) -> dict:
    """
    Valida y normaliza la respuesta estructurada del OCR.
    Retorna datos limpios o dict con error.

    La referencia_bancaria ya no es obligatoria: si no se extrae del comprobante
    se genera un identificador interno basado en hash de (monto, fecha, entidad, texto_raw)
    para garantizar deduplicación sin bloquear transacciones válidas.
    """
    if 'error' in data:
        return data

    errors = []
    cleaned = {}

    # --- Monto ---
    try:
        monto = data.get('monto')
        if monto is None or monto == '':
            errors.append('monto es obligatorio')
        else:
            monto_dec = Decimal(str(monto))
            if monto_dec <= 0:
                errors.append('monto debe ser positivo')
            else:
                cleaned['monto'] = str(monto_dec)
    except (InvalidOperation, ValueError):
        errors.append(f'monto inválido: {data.get("monto")}')

    # --- Fecha (normalizar primero para usarla en el hash de referencia) ---
    fecha_raw = data.get('fecha_transaccion', '')
    if fecha_raw:
        try:
            cleaned['fecha_transaccion'] = datetime.fromisoformat(str(fecha_raw))
        except (ValueError, TypeError):
            for fmt in ['%d/%m/%Y %H:%M', '%d/%m/%Y', '%Y-%m-%d']:
                try:
                    cleaned['fecha_transaccion'] = datetime.strptime(str(fecha_raw), fmt)
                    break
                except ValueError:
                    continue
            if 'fecha_transaccion' not in cleaned:
                cleaned['fecha_transaccion'] = datetime.now()
    else:
        cleaned['fecha_transaccion'] = datetime.now()

    # --- Entidad ---
    entidad = str(data.get('entidad', 'otro')).lower().strip()
    if entidad not in ['nequi', 'daviplata', 'bancolombia', 'otro']:
        entidad = 'otro'
    cleaned['entidad'] = entidad

    # --- Referencia Bancaria (opcional, se genera si falta) ---
    ref = str(data.get('referencia_bancaria', '')).strip()
    if ref:
        cleaned['referencia_bancaria'] = ref
    else:
        # Generar referencia interna para deduplicación
        cleaned['referencia_bancaria'] = _generate_internal_reference(
            monto=cleaned.get('monto', '0'),
            fecha=cleaned.get('fecha_transaccion', datetime.now()),
            entidad=entidad,
            raw_text=str(data.get('raw_response', ''))[:300],
        )
        logger.info(
            "Referencia bancaria no encontrada — generada internamente: %s",
            cleaned['referencia_bancaria']
        )

    # --- Tipo ---
    tipo = str(data.get('tipo', 'gasto')).lower().strip()
    if tipo not in ['gasto', 'ingreso', 'transferencia_propia']:
        tipo = 'gasto'
    cleaned['tipo'] = tipo

    # --- Campos opcionales ---
    cleaned['destinatario'] = str(data.get('destinatario', '')).strip()
    cleaned['emisor'] = str(data.get('emisor', '')).strip()
    cleaned['descripcion'] = str(data.get('descripcion', '')).strip()
    cleaned['confianza'] = min(max(float(data.get('confianza', 0.5)), 0.0), 1.0)
    cleaned['raw_response'] = data.get('raw_response')

    # Solo el monto sigue siendo crítico
    critical_errors = [e for e in errors if 'obligatori' in e or 'inválido' in e or 'positivo' in e]
    if critical_errors:
        return {
            'error': 'validation_failed',
            'message': '; '.join(critical_errors),
            'partial_data': cleaned
        }

    return cleaned


def _generate_internal_reference(monto: str, fecha: datetime, entidad: str, raw_text: str) -> str:
    """
    Genera un identificador interno para deduplicación cuando no hay referencia bancaria.

    El hash combina monto + fecha (hasta minutos) + entidad + primeros 300 chars del texto OCR.
    Esto garantiza que el mismo comprobante enviado dos veces genere el mismo hash
    (colisión controlada) y comprobantes distintos generen hashes distintos.
    """
    fecha_str = fecha.strftime("%Y%m%d%H%M") if isinstance(fecha, datetime) else str(fecha)
    seed = f"{monto}:{fecha_str}:{entidad}:{raw_text}"
    return "INT-" + hashlib.sha256(seed.encode()).hexdigest()[:14].upper()
