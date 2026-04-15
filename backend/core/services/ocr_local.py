import logging
from typing import Optional

import requests
from django.conf import settings

from .circuit_breaker import ocr_breaker

logger = logging.getLogger(__name__)


class OCRLocalService:
    """Cliente para OCR local en red interna de Docker."""

    @staticmethod
    def extract_text(image_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
        """
        Envia bytes de imagen al motor OCR local y retorna texto plano.
        Nunca expone imagenes ni texto sensible en logs.
        """
        if not image_bytes:
            logger.warning("Solicitud OCR vacia: no se recibieron bytes de imagen")
            return None

        if not ocr_breaker.can_execute():
            logger.warning("Circuit breaker OPEN para OCR local")
            return None

        url = getattr(settings, "OCR_SERVICE_URL", "http://ocr-engine:8000/process")
        files = {
            "file": ("comprobante", image_bytes, mime_type or "application/octet-stream")
        }

        try:
            response = requests.post(url, files=files, timeout=(5, 35))
            response.raise_for_status()

            extracted_text = response.text.strip()
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
