# 02 — IA OCR MAESTRO (Motor de Extracción con Gemini 1.5 Flash)

> **Proyecto:** Finanzas App  
> **Versión:** 1.0.0 (MVP)  
> **Última actualización:** 2026-04-07  
> **Referencia:** [00_SISTEMA_Y_RESILIENCIA.md](./00_SISTEMA_Y_RESILIENCIA.md) | [01_BACKEND_EVOLUTIVO.md](./01_BACKEND_EVOLUTIVO.md)

---

## 1. Prompt Maestro de Gemini (System Instruction)

### 1.1 Prompt System — Versión Producción

```text
SYSTEM PROMPT — Finanzas App OCR Engine v1.0

ROL: Eres un motor de extracción de datos financieros especializado en comprobantes bancarios colombianos. Tu única función es analizar imágenes de comprobantes de transferencias y devolver datos estructurados en JSON.

ENTIDADES SOPORTADAS:
- Nequi (billetera digital de Bancolombia)
- Daviplata (billetera digital del Banco Davivienda)
- Bancolombia (transferencias y pagos)

INSTRUCCIONES ESTRICTAS:

1. ANALIZA la imagen recibida e identifica si es un comprobante bancario válido.

2. Si NO es un comprobante bancario, responde EXACTAMENTE:
   {"error": "not_a_receipt", "message": "La imagen no parece ser un comprobante bancario."}

3. Si la imagen es de BAJA CALIDAD (borrosa, cortada, ilegible), responde EXACTAMENTE:
   {"error": "low_quality", "message": "La imagen no es suficientemente clara para extraer datos."}

4. Si ES un comprobante válido, extrae TODOS estos campos:
   - monto: número sin formato (ej: 150000, no "$150.000")
   - referencia_bancaria: código único de la transacción (número de comprobante, referencia, No. de aprobación)
   - fecha_transaccion: formato ISO 8601 (YYYY-MM-DDTHH:MM:SS). Si solo hay fecha sin hora, usar T00:00:00
   - entidad: "nequi" | "daviplata" | "bancolombia" | "otro"
   - tipo: "gasto" | "ingreso" | "transferencia_propia"
   - destinatario: nombre de la persona o comercio receptor
   - emisor: nombre de la persona que envía (si está visible)
   - descripcion: motivo o concepto del pago (si está visible)
   - confianza: número de 0.0 a 1.0 indicando tu nivel de certeza

5. REGLAS DE TIPO:
   - Si el dinero SALE de la cuenta del usuario → "gasto"
   - Si el dinero ENTRA a la cuenta del usuario → "ingreso"
   - Si ambos (emisor y destinatario) parecen ser la misma persona o cuentas propias → "transferencia_propia"

6. REGLAS DE CONFIANZA:
   - 1.0: Todos los campos se leyeron perfectamente
   - 0.8-0.99: La mayoría de campos claros, 1-2 campos inferidos
   - 0.5-0.79: Varios campos difíciles de leer, imagen parcialmente borrosa
   - < 0.5: Imagen muy borrosa o datos muy inciertos → en este caso, usa error "low_quality"

7. FORMATO DE RESPUESTA — SIEMPRE responde con JSON puro, sin markdown, sin explicaciones:

{
  "monto": 150000,
  "referencia_bancaria": "NQ1234567890",
  "fecha_transaccion": "2026-04-07T14:30:00",
  "entidad": "nequi",
  "tipo": "gasto",
  "destinatario": "Juan Pérez",
  "emisor": "María García",
  "descripcion": "Almuerzo",
  "confianza": 0.95
}

8. NUNCA inventes datos. Si un campo no es visible, usa:
   - Para strings: "" (string vacío)
   - Para referencia_bancaria: Si no la encuentras, busca cualquier número de referencia, comprobante, aprobación o transacción
   - Para fecha: Si no hay fecha, usa "" y baja la confianza a 0.6 máximo

9. NUNCA respondas como un chatbot. No digas "claro", "aquí tienes", etc. SOLO JSON.
```

### 1.2 Ejemplo de Prompt de Usuario (por cada imagen)

```text
Extrae los datos de este comprobante bancario colombiano. Responde SOLO con JSON válido.
```

---

## 2. Servicio de Gemini en Django

```python
# backend/core/services/gemini_service.py

import json
import logging
import google.generativeai as genai
from django.conf import settings
from .circuit_breaker import gemini_breaker

logger = logging.getLogger(__name__)

# Prompt System (se carga una sola vez)
SYSTEM_PROMPT = """
ROL: Eres un motor de extracción de datos financieros especializado en comprobantes bancarios colombianos. Tu única función es analizar imágenes de comprobantes de transferencias y devolver datos estructurados en JSON.

ENTIDADES SOPORTADAS:
- Nequi (billetera digital de Bancolombia)
- Daviplata (billetera digital del Banco Davivienda)
- Bancolombia (transferencias y pagos)

INSTRUCCIONES ESTRICTAS:

1. ANALIZA la imagen recibida e identifica si es un comprobante bancario válido.

2. Si NO es un comprobante bancario, responde EXACTAMENTE:
   {"error": "not_a_receipt", "message": "La imagen no parece ser un comprobante bancario."}

3. Si la imagen es de BAJA CALIDAD (borrosa, cortada, ilegible), responde EXACTAMENTE:
   {"error": "low_quality", "message": "La imagen no es suficientemente clara para extraer datos."}

4. Si ES un comprobante válido, extrae TODOS estos campos:
   - monto: número sin formato (ej: 150000)
   - referencia_bancaria: código único de la transacción
   - fecha_transaccion: formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)
   - entidad: "nequi" | "daviplata" | "bancolombia" | "otro"
   - tipo: "gasto" | "ingreso" | "transferencia_propia"
   - destinatario: nombre receptor
   - emisor: nombre emisor
   - descripcion: motivo del pago
   - confianza: 0.0 a 1.0

5. Si ambos (emisor y destinatario) parecen ser la misma persona → tipo = "transferencia_propia"
6. Si confianza < 0.5 → devolver error "low_quality"
7. SIEMPRE responde SOLO con JSON puro, sin markdown. NUNCA inventes datos.
""".strip()

USER_PROMPT = "Extrae los datos de este comprobante bancario colombiano. Responde SOLO con JSON válido."


class GeminiOCRService:
    """Servicio para extraer datos de comprobantes usando Gemini 1.5 Flash."""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.1,      # Baja creatividad, alta precisión
                max_output_tokens=1024,
                response_mime_type="application/json",
            )
        )

    def extract_from_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """
        Procesa una imagen de comprobante y retorna datos estructurados.

        Args:
            image_bytes: Bytes de la imagen
            mime_type: Tipo MIME (image/jpeg, image/png, image/webp)

        Returns:
            dict con datos extraídos o error
        """
        # Verificar circuit breaker
        if not gemini_breaker.can_execute():
            logger.warning("Circuit breaker OPEN — Gemini no disponible")
            return {
                "error": "service_unavailable",
                "message": "El servicio de procesamiento no está disponible. Tu comprobante será procesado cuando se restablezca."
            }

        try:
            # Preparar imagen para Gemini
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes
            }

            # Enviar a Gemini
            response = self.model.generate_content(
                [USER_PROMPT, image_part],
                request_options={"timeout": 30}  # Timeout de 30 segundos
            )

            # Parsear respuesta JSON
            raw_text = response.text.strip()
            result = json.loads(raw_text)

            # Registrar éxito en circuit breaker
            gemini_breaker.record_success()

            # Agregar respuesta cruda para debugging
            result['raw_response'] = raw_text

            # Validar estructura mínima
            if 'error' in result:
                return result

            required_fields = ['monto', 'referencia_bancaria', 'entidad']
            missing = [f for f in required_fields if not result.get(f)]
            if missing:
                logger.warning(f"Campos faltantes en respuesta Gemini: {missing}")
                result['confianza'] = min(result.get('confianza', 0.5), 0.5)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Gemini devolvió JSON inválido: {e}")
            gemini_breaker.record_failure()
            return {
                "error": "invalid_response",
                "message": "No se pudo procesar la respuesta del motor IA."
            }
        except Exception as e:
            logger.error(f"Error al llamar Gemini: {e}")
            gemini_breaker.record_failure()
            return {
                "error": "processing_error",
                "message": "Error al procesar la imagen. Intenta de nuevo."
            }


# Singleton para reusar la conexión
_gemini_service = None

def get_gemini_service() -> GeminiOCRService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiOCRService()
    return _gemini_service
```

---

## 3. Validación de Respuesta JSON (Schema)

```python
# backend/core/services/ocr_validator.py

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
```

---

## 4. Casos de Borde

### 4.1 Transferencias entre Cuentas Propias vs. Gastos a Terceros

```
CASO 1: Transferencia a Tercero (GASTO)
─────────────────────────────────────────
Comprobante dice:
  De: María García
  Para: Restaurante El Buen Sabor
  → tipo = "gasto"
  → categoría se infiere del destinatario

CASO 2: Transferencia entre Cuentas Propias (TRANSFERENCIA_PROPIA)
─────────────────────────────────────────────────────────────────
Comprobante dice:
  De: María García (Nequi)
  Para: María García (Bancolombia)
  → tipo = "transferencia_propia"
  → NO afecta presupuesto (no es gasto ni ingreso)

CASO 3: Recibir Dinero (INGRESO)
─────────────────────────────────
Comprobante dice:
  De: Empresa XYZ
  Para: María García
  → tipo = "ingreso"
```

```python
# Lógica de detección en post-procesamiento
# backend/core/services/transaction_classifier.py

def classify_transaction_type(ocr_data: dict, user_name: str = None) -> str:
    """
    Clasifica el tipo de transacción basado en emisor y destinatario.
    Gemini intenta clasificar, pero este post-procesamiento corrige errores.
    """
    emisor = (ocr_data.get('emisor', '') or '').lower().strip()
    destinatario = (ocr_data.get('destinatario', '') or '').lower().strip()
    tipo_gemini = ocr_data.get('tipo', 'gasto')

    # Si no hay emisor ni destinatario, confiar en Gemini
    if not emisor and not destinatario:
        return tipo_gemini

    # Detectar transferencia propia: mismo nombre en ambos campos
    if emisor and destinatario:
        # Comparación fuzzy básica (al menos 70% de similitud)
        from difflib import SequenceMatcher
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

    return tipo_gemini
```

### 4.2 Imagen Borrosa / Captura de Pantalla Parcial

```
FLUJO:
1. Gemini analiza la imagen
2. Si confianza < 0.5 OR error = "low_quality":
   → Responder por WhatsApp: "📸 La imagen no es clara. ¿Puedes enviar otra foto?"
   → NO guardar transacción
   → Guardar imagen en carpeta "pendientes" para revisión

3. Si 0.5 <= confianza < 0.8:
   → Guardar transacción con estado = "needs_review"
   → Responder: "Procesé tu comprobante pero no estoy 100% seguro. Verifica los datos."
   → Mostrar datos para confirmación con botones

4. Si confianza >= 0.8:
   → Flujo normal de confirmación con botones
```

### 4.3 Imagen que No es un Comprobante

```
FLUJO:
1. Gemini devuelve: {"error": "not_a_receipt"}
2. Responder por WhatsApp:
   "🤔 Eso no parece un comprobante de pago.
    Envíame la captura de pantalla de tu transferencia de Nequi, Daviplata o Bancolombia."
3. NO guardar nada en DB
```

### 4.4 Formato de Comprobante No Reconocido (Banco Nuevo)

```
FLUJO:
1. Gemini intenta extraer con los patrones conocidos
2. Si entidad = "otro" y confianza >= 0.7:
   → Guardar transacción normalmente
   → Loggear: "Comprobante de entidad no mapeada detectado"
   → El usuario puede confirmar/corregir vía botones

3. Si entidad = "otro" y confianza < 0.7:
   → estado = "needs_review"
   → Responder: "No reconozco este banco. ¿Puedes verificar los datos?"
```

---

## 5. Mapeo de Categorías

### 5.1 Categorías del MVP

| ID               | Nombre               | Palabras Clave en Destinatario                              |
|------------------|-----------------------|-------------------------------------------------------------|
| `alimentacion`   | Alimentación          | restaurante, rappi, ifood, domicilios, panadería, almuerzo  |
| `transporte`     | Transporte            | uber, didi, beat, taxi, gasolina, peaje, parqueadero        |
| `servicios`      | Servicios Públicos    | epm, codensa, acueducto, gas natural, etb                   |
| `salud`          | Salud                 | farmacia, droguería, eps, citas médicas, laboratorio        |
| `entretenimiento`| Entretenimiento       | netflix, spotify, cine, bar, discoteca                      |
| `educacion`      | Educación             | universidad, colegio, curso, udemy, platzi                  |
| `hogar`          | Hogar                 | arriendo, administración, mercado, éxito, jumbo, d1, ara    |
| `ropa`           | Ropa y Accesorios     | zara, arturo calle, falabella, nike, adidas                 |
| `tecnologia`     | Tecnología            | amazon, mercadolibre, alkosto, ktronix                      |
| `ahorro`         | Ahorro/Inversión      | cdt, fiducuenta, fondo, tyba, nu                            |
| `deudas`         | Pago de Deudas        | tarjeta de crédito, cuota, préstamo, crédito                |
| `transferencia`  | Transferencia Personal| (nombres de personas sin match comercial)                   |
| `sin_categorizar`| Sin Categorizar       | (fallback cuando no hay match)                              |

### 5.2 Motor de Categorización

```python
# backend/core/services/category_engine.py

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
```

---

## 6. Pipeline Completo: Imagen → Transacción

```python
# backend/core/services/ocr_pipeline.py

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
```

---

## 7. Escalabilidad: Agregar Nuevos Bancos

Para agregar un nuevo banco (ej. Banco de Bogotá), se necesitan **solo 2 cambios**:

### 7.1 Actualizar el Prompt de Gemini

```text
# Agregar a la sección ENTIDADES SOPORTADAS:
- Banco de Bogotá (transferencias y pagos)

# Actualizar el enum de entidad:
- entidad: "nequi" | "daviplata" | "bancolombia" | "banco_bogota" | "otro"
```

### 7.2 Actualizar el Modelo Django

```python
# En transactions/models.py → EntidadBancaria:
class EntidadBancaria(models.TextChoices):
    NEQUI = 'nequi', 'Nequi'
    DAVIPLATA = 'daviplata', 'Daviplata'
    BANCOLOMBIA = 'bancolombia', 'Bancolombia'
    BANCO_BOGOTA = 'banco_bogota', 'Banco de Bogotá'  # ← NUEVO
    OTRO = 'otro', 'Otro'
```

> **IMPORTANTE:** Generar y aplicar migración después de este cambio.  
> Registrar en [05_LOG_DE_DECISIONES_Y_CAMBIOS.md](./05_LOG_DE_DECISIONES_Y_CAMBIOS.md).

---

## 8. Métricas y Monitoreo del Motor IA

```python
# backend/core/services/ocr_metrics.py

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class OCRMetrics:
    """Métricas en memoria del motor OCR. Para MVP, no necesitamos Prometheus."""
    total_requests: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    duplicates_detected: int = 0
    avg_confidence: float = 0.0
    errors_by_type: dict = field(default_factory=lambda: defaultdict(int))
    confidence_history: list = field(default_factory=list)
    _last_reset: datetime = field(default_factory=datetime.now)

    def record_success(self, confidence: float):
        self.total_requests += 1
        self.successful_extractions += 1
        self.confidence_history.append(confidence)
        # Running average
        self.avg_confidence = sum(self.confidence_history) / len(self.confidence_history)

    def record_failure(self, error_type: str):
        self.total_requests += 1
        self.failed_extractions += 1
        self.errors_by_type[error_type] += 1

    def record_duplicate(self):
        self.duplicates_detected += 1

    def get_summary(self) -> dict:
        return {
            'total_requests': self.total_requests,
            'success_rate': (
                self.successful_extractions / self.total_requests * 100
                if self.total_requests > 0 else 0
            ),
            'avg_confidence': round(self.avg_confidence, 2),
            'errors_by_type': dict(self.errors_by_type),
            'duplicates': self.duplicates_detected,
        }

# Singleton
ocr_metrics = OCRMetrics()
```

---

## 9. Testing del Motor OCR

```python
# backend/core/tests/test_ocr_validator.py

from django.test import TestCase
from core.services.ocr_validator import validate_ocr_response
from core.services.category_engine import infer_category

class TestOCRValidator(TestCase):
    def test_valid_nequi_response(self):
        data = {
            'monto': 150000,
            'referencia_bancaria': 'NQ1234567890',
            'fecha_transaccion': '2026-04-07T14:30:00',
            'entidad': 'nequi',
            'tipo': 'gasto',
            'destinatario': 'Restaurante El Sabor',
            'confianza': 0.95,
        }
        result = validate_ocr_response(data)
        self.assertNotIn('error', result)
        self.assertEqual(result['monto'], '150000')
        self.assertEqual(result['entidad'], 'nequi')

    def test_missing_referencia(self):
        data = {'monto': 50000, 'entidad': 'nequi'}
        result = validate_ocr_response(data)
        self.assertIn('error', result)

    def test_negative_monto(self):
        data = {
            'monto': -5000,
            'referencia_bancaria': 'REF123',
            'entidad': 'daviplata',
        }
        result = validate_ocr_response(data)
        self.assertIn('error', result)

    def test_gemini_error_passthrough(self):
        data = {'error': 'low_quality', 'message': 'Imagen borrosa'}
        result = validate_ocr_response(data)
        self.assertEqual(result['error'], 'low_quality')


class TestCategoryEngine(TestCase):
    def test_rappi_is_alimentacion(self):
        self.assertEqual(infer_category('Rappi Colombia', ''), 'alimentacion')

    def test_uber_is_transporte(self):
        self.assertEqual(infer_category('Uber', 'viaje'), 'transporte')

    def test_unknown_is_sin_categorizar(self):
        self.assertEqual(infer_category('Juan Pérez', ''), 'sin_categorizar')

    def test_netflix_is_entretenimiento(self):
        self.assertEqual(infer_category('Netflix', 'suscripción'), 'entretenimiento')

    def test_exito_is_hogar(self):
        self.assertEqual(infer_category('Éxito Poblado', 'mercado'), 'hogar')
```

---

*Este documento sigue la [Regla de Oro](./00_SISTEMA_Y_RESILIENCIA.md#61-regla-de-oro). Cualquier cambio en el motor IA, prompt o categorías debe documentarse aquí y en el log de decisiones.*
