from difflib import SequenceMatcher


def classify_transaction_type(ocr_data: dict, user_name: str = None) -> str:
    """
    Clasifica el tipo de transacción basado en emisor y destinatario.
    El OCR inicial intenta clasificar, y este post-procesamiento corrige errores.
    """
    emisor = (ocr_data.get('emisor', '') or '').lower().strip()
    destinatario = (ocr_data.get('destinatario', '') or '').lower().strip()
    tipo_inicial = ocr_data.get('tipo', 'gasto')

    # Si no hay emisor ni destinatario, conservar el tipo inicial
    if not emisor and not destinatario:
        return tipo_inicial

    # Detectar transferencia propia: mismo nombre en ambos campos
    if emisor and destinatario:
        similarity = SequenceMatcher(None, emisor, destinatario).ratio()
        if similarity > 0.7:
            return 'transferencia_propia'

    # Si user_name coincide con destinatario → es ingreso
    if user_name:
        user_lower = user_name.lower()
        if destinatario and SequenceMatcher(None, user_lower, destinatario).ratio() > 0.7:
            return 'ingreso'
        if emisor and SequenceMatcher(None, user_lower, emisor).ratio() > 0.7:
            return 'gasto'

    return tipo_inicial
