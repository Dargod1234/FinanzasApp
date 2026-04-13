# 01 — BACKEND EVOLUTIVO

> **Proyecto:** Finanzas App  
> **Versión:** 1.0.0 (MVP)  
> **Última actualización:** 2026-04-07  
> **Referencia:** [00_SISTEMA_Y_RESILIENCIA.md](./00_SISTEMA_Y_RESILIENCIA.md)

---

## 1. Modelos Django

### 1.1 Diagrama Entidad-Relación

```
┌──────────────┐       1:1       ┌──────────────────┐
│     User     │────────────────►│     Profile      │
│  (auth.User) │                 │  (Salario, Meta) │
└──────────────┘                 └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────────────────┐
│      Transaction         │
│  (Gasto/Ingreso real)    │
│  FK: user                │
│  UNIQUE: ref_bancaria    │
└──────────────────────────┘
       │
       │ 1:1 (opcional)
       ▼
┌──────────────────────────┐
│   TransactionImage       │
│  (Imagen del comprobante)│
└──────────────────────────┘
```

### 1.2 Modelo User (Django Built-in + Extensión)

Se usa `django.contrib.auth.models.User` como base. La autenticación se vincula al número de celular.

```python
# backend/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r'^\+57\d{10}$',
    message="El número debe estar en formato +57XXXXXXXXXX"
)

class User(AbstractUser):
    """
    Usuario extendido. El 'username' es el número de celular.
    Email es opcional (muchos usuarios solo usan WhatsApp).
    """
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[phone_validator],
        help_text="Número con código de país: +573001234567"
    )

    # El username se setea automáticamente al phone_number
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users_user'

    def __str__(self):
        return self.phone_number
```

### 1.3 Modelo Profile (Salario y Presupuesto)

```python
# backend/users/models.py (continuación)

from core.fields import EncryptedCharField

class Profile(models.Model):
    """
    Perfil financiero del usuario.
    Contiene salario y presupuesto mensual como base para los KPIs.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )


    # --- Datos Financieros (Encriptados en reposo) ---
    salario_mensual = EncryptedCharField(
        max_length=512,
        blank=True,
        null=True,
        help_text="Salario mensual en COP. Encriptado AES-256."
    )
    presupuesto_mensual = EncryptedCharField(
        max_length=512,
        blank=True,
        null=True,
        help_text="Presupuesto objetivo mensual en COP. Encriptado AES-256."
    )

    # --- Datos No Sensibles ---
    dia_corte = models.PositiveSmallIntegerField(
        default=1,
        help_text="Día del mes en que inicia el ciclo financiero (1-31)"
    )
    onboarding_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_profile'

    def __str__(self):
        return f"Profile({self.user.phone_number})"

    def get_salario_decimal(self):
        """Retorna el salario como Decimal para cálculos."""
        from decimal import Decimal
        if self.salario_mensual:
            return Decimal(self.salario_mensual)
        return Decimal('0')

    def get_presupuesto_decimal(self):
        from decimal import Decimal
        if self.presupuesto_mensual:
            return Decimal(self.presupuesto_mensual)
        return Decimal('0')
```

### 1.4 Modelo Transaction

```python
# backend/transactions/models.py

from django.db import models
from django.conf import settings
from core.fields import EncryptedCharField

class Transaction(models.Model):
    """
    Transacción financiera extraída de un comprobante bancario.
    La referencia bancaria es UNIQUE para evitar duplicados.
    """

    class TipoTransaccion(models.TextChoices):
        GASTO = 'gasto', 'Gasto'
        INGRESO = 'ingreso', 'Ingreso'
        TRANSFERENCIA_PROPIA = 'transferencia_propia', 'Transferencia entre cuentas propias'

    class EstadoTransaccion(models.TextChoices):
        PENDING = 'pending', 'Pendiente de confirmación'
        CONFIRMED = 'confirmed', 'Confirmada por usuario'
        REJECTED = 'rejected', 'Rechazada por usuario'
        NEEDS_REVIEW = 'needs_review', 'Requiere revisión manual'
        ERROR = 'error', 'Error en procesamiento'

    class EntidadBancaria(models.TextChoices):
        NEQUI = 'nequi', 'Nequi'
        DAVIPLATA = 'daviplata', 'Daviplata'
        BANCOLOMBIA = 'bancolombia', 'Bancolombia'
        OTRO = 'otro', 'Otro'

    # --- FK ---
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    # --- Datos Sensibles (Encriptados) ---
    monto = EncryptedCharField(
        max_length=512,
        help_text="Monto en COP. Encriptado AES-256."
    )
    referencia_bancaria = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Referencia única del comprobante. Usada para deduplicación."
    )

    # --- Datos Contables (No encriptados) ---
    tipo = models.CharField(
        max_length=25,
        choices=TipoTransaccion.choices,
        default=TipoTransaccion.GASTO
    )
    entidad = models.CharField(
        max_length=20,
        choices=EntidadBancaria.choices
    )
    categoria = models.CharField(
        max_length=50,
        blank=True,
        default='sin_categorizar',
        help_text="Categoría inferida por IA o asignada por usuario"
    )
    destinatario = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nombre del receptor/emisor del pago"
    )
    fecha_transaccion = models.DateTimeField(
        help_text="Fecha/hora de la transacción según el comprobante"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción extraída o nota del usuario"
    )

    # --- Estado y Metadatos ---
    estado = models.CharField(
        max_length=20,
        choices=EstadoTransaccion.choices,
        default=EstadoTransaccion.PENDING
    )
    confianza_ia = models.FloatField(
        default=0.0,
        help_text="Nivel de confianza de la extracción IA (0.0 a 1.0)"
    )
    whatsapp_message_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID del mensaje de WhatsApp original"
    )
    raw_gemini_response = models.JSONField(
        blank=True,
        null=True,
        help_text="Respuesta cruda de Gemini para debugging"
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions_transaction'
        ordering = ['-fecha_transaccion']
        indexes = [
            models.Index(fields=['user', '-fecha_transaccion']),
            models.Index(fields=['user', 'estado']),
            models.Index(fields=['user', 'categoria']),
        ]

    def __str__(self):
        return f"{self.tipo}|{self.entidad}|{self.referencia_bancaria}"

    def get_monto_decimal(self):
        from decimal import Decimal
        try:
            return Decimal(self.monto)
        except Exception:
            return Decimal('0')
```

### 1.5 Modelo TransactionImage

```python
# backend/transactions/models.py (continuación)

import uuid

def comprobante_upload_path(instance, filename):
    """Genera path único: comprobantes/{user_id}/{uuid}.{ext}"""
    ext = filename.split('.')[-1]
    return f"comprobantes/{instance.transaction.user_id}/{uuid.uuid4()}.{ext}"

class TransactionImage(models.Model):
    """
    Imagen original del comprobante bancario.
    Almacenada en S3 con referencia al Transaction.
    """
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='image'
    )
    image = models.ImageField(
        upload_to=comprobante_upload_path,
        help_text="Imagen original del comprobante"
    )
    content_type = models.CharField(max_length=50, default='image/jpeg')
    file_size = models.PositiveIntegerField(
        default=0,
        help_text="Tamaño en bytes"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transactions_image'

    def __str__(self):
        return f"Image({self.transaction.referencia_bancaria})"
```

---

## 2. Señales (Auto-creación de Profile)

```python
# backend/users/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Crea un Profile automáticamente cuando se registra un User."""
    if created:
        Profile.objects.create(user=instance)
```

```python
# backend/users/apps.py

from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        import users.signals  # noqa: F401
```

---

## 3. Lógica de Validación Anti-Duplicados

### 3.1 El Problema

Un usuario puede reenviar el mismo comprobante 3 veces (por error, por impaciencia, o porque WhatsApp tuvo un delay). Cada reenvío llega como un mensaje diferente.

### 3.2 La Solución: `referencia_bancaria` como Clave Única

```python
# backend/transactions/services.py

from django.db import IntegrityError
from transactions.models import Transaction

class TransactionService:
    """Servicio de negocio para crear y gestionar transacciones."""

    @staticmethod
    def create_from_ocr(user, ocr_data: dict, whatsapp_message_id: str = None) -> dict:
        """
        Crea una transacción a partir de los datos extraídos por OCR.
        Retorna un dict con 'status' y 'transaction' o 'message'.
        """
        referencia = ocr_data.get('referencia_bancaria', '').strip()

        if not referencia:
            return {
                'status': 'error',
                'message': 'No se pudo extraer la referencia del comprobante.'
            }

        # --- Verificar duplicado ---
        existing = Transaction.objects.filter(
            referencia_bancaria=referencia
        ).first()

        if existing:
            return {
                'status': 'duplicate',
                'message': f'Este comprobante ya fue registrado el {existing.created_at.strftime("%d/%m/%Y")}.',
                'transaction': existing
            }

        # --- Crear nueva transacción ---
        try:
            transaction = Transaction.objects.create(
                user=user,
                monto=str(ocr_data.get('monto', '0')),
                referencia_bancaria=referencia,
                tipo=ocr_data.get('tipo', 'gasto'),
                entidad=ocr_data.get('entidad', 'otro'),
                categoria=ocr_data.get('categoria', 'sin_categorizar'),
                destinatario=ocr_data.get('destinatario', ''),
                fecha_transaccion=ocr_data.get('fecha_transaccion'),
                descripcion=ocr_data.get('descripcion', ''),
                estado='pending',
                confianza_ia=ocr_data.get('confianza', 0.0),
                whatsapp_message_id=whatsapp_message_id,
                raw_gemini_response=ocr_data.get('raw_response'),
            )
            return {
                'status': 'created',
                'transaction': transaction
            }
        except IntegrityError:
            # Race condition: otro request creó el mismo registro
            existing = Transaction.objects.get(referencia_bancaria=referencia)
            return {
                'status': 'duplicate',
                'message': 'Comprobante duplicado (detectado por constraint).',
                'transaction': existing
            }
```

### 3.3 Diagrama de Flujo Anti-Duplicados

```
Imagen llega por WhatsApp
         │
         ▼
   Gemini extrae JSON
         │
         ▼
   ¿referencia_bancaria vacía?
    │YES              │NO
    ▼                 ▼
  ERROR          SELECT * FROM transactions
  "No se pudo       WHERE referencia_bancaria = ?
   extraer ref"          │
                  │ Existe│           │No existe
                  ▼      │           ▼
            DUPLICADO     │     INSERT transaction
            "Ya fue       │           │
             registrado"  │     ¿IntegrityError?
                          │      │YES       │NO
                          │      ▼          ▼
                          │   DUPLICADO    CREATED ✅
                          │   (race cond.)
```

---

## 4. Autenticación JWT con Número de Celular

### 4.1 Flujo de Registro / Login

```
1. Usuario abre la App
2. Ingresa número de celular (+57...)
3. Backend envía código OTP por WhatsApp
4. Usuario ingresa código OTP en la App
5. Backend verifica OTP → genera JWT (access + refresh)
6. App almacena tokens de forma segura
```

### 4.2 Configuración JWT

```python
# backend/finanzas/settings.py

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'users.serializers.PhoneTokenObtainSerializer',
}

AUTH_USER_MODEL = 'users.User'
```

### 4.3 Serializers de Auth

```python
# backend/users/serializers.py

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile

class PhoneRegistrationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6)

    def validate_phone_number(self, value):
        import re
        if not re.match(r'^\+57\d{10}$', value):
            raise serializers.ValidationError(
                "Formato inválido. Usa +57 seguido de 10 dígitos."
            )
        return value

    def create(self, validated_data):
        phone = validated_data['phone_number']
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={'username': phone}
        )
        refresh = RefreshToken.for_user(user)
        return {
            'user': user,
            'created': created,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class ProfileSerializer(serializers.ModelSerializer):
    salario_mensual = serializers.CharField(required=False, allow_blank=True)
    presupuesto_mensual = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Profile
        fields = [
            'salario_mensual',
            'presupuesto_mensual',
            'dia_corte',
            'onboarding_completed',
        ]

class TransactionSerializer(serializers.ModelSerializer):
    monto_display = serializers.SerializerMethodField()

    class Meta:
        from transactions.models import Transaction
        model = Transaction
        fields = [
            'id', 'tipo', 'entidad', 'categoria', 'destinatario',
            'fecha_transaccion', 'descripcion', 'estado',
            'confianza_ia', 'monto_display', 'created_at',
        ]

    def get_monto_display(self, obj):
        """Desencripta monto solo para el usuario autenticado."""
        try:
            return str(obj.get_monto_decimal())
        except Exception:
            return "Error al leer monto"
```

### 4.4 Views de Auth

```python
# backend/users/views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .serializers import PhoneRegistrationSerializer, ProfileSerializer
from .otp_service import OTPService

@api_view(['POST'])
@permission_classes([AllowAny])
def phone_auth(request):
    """
    Login/Registro unificado por número de celular + OTP.
    POST: { "phone_number": "+573001234567", "otp_code": "123456" }
    """
    serializer = PhoneRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Verificar OTP
    phone = serializer.validated_data['phone_number']
    otp_code = serializer.validated_data['otp_code']

    if not OTPService.verify_otp(phone, otp_code):
        return Response(
            {'detail': 'Código OTP inválido o expirado.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    result = serializer.save()
    return Response({
        'access': result['access'],
        'refresh': result['refresh'],
        'is_new_user': result['created'],
        'onboarding_completed': result['user'].profile.onboarding_completed,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    """
    Solicitar envío de OTP al número de celular.
    POST: { "phone_number": "+573001234567" }
    """
    phone = request.data.get('phone_number', '')

    import re
    if not re.match(r'^\+57\d{10}$', phone):
        return Response(
            {'detail': 'Formato inválido. Usa +57 seguido de 10 dígitos.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    otp = OTPService.generate_otp(phone)

    # TODO: Enviar OTP por WhatsApp en producción
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"OTP generado para {phone}")

    return Response({
        'detail': 'Código OTP enviado.',
        'debug_otp': otp,  # SOLO para desarrollo, remover en producción
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """GET: Obtener perfil. PATCH: Actualizar salario/presupuesto."""
    profile = request.user.profile
    if request.method == 'GET':
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)
    elif request.method == 'PATCH':
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
```

### 4.5 Sistema OTP (Simplificado para MVP)

```python
# backend/users/otp_service.py

import random
import hashlib
from django.core.cache import cache
from django.conf import settings

class OTPService:
    """
    Servicio de One-Time Password.
    MVP: Almacena OTP en cache (Redis/Memcached).
    Producción: Usar servicio dedicado (Twilio Verify, etc.)
    """
    OTP_EXPIRY_SECONDS = 300  # 5 minutos
    MAX_ATTEMPTS = 3

    @staticmethod
    def generate_otp(phone_number: str) -> str:
        """Genera un OTP de 6 dígitos y lo almacena en cache."""
        otp = str(random.SystemRandom().randint(100000, 999999))
        cache_key = f"otp:{hashlib.sha256(phone_number.encode()).hexdigest()}"
        cache.set(cache_key, {
            'code': otp,
            'attempts': 0
        }, timeout=OTPService.OTP_EXPIRY_SECONDS)
        return otp

    @staticmethod
    def verify_otp(phone_number: str, code: str) -> bool:
        """Verifica el OTP. Retorna True si es válido."""
        cache_key = f"otp:{hashlib.sha256(phone_number.encode()).hexdigest()}"
        otp_data = cache.get(cache_key)

        if not otp_data:
            return False

        if otp_data['attempts'] >= OTPService.MAX_ATTEMPTS:
            cache.delete(cache_key)
            return False

        if otp_data['code'] == code:
            cache.delete(cache_key)  # OTP de un solo uso
            return True

        # Incrementar intentos fallidos
        otp_data['attempts'] += 1
        cache.set(cache_key, otp_data, timeout=OTPService.OTP_EXPIRY_SECONDS)
        return False
```

---

## 5. Endpoints API (REST)

### 5.1 Tabla de Endpoints

| Método | Endpoint                           | Auth   | Descripción                          |
|--------|------------------------------------|--------|--------------------------------------|
| POST   | `/api/auth/phone/request-otp/`     | No     | Solicitar envío de código OTP        |
| POST   | `/api/auth/phone/`                 | No     | Login/Registro con celular + OTP     |
| POST   | `/api/auth/token/refresh/`         | No     | Refrescar JWT                        |
| GET    | `/api/auth/profile/`               | JWT    | Obtener perfil del usuario           |
| PATCH  | `/api/auth/profile/`               | JWT    | Actualizar salario/presupuesto       |
| GET    | `/api/transactions/`              | JWT    | Listar transacciones (paginadas)     |
| GET    | `/api/transactions/{id}/`         | JWT    | Detalle de transacción               |
| PATCH  | `/api/transactions/{id}/`         | JWT    | Actualizar categoría/estado          |
| GET    | `/api/transactions/{id}/image/`   | JWT    | Obtener imagen del comprobante       |
| GET    | `/api/dashboard/summary/`         | JWT    | KPIs: ahorro, gasto por categoría   |
| POST   | `/api/whatsapp/webhook/`          | Meta*  | Webhook entrante de WhatsApp         |
| GET    | `/api/whatsapp/webhook/`          | Meta*  | Verificación del webhook             |

> *La auth del webhook de WhatsApp se verifica con firma HMAC (ver `00_SISTEMA_Y_RESILIENCIA.md` §4.5)

### 5.2 URLs

```python
# backend/finanzas/urls.py

from django.urls import path, include

urlpatterns = [
    path('api/auth/', include('users.urls')),
    path('api/', include('transactions.urls')),
    path('api/whatsapp/', include('whatsapp.urls')),
]
```

```python
# backend/users/urls.py

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('phone/', views.phone_auth, name='phone-auth'),
    path('phone/request-otp/', views.request_otp, name='request-otp'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', views.profile_view, name='profile'),
]
```

```python
# backend/transactions/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('transactions/', views.transaction_list, name='transaction-list'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction-detail'),
    path('transactions/<int:pk>/image/', views.transaction_image, name='transaction-image'),
    path('dashboard/summary/', views.dashboard_summary, name='dashboard-summary'),
]
```

---

## 6. Dashboard Summary View

```python
# backend/transactions/views.py

from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Transaction
from .serializers import TransactionSerializer

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
        cycle_start = now.replace(year=prev_year, month=prev_month, day=dia_corte,
                                   hour=0, minute=0, second=0, microsecond=0)

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
```

---

## 7. Esquema de Migraciones — Guía Operativa

### 7.1 Reglas para Migraciones Seguras

```markdown
1. NUNCA eliminar un campo en producción sin pasar por un ciclo de deprecación:
   - Sprint N: Agregar nuevo campo + migrar datos
   - Sprint N+1: Actualizar código para usar nuevo campo
   - Sprint N+2: Eliminar campo viejo (cuando esté confirmado que no se usa)

2. SIEMPRE usar RunPython reversible para migraciones de datos:
   - Cada `RunPython(forward_func)` debe tener `RunPython(forward_func, reverse_func)`

3. NUNCA hacer ALTER TABLE manualmente en producción. Solo vía Django migrations.

4. Para campos nuevos en modelos existentes, SIEMPRE usar:
   - `null=True` y `blank=True` para la primera migración
   - Una segunda migración para llenar datos por defecto
   - Una tercera migración para quitar `null=True` si necesario
```

### 7.2 Ejemplo: Agregar Campo `subcategoria` a Transaction

```python
# Paso 1: Generar migración
# python manage.py makemigrations transactions --name add_subcategoria

# Paso 2: La migración generada se ve así:
# backend/transactions/migrations/0002_add_subcategoria.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('transactions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='subcategoria',
            field=models.CharField(
                max_length=50,
                blank=True,
                null=True,  # ← Permite NULL para datos existentes
                default=None,
            ),
        ),
    ]
```

```python
# Paso 3: Migración de datos (si necesaria)
# backend/transactions/migrations/0003_populate_subcategoria.py

from django.db import migrations

def set_default_subcategoria(apps, schema_editor):
    Transaction = apps.get_model('transactions', 'Transaction')
    Transaction.objects.filter(subcategoria__isnull=True).update(subcategoria='general')

def reverse_subcategoria(apps, schema_editor):
    Transaction = apps.get_model('transactions', 'Transaction')
    Transaction.objects.filter(subcategoria='general').update(subcategoria=None)

class Migration(migrations.Migration):
    dependencies = [
        ('transactions', '0002_add_subcategoria'),
    ]

    operations = [
        migrations.RunPython(set_default_subcategoria, reverse_subcategoria),
    ]
```

### 7.3 Comandos de Migración

```bash
# Desarrollo
python manage.py makemigrations          # Genera migraciones
python manage.py migrate                 # Aplica migraciones
python manage.py showmigrations          # Estado de migraciones

# Rollback (si algo sale mal)
python manage.py migrate transactions 0001  # Revertir a migración específica

# Verificar SQL generado antes de aplicar
python manage.py sqlmigrate transactions 0002

# Chequeo de consistencia
python manage.py migrate --check         # Verifica si hay migraciones pendientes
```

### 7.4 Checklist Pre-Deploy de Migraciones

- [ ] `makemigrations --check` no genera migraciones nuevas (todo está generado)
- [ ] `sqlmigrate` revisado — no hay DROP TABLE/COLUMN inesperado
- [ ] Migración tiene operación reversa (`reverse_code` o `migrations.RunPython` con reverse)
- [ ] Campos nuevos tienen `null=True` o `default` en la primera migración
- [ ] Índices nuevos usan `concurrently=True` en PostgreSQL si la tabla es grande
- [ ] Backup de base de datos realizado antes de migrar en producción

---

## 8. Requirements

```txt
# backend/requirements.txt

Django>=5.1,<5.2
djangorestframework>=3.15,<4.0
djangorestframework-simplejwt>=5.3,<6.0
django-cors-headers>=4.3,<5.0
psycopg2-binary>=2.9,<3.0
cryptography>=42.0,<43.0
google-generativeai>=0.5,<1.0
requests>=2.31,<3.0
Pillow>=10.0,<11.0
boto3>=1.34,<2.0
django-storages>=1.14,<2.0
python-dotenv>=1.0,<2.0
gunicorn>=22.0,<23.0
```

---

*Este documento sigue la [Regla de Oro](./00_SISTEMA_Y_RESILIENCIA.md#61-regla-de-oro). Cualquier cambio en modelos o endpoints debe reflejarse aquí antes de implementarse en código.*
