from datetime import datetime
from decimal import Decimal, InvalidOperation

# Campos esperados y sus tipos
OCR_SCHEMA = {
    'monto': {'type': 'number', 'required': True},
    'referencia_bancaria': {'type': 'string', 'required': True},
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
    Valida y normaliza la respuesta de Gemini.
    Retorna datos limpios o dict con error.
    """
    # Si Gemini ya devolvió un error, retornarlo tal cual
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

    # --- Referencia Bancaria ---
    ref = str(data.get('referencia_bancaria', '')).strip()
    if not ref:
        errors.append('referencia_bancaria es obligatoria')
    else:
        cleaned['referencia_bancaria'] = ref

    # --- Fecha ---
    fecha_raw = data.get('fecha_transaccion', '')
    if fecha_raw:
        try:
            cleaned['fecha_transaccion'] = datetime.fromisoformat(str(fecha_raw))
        except (ValueError, TypeError):
            # Intentar formatos alternativos
            for fmt in ['%d/%m/%Y %H:%M', '%d/%m/%Y', '%Y-%m-%d']:
                try:
                    cleaned['fecha_transaccion'] = datetime.strptime(str(fecha_raw), fmt)
                    break
                except ValueError:
                    continue
            if 'fecha_transaccion' not in cleaned:
                cleaned['fecha_transaccion'] = datetime.now()
                errors.append(f'fecha no parseada: {fecha_raw}, usando fecha actual')
    else:
        cleaned['fecha_transaccion'] = datetime.now()

    # --- Entidad ---
    entidad = str(data.get('entidad', 'otro')).lower().strip()
    if entidad not in ['nequi', 'daviplata', 'bancolombia', 'otro']:
        entidad = 'otro'
    cleaned['entidad'] = entidad

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

    # Si hay errores críticos, retornar error
    critical_errors = [e for e in errors if 'obligatori' in e]
    if critical_errors:
        return {
            'error': 'validation_failed',
            'message': '; '.join(critical_errors),
            'partial_data': cleaned
        }

    return cleaned
