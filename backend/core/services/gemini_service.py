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
2. Si NO es un comprobante bancario, devuelve un error con el motivo.
3. Si ES un comprobante válido, extrae:
   - monto: número sin formato (ej: 150000)
   - referencia_bancaria: código único de la transacción
   - fecha_transaccion: formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)
   - entidad: "nequi" | "daviplata" | "bancolombia" | "otro"
   - tipo: "gasto" | "ingreso" | "transferencia_propia"
   - destinatario: nombre receptor
   - emisor: nombre emisor
   - descripcion: motivo del pago
   - confianza: 0.0 a 1.0
4. Devuelve SIEMPRE JSON puro.
""".strip()

class GeminiOCRService:
    """Servicio para extraer datos de comprobantes usando el SDK Unificado y Gemini 3.1 Flash-Lite."""

    def __init__(self):
        # Inicialización del cliente unificado
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # El modelo validado como más eficiente para OCR en 2026: gemini-3.1-flash-lite-preview
        self.model_id = 'gemini-3.1-flash-lite-preview'

    def extract_from_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """
        Extrae datos de comprobantes de Nequi/Daviplata/Bancolombia.
        """
        if not gemini_breaker.can_execute():
            logger.warning("Circuit breaker OPEN — Gemini no disponible")
            return {
                "error": "service_unavailable", 
                "message": "Servicio temporalmente fuera de línea."
            }

        try:
            # Configuración específica para JSON y precisión financiera
            config = types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=1024,
                response_mime_type="application/json",
                system_instruction=SYSTEM_PROMPT
            )

            # Llamada al modelo con la imagen en bytes
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    "Extrae los datos de este comprobante bancario colombiano."
                ],
                config=config
            )

            # Parsear la respuesta JSON
            raw_text = response.text.strip()
            result = json.loads(raw_text)
            
            # Registrar éxito en circuit breaker
            gemini_breaker.record_success()
            
            # Log de éxito para monitoreo
            logger.info(f"OCR Exitoso: {result.get('entidad')} - {result.get('monto')}")
            
            # Agregar respuesta cruda para debugging
            result['raw_response'] = raw_text
            
            return result

        except Exception as e:
            logger.error(f"Error procesando imagen con Gemini 3.1: {e}")
            gemini_breaker.record_failure()
            return {
                "error": "processing_error",
                "message": "No pudimos leer el comprobante. Asegúrate de que la foto sea clara."
            }

# Singleton para reusar la conexión
_gemini_service = None

def get_gemini_service() -> GeminiOCRService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiOCRService()
    return _gemini_service
