import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User, Profile
from transactions.models import Transaction


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
