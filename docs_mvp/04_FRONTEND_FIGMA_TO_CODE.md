# 04 — FRONTEND: FIGMA TO CODE (App de Visualización)

> **Proyecto:** Finanzas App  
> **Versión:** 1.0.0 (MVP)  
> **Última actualización:** 2026-04-07  
> **Referencia:** [00_SISTEMA_Y_RESILIENCIA.md](./00_SISTEMA_Y_RESILIENCIA.md) | [01_BACKEND_EVOLUTIVO.md](./01_BACKEND_EVOLUTIVO.md)

---

## 1. Prompt para Figma Make (Generación de UI)

### 1.1 Prompt Maestro — Copiar y pegar en Figma Make

```text
Diseña una aplicación móvil de gestión financiera personal llamada "Finanzas App".
El diseño debe ser moderno, limpio y funcional, optimizado para mobile-first.

PALETA DE COLORES:
- Primario: #6366F1 (Indigo 500 — acción principal, botones, acentos)
- Secundario: #10B981 (Emerald 500 — ingresos, positivo, ahorro)
- Peligro: #EF4444 (Red 500 — gastos, alertas, negativo)
- Warning: #F59E0B (Amber 500 — advertencias, presupuesto al límite)
- Background: #F8FAFC (Slate 50)
- Surface: #FFFFFF
- Text Primary: #0F172A (Slate 900)
- Text Secondary: #64748B (Slate 500)
- Border: #E2E8F0 (Slate 200)

TIPOGRAFÍA:
- Font: Inter (Google Fonts)
- Headers: Bold, 20-28px
- Body: Regular, 14-16px
- Caption: Regular, 12px
- Montos de dinero: Semibold, 24-32px

PANTALLAS A DISEÑAR (7 pantallas):

────────────────────────────────────────
PANTALLA 1: REGISTRO / LOGIN (Ingreso de Celular)
────────────────────────────────────────
- Logo de Finanzas App centrado en la parte superior
- Ilustración financiera sutil (gráficos, monedas)
- Título: "Controla tus finanzas sin esfuerzo" (bold, centrado)
- Subtítulo: "Envía fotos de tus comprobantes por WhatsApp y nosotros hacemos el resto" (caption, gris, centrado)
- Campo de input: "Número de celular" con prefijo +57 y bandera 🇨🇴
  - Máscara de formato: +57 300 123 4567
  - Validación en tiempo real: borde rojo si el número no tiene 10 dígitos
- Botón CTA: "Continuar" (estilo primario, full-width, deshabilitado hasta que el número sea válido)
- Texto legal: "Al continuar, aceptas los Términos de Servicio y la Política de Privacidad" (caption, gris, con links subrayados)
- Nota: Este flujo es unificado — sirve tanto para registro como para login. Si el número no existe, se crea la cuenta automáticamente tras verificar el OTP.

────────────────────────────────────────
PANTALLA 2: VERIFICACIÓN OTP (Código de 6 dígitos)
────────────────────────────────────────
- Header: Botón back (←) en la esquina superior izquierda
- Ícono central: 💬 o ilustración de mensaje
- Título: "Ingresa el código de verificación" (bold, centrado)
- Subtítulo: "Enviamos un código de 6 dígitos al +57 300 *** 4567" (caption, gris, número parcialmente oculto)
- Input de 6 dígitos: 6 casillas individuales separadas, auto-focus en la primera
  - Cada casilla acepta 1 dígito numérico
  - Al completar las 6 casillas, se valida automáticamente
  - Borde indigo al enfocar, borde rojo si el código es incorrecto
- Estado de error: "Código incorrecto. Intenta de nuevo." (text-danger, aparece debajo de las casillas)
- Temporizador: "Reenviar código en 0:59" (caption, gris, cuenta regresiva desde 60s)
- Link: "Reenviar código" (aparece cuando el temporizador llega a 0, estilo link primario)
- Texto: "¿Número incorrecto? Cambiar" (caption, link gris que vuelve a Pantalla 1)
- Loading state: Spinner centrado con texto "Verificando..." mientras se valida el OTP

────────────────────────────────────────
PANTALLA 3: ONBOARDING (Configuración Financiera — solo para usuarios nuevos)
────────────────────────────────────────
- Header: Step indicator (dots): ● ○ ○ (paso 1 de 3) — o barra de progreso
- Paso 1/3 — Salario:
  - Ilustración sutil de billetera/salario
  - Título: "¿Cuál es tu salario mensual?" (bold)
  - Subtítulo: "Esto nos ayuda a calcular tu ahorro real" (caption, gris)
  - Input: Formato moneda COP con placeholder "$0" y formato automático (ej: al escribir 4500000 muestra $4,500,000)
  - Botón: "Siguiente" (estilo primario, full-width)
- Paso 2/3 — Presupuesto:
  - Ilustración sutil de alcancía/objetivo
  - Título: "¿Cuánto quieres gastar máximo al mes?" (bold)
  - Subtítulo: "Te avisaremos cuando estés cerca del límite" (caption, gris)
  - Input: Formato moneda COP
  - Sugerencia automática: "Sugerido: $3,000,000 (67% de tu salario)" (caption, verde, basado en el salario ingresado)
  - Botón: "Siguiente" (estilo primario)
- Paso 3/3 — Día de corte:
  - Ilustración sutil de calendario
  - Título: "¿Qué día te pagan?" (bold)
  - Subtítulo: "Así calculamos tu ciclo financiero mensual" (caption, gris)
  - Selector visual: Grid de días 1-31, el seleccionado con fondo indigo y texto blanco
  - Botón: "Comenzar 🚀" (estilo primario, full-width)
- Opción persistente: "Configurar después" (link text, gris, visible en los 3 pasos) — salta al Dashboard

────────────────────────────────────────
PANTALLA 4: DASHBOARD PRINCIPAL
────────────────────────────────────────
- Header: "Hola, [Nombre]" con avatar placeholder a la derecha
- Card principal grande (gradiente indigo sutil):
  - Label: "Ahorro del mes"
  - Monto grande: "$2,350,000" (verde si positivo, rojo si negativo)
  - Subtexto: "Salario: $4,500,000 — Gastos: $2,150,000"
- Barra de progreso de presupuesto:
  - Label: "Presupuesto: $3,000,000"
  - Barra visual con porcentaje (verde < 70%, amarillo 70-90%, rojo > 90%)
  - Texto: "Has usado el 72% de tu presupuesto"
- Sección "Gastos por Categoría":
  - Gráfico de dona/pie chart con las top 5 categorías
  - Leyenda debajo con color, nombre y monto
  - Categorías: Alimentación, Transporte, Hogar, Entretenimiento, Otros
- Botón flotante o sección final:
  - "📸 Registrar gasto vía WhatsApp" → deep link a WhatsApp

────────────────────────────────────────
PANTALLA 5: HISTORIAL DE TRANSACCIONES
────────────────────────────────────────
- Header: "Transacciones" con filtro por mes (selector)
- Tabs: "Todos" | "Gastos" | "Ingresos"
- Lista de transacciones, cada item:
  - Ícono de categoría (emoji o ícono) a la izquierda
  - Nombre del destinatario (bold)
  - Categoría y entidad bancaria (caption, gris)
  - Fecha (caption, derecha)
  - Monto (derecha, rojo para gastos, verde para ingresos)
  - Indicador de confianza IA si < 0.8 (badge amarillo "⚠️ Verificar")
- Al tocar una transacción → Detalle (pantalla 6)
- Estado vacío: "Aún no tienes transacciones. Envía tu primer comprobante por WhatsApp 📸"

────────────────────────────────────────
PANTALLA 6: DETALLE DE TRANSACCIÓN
────────────────────────────────────────
- Header: "Detalle" con botón back
- Imagen del comprobante original (thumbnail expandible)
- Card de datos:
  - Monto (grande, bold)
  - Destinatario
  - Entidad bancaria (con logo/ícono)
  - Categoría (con ícono)  — editable (selector)
  - Referencia bancaria
  - Fecha y hora
  - Estado: Confirmado ✅ / Pendiente ⏳ / Rechazado ❌
  - Confianza IA: Barra visual (verde/amarillo/rojo)
- Botones de acción:
  - "Cambiar categoría" (outline)
  - "Eliminar transacción" (text, rojo)

────────────────────────────────────────
PANTALLA 7: PERFIL Y CONFIGURACIÓN
────────────────────────────────────────
- Avatar placeholder con número de celular
- Card "Mi Plan Financiero":
  - Salario mensual (editable)
  - Presupuesto mensual (editable)
  - Día de corte (editable)
- Sección "Estadísticas":
  - Total de transacciones registradas
  - Meses usando la app
  - Confianza promedio de la IA
- Botones:
  - "Exportar datos (CSV)" (outline)
  - "Cerrar sesión" (text, rojo)

────────────────────────────────────────
FLUJOS DE NAVEGACIÓN (PROTOTYPING)
────────────────────────────────────────
Conectar las pantallas con interacciones para crear un prototipo navegable.
Cada conexión usa la convención: [Elemento] → Acción → [Destino]

FLUJO DE AUTENTICACIÓN (lineal):
  Pantalla 1 → Botón "Continuar" → Pantalla 2 (OTP)
  Pantalla 2 → OTP válido + usuario NUEVO → Pantalla 3 (Onboarding paso 1)
  Pantalla 2 → OTP válido + usuario EXISTENTE → Pantalla 4 (Dashboard)
  Pantalla 2 → Link "¿Número incorrecto? Cambiar" → Pantalla 1 (back)
  Pantalla 3 → Botón "Siguiente" (paso 1→2→3) → Avanza dentro del Onboarding
  Pantalla 3 → Botón "Comenzar 🚀" (paso 3) → Pantalla 4 (Dashboard)
  Pantalla 3 → Link "Configurar después" (cualquier paso) → Pantalla 4 (Dashboard)

FLUJO PRINCIPAL (bottom nav — siempre visible en pantallas 4, 5, 7):
  Tab "Dashboard" → Pantalla 4
  Tab "Transacciones" → Pantalla 5
  Tab "Perfil" → Pantalla 7
  El tab activo se resalta con color primario (#6366F1) y los inactivos en gris (#64748B)

FLUJO DE TRANSACCIONES:
  Pantalla 5 → Tap en cualquier transacción de la lista → Pantalla 6 (Detalle)
  Pantalla 6 → Botón back (←) → Pantalla 5 (vuelve a la lista)
  Pantalla 6 → Botón "Cambiar categoría" → Overlay: selector de categorías (bottom sheet)
  Pantalla 6 → Botón "Eliminar transacción" → Overlay: modal de confirmación "¿Estás seguro?"

FLUJO DE PERFIL:
  Pantalla 7 → Tap en "Salario mensual" → Overlay: input editable (bottom sheet)
  Pantalla 7 → Botón "Cerrar sesión" → Overlay: confirmación → Pantalla 1 (Login)

FLUJO EXTERNO:
  Pantalla 4 → Botón "📸 Registrar gasto vía WhatsApp" → Abrir WhatsApp (link externo)

────────────────────────────────────────
ESTADOS DE COMPONENTES (VARIANTES)
────────────────────────────────────────
Diseñar cada componente interactivo con TODAS sus variantes visibles como frames separados.

BOTÓN PRIMARIO (4 estados — organizar como componente con variantes):
  • Default: Fondo #6366F1, texto blanco, border-radius 12px
  • Hover/Pressed: Fondo #4F46E5 (más oscuro)
  • Disabled: Fondo #C7D2FE (indigo claro), texto #94A3B8, no clickeable
  • Loading: Fondo #6366F1 con spinner blanco centrado, sin texto

BOTÓN OUTLINE (3 estados):
  • Default: Borde #6366F1, texto #6366F1, fondo transparente
  • Hover/Pressed: Fondo #EEF2FF (indigo-50)
  • Disabled: Borde #E2E8F0, texto #94A3B8

BOTÓN DESTRUCTIVO (texto rojo):
  • Default: Sin borde, texto #EF4444
  • Hover/Pressed: Fondo #FEF2F2 (red-50)

INPUT DE TEXTO (5 estados):
  • Empty: Borde #E2E8F0, placeholder en #94A3B8
  • Focused: Borde #6366F1 (2px), sombra sutil indigo
  • Filled: Borde #E2E8F0, texto #0F172A
  • Error: Borde #EF4444, mensaje de error en rojo debajo
  • Disabled: Fondo #F1F5F9, texto #94A3B8

INPUT OTP (casilla individual — 4 estados):
  • Empty: Borde #E2E8F0, fondo blanco
  • Focused: Borde #6366F1, sombra sutil
  • Filled: Borde #E2E8F0, dígito centrado en #0F172A, font semibold 24px
  • Error: Borde #EF4444, fondo #FEF2F2

ITEM DE TRANSACCIÓN (2 estados):
  • Default: Fondo blanco
  • Pressed: Fondo #F8FAFC (slate-50), transición sutil

TAB DE BOTTOM NAV (2 estados):
  • Activo: Ícono + texto en #6366F1, dot indicator arriba
  • Inactivo: Ícono + texto en #94A3B8

TAB DE FILTRO (Todos/Gastos/Ingresos — 2 estados):
  • Activo: Fondo #6366F1, texto blanco, border-radius 20px (pill)
  • Inactivo: Fondo transparente, texto #64748B

────────────────────────────────────────
OVERLAYS Y FEEDBACK (FRAMES ADICIONALES)
────────────────────────────────────────
Diseñar como frames separados que aparecen como overlays en el prototipo:

OVERLAY 1 — Toast de éxito:
  • Barra en la parte superior, fondo #ECFDF5, borde izquierdo verde 4px
  • Ícono ✅ + texto: "Transacción registrada correctamente"
  • Auto-dismiss en 3 segundos

OVERLAY 2 — Toast de error:
  • Igual que éxito pero fondo #FEF2F2, borde rojo
  • Ícono ❌ + texto: "Error al procesar. Intenta de nuevo."

OVERLAY 3 — Modal de confirmación (Eliminar transacción):
  • Fondo oscuro semitransparente (overlay dimming)
  • Card centrada, fondo blanco, border-radius 16px
  • Título: "¿Eliminar transacción?" (bold)
  • Subtítulo: "Esta acción no se puede deshacer" (caption, gris)
  • Botones: "Cancelar" (outline) | "Eliminar" (fondo rojo, texto blanco)

OVERLAY 4 — Bottom Sheet: Selector de categorías:
  • Slide up desde abajo, fondo blanco, border-radius top 16px
  • Handle bar gris en la parte superior (indicador de drag)
  • Título: "Seleccionar categoría"
  • Lista vertical con ícono emoji + nombre de categoría
  • Al seleccionar → cierra y actualiza la categoría

OVERLAY 5 — Bottom Sheet: Editar campo de perfil:
  • Slide up, fondo blanco
  • Título: "Editar salario mensual"
  • Input con valor actual pre-llenado
  • Botones: "Cancelar" | "Guardar"

OVERLAY 6 — Confirmación de cierre de sesión:
  • Modal centrado
  • Texto: "¿Cerrar sesión?"
  • Botones: "Cancelar" (outline) | "Cerrar sesión" (rojo)

────────────────────────────────────────
ESTADOS DE PANTALLA (VARIANTES POR PANTALLA)
────────────────────────────────────────
Para cada pantalla principal, diseñar las siguientes variantes como frames separados:

PANTALLA 4 (Dashboard):
  • Con datos: Vista normal con KPIs, gráficos y transacciones
  • Loading: Skeleton shimmer en cada card (rectángulos grises animados con border-radius)
  • Sin datos (primer uso): Card con ilustración + "¡Bienvenido! Envía tu primer comprobante por WhatsApp para empezar 📸"

PANTALLA 5 (Transacciones):
  • Con datos: Lista de transacciones
  • Loading: 5 skeleton items en la lista
  • Sin datos: Ilustración centrada + "Aún no tienes transacciones" + botón "Abrir WhatsApp"

PANTALLA 2 (OTP):
  • Default: Casillas vacías esperando input
  • Loading: Spinner + "Verificando..."
  • Error: Casillas con borde rojo + mensaje de error
  • Reenviar disponible: Temporizador en 0:00, link "Reenviar código" visible y clickeable

────────────────────────────────────────
DATOS DE EJEMPLO (CONTENIDO REALISTA)
────────────────────────────────────────
Usar estos datos para llenar las pantallas y que se vean realistas:

Dashboard:
  • Salario: $4,500,000
  • Gastos totales: $2,150,000
  • Ahorro: $2,350,000
  • Presupuesto: $3,000,000 (72% usado)
  • Categorías: Alimentación $680,000 | Transporte $420,000 | Hogar $510,000 | Entretenimiento $320,000 | Otros $220,000

Transacciones (mínimo 6 items en la lista):
  1. 🍔 Rappi Colombia — Alimentación · Nequi — 7 abr — -$45,000
  2. 🚗 Uber — Transporte · Daviplata — 6 abr — -$23,500
  3. 🏠 Almacenes Éxito — Hogar · Bancolombia — 5 abr — -$187,000
  4. 💡 EPM Medellín — Servicios · Bancolombia — 4 abr — -$95,000
  5. 🎮 Netflix — Entretenimiento · Nequi — 3 abr — -$38,900
  6. 💰 Empresa XYZ — Ingreso · Bancolombia — 1 abr — +$4,500,000 (verde)

Perfil:
  • Número: +57 300 123 4567
  • Salario: $4,500,000
  • Presupuesto: $3,000,000
  • Día de corte: 1
  • Transacciones registradas: 47
  • Meses usando la app: 3
  • Confianza promedio IA: 94%

REGLAS DE DISEÑO:
- Bordes redondeados: 12-16px en cards, 8px en inputs
- Sombras sutiles: shadow-sm en cards
- Espaciado consistente: 16px de padding general, 12px entre elementos
- Responsive: Diseñar para 390px de ancho (iPhone 14 Pro)
- Dark mode: NO incluir en MVP (solo light mode)
- Animaciones: Indicar transiciones suaves entre pantallas (slide left/right para navegación, slide up para overlays)
- Bottom navigation bar con 3 tabs: Dashboard | Transacciones | Perfil
- Organizar todas las pantallas en un flujo horizontal de izquierda a derecha
- Usar Auto Layout en todos los frames para que los elementos sean responsive
- Crear un frame de componentes reutilizables (botones, inputs, cards, badges) como librería local
```

---

## 2. Estructura del Proyecto Frontend (Post-Figma Make)

> **Nota:** La estructura actual fue generada por Figma Make y movida a `frontend/`.  
> Los módulos marcados con ⏳ se crearán en Sprint 3 durante la integración con el backend.

```
frontend/
├── package.json                    # Dependencias (React 18, Tailwind 4, Radix UI, Recharts, Sonner)
├── vite.config.ts                  # Vite 6 + @tailwindcss/vite + alias @ → ./src
├── postcss.config.mjs
├── ATTRIBUTIONS.md                 # Atribuciones de Figma Make
├── guidelines/                     # Guidelines de Figma Make
│
├── src/
│   ├── app/
│   │   ├── App.tsx                 # Entry point (renderiza RouterProvider)
│   │   ├── routes.tsx              # React Router v7 — createBrowserRouter
│   │   │                           #   / → Login
│   │   │                           #   /verify → VerifyOTP
│   │   │                           #   /onboarding → Onboarding
│   │   │                           #   /app → AppLayout (Dashboard, Transactions, Profile)
│   │   │                           #   /transaction/:id → TransactionDetail
│   │   │
│   │   ├── pages/                  # Pantallas principales (7)
│   │   │   ├── Login.tsx           # Pantalla 1: Input +57 celular
│   │   │   ├── VerifyOTP.tsx       # Pantalla 2: OTP 6 dígitos + timer + error states
│   │   │   ├── Onboarding.tsx      # Pantalla 3: Salario → Presupuesto → Día de corte
│   │   │   ├── AppLayout.tsx       # Layout wrapper con BottomNav
│   │   │   ├── Dashboard.tsx       # Pantalla 4: Ahorro, presupuesto, PieChart, WhatsApp CTA
│   │   │   ├── Transactions.tsx    # Pantalla 5: Historial con filtro tabs + mes
│   │   │   ├── TransactionDetail.tsx # Pantalla 6: Detalle + confianza IA + category sheet
│   │   │   └── Profile.tsx         # Pantalla 7: Plan financiero + stats + logout
│   │   │
│   │   ├── components/
│   │   │   ├── BottomNav.tsx       # 3 tabs: Dashboard, Transacciones, Perfil
│   │   │   ├── ui/                 # Radix UI primitives (shadcn/ui — 48 componentes)
│   │   │   │   ├── button.tsx, input.tsx, dialog.tsx, sheet.tsx, ...
│   │   │   │   ├── sonner.tsx      # Toast notifications
│   │   │   │   ├── utils.ts        # cn() helper (clsx + tailwind-merge)
│   │   │   │   └── use-mobile.ts   # Hook para detectar mobile
│   │   │   └── figma/
│   │   │       └── ImageWithFallback.tsx
│   │   │
│   │   ├── data/
│   │   │   └── mockData.ts         # Transacciones, categorías, perfil mock
│   │   │                           # ⏳ Reemplazar por API calls en Sprint 3
│   │   │
│   │   └── utils/
│   │       └── format.ts           # formatCOP(), formatPhone(), maskPhone()
│   │
│   ├── styles/
│   │   ├── tailwind.css            # @import 'tailwindcss' (Tailwind v4 syntax)
│   │   ├── theme.css               # CSS custom properties (:root vars, @theme inline)
│   │   ├── fonts.css               # Inter font imports
│   │   └── index.css               # Global styles
│   │
│   └── imports/                    # Archivos de input de Figma Make
│       └── pasted_text/
│           └── finanzas-app-prompt.md
│
│   # --- A CREAR EN SPRINT 3 ---
│   # ├── hooks/                    # useAuth, useDashboard, useTransactions, useProfile
│   # ├── services/api.ts           # API client con JWT refresh (ver §5)
│   # ├── types/index.ts            # Interfaces TypeScript (ver §4)
│   # ├── utils/storage.ts          # Capacitor Preferences para tokens (ver §8)
│   # └── constants/categories.ts   # Mapa de categorías con íconos (ver §7)
│
├── capacitor.config.ts             # ⏳ A crear al integrar Capacitor
└── android/                        # ⏳ Generado por `npx cap add android`
```

### 2.1 Dependencias Actuales (Figma Make)

**Runtime:**
- `react` 18.3.1, `react-dom` 18.3.1, `react-router` 7.13.0
- `recharts` 2.15.2 (gráficos)
- `sonner` 2.0.3 (toasts)
- `input-otp` 1.4.2 (OTP input)
- `@radix-ui/*` (suite completa — componentes UI primitivos)
- `class-variance-authority`, `clsx`, `tailwind-merge` (utilidades CSS)
- `motion` 12.23.24 (animaciones)

**Dev:**
- `vite` 6.3.5, `@vitejs/plugin-react` 4.7.0
- `tailwindcss` 4.1.12, `@tailwindcss/vite` 4.1.12

**⚠️ Pendiente de limpiar en Sprint 3** (incluidas por Figma Make pero no usadas activamente):
- `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled`
- `canvas-confetti`, `react-dnd`, `react-slick`, `react-responsive-masonry`
- `cmdk`, `vaul`, `next-themes`, `embla-carousel-react`

### 2.2 Estado Actual del Frontend (localStorage)

Figma Make usa `localStorage` como store temporal. En Sprint 3 se migra a API + Capacitor Preferences:

| Key localStorage | Persistencia final | Migración |
|---|---|---|
| `finanzas_phone` | No persistir (viene del JWT) | Eliminar |
| `finanzas_onboarded` | `Profile.onboarding_completed` vía API | `GET /api/auth/profile/` |
| `finanzas_salary` | `Profile.salario_mensual` vía API | `PATCH /api/auth/profile/` |
| `finanzas_budget` | `Profile.presupuesto_mensual` vía API | `PATCH /api/auth/profile/` |
| `finanzas_cut_day` | `Profile.dia_corte` vía API | `PATCH /api/auth/profile/` |

---

## 3. Protocolo "Clean Code" — De Figma a VS Code

### 3.1 Checklist de Limpieza Post-Figma Make (Sprint 3)

Aplicar estos pasos al integrar el frontend con el backend real:

```markdown
□ 1. ELIMINAR dependencias no usadas del package.json
     ❌ @mui/material, @emotion/react, canvas-confetti, react-dnd, cmdk, vaul, react-slick, etc.
     ✅ Solo mantener: react, react-router, recharts, sonner, radix-ui (usados), tailwind, vite

□ 2. MANTENER estilos inline con hex (funcional)
     Los valores inline bg-[#6366F1] funcionan correctamente.
     Refactorizar a CSS variables en theme.css es OPCIONAL (V2).
     ⚠️ NO romper lo que ya funciona solo por purismo.

□ 3. TIPAR props con interfaces TypeScript
     ❌ function Card({ title, amount }) { ... }
     ✅ function Card({ title, amount }: CardProps) { ... }
     Nota: Figma Make ya tipó la mayoría de props correctamente.

□ 4. REEMPLAZAR mockData por API calls
     ❌ import { mockTransactions } from '../data/mockData'
     ✅ const { data, loading, error } = useTransactions()

□ 5. REEMPLAZAR localStorage por Capacitor Preferences + API
     ❌ localStorage.getItem('finanzas_salary')
     ✅ const { profile } = useProfile() // ← datos del API

□ 6. AGREGAR estados de carga y error reales
     Las pantallas ya tienen estructura para loading/error.
     Conectar con los hooks que manejan estados async.

□ 7. CREAR módulos pendientes
     - frontend/src/hooks/ (useAuth, useDashboard, useTransactions, useProfile)
     - frontend/src/services/api.ts (API client con JWT refresh)
     - frontend/src/types/index.ts (interfaces TypeScript)
     - frontend/src/utils/storage.ts (Capacitor Preferences)

□ 8. INSTALAR Capacitor
     npx cap init "Finanzas App" co.finanzasapp.app
     npx cap add android
     Crear capacitor.config.ts
```

### 3.2 Tailwind v4 — Configuración Actual

Figma Make generó el proyecto con **Tailwind CSS v4**, que usa un modelo distinto a v3:

- **Sin `tailwind.config.js`** — la configuración se hace con CSS (`@theme inline` en `theme.css`)
- **Plugin Vite** — `@tailwindcss/vite` en vez de PostCSS plugin
- **CSS variables** — todos los tokens están en `:root` como custom properties

```css
/* frontend/src/styles/tailwind.css */
@import 'tailwindcss' source(none);
@source '../**/*.{js,ts,jsx,tsx}';
@import 'tw-animate-css';
```

```css
/* frontend/src/styles/theme.css — extracto de tokens relevantes */
:root {
  --background: #ffffff;
  --foreground: oklch(0.145 0 0);
  --primary: #030213;
  --destructive: #d4183d;
  --border: rgba(0, 0, 0, 0.1);
  --radius: 0.625rem;
  /* ... más tokens en el archivo completo */
}
```

> **Nota para Sprint 3:** Los colores de la app (#6366F1, #10B981, etc.) están hardcoded como hex inline (`bg-[#6366F1]`), no como tokens del theme. Esto es funcional pero dificulta temas futuros. Se puede refactorizar opcionalmente agregando custom properties al theme.css.

---

## 4. Types TypeScript ⏳ A IMPLEMENTAR EN SPRINT 3

> **Estado:** No generados por Figma Make. Los tipos inline están en `mockData.ts` como `Transaction` interface.  
> Al integrar con el backend, crear `frontend/src/types/index.ts` con estas interfaces:

// === Auth ===
export interface AuthResponse {
  access: string;
  refresh: string;
  is_new_user: boolean;
  onboarding_completed: boolean;
}

// === Profile ===
export interface Profile {
  salario_mensual: string | null;
  presupuesto_mensual: string | null;
  dia_corte: number;
  onboarding_completed: boolean;
}

// === Transaction ===
export type TransactionType = 'gasto' | 'ingreso' | 'transferencia_propia';
export type TransactionStatus = 'pending' | 'confirmed' | 'rejected' | 'needs_review' | 'error';
export type BankEntity = 'nequi' | 'daviplata' | 'bancolombia' | 'otro';

export interface Transaction {
  id: number;
  tipo: TransactionType;
  entidad: BankEntity;
  categoria: string;
  destinatario: string;
  fecha_transaccion: string; // ISO 8601
  descripcion: string;
  estado: TransactionStatus;
  confianza_ia: number;
  monto_display: string;
  created_at: string; // ISO 8601
}

export interface TransactionDetail extends Transaction {
  image_url?: string;
  referencia_bancaria: string;
}

// === Dashboard ===
export interface DashboardSummary {
  ciclo: {
    inicio: string;
    fin: string;
  };
  salario: string;
  presupuesto: string;
  total_gastos: string;
  total_ingresos: string;
  ahorro_real: string;
  progreso_presupuesto: number;
  gastos_por_categoria: Record<string, string>;
  transacciones_count: number;
}

// === Categories ===
export interface CategoryInfo {
  id: string;
  label: string;
  icon: string;
  color: string;
}

// === API ===
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail?: string;
  message?: string;
  [key: string]: unknown;
}
```

---

## 5. API Client ⏳ A IMPLEMENTAR EN SPRINT 3

> **Estado:** No generado por Figma Make. Todas las pantallas usan `mockData.ts` + `localStorage`.  
> Al integrar con el backend, crear `frontend/src/services/api.ts` con este client:

import { AuthResponse, DashboardSummary, PaginatedResponse, Profile, Transaction, TransactionDetail } from '../types';
import { getToken, setTokens, clearTokens } from '../utils/storage';

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.finanzasapp.co';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = await getToken('access');
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle token refresh
    if (response.status === 401) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        // Retry original request with new token
        const newToken = await getToken('access');
        headers['Authorization'] = `Bearer ${newToken}`;
        const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
          ...options,
          headers,
        });
        if (!retryResponse.ok) {
          throw new Error(`API Error: ${retryResponse.status}`);
        }
        return retryResponse.json();
      } else {
        clearTokens();
        window.location.href = '/login';
        throw new Error('Session expired');
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  private async refreshToken(): Promise<boolean> {
    try {
      const refreshToken = await getToken('refresh');
      if (!refreshToken) return false;

      const response = await fetch(`${this.baseUrl}/api/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (!response.ok) return false;

      const data = await response.json();
      await setTokens(data.access, data.refresh);
      return true;
    } catch {
      return false;
    }
  }

  // === Auth ===
  async phoneAuth(phone_number: string, otp_code: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/phone/', {
      method: 'POST',
      body: JSON.stringify({ phone_number, otp_code }),
    });
  }

  // === Profile ===
  async getProfile(): Promise<Profile> {
    return this.request<Profile>('/api/auth/profile/');
  }

  async updateProfile(data: Partial<Profile>): Promise<Profile> {
    return this.request<Profile>('/api/auth/profile/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // === Dashboard ===
  async getDashboardSummary(): Promise<DashboardSummary> {
    return this.request<DashboardSummary>('/api/dashboard/summary/');
  }

  // === Transactions ===
  async getTransactions(page = 1, tipo?: string): Promise<PaginatedResponse<Transaction>> {
    const params = new URLSearchParams({ page: String(page) });
    if (tipo) params.set('tipo', tipo);
    return this.request<PaginatedResponse<Transaction>>(
      `/api/transactions/?${params.toString()}`
    );
  }

  async getTransaction(id: number): Promise<TransactionDetail> {
    return this.request<TransactionDetail>(`/api/transactions/${id}/`);
  }

  async updateTransaction(id: number, data: Partial<Transaction>): Promise<Transaction> {
    return this.request<Transaction>(`/api/transactions/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }
}

export const api = new ApiClient(API_BASE);
```

---

## 6. Utilidades de Formateo (Parcialmente Implementado)

> **Estado:** Figma Make generó `frontend/src/app/utils/format.ts` con `formatCOP()`, `formatPhone()`, `maskPhone()`.  
> En Sprint 3, reemplazar `formatCOP()` por `formatCurrency()` con `Intl.NumberFormat('es-CO')` y agregar helpers de fecha.
>
> **Actual (`format.ts`):**
> ```typescript
> export function formatCOP(amount: number): string {
>   const abs = Math.abs(amount);
>   return '$' + abs.toLocaleString('en-US');  // ← Cambiar a es-CO en Sprint 3
> }
> ```

Implementación completa para Sprint 3:

/**
 * Formatea un valor numérico como moneda colombiana.
 * Ejemplo: 2350000 → "$2,350,000"
 */
export function formatCurrency(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '$0';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

/**
 * Formatea una fecha ISO a formato legible.
 * Ejemplo: "2026-04-07T14:30:00" → "7 abr 2026, 2:30 p.m."
 */
export function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat('es-CO', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(date);
}

/**
 * Formatea solo la fecha sin hora.
 * Ejemplo: "2026-04-07T14:30:00" → "7 de abril de 2026"
 */
export function formatDateShort(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat('es-CO', {
    day: 'numeric',
    month: 'short',
  }).format(date);
}

/**
 * Retorna color CSS según el progreso del presupuesto.
 */
export function getBudgetColor(percentage: number): string {
  if (percentage < 70) return 'bg-success-500';
  if (percentage < 90) return 'bg-warning-500';
  return 'bg-danger-500';
}

/**
 * Retorna color del texto según tipo de transacción.
 */
export function getAmountColor(tipo: string): string {
  switch (tipo) {
    case 'gasto': return 'text-danger-500';
    case 'ingreso': return 'text-success-500';
    case 'transferencia_propia': return 'text-slate-500';
    default: return 'text-slate-900';
  }
}
```

---

## 7. Constantes de Categorías ⏳ A IMPLEMENTAR EN SPRINT 3

> **Estado:** Figma Make generó `allCategories` y `mockCategories` dentro de `mockData.ts`.  
> En Sprint 3, extraer a `frontend/src/constants/categories.ts` con esta estructura:

import { CategoryInfo } from '../types';

export const CATEGORIES: Record<string, CategoryInfo> = {
  alimentacion: {
    id: 'alimentacion',
    label: 'Alimentación',
    icon: '🍔',
    color: '#F59E0B',
  },
  transporte: {
    id: 'transporte',
    label: 'Transporte',
    icon: '🚗',
    color: '#3B82F6',
  },
  servicios: {
    id: 'servicios',
    label: 'Servicios',
    icon: '💡',
    color: '#8B5CF6',
  },
  salud: {
    id: 'salud',
    label: 'Salud',
    icon: '🏥',
    color: '#EC4899',
  },
  entretenimiento: {
    id: 'entretenimiento',
    label: 'Entretenimiento',
    icon: '🎮',
    color: '#14B8A6',
  },
  educacion: {
    id: 'educacion',
    label: 'Educación',
    icon: '📚',
    color: '#6366F1',
  },
  hogar: {
    id: 'hogar',
    label: 'Hogar',
    icon: '🏠',
    color: '#F97316',
  },
  ropa: {
    id: 'ropa',
    label: 'Ropa',
    icon: '👕',
    color: '#A855F7',
  },
  tecnologia: {
    id: 'tecnologia',
    label: 'Tecnología',
    icon: '💻',
    color: '#06B6D4',
  },
  ahorro: {
    id: 'ahorro',
    label: 'Ahorro',
    icon: '🏦',
    color: '#10B981',
  },
  deudas: {
    id: 'deudas',
    label: 'Deudas',
    icon: '💳',
    color: '#EF4444',
  },
  transferencia: {
    id: 'transferencia',
    label: 'Transferencia',
    icon: '👤',
    color: '#64748B',
  },
  sin_categorizar: {
    id: 'sin_categorizar',
    label: 'Sin Categorizar',
    icon: '❓',
    color: '#94A3B8',
  },
};

export function getCategoryInfo(categoryId: string): CategoryInfo {
  return CATEGORIES[categoryId] || CATEGORIES.sin_categorizar;
}
```

---

## 8. Token Storage Seguro (Capacitor) ⏳ A IMPLEMENTAR EN SPRINT 3

> **Estado:** Figma Make usa `localStorage` directamente. No tiene Capacitor.  
> En Sprint 3, instalar `@capacitor/preferences` y crear `frontend/src/utils/storage.ts`:
>
> **Migración requerida (5 archivos):**
> - `Login.tsx` — `localStorage.setItem('finanzas_phone', ...)` → no persistir (JWT)
> - `VerifyOTP.tsx` — `localStorage.getItem('finanzas_onboarded')` → API call
> - `Onboarding.tsx` — `localStorage.setItem('finanzas_salary/budget/cut_day')` → PATCH profile
> - `Dashboard.tsx` — `localStorage.getItem(...)` → useDashboard hook
> - `Profile.tsx` — `localStorage.getItem/setItem(...)` → useProfile hook

import { Preferences } from '@capacitor/preferences';

const TOKEN_KEYS = {
  access: 'finanzas_access_token',
  refresh: 'finanzas_refresh_token',
} as const;

type TokenType = keyof typeof TOKEN_KEYS;

export async function getToken(type: TokenType): Promise<string | null> {
  const { value } = await Preferences.get({ key: TOKEN_KEYS[type] });
  return value;
}

export async function setTokens(access: string, refresh: string): Promise<void> {
  await Preferences.set({ key: TOKEN_KEYS.access, value: access });
  await Preferences.set({ key: TOKEN_KEYS.refresh, value: refresh });
}

export async function clearTokens(): Promise<void> {
  await Preferences.remove({ key: TOKEN_KEYS.access });
  await Preferences.remove({ key: TOKEN_KEYS.refresh });
}

export async function isAuthenticated(): Promise<boolean> {
  const token = await getToken('access');
  return token !== null;
}
```

---

## 9. Ejemplo de Componente: Dashboard Page (Referencia Sprint 3)

> **Nota:** Este es el código de referencia para cuando se integre con la API real.  
> La versión actual generada por Figma Make (`frontend/src/app/pages/Dashboard.tsx`) usa `mockData.ts` + `localStorage` directamente.

```tsx
// frontend/src/pages/Dashboard.tsx
import { api } from '../services/api';
import { DashboardSummary } from '../types';
import { formatCurrency, getBudgetColor } from '../utils/format';
import { SavingsCard } from '../components/dashboard/SavingsCard';
import { BudgetProgress } from '../components/dashboard/BudgetProgress';
import { CategoryChart } from '../components/dashboard/CategoryChart';

export default function Dashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);
      const summary = await api.getDashboardSummary();
      setData(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error cargando datos');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-screen p-6 text-center">
        <p className="text-danger-500 mb-4">{error || 'Error desconocido'}</p>
        <button
          onClick={loadDashboard}
          className="bg-primary-500 text-white px-6 py-2 rounded-button"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="pb-20 px-4 pt-6 bg-slate-50 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
        <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
          <span className="text-primary-600 font-semibold">U</span>
        </div>
      </div>

      {/* Savings Card */}
      <SavingsCard
        ahorro={data.ahorro_real}
        salario={data.salario}
        gastos={data.total_gastos}
      />

      {/* Budget Progress */}
      <BudgetProgress
        presupuesto={data.presupuesto}
        gastado={data.total_gastos}
        progreso={data.progreso_presupuesto}
      />

      {/* Category Chart */}
      <CategoryChart
        gastosPorCategoria={data.gastos_por_categoria}
        totalGastos={data.total_gastos}
      />

      {/* WhatsApp CTA */}
      <a
        href="https://wa.me/573001234567?text=Hola"
        className="mt-6 flex items-center justify-center bg-green-500 text-white p-4 rounded-card font-semibold"
      >
        📸 Registrar gasto vía WhatsApp
      </a>
    </div>
  );
}
```

---

## 10. Capacitor Config

```typescript
// frontend/capacitor.config.ts

import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'co.finanzasapp.app',
  appName: 'Finanzas App',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      androidSplashResourceName: 'splash',
      showSpinner: false,
    },
    StatusBar: {
      style: 'LIGHT',
      backgroundColor: '#F8FAFC',
    },
    Preferences: {
      // Usa el almacenamiento seguro del dispositivo
    },
  },
};

export default config;
```

---

## 11. Dependencias del Frontend

```json
{
  "name": "finanzas-app-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "cap:build": "npm run build && npx cap sync",
    "cap:android": "npx cap open android",
    "cap:ios": "npx cap open ios"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.26.0",
    "@capacitor/core": "^6.1.0",
    "@capacitor/preferences": "^6.0.0",
    "@capacitor/status-bar": "^6.0.0",
    "@capacitor/splash-screen": "^6.0.0",
    "recharts": "^2.12.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "@capacitor/cli": "^6.1.0"
  }
}
```

---

*Este documento sigue la [Regla de Oro](./00_SISTEMA_Y_RESILIENCIA.md#61-regla-de-oro). Cambios en la estructura del frontend o API endpoints consumidos deben reflejarse aquí.*
