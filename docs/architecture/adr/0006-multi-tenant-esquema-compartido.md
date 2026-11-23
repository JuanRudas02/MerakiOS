# ADR-0006 · Multi-tenancy con esquema compartido y `tenant_id`

- **Estado:** Aceptado · 2026-11-22

## Contexto
Stays usaba `admin_id` como tenant implícito; MerakiOS no tenía multi-tenancy.

## Decisión
Entidad `Workspace` explícita. Todas las tablas de negocio llevan `tenant_id` indexado (`TenantMixin`).
El tenant se obtiene del JWT (`Principal.tenant_id`) y los repositorios lo reciben como parámetro obligatorio.
Un recurso de otro tenant responde **404** (no se revela su existencia).

## Alternativas
Esquema por tenant o base por tenant: mayor aislamiento pero migraciones y operación más complejas para cientos de clientes pequeños.

## Consecuencias
- ✅ Simple, barato, escalable a miles de workspaces.
- ⚠️ Un olvido de filtro es una fuga de datos: pruebas de aislamiento obligatorias por endpoint;
  evaluar Row Level Security de Postgres como defensa en profundidad.
