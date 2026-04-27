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
    # Campos del User — se leen/escriben mediante source y override de update()
    first_name = serializers.CharField(
        source='user.first_name', required=False, allow_blank=True, default=''
    )
    last_name = serializers.CharField(
        source='user.last_name', required=False, allow_blank=True, default=''
    )

    class Meta:
        model = Profile
        fields = [
            'salario_mensual',
            'presupuesto_mensual',
            'dia_corte',
            'onboarding_completed',
            'first_name',
            'last_name',
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        fields_to_save = []
        if 'first_name' in user_data:
            instance.user.first_name = user_data['first_name']
            fields_to_save.append('first_name')
        if 'last_name' in user_data:
            instance.user.last_name = user_data['last_name']
            fields_to_save.append('last_name')
        if fields_to_save:
            instance.user.save(update_fields=fields_to_save)
        return super().update(instance, validated_data)
