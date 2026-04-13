import re
from typing import Optional

CATEGORY_RULES = [
    {
        'id': 'alimentacion',
        'keywords': [
            'restaurante', 'rappi', 'ifood', 'domicilio', 'panaderia', 'panderia',
            'almuerzo', 'comida', 'burger', 'pizza', 'pollo', 'sushi', 'cafe',
            'cafeteria', 'asadero', 'frisby', 'mcdonalds', 'subway', 'kfc',
            'crepes', 'corrientazo', 'desayuno', 'cena',
        ],
    },
    {
        'id': 'transporte',
        'keywords': [
            'uber', 'didi', 'beat', 'taxi', 'indriver', 'gasolina', 'tanqueo',
            'peaje', 'parqueadero', 'estacionamiento', 'transmilenio', 'metro',
            'bus', 'sitp',
        ],
    },
    {
        'id': 'servicios',
        'keywords': [
            'epm', 'codensa', 'enel', 'acueducto', 'gas natural', 'vanti',
            'claro', 'movistar', 'tigo', 'wom', 'etb', 'internet', 'celular',
            'plan datos',
        ],
    },
    {
        'id': 'salud',
        'keywords': [
            'farmacia', 'drogueria', 'droguería', 'eps', 'medic', 'doctor',
            'laboratorio', 'clinica', 'hospital', 'dental', 'optometr',
            'cruz verde', 'locatel', 'farmatodo',
        ],
    },
    {
        'id': 'entretenimiento',
        'keywords': [
            'netflix', 'spotify', 'disney', 'hbo', 'prime video', 'youtube',
            'cine', 'cinecolombia', 'procinal', 'bar', 'discoteca', 'fiesta',
            'concierto', 'teatro', 'museo', 'parque',
        ],
    },
    {
        'id': 'educacion',
        'keywords': [
            'universidad', 'colegio', 'curso', 'udemy', 'platzi', 'coursera',
            'libro', 'libreria', 'librería', 'papeleria', 'semestre', 'matricula',
        ],
    },
    {
        'id': 'hogar',
        'keywords': [
            'arriendo', 'administracion', 'mercado', 'exito', 'éxito', 'jumbo',
            'd1', 'ara', 'olimpica', 'carulla', 'metro', 'surtimax', 'supermercado',
            'hogar', 'homecenter', 'mueble',
        ],
    },
    {
        'id': 'ropa',
        'keywords': [
            'zara', 'arturo calle', 'falabella', 'nike', 'adidas', 'tennis',
            'koaj', 'studio f', 'ela', 'bershka', 'hm', 'pull and bear',
        ],
    },
    {
        'id': 'tecnologia',
        'keywords': [
            'amazon', 'mercadolibre', 'mercado libre', 'alkosto', 'ktronix',
            'linio', 'apple', 'samsung', 'lenovo', 'computador', 'celular',
            'audifonos', 'cargador',
        ],
    },
    {
        'id': 'ahorro',
        'keywords': [
            'cdt', 'fiducuenta', 'fondo', 'tyba', 'nu colombia', 'inversion',
            'rendimiento', 'ahorro programado',
        ],
    },
    {
        'id': 'deudas',
        'keywords': [
            'tarjeta de credito', 'cuota', 'prestamo', 'crédito', 'credito',
            'pago minimo', 'amortizacion', 'leasing',
        ],
    },
]


def infer_category(destinatario: str, descripcion: str = '') -> str:
    """
    Infiere la categoría de una transacción basándose en
    el nombre del destinatario y la descripción.

    Returns:
        ID de la categoría más probable, o 'sin_categorizar' si no hay match.
    """
    if not destinatario and not descripcion:
        return 'sin_categorizar'

    text = f"{destinatario} {descripcion}".lower().strip()

    # Buscar match por keywords
    best_match = None
    best_score = 0

    for rule in CATEGORY_RULES:
        score = 0
        for keyword in rule['keywords']:
            if keyword in text:
                # Keywords más largos dan más confianza
                score += len(keyword)
        if score > best_score:
            best_score = score
            best_match = rule['id']

    if best_match and best_score >= 3:
        return best_match

    return 'sin_categorizar'
