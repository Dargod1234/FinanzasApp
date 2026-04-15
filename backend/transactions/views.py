from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import EncryptedTransaction, Transaction
from .serializers import (
    EncryptedTransactionCreateSerializer,
    EncryptedTransactionListSerializer,
    TransactionSerializer,
)


class TransactionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def encrypted_transaction_list_create(request):
    """Almacen y listado ciego de transacciones cifradas (E2EE)."""
    if request.method == 'POST':
        serializer = EncryptedTransactionCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        output = EncryptedTransactionListSerializer(obj)
        return Response(output.data, status=status.HTTP_201_CREATED)

    encrypted_qs = EncryptedTransaction.objects.filter(user=request.user)
    paginator = TransactionPagination()
    page = paginator.paginate_queryset(encrypted_qs, request)
    serializer = EncryptedTransactionListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_list(request):
    """Listar transacciones del usuario autenticado (paginadas)."""
    queryset = Transaction.objects.filter(user=request.user)

    # Filtros opcionales
    estado = request.query_params.get('estado')
    if estado:
        queryset = queryset.filter(estado=estado)

    categoria = request.query_params.get('categoria')
    if categoria:
        queryset = queryset.filter(categoria=categoria)

    tipo = request.query_params.get('tipo')
    if tipo:
        queryset = queryset.filter(tipo=tipo)

    paginator = TransactionPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = TransactionSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def transaction_detail(request, pk):
    """Detalle o actualización parcial de una transacción."""
    try:
        transaction = Transaction.objects.get(pk=pk, user=request.user)
    except Transaction.DoesNotExist:
        return Response(
            {'detail': 'Transacción no encontrada.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        allowed_fields = {'categoria', 'estado', 'descripcion'}
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        serializer = TransactionSerializer(transaction, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_image(request, pk):
    """Obtener URL de la imagen del comprobante."""
    try:
        transaction = Transaction.objects.get(pk=pk, user=request.user)
    except Transaction.DoesNotExist:
        return Response(
            {'detail': 'Transacción no encontrada.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if not hasattr(transaction, 'image') or not transaction.image:
        return Response(
            {'detail': 'Esta transacción no tiene imagen.'},
            status=status.HTTP_404_NOT_FOUND
        )

    img = transaction.image
    return Response({
        'image_url': img.image.url,
        'content_type': img.content_type,
        'file_size': img.file_size,
        'uploaded_at': img.uploaded_at.isoformat(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    Retorna KPIs del ciclo actual:
    - Ahorro real (salario - gastos)
    - Progreso vs presupuesto
    - Gasto por categoría
    """
    user = request.user
    profile = user.profile
    now = timezone.now()

    # Determinar inicio del ciclo según dia_corte
    dia_corte = profile.dia_corte
    if now.day >= dia_corte:
        cycle_start = now.replace(day=dia_corte, hour=0, minute=0, second=0, microsecond=0)
    else:
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        cycle_start = now.replace(
            year=prev_year, month=prev_month, day=dia_corte,
            hour=0, minute=0, second=0, microsecond=0
        )

    # Transacciones confirmadas del ciclo actual
    transactions = Transaction.objects.filter(
        user=user,
        estado='confirmed',
        fecha_transaccion__gte=cycle_start,
        fecha_transaccion__lte=now,
    )

    # Calcular totales (los montos están encriptados, necesitamos desencriptar)
    total_gastos = Decimal('0')
    total_ingresos = Decimal('0')
    categorias = {}

    for t in transactions:
        monto = t.get_monto_decimal()
        if t.tipo == 'gasto':
            total_gastos += monto
            cat = t.categoria or 'sin_categorizar'
            categorias[cat] = categorias.get(cat, Decimal('0')) + monto
        elif t.tipo == 'ingreso':
            total_ingresos += monto

    salario = profile.get_salario_decimal()
    presupuesto = profile.get_presupuesto_decimal()
    ahorro_real = salario - total_gastos + total_ingresos

    return Response({
        'ciclo': {
            'inicio': cycle_start.isoformat(),
            'fin': now.isoformat(),
        },
        'salario': str(salario),
        'presupuesto': str(presupuesto),
        'total_gastos': str(total_gastos),
        'total_ingresos': str(total_ingresos),
        'ahorro_real': str(ahorro_real),
        'progreso_presupuesto': (
            float(total_gastos / presupuesto * 100) if presupuesto > 0 else 0
        ),
        'gastos_por_categoria': {k: str(v) for k, v in categorias.items()},
        'transacciones_count': transactions.count(),
    })
