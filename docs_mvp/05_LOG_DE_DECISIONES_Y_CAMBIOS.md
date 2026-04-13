# 05 — LOG DE DECISIONES Y CAMBIOS

> **Proyecto:** Finanzas App  
> **Versión:** 1.0.0 (MVP)  
> **Última actualización:** 2026-04-07  
> **Propósito:** Evitar que la IA proponga soluciones que ya fueron descartadas o cambiadas previamente.

---

## Reglas de Este Archivo

1. **Solo se AÑADEN registros, NUNCA se eliminan.** Los registros descartados se marcan como `[REVERTIDO]` pero permanecen visibles.
2. **Cada decisión técnica significativa** debe registrarse antes de implementarse.
3. **El agente debe consultar este archivo** antes de proponer cambios para verificar que la propuesta no contradice una decisión previa.
4. **Formato de fecha:** YYYY-MM-DD

---

## Historial de Decisiones

| # | Fecha | Decisión Técnica | Razón del Cambio | Archivos Afectados | Estado |
|---|-------|------------------|------------------|--------------------|--------|
| 001 | 2026-04-07 | Stack seleccionado: Django + PostgreSQL + React + Capacitor + Gemini 1.5 Flash | Decisión fundacional del MVP. Django por velocidad de desarrollo, PostgreSQL por robustez, React por ecosistema, Capacitor para compilación nativa, Gemini Flash por costo/velocidad. | `00_SISTEMA_Y_RESILIENCIA.md` (§2) | ✅ VIGENTE |
| 002 | 2026-04-07 | Autenticación por JWT vinculado a número de celular (no email) | El público objetivo (usuarios de Nequi/Daviplata en Colombia) se identifica por celular, no por email. WhatsApp ya provee el número. | `01_BACKEND_EVOLUTIVO.md` (§4) | ✅ VIGENTE |
| 003 | 2026-04-07 | Encriptación AES-256-GCM para monto y referencia bancaria en reposo | Cumplimiento de mejores prácticas de seguridad financiera. Solo datos PII financieros se encriptan; datos contables (categoría, fecha) quedan en texto plano para permitir queries eficientes. | `00_SISTEMA_Y_RESILIENCIA.md` (§4), `01_BACKEND_EVOLUTIVO.md` (§1.4) | ✅ VIGENTE |
| 004 | 2026-04-07 | `referencia_bancaria` como UNIQUE constraint para deduplicación | Solución más simple y robusta para evitar duplicados cuando el usuario reenvía el mismo comprobante. Race conditions manejadas con IntegrityError catch. | `01_BACKEND_EVOLUTIVO.md` (§3) | ✅ VIGENTE |
| 005 | 2026-04-07 | Gemini 1.5 Flash como motor OCR (no Tesseract, no GPT-4 Vision) | Gemini Flash ofrece mejor relación costo/velocidad para OCR. Tesseract requiere pre-procesamiento complejo para comprobantes. GPT-4V es más caro sin beneficio significativo para este caso. | `02_IA_OCR_MAESTRO.md` (§1, §2) | ✅ VIGENTE |
| 006 | 2026-04-07 | Circuit Breaker para llamadas a Gemini API | Protege el sistema si Gemini cae. Tras 5 fallos consecutivos, activa modo manual (guardar imagen sin procesar). Recovery timeout de 60s. | `00_SISTEMA_Y_RESILIENCIA.md` (§3.3) | ✅ VIGENTE |
| 007 | 2026-04-07 | Categorización por keywords en destinatario (no ML) | Para MVP, un motor de reglas basado en keywords es suficiente y determinístico. ML de categorización se considerará en V2 cuando haya datos suficientes. | `02_IA_OCR_MAESTRO.md` (§5) | ✅ VIGENTE |
| 008 | 2026-04-07 | Máquina de estados en cache (Redis) para conversación WhatsApp | Estado de conversación efímero (TTL 30 min). No justifica tabla en DB. Si Redis cae, el peor caso es pedir al usuario que reenvíe la imagen. | `03_WHATSAPP_UX_FLOW.md` (§1) | ✅ VIGENTE |
| 009 | 2026-04-07 | Solo light mode en MVP (no dark mode) | Reducir scope de diseño y CSS. Dark mode planificado para V2. | `04_FRONTEND_FIGMA_TO_CODE.md` (§1.1) | ✅ VIGENTE |
| 010 | 2026-04-07 | Entidades bancarias iniciales: Nequi, Daviplata, Bancolombia | Las 3 entidades más usadas en Colombia para pagos digitales. Escalable vía prompt de Gemini + nuevo valor en TextChoices. | `02_IA_OCR_MAESTRO.md` (§1.1, §7) | ✅ VIGENTE |
| 011 | 2026-04-07 | Actualizar stack frontend: Tailwind v4, React Router v7, Sonner, Radix UI | Figma Make generó el proyecto con estas versiones más recientes. Son mejoras sobre lo documentado originalmente (TW3, RR6). Se adoptan tal cual. MUI/Emotion incluidos por Figma Make pero pendientes de limpiar (no usados activamente). | `00_SISTEMA_Y_RESILIENCIA.md` (§2), `04_FRONTEND_FIGMA_TO_CODE.md` (§2, §3.2) | ✅ VIGENTE |
| 012 | 2026-04-07 | Estructura frontend: `frontend/src/app/` (generada por Figma Make) | Figma Make genera estructura `src/app/pages/`, `src/app/components/`, `src/app/data/`, `src/app/utils/`. Se adopta como base y se mueve a `frontend/`. Los módulos documentados (hooks, services, types, constants) se crearán en Sprint 3 durante integración. | `00_SISTEMA_Y_RESILIENCIA.md` (§7), `04_FRONTEND_FIGMA_TO_CODE.md` (§2) | ✅ VIGENTE |
| 013 | 2026-04-07 | Archivos de Figma Make movidos de raíz a `frontend/` | Mantener separación clara backend/frontend según arquitectura documentada. Los archivos generados (package.json, vite.config.ts, src/, etc.) ahora viven en `frontend/`. | `00_SISTEMA_Y_RESILIENCIA.md` (§7), `06_CHECKPOINT` | ✅ VIGENTE |
| 014 | 2026-04-07 | Endpoint `/api/auth/phone/request-otp/` añadido (no estaba en diseño original) | El flujo de auth requiere un paso previo para solicitar el OTP antes de verificarlo. El doc original solo tenía `/api/auth/phone/` para verificar. Se añade el endpoint de solicitud como paso 1 del flujo. | `01_BACKEND_EVOLUTIVO.md` (§4.4, §5.1) | ✅ VIGENTE |
| 015 | 2026-04-07 | Profile endpoint movido a `/api/auth/profile/` (era `/api/profile/`) | Profile pertenece lógicamente al módulo de auth/users, no a un módulo independiente. Al incluir `users.urls` bajo `api/auth/`, el profile queda en `/api/auth/profile/`. Más coherente con la estructura de apps. | `01_BACKEND_EVOLUTIVO.md` (§5.1) | ✅ VIGENTE |
| 016 | 2026-04-07 | SQLite como DB de desarrollo, PostgreSQL configurable vía `.env` | Para desarrollo local no se requiere PostgreSQL instalado. `DATABASE_URL` en `.env` activa PostgreSQL automáticamente. Reduce fricción de onboarding para desarrollo. | `finanzas/settings.py`, `06_CHECKPOINT` | ✅ VIGENTE |
| 017 | 2026-04-07 | Cache OTP usa `DatabaseCache` en vez de Redis (MVP) | Redis añade complejidad de infraestructura para MVP. Django `DatabaseCache` es suficiente para OTP con TTL de 5 min y bajo volumen. Se migrará a Redis cuando se implemente la state machine de WhatsApp (Sprint 2). | `finanzas/settings.py` | ✅ VIGENTE |
| 018 | 2026-04-07 | State machine de WhatsApp usa `DatabaseCache` (mismo que OTP) | Para MVP, el volumen es bajo y `DatabaseCache` es suficiente para la state machine de conversación (TTL 30 min). Redis se considerará cuando el volumen lo justifique. Contradice parcialmente decisión 017 que prometía migrar a Redis en Sprint 2, pero se prioriza simplicidad. | `whatsapp/state_machine.py`, `finanzas/settings.py` | ✅ VIGENTE |
| 019 | 2026-04-07 | Webhook WhatsApp usa `@csrf_exempt` + Django nativo (no DRF) | El webhook de Meta no envía JWT ni cookies — no necesita DRF. `@csrf_exempt` con `@require_http_methods` es más ligero y directo. La verificación se hace vía HMAC-SHA256 del App Secret. | `whatsapp/views.py` | ✅ VIGENTE |
| 020 | 2026-04-07 | AuthProvider context pattern para compartir estado auth entre Login y VerifyOTP | Login captura el teléfono y solicita OTP, VerifyOTP necesita el teléfono para verificar. Un contexto React es más limpio que pasar state vía URL params o localStorage. AuthProvider envuelve el router en routes.tsx. | `src/hooks/useAuth.tsx`, `src/app/routes.tsx` | ✅ VIGENTE |
| 021 | 2026-04-07 | Crear index.html y main.tsx manualmente (Figma Make no los generó) | Figma Make genera componentes React pero no el punto de entrada de Vite (index.html) ni el mount point de React (main.tsx). Sin estos archivos el build falla. Se crearon siguiendo el patrón estándar de Vite + React. | `frontend/index.html`, `frontend/src/main.tsx` | ✅ VIGENTE |
| 022 | 2026-04-07 | Capacitor Preferences para almacenamiento de JWT tokens (no localStorage) | Capacitor Preferences es la API recomendada para apps móviles — funciona en iOS, Android y web. localStorage no es persistente en WebViews de algunos dispositivos. Tokens (access + refresh) se almacenan/leen de forma async. | `src/utils/storage.ts`, `src/hooks/useAuth.tsx`, `src/services/api.ts` | ✅ VIGENTE |
| 023 | 2026-04-07 | ApiClient singleton con JWT auto-refresh en interceptor | Un solo cliente API con refresh automático en 401: intenta renovar el token con el refresh token, si falla redirige a login. Evita duplicar lógica de auth en cada hook. Base URL configurable vía `VITE_API_URL`. | `src/services/api.ts` | ✅ VIGENTE |
| 024 | 2026-04-07 | 18 dependencias de Figma Make eliminadas (MUI, Emotion, canvas-confetti, etc.) | Figma Make incluyó dependencias que no se usan en ningún componente: Material UI, Emotion, canvas-confetti, react-dnd, cmdk, vaul, embla-carousel, react-slick, next-themes, date-fns, react-day-picker, react-hook-form, react-popper, react-resizable-panels, react-responsive-masonry, @popperjs/core. Eliminadas para reducir bundle y claridad. | `frontend/package.json` | ✅ VIGENTE |
| 025 | 2026-04-07 | mockData.ts queda como archivo huérfano (no eliminado) | Tras integrar todas las páginas con API real, `src/app/data/mockData.ts` ya no es importado por ningún componente. Se deja en el proyecto como referencia de la estructura de datos pero puede eliminarse en cualquier momento. | `src/app/data/mockData.ts` | ✅ VIGENTE |
| 026 | 2026-04-07 | pytest + pytest-django como framework de tests (no unittest) | pytest tiene fixtures composables, auto-discovery, marks, y sintaxis más limpia que unittest. pytest-django agrega el mark `django_db` y fixtures (`client`, `settings`). 95 tests organizados en tests/test_{app}.py + conftest.py raíz. | `backend/pytest.ini`, `backend/conftest.py`, `backend/tests/`, `backend/requirements.txt` | ✅ VIGENTE |
| 027 | 2026-04-07 | Suprimir FutureWarning de google.generativeai en import | El paquete `google.generativeai` (deprecated) emite FutureWarning a stderr al importarse. PowerShell interpreta stderr como error y asigna exit code 1, rompiendo `manage.py runserver`. Fix: `warnings.catch_warnings()` + `filterwarnings("ignore", category=FutureWarning)` envuelve el import. Migración a `google.genai` planificada para Sprint 4. | `core/services/gemini_service.py` | ✅ VIGENTE |
| 028 | 2026-04-07 | Dockerfile multi-stage con python:3.12-slim + gunicorn | Imagen base `python:3.12-slim` para tamaño reducido. Se instala solo `libpq-dev` para psycopg2. Gunicorn con 3 workers y timeout 120s. docker-compose.yml orquesta PostgreSQL 16 + backend con healthcheck en servicio db. | `backend/Dockerfile`, `docker-compose.yml`, `.dockerignore` | ✅ VIGENTE |

---

## Decisiones Descartadas / Alternativas Evaluadas

| Alternativa | Razón de Descarte | Fecha | Podría Reconsiderarse Si... |
|-------------|-------------------|-------|------------------------------|
| Tesseract OCR local | Requiere pre-procesamiento complejo (binarización, corrección de perspectiva). Muy frágil con capturas de pantalla de apps bancarias. | 2026-04-07 | Se necesite procesamiento offline sin internet. |
| MongoDB en lugar de PostgreSQL | Para el modelo relacional de User→Profile→Transaction, PostgreSQL es más natural. MongoDB sería útil si los comprobantes tuvieran esquemas muy variables. | 2026-04-07 | Se necesite almacenar documentos con estructura muy dinámica. |
| Firebase Auth | Agrega dependencia a Google Cloud y complica la vinculación celular→JWT. Django SimpleJWT es más directo para nuestro caso. | 2026-04-07 | Se necesite auth social (Google, Facebook) además de celular. |
| Flutter en lugar de React+Capacitor | Flutter tiene mejor performance nativo pero el equipo tiene más experiencia en React. | 2026-04-07 | Se requiera performance nativo crítico (animaciones complejas, AR). |
| Webhook async con Celery | Para MVP, el procesamiento síncrono en el webhook es aceptable (Gemini responde en ~2-5s). Celery agrega complejidad operacional. | 2026-04-07 | El volumen de mensajes supere 100/minuto o el procesamiento tome >10s. |

---

## Template para Nuevas Entradas

```markdown
| XXX | YYYY-MM-DD | [Descripción de la decisión] | [Por qué se tomó esta decisión] | `archivo.md` (§sección) | ✅ VIGENTE |
```

Para marcar una decisión como revertida:
```markdown
| XXX | YYYY-MM-DD | [REVERTIDO] Descripción original | Revertido el YYYY-MM-DD. Razón: [explicación]. Ver decisión #YYY. | `archivos` | ❌ REVERTIDO |
```

---

*Este archivo es append-only. Los registros NUNCA se eliminan. Decisiones revertidas se marcan con `[REVERTIDO]` y se referencia la nueva decisión.*
