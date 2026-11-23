# Catálogo de eventos de integración

Fuente: `apps/api/src/oneheavy/shared/domain/integration_events.py`. Todos heredan de `DomainEvent`:
`tenant_id`, `actor_id?`, `event_id`, `occurred_at` (UTC). Son inmutables (`frozen`).

**Reglas**
1. Un evento describe un hecho pasado, en pasado (`DealWon`, no `WinDeal`).
2. Se publican **después** del commit (UoW). Los consumidores abren su propia UoW.
3. Los handlers deben ser **idempotentes** (usar `event_id`) y tolerar fallas (el bus las registra y continúa).
4. Agregar/cambiar un campo es un cambio de contrato: PR que actualice este documento.

| Evento | Productor | Consumidores | Payload |
|---|---|---|---|
| `WorkspaceCreated` | identity | analytics | `workspace_name, owner_id` |
| `UserRegistered` | identity | stays (staff), gamification (jugador), crm | `user_id, email?, name, role, phone?` |
| `CleaningTaskScheduled` | stays | analytics | `task_id, property_id, staff_id?, scheduled_at` |
| `CleaningArrivalConfirmed` | stays | gamification (puntualidad), analytics | `task_id, staff_id?, minutes_late` |
| `CleaningTaskCompleted` | stays | gamification, analytics | `task_id, property_id, staff_id?, duration_minutes?, photos_count, on_time` |
| `CleaningIssueReported` | stays | analytics | `task_id, staff_id?, kind, description` |
| `ReceiptVerified` | stays | gamification (propietario al día), analytics | `property_id, receipt_id, service` |
| `ContactCreated` | crm | marketing (sync Mautic), meta (espejo hasheado), gamification, analytics | `contact_id, email?, phone?, source, owner_id?, stage, first_name?, last_name?, tags` |
| `ContactLifecycleChanged` | crm | marketing (segmentos), meta (CAPI), analytics | `contact_id, from_stage, to_stage` |
| `DealWon` | crm | meta (CAPI Purchase), gamification, analytics | `deal_id, contact_id?, owner_id?, amount, currency` |
| `DealLost` | crm | analytics (win rate) | `deal_id, owner_id?, reason?` |
| `LeadCaptured` | meta | crm (crear/fusionar contacto), analytics | `source, external_id?, full_name?, email?, phone?, campaign_ref?, answers` |
| `AdPerformanceAnomalyDetected` | meta | analytics | `campaign_ref, metric, value, benchmark, severity` |
| `AdInsightsSynced` | meta | analytics (inversión, CPL) | `day, spend, currency, impressions, clicks, leads` |
| `MarketingEngagementRecorded` | marketing | crm (score, timeline), analytics | `contact_id?, email?, kind, points` |
| `MarketingContactSynced` | marketing | crm (guarda `mautic_id`) | `contact_id, mautic_id` |
| `CampaignLaunched` | marketing | gamification, analytics | `campaign_id, name, channel` |
| `MarketAuditCompleted` | growth | gamification, analytics | `project_id, awareness_level` |
| `FunnelDesigned` | growth | gamification, analytics | `project_id, nodes_count` |
| `PointsAwarded` | gamification | analytics | `user_id, points, reason, rule_key` |
| `PaymentApproved` | billing | identity (plan), analytics | `payment_id, reference, amount_in_cents, currency, plan?` |

## Evolución
El `InMemoryEventBus` es suficiente para un único proceso. Al escalar a varias réplicas o separar un módulo:
1. Patrón **Outbox** (tabla `outbox_events` escrita en la misma transacción).
2. Relay a Redis Streams / cola gestionada.
3. Los handlers no cambian: el puerto `EventBus` se mantiene ([ADR-0002](adr/0002-bus-de-eventos-en-proceso.md)).
