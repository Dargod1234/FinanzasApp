# Sprint: Webhook Asíncrono con Celery

**Fecha:** Abril 2026  
**Branch:** `feature/async-webhook-celery`  
**Contexto:** El pipeline OCR puede tardar hasta 35s. Meta requiere 200 OK en <20s o reintenta el delivery. Este sprint desacopla la recepción del webhook del procesamiento OCR usando Celery + Redis.

---

## Hallazgos clave (ya investigados — no requieren más lectura)

- `ConversationManager` ya usa `django.core.cache` → funciona entre procesos sin cambios
- `WhatsAppUserThrottle` ya usa `django.core.cache` → funciona entre procesos sin cambios
- El cache backend actual es `DatabaseCache` (`django_cache_table`) → se mantiene para estado
- Redis se agrega **solo como broker de Celery**, no reemplaza el cache de Django
- `whatsapp_message_id` ya existe en el modelo `Transaction` → se usa como idempotency key

---

## Archivos a modificar

1. `backend/requirements.txt`
2. `backend/finanzas/celery.py` ← archivo nuevo
3. `backend/finanzas/__init__.py`
4. `backend/finanzas/settings.py`
5. `backend/whatsapp/tasks.py` ← archivo nuevo
6. `backend/whatsapp/views.py`
7. `backend/whatsapp/message_handler.py`
8. `docker-compose.yml`
9. `.env` del servidor (solo agregar variable, no subir al repo)

---

## Cambio 1: `backend/requirements.txt`

Agregar al final:

```
celery[redis]==5.3.6
redis==5.0.1
```

---

## Cambio 2: `backend/finanzas/celery.py` (archivo nuevo)

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finanzas.settings')

app = Celery('finanzas')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

---

## Cambio 3: `backend/finanzas/__init__.py`

Agregar al inicio del archivo (o crear si no existe):

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

---

## Cambio 4: `backend/finanzas/settings.py`

Agregar al final del archivo (junto a la config de CACHES que ya existe):

```python
# Celery — broker Redis, resultados en cache Django existente
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = 'cache+django://'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_TRACK_STARTED = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
```

> **Nota:** Se usa `cache+django://` como result backend para aprovechar el `DatabaseCache` existente sin agregar dependencias extra (`django-celery-results`).

---

## Cambio 5: `backend/whatsapp/tasks.py` (archivo nuevo)

```python
import json
import logging

from celery import shared_task
from django.core.cache import cache

from users.models import User

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL = 3600  # 1 hora


@shared_task(bind=True, max_retries=1, default_retry_delay=15)
def process_whatsapp_image(self, phone_number: str, message_id: str, message_data_json: str):
    """
    Task Celery para procesar imágenes de comprobantes de WhatsApp.
    Desacoplado del webhook para responder 200 OK a Meta inmediatamente.
    """
    # Idempotency check — evita doble procesamiento si Meta reintenta
    # y Celery también reintenta simultáneamente
    idempotency_key = f"wa_processing:{message_id}"
    if cache.get(idempotency_key):
        logger.info("Task duplicado detectado para message_id=%s, ignorando.", message_id)
        return {"status": "duplicate_task", "message_id": message_id}

    # Marcar como en proceso ANTES de empezar (TTL cubre tiempo máximo de OCR)
    cache.set(idempotency_key, True, timeout=IDEMPOTENCY_TTL)

    try:
        message_data = json.loads(message_data_json)

        # Obtener usuario (ya fue creado en el webhook antes del dispatch)
        user = User.objects.get(phone_number=f"+{phone_number}")

        # Import dentro de la función para evitar imports circulares
        from whatsapp.message_handler import handle_image_message
        handle_image_message(user, phone_number, message_id, message_data)

    except User.DoesNotExist:
        logger.error("Usuario no encontrado para phone_number=%s", phone_number)
    except Exception as exc:
        logger.error("Error en process_whatsapp_image: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
```

---

## Cambio 6: `backend/whatsapp/views.py`

Reemplazar el archivo completo. El webhook ahora:
1. Verifica firma HMAC
2. Hace throttle check (antes del dispatch)
3. Crea el usuario si no existe (el task necesita que ya exista para hacer `.get()`)
4. Despacha a Celery solo imágenes (async)
5. Procesa síncronamente texto y botones (son < 1s)

```python
import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .meta_api import verify_webhook_signature
from .message_handler import handle_incoming_message
from .throttling import WhatsAppUserThrottle
from users.models import User

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == 'GET':
        return verify_webhook(request)
    elif request.method == 'POST':
        return receive_message(request)


def verify_webhook(request):
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')

    if mode == 'subscribe' and token == settings.META_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verificado correctamente")
        return HttpResponse(challenge, status=200)

    logger.warning(f"Verificación de webhook fallida: token={token}")
    return HttpResponse('Forbidden', status=403)


def receive_message(request):
    if not verify_webhook_signature(request):
        logger.warning("Firma de webhook inválida — posible spoofing")
        return HttpResponse('Invalid signature', status=403)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)

    try:
        entry = body.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        if not messages:
            # Notificación de estado (delivered, read), ignorar
            return HttpResponse('OK', status=200)

        message = messages[0]
        phone_number = message.get('from', '')
        message_id = message.get('id', '')
        message_type = message.get('type', '')

        # Rate limiting — verificar ANTES de cualquier procesamiento
        if not WhatsAppUserThrottle.is_allowed(phone_number):
            from .meta_api import send_text_message
            send_text_message(
                phone_number,
                "⏳ Has enviado muchos mensajes. Intenta de nuevo en unos minutos."
            )
            return HttpResponse('OK', status=200)

        # Crear usuario si no existe — el task Celery hace .get(), no get_or_create
        user, created = User.objects.get_or_create(
            phone_number=f"+{phone_number}",
            defaults={'username': f"+{phone_number}"}
        )

        if created:
            from .meta_api import send_text_message
            send_text_message(
                phone_number,
                "👋 ¡Hola! Soy tu asistente de Finanzas App.\n\n"
                "Envíame una foto de tu comprobante de pago (Nequi, Daviplata o Bancolombia) "
                "y yo registro el gasto automáticamente.\n\n"
                "También puedes preguntarme:\n"
                "• \"¿Cuánto he gastado este mes?\"\n"
                "• \"¿Cuál es mi ahorro?\"\n"
                "• \"Resumen\""
            )
            return HttpResponse('OK', status=200)

        if message_type == 'image':
            # ASYNC: despachar a Celery y retornar 200 OK inmediatamente a Meta
            from whatsapp.tasks import process_whatsapp_image
            process_whatsapp_image.delay(
                phone_number=phone_number,
                message_id=message_id,
                message_data_json=json.dumps(message),
            )
        else:
            # SÍNCRONO: texto y botones son < 1s, no necesitan async
            handle_incoming_message(
                user=user,
                phone_number=phone_number,
                message_id=message_id,
                message_type=message_type,
                message_data=message,
            )

    except (IndexError, KeyError) as e:
        logger.error(f"Error parseando webhook: {e}")

    # SIEMPRE responder 200 a Meta (si no, reenvía el mensaje)
    return HttpResponse('OK', status=200)
```

---

## Cambio 7: `backend/whatsapp/message_handler.py`

Dos modificaciones:

### 7a. Cambiar la firma de `handle_incoming_message`

Agregar `user` como primer parámetro (antes lo obtenía internamente):

```python
def handle_incoming_message(user, phone_number: str, message_id: str,
                            message_type: str, message_data: dict):
```

### 7b. Eliminar el bloque de throttle y get_or_create del inicio de la función

Eliminar estas líneas del inicio de `handle_incoming_message` (ya están en `views.py`):

```python
# ELIMINAR — ya está en views.py:
if not WhatsAppUserThrottle.is_allowed(phone_number):
    send_text_message(
        phone_number,
        "⏳ Has enviado muchos mensajes. Intenta de nuevo en unos minutos."
    )
    return

user, created = User.objects.get_or_create(
    phone_number=f"+{phone_number}",
    defaults={'username': f"+{phone_number}"}
)

if created:
    send_text_message(...)
    return
```

> El resto de la función (`handle_image_message`, `handle_button_response`, `handle_text_message`, etc.) no cambia.

---

## Cambio 8: `docker-compose.yml`

### 8a. Agregar servicios `redis` y `celery-worker`

```yaml
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  celery-worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    command: celery -A finanzas worker -l info -c 2 --max-tasks-per-child=50
    env_file:
      - ${ENV_FILE:-/opt/finanzas-backend/.env}
    environment:
      DB_HOST: ${DB_HOST:-172.17.0.1}
      DB_PORT: ${DB_PORT:-5432}
      CELERY_BROKER_URL: "redis://redis:6379/0"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - /opt/finanzas-backend/backend/finanzas/settings.py:/app/finanzas/settings.py:ro
    depends_on:
      redis:
        condition: service_healthy
      ocr-engine:
        condition: service_healthy
```

### 8b. Agregar `redis` como dependencia del servicio `backend`

```yaml
  backend:
    ...
    depends_on:
      ocr-engine:
        condition: service_healthy
      redis:                   # ← agregar
        condition: service_healthy
```

---

## Cambio 9: `.env` del servidor (NO va al repo)

Agregar manualmente en el servidor en `/opt/finanzas-backend/.env`:

```
CELERY_BROKER_URL=redis://redis:6379/0
```

---

## Prueba mínima antes del push a producción

Levantar el stack completo localmente y verificar:

```bash
docker compose up -d redis ocr-engine backend celery-worker
docker compose logs celery-worker --tail=20  # debe mostrar "ready." sin errores
```

Checklist de validación:

- [ ] Webhook responde en < 500ms al recibir una imagen (medir con curl o Postman)
- [ ] El worker procesa la imagen y el usuario recibe el mensaje de confirmación
- [ ] Enviar el mismo comprobante dos veces → solo llega una confirmación (idempotency key funciona)
- [ ] Si el OCR está caído, el task falla con retry y no rompe el webhook
- [ ] Los mensajes de texto y botones siguen funcionando síncronamente

---

## Despliegue en servidor (después del push y pull en servidor)

```bash
cd /opt/finanzas-backend
git pull

# Agregar CELERY_BROKER_URL al .env manualmente si no está
echo "CELERY_BROKER_URL=redis://redis:6379/0" >> .env

# Build de las imágenes que cambiaron
docker compose build backend celery-worker

# Levantar Redis primero
docker compose up -d redis

# Levantar el worker
docker compose up -d celery-worker

# Recrear backend (recoge las dependencias nuevas y settings actualizados)
docker compose up -d --no-deps backend

# Verificar estado final
docker compose ps
docker compose logs celery-worker --tail=30
```

---

## Impacto esperado

| Métrica | Antes | Después |
|---------|-------|---------|
| Tiempo de respuesta al webhook de Meta | Hasta 35s | < 500ms |
| Riesgo de retry de Meta | Alto (>20s frecuentes) | Eliminado |
| Doble procesamiento por retry | Posible | Bloqueado por idempotency key |
| Complejidad del stack | 2 servicios | 4 servicios (+Redis, +Celery worker) |
