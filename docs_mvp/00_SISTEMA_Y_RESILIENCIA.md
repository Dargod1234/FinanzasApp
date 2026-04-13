# 00 — SISTEMA Y RESILIENCIA (La Constitución)

> **Proyecto:** Finanzas App — Sistema de Gestión Financiera "Zero-Friction"  
> **Versión:** 1.0.0 (MVP)  
> **Última actualización:** 2026-04-07  
> **Autor:** Lead Solutions Architect

---

## 1. Visión General del Sistema

Finanzas App es un ecosistema que permite a usuarios colombianos capturar sus gastos e ingresos enviando fotos de comprobantes bancarios (Nequi, Daviplata, Bancolombia) por WhatsApp. Un motor de IA (Gemini 1.5 Flash) extrae los datos automáticamente. Una App React+Capacitor sirve como dashboard de control presupuestal.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ARQUITECTURA E2E                             │
│                                                                     │
│  [Usuario]                                                          │
│     │                                                               │
│     ├──► [WhatsApp] ──► [Meta Webhook] ──► [Django API]             │
│     │                                       │                       │
│     │                                       ├──► [Gemini 1.5 Flash] │
│     │                                       │       (OCR/IA)        │
│     │                                       │                       │
│     │                                       ├──► [PostgreSQL]       │
│     │                                       │       (Datos)         │
│     │                                       │                       │
│     │                                       ├──► [Media Storage]    │
│     │                                       │       (S3/Local)      │
│     │                                       │                       │
│     └──► [App React + Capacitor] ◄──────────┘                       │
│              (Dashboard Visual)         (REST API + JWT)            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Stack Tecnológico

| Capa             | Tecnología                        | Versión Mínima |
|------------------|-----------------------------------|----------------|
| Backend / API    | Django + Django REST Framework     | 5.1 / 3.15     |
| Base de Datos    | PostgreSQL                        | 16             |
| Frontend / App   | React + TypeScript + Tailwind CSS | 18 / 5.x / 4.x|
| Router Frontend  | React Router                      | 7.x            |
| UI Components    | Radix UI + Sonner + Recharts      | —              |
| Empaquetado Móvil| Capacitor (Ionic)                 | 6.x (pendiente)|
| IA / OCR         | Google Gemini 1.5 Flash API       | v1             |
| Canal de Entrada | WhatsApp Business API (Meta Cloud)| v20.0          |
| Auth             | JWT (djangorestframework-simplejwt)| 5.x           |
| Media Storage    | AWS S3 / Cloudflare R2            | —              |
| CI/CD            | GitHub Actions                    | —              |

---

## 3. Flujo Extremo a Extremo (E2E) con Manejo de Errores

### 3.1 Flujo Principal: Comprobante vía WhatsApp

```
1. Usuario envía imagen de comprobante por WhatsApp
2. Meta Cloud API envía POST al Webhook Django (/api/whatsapp/webhook/)
3. Django descarga la imagen vía Meta Graph API (GET media URL)
4. Django envía imagen a Gemini 1.5 Flash para extracción OCR
5. Gemini devuelve JSON estructurado con datos del comprobante
6. Django valida JSON:
   a. Verifica campos obligatorios (monto, referencia, fecha, entidad)
   b. Busca duplicados por referencia_bancaria
   c. Encripta datos sensibles (monto, referencia)
7. Django guarda Transaction en PostgreSQL
8. Django almacena imagen original en S3/Storage
9. Django responde al usuario por WhatsApp con Interactive Message:
   - Botón "✅ Correcto" → confirma y guarda definitivamente
   - Botón "❌ Incorrecto" → marca como pendiente de revisión
10. Usuario confirma → Transaction.status = 'confirmed'
```

### 3.2 Tabla de Errores y Resiliencia

| Punto de Fallo                  | Error                              | Estrategia de Resiliencia                                                                 |
|---------------------------------|------------------------------------|-------------------------------------------------------------------------------------------|
| **Meta API caída**              | Webhook no llega                   | Meta tiene retry automático (hasta 7 días). Django registra `webhook_received_at` para detectar gaps. |
| **Descarga de imagen falla**    | HTTP 5xx de Graph API              | Retry con backoff exponencial (3 intentos, 2s/4s/8s). Si falla, responder al usuario: "No pude descargar tu imagen, intenta de nuevo." |
| **Gemini API caída/timeout**    | HTTP 503 / Timeout > 30s          | Circuit breaker: tras 5 fallos consecutivos, activar modo "manual" → guardar imagen sin procesar y notificar al usuario que será procesada después. |
| **Gemini devuelve JSON inválido**| Parsing error                     | Validación con schema JSON. Si falla, reintentar 1 vez con prompt reforzado. Si falla de nuevo, marcar como `needs_manual_review`. |
| **Imagen borrosa/ilegible**     | Gemini devuelve `error: low_quality`| Responder: "La imagen no es clara. ¿Puedes enviar otra foto del comprobante?" |
| **Comprobante duplicado**       | `referencia_bancaria` ya existe    | Responder: "Este comprobante ya fue registrado el [fecha]. ¿Necesitas algo más?" |
| **PostgreSQL caída**            | Connection refused                 | Health check cada 30s. Cola de reintentos en memoria (max 50 transacciones). Alerta a admin. |
| **S3/Storage caída**            | Upload falla                       | Guardar imagen temporalmente en disco local. Job de sincronización cada 5 min. |
| **JWT expirado (App)**          | 401 Unauthorized                   | Refresh token automático. Si refresh también expira, redirigir a login. |

### 3.3 Diagrama de Resiliencia (Circuit Breaker para Gemini)

```python
# backend/core/services/circuit_breaker.py

import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"        # Funcionando normal
    OPEN = "open"            # Cortado — no intenta llamar a Gemini
    HALF_OPEN = "half_open"  # Probando si Gemini ya se recuperó

class GeminiCircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Uso:
gemini_breaker = GeminiCircuitBreaker()
```

---

## 4. Seguridad

### 4.1 Clasificación de Datos

| Tipo              | Categoría           | Tratamiento                                    | Ejemplos                              |
|-------------------|----------------------|------------------------------------------------|---------------------------------------|
| **Dato Sensible** | PII Financiero       | Encriptación AES-256 en reposo + TLS en tránsito| Monto, referencia bancaria, saldo     |
| **Dato Sensible** | PII Personal         | Encriptación AES-256 en reposo                 | Número de celular, nombre completo    |
| **Dato Contable** | No sensible          | Texto plano en DB (pero acceso controlado)     | Categoría, fecha, tipo de transacción |
| **Dato Público**  | Metadata del sistema | Sin encriptación especial                      | Timestamps, IDs internos, estados     |

### 4.2 Protocolo de Encriptación AES-256

```python
# backend/core/encryption.py

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class FieldEncryptor:
    """
    Encripta/desencripta campos individuales usando AES-256-GCM.
    La clave se almacena en variable de entorno, NUNCA en código.
    """

    def __init__(self):
        key_b64 = os.environ.get('FIELD_ENCRYPTION_KEY')
        if not key_b64:
            raise ValueError("FIELD_ENCRYPTION_KEY no está configurada")
        self.key = base64.b64decode(key_b64)
        if len(self.key) != 32:
            raise ValueError("La clave debe tener exactamente 32 bytes (256 bits)")

    def encrypt(self, plaintext: str) -> str:
        """Encripta un string y devuelve base64(nonce + ciphertext)."""
        nonce = os.urandom(12)
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt(self, encrypted_b64: str) -> str:
        """Desencripta un string previamente encriptado."""
        raw = base64.b64decode(encrypted_b64)
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self.key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')


# Generar clave nueva (ejecutar UNA sola vez):
# python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

### 4.3 Campo Encriptado en Django Model

```python
# backend/core/fields.py

from django.db import models
from .encryption import FieldEncryptor

class EncryptedCharField(models.CharField):
    """Campo que se encripta automáticamente al guardar y desencripta al leer."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 512)  # Ciphertext es más largo
        super().__init__(*args, **kwargs)
        self._encryptor = None

    @property
    def encryptor(self):
        if self._encryptor is None:
            self._encryptor = FieldEncryptor()
        return self._encryptor

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encryptor.encrypt(str(value))

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return self.encryptor.decrypt(value)
        except Exception:
            return value  # Fallback para datos migrados sin encriptar
```

### 4.4 Seguridad en Tránsito

```python
# backend/finanzas/settings.py — Fragmento de seguridad

# === HTTPS / TLS ===
SECURE_SSL_REDIRECT = True  # Redirigir HTTP → HTTPS
SECURE_HSTS_SECONDS = 31536000  # 1 año de HSTS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# === CORS (solo para la App) ===
CORS_ALLOWED_ORIGINS = [
    "https://app.finanzasapp.co",
    "capacitor://localhost",  # Capacitor iOS
    "http://localhost",       # Capacitor Android
]

# === Rate Limiting ===
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/hour',
        'user': '200/hour',
        'whatsapp_webhook': '500/hour',
    }
}
```

### 4.5 Verificación del Webhook de Meta

```python
# backend/whatsapp/views.py — Verificación de firma

import hashlib
import hmac
from django.conf import settings

def verify_webhook_signature(request) -> bool:
    """
    Verifica que el request realmente viene de Meta.
    Meta firma cada request con HMAC-SHA256 usando el App Secret.
    """
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not signature.startswith('sha256='):
        return False

    expected_sig = hmac.new(
        settings.META_APP_SECRET.encode('utf-8'),
        request.body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature[7:], expected_sig)
```

---

## 5. Variables de Entorno Requeridas

```bash
# .env.example — NUNCA commitear .env real

# === Django ===
DJANGO_SECRET_KEY=cambiar-por-clave-segura-generada
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.finanzasapp.co

# === Base de Datos ===
DATABASE_URL=postgresql://user:password@localhost:5432/finanzas_db

# === Encriptación ===
FIELD_ENCRYPTION_KEY=base64-de-32-bytes-aqui

# === Gemini IA ===
GEMINI_API_KEY=AIza...tu-clave-gemini

# === WhatsApp / Meta ===
META_PHONE_NUMBER_ID=123456789
META_ACCESS_TOKEN=EAAx...tu-token
META_APP_SECRET=abc123...secreto
META_VERIFY_TOKEN=mi-token-de-verificacion-personalizado

# === Storage ===
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=secreto
AWS_STORAGE_BUCKET_NAME=finanzas-app-media
AWS_S3_REGION_NAME=us-east-1

# === JWT ===
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=30
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

---

## 6. Gobernanza de Documentación

### 6.1 Regla de Oro

> **Si durante el desarrollo una decisión de código contradice la documentación, el agente DEBE proponer la actualización del archivo `.md` correspondiente ANTES de proceder con el cambio de código.**

### 6.2 Protocolo de Actualización de Docs

Cuando el usuario solicita un **cambio estructural** (ej. "Cambiamos PostgreSQL por MongoDB"), el agente debe:

```
1. IDENTIFICAR archivos afectados
   → Revisar tabla de dependencias (sección 6.3)

2. REGISTRAR en 05_LOG_DE_DECISIONES_Y_CAMBIOS.md
   → Fecha, decisión, razón, archivos a modificar

3. ACTUALIZAR cada archivo afectado
   → Buscar todas las menciones de la tecnología/patrón anterior
   → Reemplazar con la nueva decisión
   → Adaptar código de ejemplo

4. VERIFICAR coherencia
   → Asegurarse de que ningún archivo referencia la decisión anterior

5. NOTIFICAR al usuario
   → Lista de cambios realizados en cada archivo
```

### 6.3 Mapa de Dependencias entre Documentos

```
00_SISTEMA_Y_RESILIENCIA.md (este archivo)
├── Referenciado por: TODOS los archivos
├── Afectado por: Cambios de stack, seguridad, arquitectura
│
01_BACKEND_EVOLUTIVO.md
├── Depende de: 00 (stack, seguridad)
├── Afectado por: Cambios de DB, modelos, auth
│
02_IA_OCR_MAESTRO.md
├── Depende de: 00 (stack IA), 01 (modelo Transaction)
├── Afectado por: Cambios de proveedor IA, formato de datos
│
03_WHATSAPP_UX_FLOW.md
├── Depende de: 00 (stack WhatsApp), 01 (modelos), 02 (OCR)
├── Afectado por: Cambios de canal, flujo UX, API Meta
│
04_FRONTEND_FIGMA_TO_CODE.md
├── Depende de: 00 (stack frontend), 01 (API endpoints)
├── Afectado por: Cambios de framework frontend, diseño
│
05_LOG_DE_DECISIONES_Y_CAMBIOS.md
├── Referenciado por: Agente antes de cada decisión
├── Solo se añaden registros, NUNCA se eliminan
│
06_CHECKPOINT_Y_CONTEXTO_ACTUAL.md
├── Depende de: TODOS (refleja estado actual)
├── Se actualiza al final de cada sesión de trabajo
```

### 6.4 Convención de Versionado de Docs

- **Patch** (x.x.X): Corrección de typos, mejora de ejemplos → No requiere log
- **Minor** (x.X.0): Nuevo endpoint, nueva categoría, ajuste de lógica → Registrar en log
- **Major** (X.0.0): Cambio de tecnología, reestructuración de modelos → Registrar + revisión completa

---

## 7. Estructura de Directorios del Proyecto

```
FinanzasApp/
├── docs_mvp/                          # ← Esta documentación
│   ├── 00_SISTEMA_Y_RESILIENCIA.md
│   ├── 01_BACKEND_EVOLUTIVO.md
│   ├── 02_IA_OCR_MAESTRO.md
│   ├── 03_WHATSAPP_UX_FLOW.md
│   ├── 04_FRONTEND_FIGMA_TO_CODE.md
│   ├── 05_LOG_DE_DECISIONES_Y_CAMBIOS.md
│   └── 06_CHECKPOINT_Y_CONTEXTO_ACTUAL.md
│
├── backend/                           # Django Project
│   ├── manage.py
│   ├── requirements.txt
│   ├── finanzas/                      # Django Settings Module
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── core/                          # App: Modelos, Encriptación, Utils
│   │   ├── models.py
│   │   ├── encryption.py
│   │   ├── fields.py
│   │   └── services/
│   │       ├── circuit_breaker.py
│   │       └── gemini_service.py
│   ├── whatsapp/                      # App: Webhook y Lógica WhatsApp
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── state_machine.py
│   │   └── meta_api.py
│   ├── transactions/                  # App: CRUD de Transacciones
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   └── users/                         # App: Auth, JWT, Perfil
│       ├── views.py
│       ├── serializers.py
│       └── urls.py
│
├── frontend/                          # React + Capacitor (generado por Figma Make + limpieza)
│   ├── package.json
│   ├── vite.config.ts
│   ├── postcss.config.mjs
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx                # Entry point
│   │   │   ├── routes.tsx             # React Router v7 (createBrowserRouter)
│   │   │   ├── pages/                 # 7 pantallas (Figma Make)
│   │   │   │   ├── Login.tsx
│   │   │   │   ├── VerifyOTP.tsx
│   │   │   │   ├── Onboarding.tsx
│   │   │   │   ├── AppLayout.tsx
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Transactions.tsx
│   │   │   │   ├── TransactionDetail.tsx
│   │   │   │   └── Profile.tsx
│   │   │   ├── components/
│   │   │   │   ├── BottomNav.tsx
│   │   │   │   ├── ui/                # Radix UI primitives (shadcn/ui)
│   │   │   │   └── figma/
│   │   │   ├── data/
│   │   │   │   └── mockData.ts        # Datos mock (reemplazar por API en Sprint 3)
│   │   │   └── utils/
│   │   │       └── format.ts          # formatCOP, formatPhone, maskPhone
│   │   └── styles/
│   │       ├── tailwind.css
│   │       ├── theme.css              # CSS variables (Tailwind v4)
│   │       ├── fonts.css
│   │       └── index.css
│   │
│   │   # --- A CREAR EN SPRINT 3 (integración con backend) ---
│   │   # ├── hooks/                   # useAuth, useDashboard, useTransactions
│   │   # ├── services/api.ts          # API client con JWT refresh
│   │   # ├── types/index.ts           # TypeScript interfaces
│   │   # └── constants/categories.ts  # Mapa de categorías
│   └── capacitor.config.ts            # A CREAR al integrar Capacitor
│
├── .env.example
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
└── README.md
```

---

## 8. Checklist de Lanzamiento MVP

- [ ] Variables de entorno configuradas en producción
- [ ] PostgreSQL provisionado y migrado
- [ ] HTTPS configurado (Let's Encrypt / Cloudflare)
- [ ] Webhook de Meta verificado y registrado
- [ ] Gemini API key activa con billing habilitado
- [ ] S3 bucket creado con permisos correctos
- [ ] App compilada para Android (APK / AAB)
- [ ] Rate limiting verificado en producción
- [ ] Backup automático de DB configurado
- [ ] Monitoreo básico (health check endpoint)

---

*Documento regido por la Regla de Oro: toda contradicción código ↔ docs debe resolverse actualizando este archivo primero.*
