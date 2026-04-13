import json
import logging

import google.genai as genai

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
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

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
            image_part = genai.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )

            # Enviar a Gemini con configuración JSON
            response = self.client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[
                    USER_PROMPT,
                    image_part
                ],
                config=genai.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                    system_instruction=SYSTEM_PROMPT
                )
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
