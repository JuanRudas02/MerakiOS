# Pipelines

Dos tipos de pipeline: el de **entrega de software** (CI/CD) y los **pipelines de negocio** que la
plataforma ejecuta. Ambos están diseñados como etapas con entradas/salidas explícitas.

## 1. Pipeline CI/CD

```mermaid
flowchart LR
  PR[PR / push] --> F{paths-filter}
  F -->|apps/api| L1[ruff check + format] --> T1[mypy] --> U1[pytest + cobertura ≥80%]
  F -->|apps/web| L2[eslint] --> T2[tsc] --> U2[tests] --> B2[vite build]
  F -->|infra| C[compose config]
  U1 & B2 --> IMG[build imágenes Docker api/web<br/>tag = SHA]
  IMG --> STG[deploy staging] --> SMK[smoke tests] --> APR{aprobación manual} --> PRD[promote a producción]
  PRD -. falla .-> RB[rollback al SHA anterior]
```

| Etapa | Herramienta | Falla si |
|---|---|---|
| Lint | ruff, eslint | cualquier error |
| Formato | ruff format --check | archivo sin formatear |
| Tipos | mypy, tsc | cualquier error |
| Pruebas | pytest-cov, vitest | test rojo o cobertura < 80 % |
| Build | vite, docker buildx | error de build |
| Seguridad | CodeQL (semanal + PR), Dependabot | alerta alta sin triage |

Workflows: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), [`codeql.yml`](../../.github/workflows/codeql.yml).

## 2. Lead-to-customer (Meta → CRM → Mautic → Deal → Conversions API)

```mermaid
sequenceDiagram
  autonumber
  participant Meta as Meta Lead Ads
  participant MB as meta
  participant CRM as crm
  participant MK as marketing
  participant Mautic
  participant GM as gamification
  Meta->>MB: webhook leadgen (X-Hub-Signature-256)
  MB->>MB: validar firma, obtener lead (Graph API)
  MB-->>CRM: LeadCaptured
  CRM->>CRM: dedupe email/teléfono → crear o fusionar Contact (stage=lead)
  CRM-->>MK: ContactCreated
  MK->>Mautic: upsert contacto + segmento
  Mautic-->>MK: webhook email_open/click/form
  MK-->>CRM: MarketingEngagementRecorded → score ↑, timeline
  CRM->>CRM: score ≥ umbral → stage mql/sql (ContactLifecycleChanged)
  Note over CRM: Ventas crea Deal y lo mueve por el pipeline
  CRM-->>MB: DealWon → Conversions API (Purchase, datos hasheados SHA-256)
  CRM-->>GM: DealWon → puntos para el vendedor
```

## 3. Ciclo de vida de la tarea de limpieza (Stays)

```mermaid
stateDiagram-v2
  [*] --> pending: programar (manual o iCal)
  pending --> arrived: confirmar llegada + fotos iniciales
  pending --> cancelled: cancelar (motivo)
  arrived --> in_progress: iniciar
  in_progress --> completed: checklist 100% + fotos finales
  pending --> pending: editar (sólo pending)
  completed --> [*]
  cancelled --> [*]
```

| Job (scheduler) | Frecuencia | Acción |
|---|---|---|
| Recordatorio diario | 19:00 (configurable por workspace) | WhatsApp a cada staff con sus tareas de mañana |
| Confirmación de llegada | cada 5 min | botones "Ya llegué / No han salido / Tengo un problema" a tareas que inician |
| Escalamiento | cada 5 min | tarea `pending` sin llegada a `escalation_minutes` (def. 10) → WhatsApp al supervisor |
| Cortes de servicios | 09:00 | aviso 5 días antes y el día del corte al propietario; pausa automatización hasta verificar comprobante |
| Sincronización iCal | periódico | reservas Airbnb/Booking → tareas en el check-out |

Eventos: `CleaningTaskScheduled`, `CleaningArrivalConfirmed`, `CleaningIssueReported`, `CleaningTaskCompleted`, `ReceiptVerified`.

## 4. Growth IA (Genesis → Blueprint → Assets)

```mermaid
flowchart LR
  P[Project draft] --> G1[Planner<br/>3 queries] --> G2[Researcher<br/>WebSearch] --> G3[Auditor<br/>Schwartz + JTBD]
  G3 -->|info insuficiente y < 2 iteraciones| G1
  G3 -->|audited| B1[Architect<br/>nivel de consciencia → tipo de embudo]
  B1 --> B2[Validación de grafo<br/>nodos/aristas]
  B2 -->|completed| A[Assets IA<br/>ads · landing · emails]
  G3 & B2 -. error .-> X[failed + mensaje]
```
Estados: `draft → analyzing → audited → designing → completed | failed`. Eventos: `MarketAuditCompleted`, `FunnelDesigned`.

## 5. Marketing automation con IA

```mermaid
flowchart LR
  SEG[Segmento<br/>filtros: etapa, tags, score] --> SYNC[Sync a Mautic]
  OBJ[Objetivo + audiencia] --> AI1[IA: plan de campaña<br/>pasos por día/canal]
  AI1 --> AI2[IA: emails<br/>asunto, preheader, HTML]
  AI2 --> PUSH[Push a Mautic como borrador]
  PUSH --> REV{Revisión humana} --> LAUNCH[Lanzar campaña]
  LAUNCH --> WH[Webhooks Mautic] --> ENG[MarketingEngagementRecorded] --> CRM[score + timeline]
```
Regla: la IA **propone**; una persona aprueba antes de enviar (human-in-the-loop).

## 6. Gamificación

```mermaid
flowchart LR
  EV[Eventos de dominio<br/>TaskCompleted, DealWon, ContactCreated,<br/>CampaignLaunched, MarketAuditCompleted...] --> R[Motor de reglas<br/>Strategy por regla]
  R --> L[Ledger inmutable<br/>PointTransaction]
  L --> PL[PlayerProfile<br/>puntos, nivel, racha]
  PL --> BD[Insignias] & CH[Progreso de retos] & LB[Leaderboard semana/mes]
  L --> PA[PointsAwarded] --> AN[analytics]
```
Idempotencia: una transacción por (`event_id`, `rule_key`).
