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

## 2. Estructura del Proyecto Frontend

```
frontend/
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── capacitor.config.ts
├── vite.config.ts
├── index.html
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx                    # Entry point
│   ├── App.tsx                     # Router principal
│   ├── index.css                   # Tailwind imports + custom vars
│   │
│   ├── pages/                      # Pantallas principales
│   │   ├── Login.tsx               # Pantalla 1: Input de celular
│   │   ├── VerifyOTP.tsx           # Pantalla 2: Código de 6 dígitos
│   │   ├── Onboarding.tsx          # Pantalla 3: Salario/Presupuesto/Día de corte
│   │   ├── Dashboard.tsx           # Pantalla 4: KPIs y gráficos
│   │   ├── Transactions.tsx        # Pantalla 5: Historial
│   │   ├── TransactionDetail.tsx   # Pantalla 6: Detalle + imagen
│   │   └── Profile.tsx             # Pantalla 7: Config y perfil
│   │
│   ├── components/                 # Componentes reutilizables
│   │   ├── ui/                     # Primitivos de UI
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── Spinner.tsx
│   │   ├── layout/
│   │   │   ├── BottomNav.tsx
│   │   │   └── PageHeader.tsx
│   │   ├── dashboard/
│   │   │   ├── SavingsCard.tsx
│   │   │   ├── BudgetProgress.tsx
│   │   │   └── CategoryChart.tsx
│   │   └── transactions/
│   │       ├── TransactionItem.tsx
│   │       └── TransactionFilters.tsx
│   │
│   ├── hooks/                      # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useDashboard.ts
│   │   ├── useTransactions.ts
│   │   └── useProfile.ts
│   │
│   ├── services/                   # API client
│   │   └── api.ts
│   │
│   ├── types/                      # TypeScript types
│   │   └── index.ts
│   │
│   ├── utils/                      # Utilidades
│   │   ├── format.ts               # Formateo de moneda, fechas
│   │   └── storage.ts              # Secure storage (tokens)
│   │
│   └── constants/
│       └── categories.ts           # Mapa de categorías + íconos
```