# Arquitectura de 1heavy — visión general

**Estilo:** monolito modular (un despliegue) organizado por *bounded contexts*, cada uno con
**arquitectura hexagonal** (puertos y adaptadores). Los módulos se comunican por **eventos de
integración** en proceso. Decisiones en [ADRs](adr/).

## C4 · Nivel 1 — Contexto

```mermaid
flowchart TB
  subgraph Personas
    OW[Dueño / Admin]:::p
    OPS[Gerente / Coordinador]:::p
    ST[Personal de limpieza]:::p
    PO[Propietario-inversionista]:::p
    MK[Marketer]:::p
    SA[Ventas]:::p
  end
  H((1heavy)):::sys
  OW & OPS & ST & PO & MK & SA --> H
  H <--> META[Meta Graph / Marketing API]:::ext
  H <--> MAU[Mautic]:::ext
  H <--> EVO[Evolution API · WhatsApp]:::ext
  H --> LLM[Proveedor LLM]:::ext
  H --> TAV[Búsqueda web · Tavily]:::ext
  H <--> WOM[Wompi]:::ext
  H --> ICAL[iCal Airbnb/Booking]:::ext
  classDef p fill:#3B5BFD,color:#fff,stroke:none
  classDef sys fill:#070A12,color:#EEF2FF,stroke:#22D3EE
  classDef ext fill:#151B2C,color:#EEF2FF,stroke:#232B40
```

## C4 · Nivel 2 — Contenedores

```mermaid
flowchart LR
  B[Navegador / PWA] --> WEB[apps/web<br/>React + Vite · nginx]
  WEB -->|REST /api/v1 · JWT| API[apps/api<br/>FastAPI · uvicorn]
  API --> PG[(PostgreSQL 16<br/>+ pgvector)]
  API --> FS[(Storage<br/>fotos y comprobantes)]
  API -. futuro: caché/colas .-> RD[(Redis)]
  API <--> MAU[Mautic 5] --> MDB[(MariaDB)]
  API <--> EVO[Evolution API] --> PG
  SCH[Scheduler APScheduler<br/>dentro de la API] --> API
```

## C4 · Nivel 3 — Componentes de la API

```mermaid
flowchart TB
  subgraph main.py [Composition Root]
    CT[Container<br/>settings, engine, bus, llm, sender, storage, tokens]
  end
  subgraph modules
    ID[identity] ; STY[stays] ; CRM[crm] ; MKT[marketing] ; MT[meta]
    GR[growth] ; GM[gamification] ; AN[analytics] ; BI[billing]
  end
  subgraph shared [shared kernel]
    DOM[domain: Entity, AggregateRoot, ValueObjects, Access, Errors, integration_events]
    APP[application: UseCase, puertos EventBus/UoW/MessageSender/LLMClient/WebSearch/FileStorage]
    INF[infrastructure: db, UoW, event bus, security, http, scheduler, adaptadores]
  end
  CT --> modules
  modules --> shared
  BUS{{InMemoryEventBus}}
  STY & CRM & MT & MKT & GR & BI & GM -- publican --> BUS
  BUS -- suscriben --> GM & AN & CRM & MKT & MT & STY & ID
```

## Capas hexagonales de cada módulo

```
modules/<contexto>/
  domain/          Entidades, agregados, value objects, reglas, repositorios (ABC). Python puro.
  application/     Casos de uso (Command → resultado), UoW del módulo (ABC), puertos externos.
  infrastructure/  ORM SQLAlchemy, repositorios SQL, adaptadores HTTP (Mautic, Meta, Wompi...), fakes.
  api/             Router FastAPI + esquemas Pydantic (adaptador de entrada).
  __init__.py      <Contexto>Module: router(), register(container), jobs(container)
```

**Regla de dependencia:** `api → application → domain` e `infrastructure → application/domain`.
El dominio no depende de nada externo. **Ningún módulo importa a otro**; sólo comparten `shared/`
y el catálogo `shared/domain/integration_events.py` (*Published Language*).

```mermaid
flowchart LR
  API[api] --> APP[application] --> DOM[domain]
  INF[infrastructure] --> APP
  INF --> DOM
  DOM --> SK[shared.domain]
```

## Contrato de módulo y Composition Root
`Container.from_settings()` es el único lugar que elige implementaciones concretas (p. ej. `FakeLLMClient`
vs `OpenAIChatClient`, `ConsoleMessageSender` vs `EvolutionApiSender`) según configuración. Cada módulo
implementa `Module`:

| Hook | Uso |
|---|---|
| `router()` | expone su API bajo `/api/v1` |
| `register(container)` | suscribe handlers al bus y registra singletons propios en `container.extras` |
| `jobs(container)` | procesos batch (`ScheduledJob`) que el `Scheduler` agenda al arrancar |

`create_app()` recorre `default_modules()`; los tests inyectan un `Container` con SQLite y fakes.

## Unit of Work y eventos después del commit

```mermaid
sequenceDiagram
  participant R as Router
  participant UC as Caso de uso
  participant U as UoW
  participant A as Agregado
  participant B as EventBus
  participant H as Handler (otro módulo)
  R->>UC: execute(command)
  UC->>U: async with uow
  UC->>A: método de negocio (valida reglas, record(event))
  UC->>U: repos.add/update · collect(A.pull_events())
  UC->>U: commit()
  U->>U: session.commit()
  U->>B: publish_all(eventos)
  B->>H: handler(event) — abre su propia UoW
  Note over B,H: Si el handler falla se registra en log<br/>y NO revierte la transacción original
```

## Multi-tenancy
- Esquema compartido: toda tabla de negocio tiene `tenant_id` indexado ([ADR-0006](adr/0006-multi-tenant-esquema-compartido.md)).
- El `tenant_id` sale del JWT (`Principal`), nunca del cliente. Los repositorios reciben el tenant explícitamente.
- Cada workspace tiene su marca blanca y su propia instancia de WhatsApp (`whatsapp_instance`).

## Atributos de calidad
| Atributo | Táctica |
|---|---|
| Mantenibilidad | módulos aislados, contrato REST, eventos tipados, mypy estricto |
| Testabilidad | puertos con fakes, Composition Root inyectable, SQLite en memoria |
| Seguridad | RBAC, tenant por token, firmas de webhooks, validación de uploads ([seguridad](../process/seguridad.md)) |
| Resiliencia | handlers aislados, errores externos → 502 controlado, jobs con `coalesce` |
| Escalabilidad | API stateless; bus y rate limiter reemplazables por Redis; módulo extraíble a servicio si lo exige la carga |
| Observabilidad | logs JSON estructurados, `/health`, eventos auditables |
