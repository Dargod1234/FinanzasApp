from django.db import IntegrityError
from .models import Transaction


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
                raw_ocr_response=ocr_data.get('raw_response'),
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
