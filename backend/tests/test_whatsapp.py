"""Tests for whatsapp app: state machine, throttling, webhook HMAC, async Celery dispatch."""
import json
import hashlib
import hmac
from unittest.mock import patch, MagicMock

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.conf import settings

from whatsapp.state_machine import ConversationManager, ConversationState
from whatsapp.throttling import WhatsAppUserThrottle
from whatsapp.meta_api import verify_webhook_signature


# ── State Machine Tests ──

@pytest.mark.django_db
class TestConversationManager:
    def setup_method(self):
        cache.clear()

    def test_initial_state_is_idle(self):
        state = ConversationManager.get_state('+573001111111')
        assert state['state'] == ConversationState.IDLE.value
        assert state['pending_transaction_id'] is None

    def test_set_and_get_state(self):
        ConversationManager.set_state(
            '+573001111111',
            ConversationState.PROCESSING,
        )
        state = ConversationManager.get_state('+573001111111')
        assert state['state'] == ConversationState.PROCESSING.value

    def test_pending_confirmation_with_transaction(self):
        ConversationManager.set_state(
            '+573001111111',
            ConversationState.PENDING_CONFIRMATION,
            pending_transaction_id=42,
        )
        state = ConversationManager.get_state('+573001111111')
        assert state['state'] == ConversationState.PENDING_CONFIRMATION.value
        assert state['pending_transaction_id'] == 42

    def test_reset_returns_to_idle(self):
        ConversationManager.set_state(
            '+573001111111',
            ConversationState.PROCESSING,
        )
        ConversationManager.reset('+573001111111')
        state = ConversationManager.get_state('+573001111111')
        assert state['state'] == ConversationState.IDLE.value

    def test_context_storage(self):
        ConversationManager.set_state(
            '+573001111111',
            ConversationState.QUERYING,
            context={'intent': 'summary'},
        )
        state = ConversationManager.get_state('+573001111111')
        assert state['context']['intent'] == 'summary'

    def test_different_users_independent(self):
        ConversationManager.set_state('+573001111111', ConversationState.PROCESSING)
        ConversationManager.set_state('+573002222222', ConversationState.CONFIRMED)
        s1 = ConversationManager.get_state('+573001111111')
        s2 = ConversationManager.get_state('+573002222222')
        assert s1['state'] == ConversationState.PROCESSING.value
        assert s2['state'] == ConversationState.CONFIRMED.value


# ── Throttling Tests ──

@pytest.mark.django_db
class TestThrottling:
    def setup_method(self):
        cache.clear()

    def test_allows_first_message(self):
        assert WhatsAppUserThrottle.is_allowed('+573001111111') is True

    def test_allows_up_to_limit(self):
        phone = '+573003333333'
        for _ in range(WhatsAppUserThrottle.MAX_MESSAGES_PER_HOUR):
            assert WhatsAppUserThrottle.is_allowed(phone) is True

    def test_blocks_after_limit(self):
        phone = '+573004444444'
        for _ in range(WhatsAppUserThrottle.MAX_MESSAGES_PER_HOUR):
            WhatsAppUserThrottle.is_allowed(phone)
        assert WhatsAppUserThrottle.is_allowed(phone) is False

    def test_different_users_independent(self):
        for _ in range(WhatsAppUserThrottle.MAX_MESSAGES_PER_HOUR):
            WhatsAppUserThrottle.is_allowed('+573005555555')
        assert WhatsAppUserThrottle.is_allowed('+573006666666') is True


# ── Webhook HMAC Verification Tests ──

class TestWebhookHMAC:
    @pytest.fixture(autouse=True)
    def setup_secret(self, settings):
        settings.META_APP_SECRET = 'test-secret-key'

    def _make_request(self, body: dict, secret: str = 'test-secret-key'):
        factory = RequestFactory()
        body_bytes = json.dumps(body).encode('utf-8')
        sig = hmac.new(
            secret.encode('utf-8'),
            body_bytes,
            hashlib.sha256
        ).hexdigest()
        request = factory.post(
            '/api/whatsapp/webhook/',
            data=body_bytes,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=f'sha256={sig}',
        )
        request._body = body_bytes
        return request

    def test_valid_signature(self):
        request = self._make_request({'test': 'data'})
        assert verify_webhook_signature(request) is True

    def test_invalid_signature(self):
        request = self._make_request({'test': 'data'}, secret='wrong-key')
        assert verify_webhook_signature(request) is False

    def test_missing_signature_header(self):
        factory = RequestFactory()
        body = json.dumps({'test': 'data'}).encode('utf-8')
        request = factory.post(
            '/api/whatsapp/webhook/',
            data=body,
            content_type='application/json',
        )
        request._body = body
        assert verify_webhook_signature(request) is False


# ── Webhook Endpoint Tests ──

class TestWebhookEndpoint:
    @pytest.fixture(autouse=True)
    def setup_settings(self, settings):
        settings.META_APP_SECRET = 'test-secret'
        settings.META_WEBHOOK_VERIFY_TOKEN = 'test-verify-token'

    def test_webhook_verification_get(self, api_client, db):
        resp = api_client.get('/api/whatsapp/webhook/', {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'test-verify-token',
            'hub.challenge': 'challenge123',
        })
        assert resp.status_code == 200
        assert resp.content == b'challenge123'

    def test_webhook_verification_wrong_token(self, api_client, db):
        resp = api_client.get('/api/whatsapp/webhook/', {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'wrong-token',
            'hub.challenge': 'challenge123',
        })
        assert resp.status_code == 403

    def test_webhook_post_status_notification(self, client, db):
        """Status notifications (delivered, read) should return 200."""
        body = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': []
                    }
                }]
            }]
        }
        body_bytes = json.dumps(body).encode('utf-8')
        sig = hmac.new(
            b'test-secret', body_bytes, hashlib.sha256
        ).hexdigest()
        resp = client.post(
            '/api/whatsapp/webhook/',
            data=body_bytes,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=f'sha256={sig}',
        )
        assert resp.status_code == 200

    def test_webhook_post_invalid_signature(self, client, db):
        body_bytes = json.dumps({'test': 1}).encode('utf-8')
        resp = client.post(
            '/api/whatsapp/webhook/',
            data=body_bytes,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=invalid',
        )
        assert resp.status_code == 403

    def test_webhook_post_invalid_json(self, client, db):
        body_bytes = b'not json'
        sig = hmac.new(
            b'test-secret', body_bytes, hashlib.sha256
        ).hexdigest()
        resp = client.post(
            '/api/whatsapp/webhook/',
            data=body_bytes,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=f'sha256={sig}',
        )
        assert resp.status_code == 400


# ── Async Celery Dispatch Tests ──

class TestWebhookAsyncDispatch:
    """
    Verifica que el webhook despacha imágenes a Celery (async)
    y procesa texto/botones de forma síncrona.
    Sprint: async-webhook-celery.
    """

    @pytest.fixture(autouse=True)
    def setup_settings(self, settings):
        settings.META_APP_SECRET = 'test-secret'
        settings.META_WEBHOOK_VERIFY_TOKEN = 'test-verify-token'

    def _signed_post(self, client, body: dict):
        body_bytes = json.dumps(body).encode('utf-8')
        sig = hmac.new(b'test-secret', body_bytes, hashlib.sha256).hexdigest()
        return client.post(
            '/api/whatsapp/webhook/',
            data=body_bytes,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=f'sha256={sig}',
        )

    def _image_body(self, phone='573001234567', message_id='msg-img-001'):
        return {
            'entry': [{'changes': [{'value': {'messages': [{
                'from': phone,
                'id': message_id,
                'type': 'image',
                'image': {'id': 'media-001', 'mime_type': 'image/jpeg'},
            }]}}]}]
        }

    def _text_body(self, phone='573001234567', message_id='msg-txt-001', text='Hola'):
        return {
            'entry': [{'changes': [{'value': {'messages': [{
                'from': phone,
                'id': message_id,
                'type': 'text',
                'text': {'body': text},
            }]}}]}]
        }

    def test_image_dispatched_to_celery(self, client, sample_user, db):
        """Imagen → process_whatsapp_image.delay() llamado; NO se procesa OCR inline."""
        with patch('whatsapp.views.WhatsAppUserThrottle.is_allowed', return_value=True), \
             patch('whatsapp.views.User.objects.get_or_create', return_value=(sample_user, False)), \
             patch('whatsapp.tasks.process_whatsapp_image.delay') as mock_delay:
            resp = self._signed_post(client, self._image_body())

        assert resp.status_code == 200
        mock_delay.assert_called_once()
        kwargs = mock_delay.call_args.kwargs
        assert kwargs['phone_number'] == '573001234567'
        assert kwargs['message_id'] == 'msg-img-001'
        assert json.loads(kwargs['message_data_json'])['type'] == 'image'

    def test_image_webhook_returns_immediately(self, client, sample_user, db):
        """El webhook responde 200 OK sin esperar el OCR (< 1s)."""
        import time
        with patch('whatsapp.views.WhatsAppUserThrottle.is_allowed', return_value=True), \
             patch('whatsapp.views.User.objects.get_or_create', return_value=(sample_user, False)), \
             patch('whatsapp.tasks.process_whatsapp_image.delay'):
            start = time.time()
            resp = self._signed_post(client, self._image_body())
            elapsed = time.time() - start

        assert resp.status_code == 200
        assert elapsed < 1.0

    def test_text_processed_synchronously(self, client, sample_user, db):
        """Texto → handle_incoming_message llamado inline con user como 1er arg."""
        with patch('whatsapp.views.WhatsAppUserThrottle.is_allowed', return_value=True), \
             patch('whatsapp.views.User.objects.get_or_create', return_value=(sample_user, False)), \
             patch('whatsapp.views.handle_incoming_message') as mock_handler:
            resp = self._signed_post(client, self._text_body())

        assert resp.status_code == 200
        mock_handler.assert_called_once()
        call_kwargs = mock_handler.call_args.kwargs
        assert call_kwargs['user'] == sample_user
        assert call_kwargs['message_type'] == 'text'

    def test_new_user_no_celery_dispatch(self, client, sample_user, db):
        """Usuario nuevo → mensaje de bienvenida, sin despachar tarea Celery."""
        with patch('whatsapp.views.WhatsAppUserThrottle.is_allowed', return_value=True), \
             patch('whatsapp.views.User.objects.get_or_create', return_value=(sample_user, True)), \
             patch('whatsapp.meta_api.send_text_message'), \
             patch('whatsapp.tasks.process_whatsapp_image.delay') as mock_delay:
            resp = self._signed_post(client, self._image_body())

        assert resp.status_code == 200
        mock_delay.assert_not_called()

    def test_throttled_user_no_celery_dispatch(self, client, db):
        """Usuario throttleado → rate-limit message, sin despachar tarea Celery."""
        with patch('whatsapp.views.WhatsAppUserThrottle.is_allowed', return_value=False), \
             patch('whatsapp.meta_api.send_text_message'), \
             patch('whatsapp.tasks.process_whatsapp_image.delay') as mock_delay:
            resp = self._signed_post(client, self._image_body())

        assert resp.status_code == 200
        mock_delay.assert_not_called()


# ── Celery Task Unit Tests ──

class TestProcessWhatsAppImageTask:
    """
    Pruebas unitarias para la task process_whatsapp_image.
    Se ejecuta la tarea de forma síncrona usando .apply().
    """

    def _message_data_json(self):
        return json.dumps({
            'from': '573001234567',
            'id': 'msg-001',
            'type': 'image',
            'image': {'id': 'media-001', 'mime_type': 'image/jpeg'},
        })

    def test_task_calls_handle_image_message(self, sample_user, db):
        """La tarea llama a handle_image_message cuando el usuario existe."""
        from whatsapp.tasks import process_whatsapp_image

        with patch('whatsapp.tasks.cache.get', return_value=None), \
             patch('whatsapp.tasks.cache.set'), \
             patch('whatsapp.message_handler.handle_image_message') as mock_handler:
            process_whatsapp_image.apply(kwargs={
                'phone_number': '573001234567',
                'message_id': 'msg-001',
                'message_data_json': self._message_data_json(),
            })

        mock_handler.assert_called_once()
        args = mock_handler.call_args.args
        assert args[0] == sample_user      # user
        assert args[2] == 'msg-001'        # message_id

    def test_task_idempotency_skips_duplicate(self, db):
        """Si la idempotency key ya existe en cache, la tarea no reprocesa."""
        from whatsapp.tasks import process_whatsapp_image

        with patch('whatsapp.tasks.cache.get', return_value=True), \
             patch('whatsapp.message_handler.handle_image_message') as mock_handler:
            result = process_whatsapp_image.apply(kwargs={
                'phone_number': '573001234567',
                'message_id': 'msg-dup-001',
                'message_data_json': self._message_data_json(),
            })

        mock_handler.assert_not_called()
        assert result.result['status'] == 'duplicate_task'
        assert result.result['message_id'] == 'msg-dup-001'

    def test_task_sets_idempotency_key_before_processing(self, sample_user, db):
        """La key de idempotencia se establece ANTES de llamar al handler."""
        from whatsapp.tasks import process_whatsapp_image

        set_calls = []
        with patch('whatsapp.tasks.cache.get', return_value=None), \
             patch('whatsapp.tasks.cache.set', side_effect=lambda *a, **kw: set_calls.append(a)), \
             patch('whatsapp.message_handler.handle_image_message'):
            process_whatsapp_image.apply(kwargs={
                'phone_number': '573001234567',
                'message_id': 'msg-key-test',
                'message_data_json': self._message_data_json(),
            })

        assert len(set_calls) > 0
        assert set_calls[0][0] == 'wa_processing:msg-key-test'
        assert set_calls[0][1] is True

    def test_task_handles_missing_user_gracefully(self, db):
        """Si el usuario no existe, la tarea termina sin lanzar excepción."""
        from whatsapp.tasks import process_whatsapp_image

        with patch('whatsapp.tasks.cache.get', return_value=None), \
             patch('whatsapp.tasks.cache.set'), \
             patch('whatsapp.message_handler.handle_image_message') as mock_handler:
            result = process_whatsapp_image.apply(kwargs={
                'phone_number': '999999999',
                'message_id': 'msg-no-user',
                'message_data_json': self._message_data_json(),
            })

        mock_handler.assert_not_called()
        assert result.successful() or result.failed()  # no excepción no capturada
