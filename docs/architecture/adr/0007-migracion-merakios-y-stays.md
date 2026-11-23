# ADR-0007 · Migración de MerakiOS y 1heavy Stays a 1heavy

- **Estado:** Aceptado · 2026-11-22

## Contexto
Dos bases de código con propósitos complementarios: MerakiOS (estrategia de crecimiento con IA, `merakios-core/`)
y 1heavy Stays (operación de alquileres por WhatsApp, repositorio aparte con arquitectura hexagonal).

## Decisión
Nuevo monorepo `apps/api` + `apps/web`; la lógica de ambos se porta a módulos de `apps/api`. Stays se conserva
como repositorio de referencia (sin cambios); el código original de MerakiOS queda en el historial de git (commit `e6aa28b`).

### Qué se migró
| Origen | Destino |
|---|---|
| MerakiOS `agents/genesis.py` (Planner/Researcher/Auditor) | `growth` · `GenesisPipeline` |
| MerakiOS `agents/blueprint.py` (Architect) | `growth` · `BlueprintPipeline` |
| MerakiOS `agents/director.py` (métricas y alertas) | `meta` · reglas de anomalía + insights |
| MerakiOS `User`, login | `identity` (ahora multi-tenant con roles) |
| MerakiOS frontend (landing, servicios, métricas) | `apps/web` rebrand 1heavy |
| Stays entidades `Apartment`, `Task`, `Staff`, `User` | `stays.Property`, `CleaningTask`, `StaffMember`; `identity.User` |
| Stays casos de uso (tareas, ejecución, notificaciones, iCal, checklist/inventario, analítica) | `stays` + `analytics` |
| Stays pagos Wompi | `billing` |
| Stays plantillas white-label | `identity.Workspace` (branding + templates) |
| Stays vistas Next.js (dashboard, tareas, propiedades, staff, recibos, reportes) | páginas en `apps/web` |

### Bugs corregidos durante la migración
1. Scheduler: fecha de recordatorios evaluada una sola vez al arrancar.
2. `os` sin importar en notificaciones (escalamiento fallaba).
3. `find_by_range` / `find_by_phone` usados pero no definidos en los puertos.
4. Firma de webhook Wompi que siempre retornaba `True`.
5. Mezcla de datetimes naive y aware.
6. `except: pass` silenciosos y `print()` en producción.
7. Uploads sin validación de tipo/tamaño.
8. Contraseñas enviadas en texto plano por WhatsApp.
9. Errores 500 que devolvían el detalle interno al cliente.
10. Mock de mensajería incompatible con la interfaz real.
11. MerakiOS: `status` sin importar, `run_genesis_agent` duplicado, `user_id` aleatorio al crear proyectos, endpoints sin autenticación, `axios` usado sin declararse.
12. Credenciales en texto plano en `setup_and_run.sh` (eliminado; rotar credencial).

### Qué se deprecó
LangChain/LangGraph, integración Supabase del frontend, frontend Next.js de Stays, `SUPERVISOR_PHONE` global
(ahora configuración por workspace), docker-compose duplicados.

## Consecuencias
- ✅ Una sola plataforma, un design system, un pipeline de CI.
- ⚠️ No hay migración de datos productivos automatizada: si Stays tiene clientes activos, se requiere un script
  de migración (`admin_id → tenant_id`, `apartments → stays_properties`, `tasks → stays_tasks`).
