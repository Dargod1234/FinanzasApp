"""Tests for users app: models, signals, auth endpoints, profile endpoint."""
import pytest
from django.core.cache import cache
from users.models import User, Profile
from users.otp_service import OTPService


# ── Model Tests ──

class TestUserModel:
    def test_create_user(self, db):
        user = User.objects.create_user(
            username='+573009999999',
            phone_number='+573009999999',
            password='pass123',
        )
        assert user.phone_number == '+573009999999'
        assert user.USERNAME_FIELD == 'phone_number'
        assert str(user) == '+573009999999'

    def test_phone_number_unique(self, sample_user, db):
        with pytest.raises(Exception):
            User.objects.create_user(
                username='dup',
                phone_number='+573001234567',
                password='pass',
            )

    def test_str_representation(self, sample_user):
        assert str(sample_user) == '+573001234567'


class TestProfileSignal:
    def test_profile_auto_created(self, sample_user):
        assert hasattr(sample_user, 'profile')
        assert isinstance(sample_user.profile, Profile)

    def test_profile_defaults(self, sample_user):
        p = sample_user.profile
        assert p.dia_corte == 1
        assert p.onboarding_completed is False
        assert p.salario_mensual is None or p.salario_mensual == ''

    def test_profile_str(self, sample_user):
        assert 'Profile' in str(sample_user.profile)

    def test_salario_decimal(self, sample_profile):
        from decimal import Decimal
        assert sample_profile.get_salario_decimal() == Decimal('3000000')

    def test_presupuesto_decimal(self, sample_profile):
        from decimal import Decimal
        assert sample_profile.get_presupuesto_decimal() == Decimal('2000000')

    def test_zero_when_no_salario(self, sample_user):
        from decimal import Decimal
        p = sample_user.profile
        p.salario_mensual = None
        assert p.get_salario_decimal() == Decimal('0')


# ── OTP Service Tests ──

@pytest.mark.django_db
class TestOTPService:
    def setup_method(self):
        cache.clear()

    def test_generate_otp_returns_6_digits(self):
        otp = OTPService.generate_otp('+573001234567')
        assert len(otp) == 6
        assert otp.isdigit()

    def test_verify_valid_otp(self):
        otp = OTPService.generate_otp('+573001234567')
        assert OTPService.verify_otp('+573001234567', otp) is True

    def test_verify_wrong_code(self):
        OTPService.generate_otp('+573001234567')
        assert OTPService.verify_otp('+573001234567', '000000') is False

    def test_otp_consumed_after_use(self):
        otp = OTPService.generate_otp('+573001234567')
        OTPService.verify_otp('+573001234567', otp)
        assert OTPService.verify_otp('+573001234567', otp) is False

    def test_max_attempts(self):
        otp = OTPService.generate_otp('+573001234567')
        for _ in range(OTPService.MAX_ATTEMPTS):
            OTPService.verify_otp('+573001234567', 'wrong1')
        assert OTPService.verify_otp('+573001234567', otp) is False

    def test_verify_nonexistent_phone(self):
        assert OTPService.verify_otp('+573000000000', '123456') is False


# ── Auth Endpoint Tests ──

class TestRequestOTP:
    def test_request_otp_success(self, api_client, db):
        resp = api_client.post('/api/auth/phone/request-otp/', {
            'phone_number': '+573001234567'
        })
        assert resp.status_code == 200
        assert 'debug_otp' in resp.data

    def test_request_otp_invalid_phone(self, api_client, db):
        resp = api_client.post('/api/auth/phone/request-otp/', {
            'phone_number': '123'
        })
        assert resp.status_code == 400

    def test_request_otp_empty_phone(self, api_client, db):
        resp = api_client.post('/api/auth/phone/request-otp/', {})
        assert resp.status_code == 400


class TestPhoneAuth:
    def test_full_auth_flow(self, api_client, db):
        cache.clear()
        phone = '+573005551234'
        # Step 1: request OTP
        resp = api_client.post('/api/auth/phone/request-otp/', {
            'phone_number': phone
        })
        otp = resp.data['debug_otp']

        # Step 2: verify OTP
        resp = api_client.post('/api/auth/phone/', {
            'phone_number': phone,
            'otp_code': otp,
        })
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh' in resp.data
        assert resp.data['is_new_user'] is True

    def test_auth_existing_user(self, api_client, sample_user):
        cache.clear()
        phone = sample_user.phone_number
        resp = api_client.post('/api/auth/phone/request-otp/', {
            'phone_number': phone
        })
        otp = resp.data['debug_otp']
        resp = api_client.post('/api/auth/phone/', {
            'phone_number': phone,
            'otp_code': otp,
        })
        assert resp.status_code == 200
        assert resp.data['is_new_user'] is False

    def test_auth_wrong_otp(self, api_client, db):
        cache.clear()
        api_client.post('/api/auth/phone/request-otp/', {
            'phone_number': '+573005559999'
        })
        resp = api_client.post('/api/auth/phone/', {
            'phone_number': '+573005559999',
            'otp_code': '000000',
        })
        assert resp.status_code == 400

    def test_auth_invalid_phone_format(self, api_client, db):
        resp = api_client.post('/api/auth/phone/', {
            'phone_number': 'bad',
            'otp_code': '123456',
        })
        assert resp.status_code == 400


# ── Profile Endpoint Tests ──

class TestProfileEndpoint:
    def test_get_profile(self, authenticated_client, sample_profile):
        resp = authenticated_client.get('/api/auth/profile/')
        assert resp.status_code == 200
        assert 'salario_mensual' in resp.data
        assert 'dia_corte' in resp.data

    def test_patch_profile(self, authenticated_client, sample_user):
        resp = authenticated_client.patch('/api/auth/profile/', {
            'salario_mensual': '5000000',
            'presupuesto_mensual': '3000000',
            'dia_corte': 15,
            'onboarding_completed': True,
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['dia_corte'] == 15
        assert resp.data['onboarding_completed'] is True

    def test_profile_unauthenticated(self, api_client):
        resp = api_client.get('/api/auth/profile/')
        assert resp.status_code == 401


# ── Token Refresh Tests ──

class TestTokenRefresh:
    def test_refresh_token(self, api_client, auth_tokens):
        resp = api_client.post('/api/auth/token/refresh/', {
            'refresh': auth_tokens['refresh']
        })
        assert resp.status_code == 200
        assert 'access' in resp.data

    def test_refresh_invalid_token(self, api_client, db):
        resp = api_client.post('/api/auth/token/refresh/', {
            'refresh': 'invalid-token'
        })
        assert resp.status_code == 401
