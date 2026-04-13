import re
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile


class PhoneRegistrationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6)

    def validate_phone_number(self, value):
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
