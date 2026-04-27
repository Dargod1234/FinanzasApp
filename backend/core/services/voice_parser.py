"""
Parser de texto de voz para registrar transacciones.

Soporta frases como:
  "Gasto de 50 mil en almuerzo hoy"
  "Pagué 150000 de gasolina ayer"
  "Recibí 500 mil de salario"
  "Compré algo por 35 mil en el supermercado"
"""

import re
from datetime import timedelta
from django.utils import timezone


FREE_LIMIT = 15  # transacciones/mes desde la app para plan free


def parse_voice_text(text: str) -> dict:
    """
    Retorna un dict con los campos parseados y su confianza (0..1).
    Si la confianza < 0.5 se recomienda al front mostrar el formulario pre-llenado.
    """
    original = text
    text = text.lower().strip()

    result = {
        'monto': None,
        'tipo': _detect_tipo(text),
        'fecha_transaccion': None,
        'descripcion': original,
        'categoria': 'sin_categorizar',
        'destinatario': '',
        'confianza': 0.0,
    }

    monto = _extract_monto(text)
    if monto:
        result['monto'] = monto

    fecha = _extract_fecha(text)
    result['fecha_transaccion'] = (fecha or timezone.now()).isoformat()

    # Intentar extraer destinatario ("a Juan", "de Pedro", "en Éxito")
    result['destinatario'] = _extract_destinatario(text)

    # Calcular confianza
    score = 0.0
    if result['monto']:
        score += 0.55
    if any(kw in text for kw in _INCOME_KW + _EXPENSE_KW):
        score += 0.20
    if fecha:
        score += 0.10
    if len(text) > 8:
        score += 0.15
    result['confianza'] = round(min(score, 1.0), 2)

    return result


# ── Helpers ────────────────────────────────────────────────────────────────────

_INCOME_KW = [
    'recibí', 'recibi', 'ingreso', 'me pagaron', 'me transfirieron',
    'entrada', 'cobré', 'cobre', 'gané', 'gane', 'salario', 'sueldo',
]

_EXPENSE_KW = [
    'gasto', 'gasté', 'gaste', 'pagué', 'pague',
    'compré', 'compre', 'invertí', 'inverti', 'abono',
]


def _detect_tipo(text: str) -> str:
    for kw in _INCOME_KW:
        if kw in text:
            return 'ingreso'
    return 'gasto'


def _extract_monto(text: str) -> int | None:
    # "X millones"
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:millones?|mm)\b', text)
    if m:
        return int(float(m.group(1).replace(',', '.')) * 1_000_000)

    # "medio millón"
    if 'medio millón' in text or 'medio millon' in text:
        return 500_000

    # "X mil"
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*mil\b', text)
    if m:
        return int(float(m.group(1).replace(',', '.')) * 1_000)

    # "$50.000" o "50.000" o "50,000"
    m = re.search(r'\$?\s*(\d{1,3}(?:[.,]\d{3})+)', text)
    if m:
        clean = re.sub(r'[.,]', '', m.group(1))
        return int(clean)

    # Número suelto >= 1000
    m = re.search(r'\b(\d{4,})\b', text)
    if m:
        return int(m.group(1))

    return None


def _extract_fecha(text):
    now = timezone.now()
    if 'hoy' in text:
        return now
    if 'ayer' in text:
        return now - timedelta(days=1)
    if 'antier' in text or 'antes de ayer' in text:
        return now - timedelta(days=2)

    months = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    }
    for name, num in months.items():
        m = re.search(rf'(\d{{1,2}})\s+de\s+{name}', text)
        if m:
            try:
                return now.replace(month=num, day=int(m.group(1)), hour=12, minute=0, second=0)
            except ValueError:
                pass
    return None


def _extract_destinatario(text: str) -> str:
    # "a [nombre]" o "de [nombre]" o "en [lugar]"
    m = re.search(r'\b(?:a|de|en|para)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][a-záéíóúñ]+(?: [A-Za-záéíóúñ]+)?)', text)
    if m:
        return m.group(1).title()
    return ''
