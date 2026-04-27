import base64

from rest_framework import serializers

from .models import EncryptedTransaction, Transaction, UserCategory


class TransactionSerializer(serializers.ModelSerializer):
    monto_display = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'tipo', 'entidad', 'categoria', 'destinatario',
            'fecha_transaccion', 'descripcion', 'estado',
            'confianza_ia', 'monto_display', 'referencia_bancaria', 'created_at',
        ]
        read_only_fields = [
            'id', 'monto_display', 'confianza_ia', 'referencia_bancaria', 'created_at',
        ]

    def get_monto_display(self, obj):
        """Desencripta monto solo para el usuario autenticado."""
        try:
            return str(obj.get_monto_decimal())
        except Exception:
            return "Error al leer monto"


class EncryptedTransactionCreateSerializer(serializers.Serializer):
    ciphertext = serializers.CharField()
    iv = serializers.CharField()
    salt = serializers.CharField()
    crypto_version = serializers.IntegerField(required=False, min_value=1, default=1)

    def _decode_required(self, field_name: str, expected_len: int | None = None) -> bytes:
        raw_value = self.validated_data[field_name]
        try:
            decoded = base64.b64decode(raw_value, validate=True)
        except Exception as exc:
            raise serializers.ValidationError({field_name: "Base64 invalido"}) from exc

        if not decoded:
            raise serializers.ValidationError({field_name: "No puede estar vacio"})
        if expected_len is not None and len(decoded) != expected_len:
            raise serializers.ValidationError({field_name: f"Longitud invalida; se esperaba {expected_len} bytes"})
        return decoded

    def create(self, validated_data):
        request = self.context["request"]
        return EncryptedTransaction.objects.create(
            user=request.user,
            encrypted_data=self._decode_required("ciphertext"),
            nonce=self._decode_required("iv", expected_len=12),
            salt=self._decode_required("salt", expected_len=16),
            crypto_version=validated_data.get("crypto_version", 1),
        )


class UserCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCategory
        fields = ['id', 'name', 'icon', 'color', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        if len(value) > 50:
            raise serializers.ValidationError("Máximo 50 caracteres.")
        return value

    def validate_color(self, value):
        import re as _re
        if not _re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError("Color debe ser hex de 6 dígitos, ej: #6366F1")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        return UserCategory.objects.create(user=user, **validated_data)


class EncryptedTransactionListSerializer(serializers.ModelSerializer):
    ciphertext = serializers.SerializerMethodField()
    iv = serializers.SerializerMethodField()
    salt = serializers.SerializerMethodField()

    class Meta:
        model = EncryptedTransaction
        fields = ["id", "ciphertext", "iv", "salt", "crypto_version", "created_at"]

    def get_ciphertext(self, obj):
        return base64.b64encode(bytes(obj.encrypted_data)).decode("utf-8")

    def get_iv(self, obj):
        return base64.b64encode(bytes(obj.nonce)).decode("utf-8")

    def get_salt(self, obj):
        return base64.b64encode(bytes(obj.salt)).decode("utf-8")
