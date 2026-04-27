import gc
import io
import json
import logging
from typing import Optional

import requests
from django.conf import settings

from .circuit_breaker import ocr_breaker

logger = logging.getLogger(__name__)

# Tamaño mínimo al que se hace upscale si la imagen es pequeña
_MIN_DIMENSION_PX = 1000
# Factor de upscale máximo para evitar imágenes demasiado grandes
_MAX_UPSCALE_FACTOR = 3.0


class OCRLocalService:
    """Cliente para OCR local en red interna de Docker."""

    @staticmethod
    def extract_text(image_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
        """
        Envia bytes de imagen al motor OCR local y retorna texto plano.
        Aplica preprocesamiento con Pillow antes de enviar para mejorar calidad OCR.
        Nunca expone imagenes ni texto sensible en logs.
        """
        if not image_bytes:
            logger.warning("Solicitud OCR vacia: no se recibieron bytes de imagen")
            return None

        if not ocr_breaker.can_execute():
            logger.warning("Circuit breaker OPEN para OCR local")
            return None

        # Preprocesar imagen para mejorar calidad antes de enviar al OCR
        processed_bytes = OCRLocalService._preprocess_image(image_bytes, mime_type)
        if processed_bytes is None:
            logger.warning("Preprocesamiento de imagen falló — usando imagen original")
            processed_bytes = image_bytes

        url = getattr(settings, "OCR_SERVICE_URL", "http://ocr-engine:8000/process")
        payload = bytearray(processed_bytes)
        image_stream = io.BytesIO(payload)
        files = {
            "file": ("comprobante", image_stream, "image/jpeg")
        }

        try:
            response = requests.post(url, files=files, timeout=(5, 35))
            response.raise_for_status()

            extracted_text = OCRLocalService._parse_ocr_response(response)
            if not extracted_text:
                logger.warning("OCR local respondio sin texto")
                return ""

            ocr_breaker.record_success()
            logger.info("OCR local completado; longitud_texto=%s", len(extracted_text))
            return extracted_text

        except requests.exceptions.Timeout:
            logger.error("Timeout en OCR local")
            ocr_breaker.record_failure()
            return None
        except requests.exceptions.RequestException as exc:
            logger.error("Fallo de conexion con OCR local: %s", exc)
            ocr_breaker.record_failure()
            return None
        finally:
            image_stream.close()
            payload[:] = b"\x00" * len(payload)
            del payload
            del image_stream
            del processed_bytes
            gc.collect()

    @staticmethod
    def _preprocess_image(image_bytes: bytes, mime_type: str) -> Optional[bytes]:
        """
        Aplica preprocesamiento para mejorar la calidad del OCR:
        1. Convierte a escala de grises
        2. Aumenta contraste con ImageEnhance
        3. Aplica sharpening
        4. Upscale si la imagen es muy pequeña (< _MIN_DIMENSION_PX en cualquier eje)
        5. Exporta como JPEG optimizado para el motor OCR

        Retorna bytes procesados o None si falla (el caller usará la imagen original).
        """
        try:
            from PIL import Image, ImageEnhance, ImageFilter
        except ImportError:
            logger.debug("Pillow no disponible — saltando preprocesamiento")
            return None

        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Convertir a RGB si es RGBA, P (paleta) u otro modo
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Upscale si la imagen es demasiado pequeña
            width, height = img.size
            min_dim = min(width, height)
            if min_dim < _MIN_DIMENSION_PX:
                scale = min(_MIN_DIMENSION_PX / min_dim, _MAX_UPSCALE_FACTOR)
                new_w = int(width * scale)
                new_h = int(height * scale)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                logger.debug(
                    "Imagen upscaled: %dx%d → %dx%d (factor=%.2f)",
                    width, height, new_w, new_h, scale
                )

            # Convertir a escala de grises (mejora rendimiento OCR en texto negro sobre blanco)
            img = img.convert("L")

            # Aumentar contraste (factor 1.5 = incremento moderado)
            img = ImageEnhance.Contrast(img).enhance(1.5)

            # Sharpening suave para definir bordes de letras
            img = img.filter(ImageFilter.SHARPEN)

            # Exportar como JPEG de alta calidad en escala de grises
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=90, optimize=True)
            result = output.getvalue()
            output.close()

            logger.debug(
                "Preprocesamiento OK: %d bytes → %d bytes",
                len(image_bytes), len(result)
            )
            return result

        except Exception as exc:
            logger.warning("Error en preprocesamiento de imagen: %s", exc)
            return None

    @staticmethod
    def _parse_ocr_response(response: requests.Response) -> str:
        """
        Soporta dos contratos del microservicio OCR:
        1) JSON: {"status":"success","text":"..."}
        2) Texto plano en body.
        """
        content_type = (response.headers.get("Content-Type") or "").lower()
        body = response.text or ""

        if "application/json" in content_type or body.strip().startswith("{"):
            try:
                parsed = response.json()
            except (ValueError, json.JSONDecodeError):
                parsed = None

            if isinstance(parsed, dict):
                if parsed.get("status") == "error":
                    logger.warning("OCR local respondio estado error")
                    return ""
                text = parsed.get("text")
                if isinstance(text, str):
                    return text.strip()

        return body.strip()
