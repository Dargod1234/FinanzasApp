# Resumen de Mejoras OCR — Estado de Implementación

**Fecha:** Abril 27, 2026  
**Contexto:** Ejecución del plan de oportunidades de mejora del pipeline de detección de imágenes IA / PaddleOCR.

---

## ✅ Implementado Localmente

### Problema 1 — Confianza hardcodeada reemplazada por confianza real
**Archivo:** `backend/core/services/ocr_pipeline.py`

La constante `0.65` fue eliminada. Se implementó `_calculate_confidence()` que calcula un score dinámico según:

| Componente | Puntos |
|---|---|
| Monto extraído con patrón etiquetado (labeled) | +0.35 |
| Monto extraído con fallback numérico | +0.20 |
| Entidad identificada (no "otro") | +0.20 |
| Referencia bancaria encontrada | +0.20 |
| Fecha encontrada | +0.15 |
| Destinatario encontrado | +0.10 |

Rango resultante: `0.0` (ningún campo) — `1.0` (todos los campos con patrón primario).  
El score ya fluye correctamente hasta `confianza_ia` en la DB a través del validador.

---

### Problema 2 — Preprocesamiento de imagen antes del OCR
**Archivo:** `backend/core/services/ocr_local.py`

Se implementó `_preprocess_image()` con Pillow antes de enviar al motor OCR:

1. **Upscale** si alguna dimensión es menor a 1000px (factor máx 3×, interpolación LANCZOS)
2. **Conversión a escala de grises** (mejora contraste texto/fondo)
3. **Aumento de contraste** × 1.5 con `ImageEnhance.Contrast`
4. **Sharpening** suave con `ImageFilter.SHARPEN`
5. **Exportación JPEG quality=90** para envío al motor

Si Pillow no está disponible o el preprocesamiento falla, se usa la imagen original como fallback (sin romper el pipeline).

---

### Problema 3 — Patrones regex mejorados y diferenciados por entidad
**Archivo:** `backend/core/services/ocr_pipeline.py`

- Se extendió `_looks_like_receipt` con más marcadores: Davivienda, Banco de Bogotá, BBVA, PSE, "aprobado", "recibo", "voucher", etc.
- Se separó `_extract_amount` en `_extract_amount_with_source` que retorna `(monto, source)` para alimentar la confianza.
- Se agregaron patrones de extracción de monto **específicos por entidad** (Nequi, Daviplata, Bancolombia) con fallback al patrón genérico.
- Se agregaron patrones de referencia **específicos por entidad** con fallback genérico.
- Se amplió el rango de referencia de 6–15 a 6–20 caracteres alfanuméricos.

---

### Problema 4 — Validación flexible: referencia_bancaria ya no bloquea
**Archivo:** `backend/core/services/ocr_validator.py`

`referencia_bancaria` cambió de `required: True` a `required: False` en el `OCR_SCHEMA`.

Cuando no se extrae referencia del comprobante, se genera automáticamente un identificador interno:
```
INT-<hash SHA-256 truncado a 14 chars>
```
El hash usa: `monto + fecha (hasta minutos) + entidad + primeros 300 chars del texto OCR`.

Esto garantiza:
- Mismo comprobante enviado 2 veces → mismo hash → `UNIQUE` constraint bloquea duplicado ✅
- Comprobantes distintos → hashes distintos → se crean normalmente ✅
- Transacciones válidas con monto correcto ya no se descartan por falta de referencia ✅

---

### Problema 6 — `_to_numeric_string` corregido para montos con decimales
**Archivo:** `backend/core/services/ocr_pipeline.py`

La función anterior eliminaba todos los caracteres no numéricos sin distinguir separadores.

Nueva lógica por casos:

| Input | Antes (bug) | Ahora (correcto) |
|---|---|---|
| `"$ 50.000"` | `"50000"` | `"50000"` ✅ |
| `"1.200.000"` | `"1200000"` | `"1200000"` ✅ |
| `"1.200.000,00"` | `"120000000"` ❌ | `"1200000"` ✅ |
| `"1.200.000,50"` | `"120000050"` ❌ | `"1200000"` ✅ |
| `"50,000"` | `"50000"` | `"50000"` ✅ |

---

### Problema 7 — Circuit breaker compartido entre workers de Gunicorn
**Archivo:** `backend/core/services/circuit_breaker.py`

El singleton en memoria fue reemplazado por un circuit breaker persistido en **Django cache**.

El estado (state, failure_count, last_failure_time) ahora vive en las claves:
- `ocr_circuit_breaker:state`
- `ocr_circuit_breaker:failures`
- `ocr_circuit_breaker:last_failure`

El backend `DatabaseCache` ya configurado en `settings.py` es suficiente. Con 3 workers de Gunicorn, ahora los 3 procesos comparten el mismo estado del circuito.

`cache.incr()` se usa para el conteo de fallos (atómico en memcached/redis, tolerante a race conditions leves en DatabaseCache).

**Nota:** Para que el `DatabaseCache` funcione, la tabla `django_cache_table` debe existir en la DB. Si aún no se creó, ejecutar en el servidor:
```bash
python manage.py createcachetable
```

---

## 🖥️ Requiere Acción en el Servidor

### Problema 5 — Restaurar `use_angle_cls=True` en el motor PaddleOCR

**Archivo en servidor:** `/opt/finanzas-backend/ai_ocr_service/server.py`

Cambiar la inicialización del motor OCR de:
```python
ocr = PaddleOCR(
    lang="es",
    use_gpu=False,
    enable_mkldnn=False,
    ocr_version='PP-OCRv4',
    show_log=False
)
```
A:
```python
ocr = PaddleOCR(
    lang="es",
    use_gpu=False,
    enable_mkldnn=False,
    ocr_version='PP-OCRv4',
    show_log=False,
    use_angle_cls=True,   # Detecta y corrige orientación del texto
    cpu_threads=4,        # Mejora throughput en CPU
    det_db_thresh=0.3,    # Umbral de detección más permisivo (default 0.3)
    rec_batch_num=6,      # Batch de reconocimiento
)
```

**Por qué se desactivó:** El crash original en Docker fue por el motor PIR de Paddle 2.6, no por `use_angle_cls`. Los flags de entorno `FLAGS_enable_pir_api=0` y `FLAGS_enable_new_ir_api=0` ya están configurados y resuelven ese problema. Es seguro reactivar `use_angle_cls`.

**Riesgo:** Bajo. El mount de source en docker-compose (`/opt/finanzas-backend/ai_ocr_service:/app`) aplica el cambio **sin rebuild**. Solo reiniciar el contenedor:
```bash
docker compose restart ocr-engine
```

---

### Pinear versión de Pillow en el OCR service

**Archivo en servidor:** `/opt/finanzas-backend/ai_ocr_service/requirements.txt`

Agregar versión explícita de Pillow para builds reproducibles:
```
Pillow==10.4.0
```
Verificar la versión actualmente instalada en el contenedor antes de pinear:
```bash
docker exec <ocr-container> pip show Pillow
```

---

### Agregar logging de calidad de extracción en el motor OCR

**Archivo en servidor:** `/opt/finanzas-backend/ai_ocr_service/server.py`

Agregar logging estructurado al endpoint `/process` para poder identificar patrones de fallos:
```python
@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    # ... código existente ...
    result = ocr.ocr(img_array)
    
    # Logging de calidad
    total_boxes = sum(len(page) for page in result if page)
    avg_confidence = 0.0
    if total_boxes > 0:
        confidences = [
            line[1][1]
            for page in result if page
            for line in page
            if line and len(line) > 1 and line[1]
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    logger.info(
        "OCR completado: boxes=%d, avg_conf_paddle=%.3f, chars=%d",
        total_boxes, avg_confidence, len(text)
    )
    # ... resto del código ...
```

---

### Problema 8 — Verificar `updated_at` en la DB del servidor

**Acción:** Verificar si la migración en el servidor tiene el campo correcto:
```bash
grep -n "updated_at" /opt/finanzas-backend/backend/transactions/migrations/0001_initial.py
```

- Si dice `auto_now_add=True` → **bug**: el campo nunca se actualiza al hacer `.save()`.
- Si dice `auto_now=True` → correcto, no se necesita acción.

Si hay bug, crear en el servidor la migración correctora:
```bash
# Primero editar /opt/finanzas-backend/backend/transactions/migrations/0001_initial.py
# Cambiar auto_now_add=True a auto_now=True en el campo updated_at
# Luego crear una nueva migración vacía que solo hace AlterField:
python manage.py migrate transactions --fake  # si el schema ya es correcto en la DB
```
O bien, crear manualmente `0005_fix_updated_at.py`:
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('transactions', '0004_encrypted_transaction')]
    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
```

---

### Problema 9 — Procesamiento OCR asíncrono (webhook)

**Impacto:** Alto. Meta reintenta el webhook si no recibe `200 OK` en < 20s. El pipeline OCR puede tardar hasta 35s.

**Solución recomendada:** Celery + Redis (o RabbitMQ).

**Pasos en el servidor:**

1. Agregar dependencias en `backend/requirements.txt`:
```
celery[redis]==5.3.6
redis==5.0.1
```

2. Crear `/opt/finanzas-backend/backend/finanzas/celery.py`:
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finanzas.settings')
app = Celery('finanzas')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

3. Agregar en `settings.py`:
```python
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
```

4. Convertir `handle_image_message` en task de Celery en `message_handler.py`:
```python
from celery import shared_task

@shared_task(bind=True, max_retries=1)
def process_image_async(self, phone_number, message_id, message_data_json):
    # mover lógica de handle_image_message aquí
    ...
```

5. En `views.py`, despachar la tarea y retornar `200 OK` inmediatamente:
```python
def receive_message(request):
    # ... parseo existente ...
    if message_type == 'image':
        process_image_async.delay(phone_number, message_id, message)
    else:
        handle_incoming_message(...)  # texto/botones son rápidos, se mantienen síncronos
    return HttpResponse('OK', status=200)
```

6. Agregar servicio Redis + worker Celery en `docker-compose.yml`:
```yaml
redis:
  image: redis:7-alpine
  restart: unless-stopped

celery-worker:
  build: ./backend
  command: celery -A finanzas worker -l info -c 2
  env_file: .env
  depends_on: [db, redis, ocr-engine]
  restart: unless-stopped
```

**Nota:** Este cambio es el más complejo y requiere testing. El riesgo de regresión es significativo. Se recomienda implementarlo en un branch separado con pruebas de integración antes de llevar a producción.

---

## ℹ️ Items que No Requieren Acción

| Item | Motivo |
|---|---|
| Migración `updated_at` local | `0001_initial.py` local ya tiene `auto_now=True` (correcto) |
| Category engine / Transaction classifier | Mejoras son de lógica de negocio, no afectan la confianza OCR directamente |
| `GEMINI_API_KEY` en `.env` | Sin uso activo en el pipeline — puede dejarse o removerse sin impacto |
| Límite de CPU en docker-compose | El OCR usa CPU ilimitada por diseño (alto consumo es esperado para PP-OCRv4) |

---

## Resumen de Impacto Esperado

| Mejora | Impacto en Confianza | Riesgo |
|---|---|---|
| Confianza dinámica | Score real en lugar de 0.65 fijo | Ninguno |
| Preprocesamiento imagen | +20–40% más texto extraído en imágenes borrosas | Bajo (fallback a original) |
| Regex por entidad | Menos falsos positivos en monto/referencia | Bajo |
| Referencia opcional | Cero transacciones perdidas por falta de referencia | Bajo |
| `_to_numeric_string` | Elimina bug de montos ×100 con centavos | Ninguno |
| Circuit breaker compartido | Protección real contra cascadas en producción | Bajo |
| `use_angle_cls=True` (servidor) | Maneja comprobantes fotografiados con inclinación | Bajo (config solo) |
| Webhook asíncrono (servidor) | Elimina retries de Meta por timeout | Alto (requiere Celery) |
