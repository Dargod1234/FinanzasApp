from difflib import SequenceMatcher


def classify_transaction_type(ocr_data: dict, user_name: str = None) -> str:
    """
    Clasifica el tipo de transacción basado en emisor y destinatario.
    El OCR inicial intenta clasificar, y este post-procesamiento corrige errores.
    """
    emisor = (ocr_data.get('emisor', '') or '').lower().strip()
    destinatario = (ocr_data.get('destinatario', '') or '').lower().strip()
    tipo_inicial = ocr_data.get('tipo', 'gasto')

    # Keywords explícitas en el texto OCR (mayor prioridad — cubre Nequi Bre-B, etc.)
    raw_text = (ocr_data.get('raw_response', '') or '').lower()
    income_kw = ["recibiste", "te llegaron", "te llegó", "te llego", "recibido por", "depósito recibido", "deposito recibido"]
    expense_kw = ["enviaste", "transferiste", "pagaste", "debitado", "enviado a"]
    if any(kw in raw_text for kw in income_kw):
        return 'ingreso'
    if any(kw in raw_text for kw in expense_kw):
        return 'gasto'

    # Si no hay emisor ni destinatario, conservar el tipo inicial
    if not emisor and not destinatario:
        return tipo_inicial

    # Detectar transferencia propia: mismo nombre en ambos campos
    if emisor and destinatario:
        similarity = SequenceMatcher(None, emisor, destinatario).ratio()
        if similarity > 0.7:
            return 'transferencia_propia'

    # Si user_name coincide con destinatario → es ingreso
    # Comparamos nombre completo Y cada parte por separado para cubrir casos como
    # "Damian" coincidiendo con el first_name aunque el full_name sea "Damian Apellido"
    if user_name:
        user_lower = user_name.lower()
        name_parts = [p for p in user_lower.split() if len(p) >= 3]
        candidates = [user_lower] + name_parts

        def _matches(field: str) -> bool:
            if not field:
                return False
            return any(
                SequenceMatcher(None, candidate, field).ratio() > 0.75
                for candidate in candidates
            )

        if _matches(destinatario):
            return 'ingreso'
        if _matches(emisor):
            return 'gasto'

    return tipo_inicial
