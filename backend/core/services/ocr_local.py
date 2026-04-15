import logging
import gc
import io
from typing import Optional
import json

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
        payload = bytearray(image_bytes)
        image_stream = io.BytesIO(payload)
        files = {
            "file": ("comprobante", image_stream, mime_type or "application/octet-stream")
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
            del image_bytes
            gc.collect()

    @staticmethod
    def _parse_ocr_response(response: requests.Response) -> str:
        """
        Soporta dos contratos del microservicio OCR:
        1) JSON: {"status":"success","text":"..."}
        2) Texto plano en body.
        """
        content_type = (response.headers.get("Content-Type") or "").lower()
        body = response.text or ""

        # Si el servidor declara JSON, o el cuerpo parece JSON, intentar parsear.
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
