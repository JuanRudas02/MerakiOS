# Design system 1heavy

**Personalidad:** potente, preciso, confiable. "Heavy" = robusto y con peso; la interfaz es oscura por
defecto (centro de mando), con acentos eléctricos que codifican cada módulo. Modo claro completo.

## 1. Paleta

### Neutros — modo oscuro (por defecto)
| Token | Hex | HSL (para `hsl(var(--x))`) | Uso |
|---|---|---|---|
| `--ink` / `--background` | `#070A12` | `224 44% 5%` | fondo de la app |
| `--surface` / `--card` | `#0E1320` | `223 39% 9%` | tarjetas, sidebar |
| `--elevated` / `--popover` | `#151B2C` | `224 35% 13%` | menús, modales, hover |
| `--border` | `#232B40` | `223 29% 19%` | bordes y divisores |
| `--foreground` | `#EEF2FF` | `226 100% 97%` | texto principal |
| `--muted-foreground` | `#8B93A7` | `223 14% 60%` | texto secundario, labels |

### Neutros — modo claro
| Token | Hex | HSL |
|---|---|---|
| `--background` | `#F7F8FC` | `228 45% 98%` |
| `--card` | `#FFFFFF` | `0 0% 100%` |
| `--foreground` | `#0B1020` | `226 49% 8%` |
| `--border` | `#E3E7F1` | `223 33% 92%` |
| `--muted-foreground` | `#5B6478` | `221 14% 41%` |

### Acentos
| Nombre | Hex | HSL | Rol semántico |
|---|---|---|---|
| **Heavy Blue** | `#3B5BFD` | `230 98% 61%` | `--primary`: acciones principales, foco, enlaces, CRM |
| **Volt Cyan** | `#22D3EE` | `188 86% 53%` | IA y analítica, datos en vivo |
| **Ember** | `#F5A524` | `37 91% 55%` | gamificación, recompensas, advertencias |
| **Signal Violet** | `#8B5CF6` | `258 90% 66%` | marketing (Mautic) y growth IA |
| **Mint** | `#10B981` | `160 84% 39%` | operación (Stays), éxito |
| **Rose** | `#F43F5E` | `350 89% 60%` | errores, acciones destructivas, alertas críticas |

Gradiente de marca: `linear-gradient(135deg, #3B5BFD 0%, #8B5CF6 55%, #22D3EE 100%)` — sólo en hero, logo y CTA principal.

### Codificación por módulo
| Módulo | Color | Icono (lucide) |
|---|---|---|
| Inicio / Analytics | Volt Cyan | `LayoutDashboard`, `LineChart` |
| Stays (operación) | Mint | `Building2`, `SprayCan` |
| CRM | Heavy Blue | `Users`, `KanbanSquare` |
| Marketing (Mautic + IA) | Signal Violet | `Mail`, `Sparkles` |
| Meta Business | Heavy Blue → Cyan | `Megaphone` |
| Growth IA | Signal Violet → Cyan | `Brain`, `Workflow` |
| Gamificación | Ember | `Trophy`, `Flame` |
| Billing / Ajustes | neutro | `CreditCard`, `Settings` |

> Las integraciones de terceros (Meta, Mautic, WhatsApp) se nombran como tales, pero **no** se usan sus logos ni colores de marca como identidad de 1heavy.

### Reglas de uso
1. Máximo **un acento** dominante por pantalla (el del módulo) + primary para CTAs.
2. Estados: éxito = Mint, advertencia = Ember, error = Rose, info = Cyan. Nunca sólo color: acompañar con icono/texto.
3. Gráficos: series en el orden Blue, Cyan, Violet, Mint, Ember, Rose; ejes y grillas en `--border`.
4. Fondos de acento al 10–15 % de opacidad para badges (`bg-primary/10 text-primary`).

## 2. Tipografía
| Rol | Fuente | Tamaño / peso |
|---|---|---|
| Display (h1 hero) | Space Grotesk | 48–64 px / 700, tracking −0.02em |
| Títulos h2–h3 | Space Grotesk | 24–32 px / 600 |
| UI y cuerpo | Inter | 14–16 px / 400–500, interlineado 1.5 |
| Números KPI | Inter `tabular-nums` | 28–36 px / 600 |
| Código / IDs | JetBrains Mono (opcional) | 13 px |

## 3. Espaciado, radio, elevación
- Escala de espaciado Tailwind (múltiplos de 4 px). Gutter de página 16 px móvil / 24–32 px escritorio.
- Radio: `--radius: 0.75rem` (tarjetas), `md` 10 px (inputs/botones), `full` para avatares y badges.
- Elevación en oscuro por **luminosidad** (ink → surface → elevated), no por sombras; sombra suave sólo en modales.
- Glow de foco: `0 0 0 3px hsl(230 98% 61% / .35)`.

## 4. Movimiento
- Duraciones: 150 ms (hover), 200–250 ms (entradas), 400 ms (transiciones de página). Easing `cubic-bezier(.2,.8,.2,1)`.
- framer-motion para entradas de secciones, contadores de KPI y celebración de logros (confeti/insignia) en gamificación.
- Respetar `prefers-reduced-motion`: desactivar animaciones no esenciales.

## 5. Librerías (alto rendimiento)
| Necesidad | Librería | Nota |
|---|---|---|
| Componentes accesibles | **shadcn/ui** sobre **Radix UI** | código propio en `src/components/ui`, sin runtime pesado |
| Estilos | **Tailwind CSS** + tokens CSS | purga en build, sin CSS-in-JS en runtime |
| Datos del servidor | **TanStack Query** | caché, reintentos, invalidación por módulo |
| Formularios | react-hook-form + zod | validación tipada, re-render mínimo |
| Gráficos | **Recharts** | combinar con tokens de color |
| Animación | **framer-motion** | ver reglas de movimiento |
| Iconos | **lucide-react** | importación por icono (tree-shaking) |
| Paleta de comandos | **cmdk** | `⌘K` para navegar módulos |
| Notificaciones | sonner | toasts no bloqueantes |
| Rendimiento | `React.lazy` + `Suspense` por ruta | cada módulo es un chunk |

## 6. Accesibilidad
- Contraste AA: `#EEF2FF` sobre `#070A12` ≈ 18:1; `#8B93A7` sobre `#070A12` ≈ 6.4:1 (apto para texto secundario).
- Heavy Blue `#3B5BFD` sobre ink ≈ 3.9:1 (sólo AA para texto grande ≥ 18 px e iconos) → en botones usar texto **blanco** encima (≈ 5.1:1); para texto de enlace sobre oscuro usar la variante `#7C93FF` (≈ 7.0:1).
- Ember y Mint sobre fondo oscuro cumplen AA para texto; sobre fondo claro usar texto oscuro encima del acento.
- Foco visible siempre, navegación completa por teclado (Radix), `aria-live` para toasts y resultados de IA.
- Objetivos táctiles ≥ 44 px en vistas del personal (uso en celular, con guantes).
