import uuid
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import EncryptedTransaction, Transaction, TransactionImage, UserCategory
from .serializers import (
    EncryptedTransactionCreateSerializer,
    EncryptedTransactionListSerializer,
    TransactionSerializer,
    UserCategorySerializer,
)

APP_LIMIT_FREE = 15  # transacciones/mes creadas desde la app (plan free)


class TransactionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ── Helpers ──────────────────────────────────────────────────────────────────

def _check_app_limit(user) -> dict:
    """Devuelve estado del límite freemium para creaciones desde la app."""
    plan = getattr(user.profile, 'plan', 'free')
    if plan == 'premium':
        return {'allowed': True, 'used': 0, 'limit': None, 'plan': 'premium'}
    now = timezone.now()
    used = Transaction.objects.filter(
        user=user,
        whatsapp_message_id__isnull=True,
        created_at__year=now.year,
        created_at__month=now.month,
    ).count()
    return {
        'allowed': used < APP_LIMIT_FREE,
        'used': used,
        'limit': APP_LIMIT_FREE,
        'plan': 'free',
    }


def _cycle_start(profile, now):
    """Calcula el inicio del ciclo financiero actual."""
    dia_corte = profile.dia_corte
    if now.day >= dia_corte:
        return now.replace(day=dia_corte, hour=0, minute=0, second=0, microsecond=0)
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    return now.replace(
        year=prev_year, month=prev_month, day=dia_corte,
        hour=0, minute=0, second=0, microsecond=0,
    )


# ── Encrypted transactions ────────────────────────────────────────────────────

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


# ── Transactions ──────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def transaction_list(request):
    """
    GET  — Lista transacciones paginadas con filtros opcionales.
    POST — Crea transacción manual (sujeta a límite freemium).
    """
    if request.method == 'POST':
        # Freemium gate
        limit_status = _check_app_limit(request.user)
        if not limit_status['allowed']:
            return Response(
                {
                    'error': 'limit_reached',
                    'detail': f"Has alcanzado el límite de {APP_LIMIT_FREE} registros/mes en el plan gratuito.",
                    'used': limit_status['used'],
                    'limit': limit_status['limit'],
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        data = request.data
        try:
            monto_raw = int(data.get('monto', 0))
            if monto_raw <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            return Response({'detail': 'El monto debe ser un número entero positivo.'}, status=400)

        tipo = data.get('tipo', 'gasto')
        if tipo not in ('gasto', 'ingreso', 'transferencia_propia'):
            return Response({'detail': 'Tipo inválido.'}, status=400)

        fecha_raw = data.get('fecha_transaccion')
        if fecha_raw:
            from django.utils.dateparse import parse_datetime, parse_date
            fecha = parse_datetime(fecha_raw) or parse_date(fecha_raw)
            if fecha is None:
                return Response({'detail': 'Fecha inválida.'}, status=400)
            if hasattr(fecha, 'date'):
                fecha_dt = fecha if hasattr(fecha, 'hour') else timezone.make_aware(
                    fecha.replace(hour=12, minute=0, second=0)
                )
            else:
                from datetime import datetime
                fecha_dt = timezone.make_aware(datetime.combine(fecha, datetime.min.time().replace(hour=12)))
        else:
            fecha_dt = timezone.now()

        referencia = data.get('referencia_bancaria') or f"manual-{uuid.uuid4().hex[:16]}"

        tx = Transaction.objects.create(
            user=request.user,
            monto=str(monto_raw),
            referencia_bancaria=referencia,
            tipo=tipo,
            entidad=data.get('entidad', 'otro'),
            categoria=data.get('categoria', 'sin_categorizar'),
            destinatario=data.get('destinatario', ''),
            fecha_transaccion=fecha_dt,
            descripcion=data.get('descripcion', ''),
            estado='confirmed',
            confianza_ia=1.0,
            whatsapp_message_id=None,
        )
        serializer = TransactionSerializer(tx)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # GET
    queryset = Transaction.objects.filter(user=request.user)
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


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def transaction_detail(request, pk):
    """Detalle, actualización parcial o eliminación de una transacción."""
    try:
        transaction = Transaction.objects.get(pk=pk, user=request.user)
    except Transaction.DoesNotExist:
        return Response({'detail': 'Transacción no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)

    if request.method == 'DELETE':
        transaction.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH — campos editables por el usuario
    allowed_fields = {'categoria', 'estado', 'descripcion', 'tipo', 'entidad', 'destinatario', 'fecha_transaccion'}
    data = {k: v for k, v in request.data.items() if k in allowed_fields}

    # Monto es encriptado, se maneja fuera del serializer
    monto_raw = request.data.get('monto')
    if monto_raw is not None:
        try:
            monto_int = int(monto_raw)
            if monto_int <= 0:
                raise ValueError()
            transaction.monto = str(monto_int)
        except (TypeError, ValueError):
            return Response({'detail': 'El monto debe ser un entero positivo.'}, status=400)

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
        return Response({'detail': 'Transacción no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if not hasattr(transaction, 'image') or not transaction.image:
        return Response({'detail': 'Esta transacción no tiene imagen.'}, status=status.HTTP_404_NOT_FOUND)

    img = transaction.image
    return Response({
        'image_url': img.image.url,
        'content_type': img.content_type,
        'file_size': img.file_size,
        'uploaded_at': img.uploaded_at.isoformat(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transaction_upload_image(request):
    """
    POST /api/transactions/upload/
    Recibe un comprobante (multipart image), lo procesa con OCR y crea la transacción.
    Sujeto a límite freemium.
    """
    limit_status = _check_app_limit(request.user)
    if not limit_status['allowed']:
        return Response(
            {
                'error': 'limit_reached',
                'detail': f"Has alcanzado el límite de {APP_LIMIT_FREE} registros/mes en el plan gratuito.",
                'used': limit_status['used'],
                'limit': limit_status['limit'],
            },
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )

    image_file = request.FILES.get('image')
    if not image_file:
        return Response({'detail': 'Se requiere el campo "image".'}, status=400)

    image_bytes = image_file.read()
    mime_type = image_file.content_type or 'image/jpeg'

    from core.services.ocr_pipeline import process_receipt_image
    result = process_receipt_image(
        user=request.user,
        image_bytes=image_bytes,
        mime_type=mime_type,
        whatsapp_message_id=None,
    )

    # Pipeline errors (low_quality, not_a_receipt, service_unavailable)
    if 'error' in result:
        return Response({'detail': result.get('message', result['error'])}, status=422)

    # result from TransactionService.create_from_ocr:
    # {'status': 'created'|'duplicate', 'transaction': <Transaction instance>}
    tx_obj = result.get('transaction')

    if result.get('status') == 'duplicate':
        if tx_obj:
            serializer = TransactionSerializer(tx_obj)
            return Response(
                {'detail': result.get('message', 'Comprobante duplicado.'), 'transaction': serializer.data},
                status=409,
            )
        return Response({'detail': 'Comprobante duplicado.'}, status=409)

    if tx_obj:
        # Guardar imagen asociada al comprobante
        try:
            TransactionImage.objects.get_or_create(
                transaction=tx_obj,
                defaults={
                    'image': image_file,
                    'content_type': mime_type,
                    'file_size': len(image_bytes),
                },
            )
        except Exception:
            pass  # La imagen es opcional, no bloquea la respuesta
        serializer = TransactionSerializer(tx_obj)
        return Response({'transaction': serializer.data}, status=status.HTTP_201_CREATED)

    return Response({'detail': 'No se pudo procesar el comprobante.'}, status=422)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parse_voice_transaction(request):
    """
    POST /api/transactions/parse-voice/
    Body: { "text": "Gasto de 50 mil en almuerzo hoy" }
    Retorna los campos parseados. NO crea la transacción — el front la crea tras revisión.
    """
    text = (request.data.get('text') or '').strip()
    if not text:
        return Response({'detail': 'Se requiere el campo "text".'}, status=400)

    from core.services.voice_parser import parse_voice_text
    parsed = parse_voice_text(text)
    return Response(parsed)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_status(request):
    """
    GET /api/plan/status/
    Retorna el plan, uso y límite mensual del usuario.
    """
    return Response(_check_app_limit(request.user))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    Retorna KPIs del ciclo actual + transacciones registradas fuera del ciclo.
    """
    user = request.user
    profile = user.profile
    now = timezone.now()
    cs = _cycle_start(profile, now)

    # Transacciones del ciclo actual
    active_transactions = Transaction.objects.filter(
        user=user,
        estado__in=['confirmed', 'pending', 'needs_review'],
        fecha_transaccion__gte=cs,
        fecha_transaccion__lte=now,
    )

    total_gastos = Decimal('0')
    total_ingresos = Decimal('0')
    categorias = {}

    for t in active_transactions:
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
    confirmed_count = active_transactions.filter(estado='confirmed').count()

    # Transacciones registradas en este ciclo pero con fecha anterior al ciclo
    out_of_cycle_qs = Transaction.objects.filter(
        user=user,
        estado__in=['confirmed', 'pending', 'needs_review'],
        created_at__gte=cs,
        fecha_transaccion__lt=cs,
    ).order_by('-created_at')

    fuera_ciclo = [
        {
            'id': t.id,
            'monto_display': str(t.get_monto_decimal()),
            'tipo': t.tipo,
            'entidad': t.entidad,
            'categoria': t.categoria,
            'fecha_transaccion': t.fecha_transaccion.isoformat(),
            'destinatario': t.destinatario,
        }
        for t in out_of_cycle_qs
    ]

    return Response({
        'ciclo': {
            'inicio': cs.isoformat(),
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
        'transacciones_count': active_transactions.count(),
        'confirmed_count': confirmed_count,
        'fuera_ciclo': fuera_ciclo,
        'fuera_ciclo_count': len(fuera_ciclo),
    })


# ── Categorias personalizadas ─────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def category_list_create(request):
    """GET/POST /api/categories/"""
    if request.method == 'GET':
        cats = UserCategory.objects.filter(user=request.user)
        serializer = UserCategorySerializer(cats, many=True)
        return Response(serializer.data)

    serializer = UserCategorySerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def category_delete(request, pk):
    """DELETE /api/categories/{id}/"""
    try:
        cat = UserCategory.objects.get(pk=pk, user=request.user)
    except UserCategory.DoesNotExist:
        return Response({'detail': 'No encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    Transaction.objects.filter(user=request.user, categoria=cat.slug).update(
        categoria='sin_categorizar'
    )
    cat.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
