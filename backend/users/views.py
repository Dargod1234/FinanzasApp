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
