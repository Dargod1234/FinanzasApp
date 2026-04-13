from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from core.fields import EncryptedCharField

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

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users_user'

    def __str__(self):
        return self.phone_number


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
