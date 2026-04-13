import uuid

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
