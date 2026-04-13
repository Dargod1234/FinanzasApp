import json
import logging
from google import genai
from google.genai import types
from django.conf import settings
from .circuit_breaker import gemini_breaker

logger = logging.getLogger(__name__)

# Prompt System optimizado para comprobantes colombianos (Nequi, Daviplata, Bancolombia)
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
5. Si confianza < 0.5 -> devolver error "low_quality"
6. SIEMPRE responde SOLO con JSON puro, sin markdown.
""".strip()

class GeminiOCRService:
    """Servicio para extraer datos de comprobantes usando el SDK Unificado y Gemini 2.0 Flash."""

    def __init__(self):
        # Inicialización limpia para SDK 2026 ignorando listado de modelos (evita 501 Unimplemented)
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Usamos el modelo sucesor de la serie 1.5 para máxima compatibilidad
        self.model_id = 'gemini-2.0-flash'

    def extract_from_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """
        Procesa una imagen de comprobante y retorna datos estructurados.
        """
        # Verificar circuit breaker
        if not gemini_breaker.can_execute():
            logger.warning("Circuit breaker OPEN — Gemini no disponible")
            return {
                "error": "service_unavailable",
                "message": "El servicio de procesamiento no está disponible temporalmente."
            }

        try:
            # Configuración de generación según tu investigación
            generate_config = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1024,
                response_mime_type="application/json",
                system_instruction=SYSTEM_PROMPT
            )

            # Llamada directa (sin pasar por list_models para evitar Error 501)
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    "Extrae los datos de este comprobante colombiano. Responde SOLO con JSON válido."
                ],
                config=generate_config
            )

            # Parsear respuesta JSON
            raw_text = response.text.strip()
            result = json.loads(raw_text)

            # Registrar éxito en circuit breaker
            gemini_breaker.record_success()

            # Agregar respuesta cruda para debugging
            result['raw_response'] = raw_text

            # Validar estructura mínima
            required_fields = ['monto', 'referencia_bancaria', 'entidad']
            missing = [f for f in required_fields if not result.get(f)]
            if missing and 'error' not in result:
                logger.warning(f"Campos faltantes en respuesta: {missing}")
                result['confianza'] = min(result.get('confianza', 0.5), 0.5)

            return result

        except Exception as e:
            logger.error(f"Error crítico en Gemini (OCR Directo): {e}")
            gemini_breaker.record_failure()
            return {
                "error": "extraction_error",
                "message": f"Error al extraer datos: {str(e)}"
            }


# Singleton para reusar la conexión
_gemini_service = None

def get_gemini_service() -> GeminiOCRService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiOCRService()
    return _gemini_service
