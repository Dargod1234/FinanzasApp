from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    monto_display = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'tipo', 'entidad', 'categoria', 'destinatario',
            'fecha_transaccion', 'descripcion', 'estado',
            'confianza_ia', 'monto_display', 'created_at',
        ]
        read_only_fields = [
            'id', 'monto_display', 'confianza_ia', 'created_at',
        ]

    def get_monto_display(self, obj):
        """Desencripta monto solo para el usuario autenticado."""
        try:
            return str(obj.get_monto_decimal())
        except Exception:
            return "Error al leer monto"
