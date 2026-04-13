"""Tests for core app: EncryptedCharField, FieldEncryptor, OTP service."""
import pytest
import os
from decimal import Decimal

from core.encryption import FieldEncryptor
from core.fields import EncryptedCharField
from core.services.circuit_breaker import GeminiCircuitBreaker, CircuitState
from core.services.category_engine import infer_category
from core.services.transaction_classifier import classify_transaction_type
from core.services.ocr_validator import validate_ocr_response


# ── FieldEncryptor Tests ──

class TestFieldEncryptor:
    def test_encrypt_decrypt_roundtrip(self):
        enc = FieldEncryptor()
        plaintext = '150000'
        encrypted = enc.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = enc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_different_nonces(self):
        enc = FieldEncryptor()
        e1 = enc.encrypt('same')
        e2 = enc.encrypt('same')
        assert e1 != e2  # Different nonces each time

    def test_unicode_support(self):
        enc = FieldEncryptor()
        text = 'Café con leche 🎉'
        assert enc.decrypt(enc.encrypt(text)) == text

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv('FIELD_ENCRYPTION_KEY', raising=False)
        with pytest.raises(ValueError, match='no está configurada'):
            FieldEncryptor()

    def test_invalid_key_length(self, monkeypatch):
        import base64
        short_key = base64.b64encode(b'short').decode()
        monkeypatch.setenv('FIELD_ENCRYPTION_KEY', short_key)
        with pytest.raises(ValueError, match='32 bytes'):
            FieldEncryptor()


# ── CircuitBreaker Tests ──

class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = GeminiCircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold(self):
        cb = GeminiCircuitBreaker(failure_threshold=3, recovery_timeout=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_resets_on_success(self):
        cb = GeminiCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_half_open_after_timeout(self):
        import time
        cb = GeminiCircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # With 0 timeout, should transition to HALF_OPEN immediately
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN


# ── CategoryEngine Tests ──

class TestCategoryEngine:
    def test_alimentacion(self):
        assert infer_category('Rappi', '') == 'alimentacion'
        assert infer_category('McDonald\'s', 'domicilio') == 'alimentacion'

    def test_transporte(self):
        assert infer_category('Uber', '') == 'transporte'
        assert infer_category('', 'pago gasolina') == 'transporte'

    def test_servicios(self):
        assert infer_category('Claro', 'plan datos') == 'servicios'

    def test_sin_categorizar(self):
        assert infer_category('', '') == 'sin_categorizar'
        assert infer_category('XYZABC', '') == 'sin_categorizar'

    def test_entretenimiento(self):
        assert infer_category('Netflix', '') == 'entretenimiento'

    def test_hogar(self):
        assert infer_category('Exito', 'mercado semanal') == 'hogar'


# ── TransactionClassifier Tests ──

class TestTransactionClassifier:
    def test_transferencia_propia(self):
        result = classify_transaction_type({
            'emisor': 'Juan Pérez',
            'destinatario': 'Juan Perez',
            'tipo': 'gasto',
        })
        assert result == 'transferencia_propia'

    def test_ingreso_when_user_is_destinatario(self):
        result = classify_transaction_type(
            {'emisor': 'Empresa SAS', 'destinatario': 'María López', 'tipo': 'gasto'},
            user_name='María López'
        )
        assert result == 'ingreso'

    def test_gasto_when_user_is_emisor(self):
        result = classify_transaction_type(
            {'emisor': 'María López', 'destinatario': 'Tienda', 'tipo': 'gasto'},
            user_name='María López'
        )
        assert result == 'gasto'

    def test_falls_back_to_gemini(self):
        result = classify_transaction_type({
            'emisor': '',
            'destinatario': '',
            'tipo': 'ingreso',
        })
        assert result == 'ingreso'


# ── OCR Validator Tests ──

class TestOCRValidator:
    def test_valid_response(self):
        result = validate_ocr_response({
            'monto': 150000,
            'referencia_bancaria': 'REF123',
            'entidad': 'nequi',
            'fecha_transaccion': '2026-04-07T10:00:00',
            'destinatario': 'Tienda',
            'confianza': 0.9,
        })
        assert 'error' not in result
        assert result['monto'] == '150000'
        assert result['entidad'] == 'nequi'

    def test_missing_monto(self):
        result = validate_ocr_response({
            'referencia_bancaria': 'REF123',
            'entidad': 'nequi',
        })
        assert result.get('error') == 'validation_failed'

    def test_missing_referencia(self):
        result = validate_ocr_response({
            'monto': 100,
            'entidad': 'nequi',
        })
        assert result.get('error') == 'validation_failed'

    def test_passthrough_gemini_error(self):
        result = validate_ocr_response({
            'error': 'not_a_receipt',
            'message': 'Not a receipt'
        })
        assert result['error'] == 'not_a_receipt'

    def test_invalid_entidad_defaults_to_otro(self):
        result = validate_ocr_response({
            'monto': 100,
            'referencia_bancaria': 'REF',
            'entidad': 'invalid_bank',
        })
        assert result.get('entidad') == 'otro'

    def test_confianza_clamped(self):
        result = validate_ocr_response({
            'monto': 100,
            'referencia_bancaria': 'REF',
            'entidad': 'nequi',
            'confianza': 5.0,
        })
        assert result['confianza'] == 1.0

    def test_negative_monto(self):
        result = validate_ocr_response({
            'monto': -100,
            'referencia_bancaria': 'REF',
            'entidad': 'nequi',
        })
        # Negative monto is a non-critical validation warning, not a hard error
        # The validator still returns cleaned data but monto won't be in cleaned
        assert 'monto' not in result or 'error' in result
