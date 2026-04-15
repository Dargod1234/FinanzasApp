import requests

from core.services.ocr_local import OCRLocalService
from core.services.circuit_breaker import ocr_breaker, CircuitState


class _FakeResponse:
    def __init__(self, text="", json_data=None, content_type="application/json", status_code=200):
        self.text = text
        self._json_data = json_data
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError("boom")

    def json(self):
        if self._json_data is None:
            raise ValueError("invalid json")
        return self._json_data


def _reset_breaker():
    ocr_breaker.failure_count = 0
    ocr_breaker.state = CircuitState.CLOSED
    ocr_breaker.last_failure_time = None


def test_extract_text_parses_json_payload(monkeypatch):
    _reset_breaker()

    def _fake_post(*args, **kwargs):
        return _FakeResponse(json_data={"status": "success", "text": "hola\nmundo"})

    monkeypatch.setattr("core.services.ocr_local.requests.post", _fake_post)

    result = OCRLocalService.extract_text(b"fake-image", "image/jpeg")

    assert result == "hola\nmundo"
    assert ocr_breaker.state == CircuitState.CLOSED


def test_extract_text_falls_back_to_plain_text(monkeypatch):
    _reset_breaker()

    def _fake_post(*args, **kwargs):
        return _FakeResponse(text="texto plano", json_data=None, content_type="text/plain")

    monkeypatch.setattr("core.services.ocr_local.requests.post", _fake_post)

    result = OCRLocalService.extract_text(b"fake-image", "image/jpeg")

    assert result == "texto plano"


def test_extract_text_handles_service_error_status(monkeypatch):
    _reset_breaker()

    def _fake_post(*args, **kwargs):
        return _FakeResponse(json_data={"status": "error", "message": "fail"})

    monkeypatch.setattr("core.services.ocr_local.requests.post", _fake_post)

    result = OCRLocalService.extract_text(b"fake-image", "image/jpeg")

    assert result == ""


def test_extract_text_records_failure_on_timeout(monkeypatch):
    _reset_breaker()

    def _fake_post(*args, **kwargs):
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr("core.services.ocr_local.requests.post", _fake_post)

    result = OCRLocalService.extract_text(b"fake-image", "image/jpeg")

    assert result is None
    assert ocr_breaker.failure_count == 1
