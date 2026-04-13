"""Tests for whatsapp app: state machine, throttling, webhook HMAC."""
import json
import hashlib
import hmac

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
