import os
import base64
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User, Profile
from transactions.models import Transaction


def pytest_configure(config):
    """
    Se ejecuta ANTES de que Django cargue settings.
    Inyecta variables de entorno mínimas para que los tests corran
    sin ningún .env ni credenciales de producción.
    """
    # Clave AES-256 de exactamente 32 bytes — solo para tests, no es la de producción
    _test_key = base64.b64encode(b'test-key-32bytes-pytest-internal').decode()
    os.environ.setdefault('FIELD_ENCRYPTION_KEY', _test_key)

    # Celery en memoria — no requiere Redis ni django-celery-results en tests
    os.environ.setdefault('CELERY_BROKER_URL', 'memory://')
    os.environ.setdefault('CELERY_RESULT_BACKEND', 'cache+memory://')

    # Meta tokens vacíos — todos los tests los mockean o no los usan
    os.environ.setdefault('META_APP_SECRET', 'test-meta-secret')
    os.environ.setdefault('META_WEBHOOK_VERIFY_TOKEN', 'test-verify-token')
    os.environ.setdefault('META_ACCESS_TOKEN', '')
    os.environ.setdefault('META_PHONE_NUMBER_ID', '')


@pytest.fixture(autouse=True, scope='session')
def celery_eager_mode():
    """
    Fuerza ejecución síncrona de tasks Celery en todos los tests.
    Evita necesitar un broker Redis real durante la suite de tests.
    """
    from finanzas.celery import app as celery_app
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        broker_url='memory://',
        result_backend='cache+memory://',
    )


@pytest.fixture
def api_client():
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def sample_user(db):
    """Creates a user with profile (auto-created via signal)."""
    user = User.objects.create_user(
        username='+573001234567',
        phone_number='+573001234567',
        password='testpass123',
    )
    return user


@pytest.fixture
def sample_profile(sample_user):
    """Returns the auto-created profile, with financial data set."""
    profile = sample_user.profile
    profile.salario_mensual = '3000000'
    profile.presupuesto_mensual = '2000000'
    profile.dia_corte = 1
    profile.onboarding_completed = True
    profile.save()
    return profile


@pytest.fixture
def auth_tokens(sample_user):
    """Returns access and refresh tokens for sample_user."""
    refresh = RefreshToken.for_user(sample_user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


@pytest.fixture
def authenticated_client(api_client, auth_tokens):
    """APIClient already authenticated with sample_user's JWT."""
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_tokens['access']}")
    return api_client


@pytest.fixture
def sample_transaction(sample_user, db):
    """Creates a confirmed transaction for sample_user."""
    return Transaction.objects.create(
        user=sample_user,
        monto='150000',
        referencia_bancaria='REF-TEST-001',
        tipo='gasto',
        entidad='nequi',
        categoria='alimentacion',
        destinatario='Rappi',
        fecha_transaccion=timezone.now(),
        descripcion='Domicilio almuerzo',
        estado='confirmed',
        confianza_ia=0.95,
    )


@pytest.fixture
def second_transaction(sample_user, db):
    """A second transaction for list/filter tests."""
    return Transaction.objects.create(
        user=sample_user,
        monto='50000',
        referencia_bancaria='REF-TEST-002',
        tipo='ingreso',
        entidad='bancolombia',
        categoria='sin_categorizar',
        destinatario='Empresa SAS',
        fecha_transaccion=timezone.now(),
        descripcion='Pago freelance',
        estado='confirmed',
        confianza_ia=0.9,
    )
