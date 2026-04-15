"""Tests for transactions app: models, CRUD endpoints, dashboard summary."""
import base64
import pytest
from decimal import Decimal
from django.utils import timezone

from transactions.models import Transaction, TransactionImage


# ── Model Tests ──

class TestTransactionModel:
    def test_create_transaction(self, sample_transaction):
        assert sample_transaction.pk is not None
        assert sample_transaction.tipo == 'gasto'
        assert sample_transaction.entidad == 'nequi'

    def test_encrypted_monto_roundtrip(self, sample_transaction):
        """Monto is encrypted in DB but readable via model."""
        sample_transaction.refresh_from_db()
        assert sample_transaction.get_monto_decimal() == Decimal('150000')

    def test_referencia_unique(self, sample_transaction, sample_user):
        with pytest.raises(Exception):
            Transaction.objects.create(
                user=sample_user,
                monto='99999',
                referencia_bancaria='REF-TEST-001',  # duplicate
                tipo='gasto',
                entidad='nequi',
                fecha_transaccion=timezone.now(),
            )

    def test_str_representation(self, sample_transaction):
        s = str(sample_transaction)
        assert 'gasto' in s
        assert 'nequi' in s
        assert 'REF-TEST-001' in s

    def test_get_monto_decimal_error(self, sample_user, db):
        t = Transaction.objects.create(
            user=sample_user,
            monto='not-a-number',
            referencia_bancaria='REF-BAD-MONTO',
            tipo='gasto',
            entidad='otro',
            fecha_transaccion=timezone.now(),
        )
        t.refresh_from_db()
        # The encrypted value won't decrypt to a valid decimal
        # get_monto_decimal should handle gracefully
        result = t.get_monto_decimal()
        assert isinstance(result, Decimal)

    def test_ordering(self, sample_user, db):
        t1 = Transaction.objects.create(
            user=sample_user,
            monto='100',
            referencia_bancaria='REF-ORDER-1',
            tipo='gasto', entidad='nequi',
            fecha_transaccion=timezone.now().replace(day=1),
        )
        t2 = Transaction.objects.create(
            user=sample_user,
            monto='200',
            referencia_bancaria='REF-ORDER-2',
            tipo='gasto', entidad='nequi',
            fecha_transaccion=timezone.now(),
        )
        txs = list(Transaction.objects.filter(user=sample_user))
        assert txs[0].pk == t2.pk  # newer first

    def test_choices(self):
        assert 'gasto' in dict(Transaction.TipoTransaccion.choices)
        assert 'nequi' in dict(Transaction.EntidadBancaria.choices)
        assert 'pending' in dict(Transaction.EstadoTransaccion.choices)


# ── Transaction List Endpoint ──

class TestTransactionList:
    def test_list_empty(self, authenticated_client):
        resp = authenticated_client.get('/api/transactions/')
        assert resp.status_code == 200
        assert resp.data['count'] == 0

    def test_list_with_data(self, authenticated_client, sample_transaction):
        resp = authenticated_client.get('/api/transactions/')
        assert resp.status_code == 200
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['categoria'] == 'alimentacion'

    def test_filter_by_tipo(self, authenticated_client, sample_transaction, second_transaction):
        resp = authenticated_client.get('/api/transactions/?tipo=gasto')
        assert resp.status_code == 200
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['tipo'] == 'gasto'

    def test_filter_by_estado(self, authenticated_client, sample_transaction):
        resp = authenticated_client.get('/api/transactions/?estado=confirmed')
        assert resp.data['count'] == 1

    def test_filter_by_categoria(self, authenticated_client, sample_transaction):
        resp = authenticated_client.get('/api/transactions/?categoria=alimentacion')
        assert resp.data['count'] == 1

    def test_list_unauthenticated(self, api_client):
        resp = api_client.get('/api/transactions/')
        assert resp.status_code == 401

    def test_user_isolation(self, authenticated_client, db):
        """User can't see another user's transactions."""
        other = User.objects.create_user(
            username='+573009998888', phone_number='+573009998888', password='p'
        )
        Transaction.objects.create(
            user=other, monto='1000', referencia_bancaria='REF-OTHER',
            tipo='gasto', entidad='nequi', fecha_transaccion=timezone.now(),
        )
        resp = authenticated_client.get('/api/transactions/')
        assert resp.data['count'] == 0


# ── Transaction Detail Endpoint ──

class TestTransactionDetail:
    def test_get_detail(self, authenticated_client, sample_transaction):
        resp = authenticated_client.get(f'/api/transactions/{sample_transaction.pk}/')
        assert resp.status_code == 200
        assert resp.data['id'] == sample_transaction.pk
        assert 'monto_display' in resp.data

    def test_patch_categoria(self, authenticated_client, sample_transaction):
        resp = authenticated_client.patch(
            f'/api/transactions/{sample_transaction.pk}/',
            {'categoria': 'transporte'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['categoria'] == 'transporte'

    def test_patch_disallowed_field(self, authenticated_client, sample_transaction):
        """Fields like monto and referencia_bancaria should not be patchable."""
        resp = authenticated_client.patch(
            f'/api/transactions/{sample_transaction.pk}/',
            {'tipo': 'ingreso'},
            format='json',
        )
        # The view filters to allowed_fields only, so 'tipo' is ignored
        sample_transaction.refresh_from_db()
        assert sample_transaction.tipo == 'gasto'

    def test_detail_not_found(self, authenticated_client):
        resp = authenticated_client.get('/api/transactions/99999/')
        assert resp.status_code == 404

    def test_detail_other_user(self, authenticated_client, db):
        other = User.objects.create_user(
            username='+573007777777', phone_number='+573007777777', password='p'
        )
        t = Transaction.objects.create(
            user=other, monto='100', referencia_bancaria='REF-OTHER-2',
            tipo='gasto', entidad='nequi', fecha_transaccion=timezone.now(),
        )
        resp = authenticated_client.get(f'/api/transactions/{t.pk}/')
        assert resp.status_code == 404


# ── Dashboard Summary Endpoint ──

class TestDashboardSummary:
    def test_summary_empty(self, authenticated_client, sample_profile):
        resp = authenticated_client.get('/api/dashboard/summary/')
        assert resp.status_code == 200
        assert resp.data['total_gastos'] == '0'
        assert resp.data['transacciones_count'] == 0
        assert 'salario' in resp.data
        assert 'progreso_presupuesto' in resp.data

    def test_summary_with_transactions(
        self, authenticated_client, sample_profile, sample_transaction, second_transaction
    ):
        resp = authenticated_client.get('/api/dashboard/summary/')
        assert resp.status_code == 200
        assert Decimal(resp.data['total_gastos']) == Decimal('150000')
        assert Decimal(resp.data['total_ingresos']) == Decimal('50000')
        assert resp.data['transacciones_count'] == 2
        assert 'alimentacion' in resp.data['gastos_por_categoria']

    def test_summary_unauthenticated(self, api_client):
        resp = api_client.get('/api/dashboard/summary/')
        assert resp.status_code == 401

    def test_progreso_presupuesto(self, authenticated_client, sample_profile, sample_transaction):
        resp = authenticated_client.get('/api/dashboard/summary/')
        # 150000 / 2000000 * 100 = 7.5%
        assert resp.data['progreso_presupuesto'] == pytest.approx(7.5)

    def test_ahorro_real(self, authenticated_client, sample_profile, sample_transaction):
        resp = authenticated_client.get('/api/dashboard/summary/')
        # 3000000 - 150000 + 0 = 2850000
        assert Decimal(resp.data['ahorro_real']) == Decimal('2850000')


# Import needed for user_isolation test
from users.models import User


class TestEncryptedTransactions:
    def test_create_encrypted_transaction(self, authenticated_client):
        payload = {
            'ciphertext': base64.b64encode(b'cipher-data').decode('utf-8'),
            'iv': base64.b64encode(b'123456789012').decode('utf-8'),
            'salt': base64.b64encode(b'1234567890abcdef').decode('utf-8'),
            'crypto_version': 1,
        }
        resp = authenticated_client.post('/api/encrypted-transactions/', payload, format='json')
        assert resp.status_code == 201
        assert resp.data['ciphertext'] == payload['ciphertext']
        assert resp.data['iv'] == payload['iv']
        assert resp.data['salt'] == payload['salt']

    def test_create_encrypted_transaction_invalid_iv(self, authenticated_client):
        payload = {
            'ciphertext': base64.b64encode(b'cipher-data').decode('utf-8'),
            'iv': base64.b64encode(b'short').decode('utf-8'),
            'salt': base64.b64encode(b'1234567890abcdef').decode('utf-8'),
        }
        resp = authenticated_client.post('/api/encrypted-transactions/', payload, format='json')
        assert resp.status_code == 400
        assert 'iv' in resp.data

    def test_list_encrypted_transactions(self, authenticated_client):
        payload = {
            'ciphertext': base64.b64encode(b'cipher-data').decode('utf-8'),
            'iv': base64.b64encode(b'123456789012').decode('utf-8'),
            'salt': base64.b64encode(b'1234567890abcdef').decode('utf-8'),
        }
        create_resp = authenticated_client.post('/api/encrypted-transactions/', payload, format='json')
        assert create_resp.status_code == 201

        resp = authenticated_client.get('/api/encrypted-transactions/')
        assert resp.status_code == 200
        assert resp.data['count'] >= 1
        assert resp.data['results'][0]['id']
