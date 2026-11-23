# Mapa de actores

| Actor | Rol en sistema | Objetivo principal | Canal principal |
|---|---|---|---|
| Dueño del negocio | `owner` | crecer con rentabilidad y control | web (tablero) |
| Administrador | `admin` | configurar y operar la plataforma | web |
| Gerente de operaciones | `manager` | servicio impecable y a tiempo | web + WhatsApp |
| Coordinador | `coordinator` | asignar y seguir tareas del día | web móvil |
| Marketer | `marketer` | leads baratos y campañas que convierten | web |
| Ventas | `sales` | cerrar negocios rápido | web móvil + WhatsApp |
| Personal de limpieza/mantenimiento | `staff` | saber qué hacer, cumplir y ser reconocido | WhatsApp + web móvil |
| Propietario-inversionista | `property_owner` | ver su activo y estar al día en pagos | WhatsApp + portal |
| Sistema (scheduler/webhooks) | — | automatizar recordatorios, escalamientos, sincronizaciones | interno |
| Proveedores externos | — | Meta, Mautic, Evolution (WhatsApp), LLM, Wompi, iCal | API |

## Actores × módulos
Leyenda: **G** gestiona · **U** usa · **V** ve · — sin acceso.

| Módulo | owner | admin | manager | coordinator | marketer | sales | staff | property_owner |
|---|---|---|---|---|---|---|---|---|
| identity (equipo, marca) | G | G | U (miembros) | — | — | — | — | — |
| stays · propiedades | G | G | G | V | — | — | — | V (suyas) |
| stays · tareas | G | G | G | G | — | — | U (suyas) | — |
| stays · comprobantes | G | G | U (verifica) | — | — | — | — | U (sube) |
| crm · contactos | G | G | V | — | G | G | — | — |
| crm · negocios | G | G | — | — | — | G | — | — |
| marketing (Mautic + IA) | G | G | — | — | G | — | — | — |
| meta business | G | G | — | — | G | — | — | — |
| growth IA | G | G | — | — | G | — | — | — |
| gamificación | G | G | G | V | V | V | V | — |
| analytics | V | V | V | V | V | V | — | — |
| billing | G | — | — | — | — | — | — | — |

La matriz exacta de permisos está en [seguridad.md](../process/seguridad.md#3-autorización-rbac).
