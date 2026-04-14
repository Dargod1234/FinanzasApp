import logging
import re
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .serializers import PhoneRegistrationSerializer, ProfileSerializer
from .otp_service import OTPService
from whatsapp.meta_api import send_text_message

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    """
    Solicitar envío de OTP al número de celular.
    POST: { "phone_number": "+573001234567" }
    """
    raw_phone = str(request.data.get('phone_number', '')).strip()
    
    # Limpieza profunda: Solo dejar el '+' y los dígitos
    phone = '+' + re.sub(r'\D', '', raw_phone)
    
    # Si el usuario mandó 10 dígitos sin el +57, arreglarlo
    if len(phone) == 11 and phone.startswith('+3'): # +300... -> +57300...
         phone = '+57' + phone[1:]
    elif len(phone) == 14 and phone.startswith('+5757'): # Error común de doble prefijo
         phone = '+57' + phone[5:]

    if not re.match(r'^\+57\d{10}$', phone):
        logger.warning(f"Intento de registro con formato inválido: {raw_phone} -> {phone}")
        return Response(
            {'detail': 'Formato inválido. Usa +57 seguido de 10 dígitos (ej: +573001234567).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generar el código
    otp = OTPService.generate_otp(phone)
    
    # ENVIAR POR WHATSAPP (Integración Real 2026)
    mensaje_otp = f"🔐 Tu código de acceso para Finanzas App es: *{otp}*\n\nNo lo compartas con nadie. Expira en 5 minutos."
    
    # El número para Meta debe ser sin el '+' (ej: 573001234567)
    phone_whatsapp = phone.replace("+", "")
    
    exito = send_text_message(phone_whatsapp, mensaje_otp)

    if exito:
        logger.info(f"OTP enviado exitosamente a {phone}")
        return Response({
            'detail': 'Código OTP enviado por WhatsApp.',
            'debug_otp': otp if settings.DEBUG else None
        }, status=status.HTTP_200_OK)
    else:
        logger.error(f"Fallo al enviar OTP vía Meta API a {phone}")
        return Response({
            'detail': 'No pudimos enviar el código por WhatsApp. Verifica que tu número sea correcto y tengas el chat activo.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def phone_auth(request):
    """
    Login/Registro unificado por número de celular + OTP.
    POST: { "phone_number": "+573001234567", "otp_code": "123456" }
    """
    serializer = PhoneRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

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
