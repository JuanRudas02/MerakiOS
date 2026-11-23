# Contrato REST de 1heavy API v1

> Fuente de verdad para backend (`apps/api`) y frontend (`apps/web`). Cualquier cambio
> aquí requiere PR que actualice ambos lados. OpenAPI generado en `GET /docs`.

## Convenciones

- Base: `/api/v1`. JSON UTF-8. Fechas ISO-8601 en UTC (`2026-11-22T15:00:00Z`). IDs = UUID.
- Auth: `Authorization: Bearer <jwt>`. El JWT contiene `sub` (user), `tid` (workspace), `role`.
- Multi-tenant: el workspace SIEMPRE se toma del token, nunca del body/query.
- Errores: `{"error": {"code": "snake_case", "message": "Texto para humanos"}}`
  - 401 auth · 403 permiso · 404 no existe (o es de otro tenant) · 409 conflicto · 422 regla de negocio/validación · 429 rate limit · 502 proveedor externo.
- Paginación: `?page=1&size=25` → `{"items": [...], "total": 120, "page": 1, "size": 25}`.
- Webhooks públicos (`/webhooks/...`) no usan JWT: validan firma/secreto del proveedor.
- Procesos IA largos responden `202 {"status": "accepted"}` y el cliente hace polling al recurso.

---

## identity — Identidad y workspaces ✅ implementado

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| POST | `/auth/register` | público (rate-limit) | `{workspace_name, owner_name, email, password, phone?}` → `Session` 201 |
| POST | `/auth/login` | público (rate-limit) | `{identifier (email o usuario), password}` → `Session` |
| GET | `/auth/me` | autenticado | → `{user: User, workspace: Workspace}` |
| GET | `/workspace/members` | members.manage | → `User[]` |
| POST | `/workspace/members` | members.manage | `{name, role, temporary_password, email?, phone?, username?}` → `User` 201 |
| PUT | `/workspace/branding` | workspace.manage | `{business_name, logo_url?, primary_color? (#RRGGBB), whatsapp_instance?}` → `Workspace` |

- `Session` = `{access_token, token_type: "bearer", user: User, workspace: Workspace}`
- `User` = `{id, name, username, email|null, phone|null, role, active, permissions: string[], last_login_at|null}`
- `Workspace` = `{id, name, slug, plan: trial|starter|growth|scale, business_name, logo_url|null, primary_color, whatsapp_instance|null}`
- Roles: `owner, admin, manager, coordinator, marketer, sales, staff, property_owner`.

---

## stays — Operación de alquileres de corta estadía

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| GET | `/stays/properties` | stays.properties.read | → `Property[]` (property_owner sólo ve las suyas por `owner_phone`) |
| POST | `/stays/properties` | stays.properties.manage | `PropertyIn` → `Property` 201 |
| GET | `/stays/properties/{id}` | stays.properties.read | → `Property` |
| PATCH | `/stays/properties/{id}` | stays.properties.manage | `PropertyIn` parcial → `Property` |
| POST | `/stays/properties/{id}/calendar-sync` | stays.properties.manage | → `{created: int}` |
| GET | `/stays/properties/{id}/receipts` | stays.properties.read | → `Receipt[]` |
| POST | `/stays/properties/{id}/receipts` | stays.receipts.upload | multipart `file, service, period (YYYY-MM)` → `Receipt` 201 |
| POST | `/stays/receipts/{id}/review` | stays.receipts.verify | `{approved: bool, note?}` → `Receipt` |
| GET | `/stays/staff` | stays.tasks.read | → `StaffMember[]` |
| POST | `/stays/staff` | stays.tasks.manage | `{name, phone, category}` → `StaffMember` 201 |
| GET | `/stays/tasks` | stays.tasks.read | `?from&to&property_id&staff_id&status` → `Task[]` (staff sólo ve las suyas) |
| POST | `/stays/tasks` | stays.tasks.manage | `{property_id, staff_id?, scheduled_at, observations?, luggage, supplies_required}` → `Task` 201 |
| GET | `/stays/tasks/{id}` | stays.tasks.read | → `Task` |
| PATCH | `/stays/tasks/{id}` | stays.tasks.manage | campos editables (sólo si `pending`) → `Task` |
| POST | `/stays/tasks/{id}/cancel` | stays.tasks.manage | `{reason}` → `Task` |
| GET | `/stays/tasks/{id}/required-photos` | stays.tasks.execute | `?mode=standard\|random` → `{items: string[]}` |
| POST | `/stays/tasks/{id}/arrival` | stays.tasks.execute | multipart `photos[]` (≥1) → `Task` |
| POST | `/stays/tasks/{id}/start` | stays.tasks.execute | → `Task` |
| PUT | `/stays/tasks/{id}/checklist` | stays.tasks.execute | `{items: [{item, done}]}` → `Task` |
| POST | `/stays/tasks/{id}/issues` | stays.tasks.execute | `{kind: problem\|missing_supplies\|guests_not_out, description}` → `Task` |
| POST | `/stays/tasks/{id}/complete` | stays.tasks.execute | multipart `photos[]` (≥1) → `Task` |
| GET | `/stays/dashboard` | stays.tasks.read | → `StaysDashboard` |
| GET | `/stays/settings` | stays.tasks.manage | → `StaysSettings` |
| PUT | `/stays/settings` | stays.tasks.manage | `StaysSettings` → `StaysSettings` |
| POST | `/stays/webhooks/whatsapp` | público (`?token=`) | payload Evolution (respuestas de botones) → `{ok: true}` |

- `PropertyIn` = `{code, name, address?, capacity, owner_name?, owner_phone?, default_staff_id?, billing_cutoffs: {administration?, electricity?, water?, gas?, internet?, insurance?} (día 1–31), checklist_template: string[], visual_inventory: string[], ical_url?}`
- `Property` = `PropertyIn` + `{id, automation_paused: bool, created_at}`
- `Receipt` = `{id, property_id, service, period, url, status: pending|verified|rejected, note|null, uploaded_at, reviewed_at|null}`
- `StaffMember` = `{id, name, phone, category: cleaning|maintenance, active, has_login: bool}`
- `Task` = `{id, property_id, property_name, staff_id|null, staff_name|null, scheduled_at, status: pending|arrived|in_progress|completed|cancelled, observations|null, luggage: none|leave|collect, supplies_required, arrival_confirmed_at|null, started_at|null, completed_at|null, checklist: [{item, done}], initial_photos: string[], final_photos: string[], issues: [{kind, description, reported_at}]}`
- `StaysDashboard` = `{today: {total, pending, in_progress, completed, cancelled}, week: {completed, on_time_rate (0–1), avg_cleaning_minutes, issues}, staff_ranking: [{staff_id, name, completed, on_time_rate, avg_minutes}], upcoming: Task[] (próximas 8)}`
- `StaysSettings` = `{supervisor_phone|null, daily_reminder_hour (0–23, def 19), escalation_minutes (def 10), photo_mode: standard|random}`

---

## crm — Contactos, pipeline y lead scoring

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| GET | `/crm/contacts` | crm.contacts.read | `?q&stage&tag&owner_id&page&size` → `Page<Contact>` |
| POST | `/crm/contacts` | crm.contacts.manage | `ContactIn` → `Contact` 201 (dedupe por email/teléfono → 409 `duplicate_contact`) |
| GET | `/crm/contacts/{id}` | crm.contacts.read | → `Contact` |
| PATCH | `/crm/contacts/{id}` | crm.contacts.manage | `ContactIn` parcial → `Contact` |
| POST | `/crm/contacts/{id}/stage` | crm.contacts.manage | `{stage}` → `Contact` |
| GET | `/crm/contacts/{id}/timeline` | crm.contacts.read | → `Activity[]` (más reciente primero) |
| POST | `/crm/contacts/{id}/activities` | crm.contacts.manage | `{kind, summary}` → `Activity` 201 |
| POST | `/crm/contacts/{id}/insight` | crm.contacts.read | → `{score, temperature: cold\|warm\|hot, explanation, next_best_action}` (IA) |
| POST | `/crm/contacts/import` | crm.contacts.manage | `{contacts: ContactIn[]}` → `{created, merged, skipped}` |
| GET | `/crm/pipeline` | crm.contacts.read | → `{stages: [{key, name, order, probability}], deals: Deal[]}` |
| POST | `/crm/deals` | crm.deals.manage | `{title, contact_id?, amount, currency, stage?, owner_id?, expected_close?}` → `Deal` 201 |
| PATCH | `/crm/deals/{id}` | crm.deals.manage | parcial → `Deal` |
| POST | `/crm/deals/{id}/move` | crm.deals.manage | `{stage}` → `Deal` |

- `ContactIn` = `{first_name, last_name?, email?, phone?, company?, job_title?, source? (manual|meta_lead_ads|whatsapp|instagram|web_form|import|mautic), tags: string[], owner_id?}` (email o teléfono obligatorio)
- `Contact` = `ContactIn` + `{id, full_name, stage: subscriber|lead|mql|sql|opportunity|customer|evangelist|lost, score (0–100), mautic_id|null, last_activity_at|null, created_at}`
- `Activity` = `{id, contact_id, kind: note|call|email|whatsapp|meeting|marketing|ads|system, summary, actor_id|null, occurred_at}`
- `Deal` = `{id, title, contact_id|null, contact_name|null, amount, currency, stage: new|qualified|proposal|negotiation|won|lost, owner_id|null, expected_close|null, created_at, closed_at|null}`

---

## marketing — Mautic + IA

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| GET | `/marketing/status` | marketing.manage | → `{mautic_enabled, connected, last_sync_at\|null, synced_contacts}` |
| GET | `/marketing/segments` | marketing.manage | → `Segment[]` |
| POST | `/marketing/segments` | marketing.manage | `{name, description?, filters: {stages?, tags?, min_score?}}` → `Segment` 201 |
| POST | `/marketing/segments/{id}/sync` | marketing.manage | → `Segment` (empuja a Mautic) |
| GET | `/marketing/emails` | marketing.manage | → `EmailDraft[]` |
| POST | `/marketing/emails/generate` | marketing.manage | `{goal, audience, tone?, language? (def es), segment_id?}` → `EmailDraft` 201 (IA) |
| POST | `/marketing/emails/{id}/push` | marketing.manage | → `EmailDraft` (crea email en Mautic) |
| GET | `/marketing/campaigns` | marketing.manage | → `Campaign[]` |
| POST | `/marketing/campaigns/plan` | marketing.manage | `{objective, segment_id?, duration_days}` → `Campaign` 201 (IA) |
| POST | `/marketing/campaigns/{id}/launch` | marketing.manage | → `Campaign` |
| POST | `/marketing/webhooks/mautic` | público (header `X-Mautic-Secret`) | eventos Mautic → `{ok: true}` |

- `Segment` = `{id, name, description|null, filters, contacts_count, mautic_id|null, synced_at|null}`
- `EmailDraft` = `{id, subject, preheader, body_html, body_text, goal, status: draft|pushed|sent, segment_id|null, mautic_id|null, created_at}`
- `Campaign` = `{id, name, objective, status: planned|active|paused|completed, segment_id|null, steps: [{day, channel: email|whatsapp|ads, subject, intent}], mautic_id|null, created_at}`

---

## meta — Meta Business (Ads, Lead Ads, Conversions API)

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| GET | `/meta/connection` | meta.manage | → `MetaConnection` |
| PUT | `/meta/connection` | meta.manage | `{ad_account_id, page_id?, pixel_id?, access_token}` → `MetaConnection` (el token nunca se devuelve) |
| POST | `/meta/sync` | meta.manage | → `{campaigns: int, days: int}` |
| GET | `/meta/campaigns` | meta.manage | `?days=30` → `{items: CampaignPerf[], totals: CampaignPerf-sin-id}` |
| GET | `/meta/insights/daily` | meta.manage | `?days=30` → `[{date, spend, impressions, clicks, leads}]` |
| GET | `/meta/alerts` | meta.manage | → `[{id, campaign_ref, metric, value, benchmark, severity: info\|warning\|critical, message, created_at}]` |
| POST | `/meta/leads/test` | meta.manage | `{full_name, email?, phone?}` → `{ok: true}` (simula Lead Ad → CRM) |
| GET | `/meta/webhooks` | público | verificación `hub.mode/hub.verify_token/hub.challenge` |
| POST | `/meta/webhooks` | público (`X-Hub-Signature-256`) | Lead Ads `leadgen` → `{ok: true}` |

- `MetaConnection` = `{connected, ad_account_id|null, page_id|null, pixel_id|null, last_sync_at|null}`
- `CampaignPerf` = `{id, external_id, name, status, objective, spend, impressions, clicks, ctr, cpc, cpm, leads, cpl, conversions, roas}`

---

## growth — Motor de estrategia IA (ex MerakiOS)

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| GET | `/growth/projects` | growth.use | → `Project[]` |
| POST | `/growth/projects` | growth.use | `{name, niche, url?}` → `Project` 201 |
| GET | `/growth/projects/{id}` | growth.use | → `Project` |
| POST | `/growth/projects/{id}/audit` | growth.use | → 202 (pipeline Genesis: planner → research → auditor, hasta 2 iteraciones) |
| POST | `/growth/projects/{id}/funnel` | growth.use | → 202 (pipeline Blueprint; requiere estado `audited`) |
| POST | `/growth/projects/{id}/assets` | growth.use | `{kind: ad\|landing\|email, node_id?}` → `{assets: [{kind, title, body}]}` |

- `Project` = `{id, name, niche, url|null, status: draft|analyzing|audited|designing|completed|failed, audit: Audit|null, funnel: {nodes: [{id, type: ad|landing|optin|vsl|email|checkout|upsell|thankyou, label, position:{x,y}}], edges: [{id, source, target}]}|null, error|null, created_at, updated_at}`
- `Audit` = `{avatar, pain_points[], desires[], awareness_level: unaware|problem_aware|solution_aware|product_aware|most_aware, jobs_to_be_done[], competitors[], market_opportunity}`

---

## gamification — Puntos, niveles, insignias y retos

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| GET | `/gamification/me` | gamification.read | → `PlayerProfile` |
| GET | `/gamification/leaderboard` | gamification.read | `?period=week\|month\|all&team=all\|operations\|sales\|marketing` → `[{rank, user_id, name, role, points, level}]` |
| GET | `/gamification/feed` | gamification.read | → `[{id, user_id, user_name, points, reason, occurred_at}]` (últimos 50) |
| GET | `/gamification/badges` | gamification.read | → `[{key, name, description, icon, criteria}]` |
| GET | `/gamification/challenges` | gamification.read | → `Challenge[]` (con progreso del usuario) |
| POST | `/gamification/challenges` | gamification.manage | `{title, description, metric, target, starts_at, ends_at, reward_points, team}` → `Challenge` 201 |
| GET | `/gamification/rules` | gamification.read | → `[{key, event, description, points, active}]` |
| PUT | `/gamification/rules/{key}` | gamification.manage | `{points, active}` → regla |

- `PlayerProfile` = `{user_id, name, points, level: {number, name, min_points, next_level_points|null, progress (0–1)}, streak_days, badges: [{key, name, description, icon, earned_at}], rank|null}`
- `Challenge` = `{id, title, description, metric, target, progress, starts_at, ends_at, reward_points, team, status: upcoming|active|finished}`

---

## analytics — Analítica unificada + IA

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| GET | `/analytics/overview` | analytics.read | `?days=30` → `Overview` |
| GET | `/analytics/timeseries` | analytics.read | `?metric=<key>&days=30` → `[{date, value}]` |
| GET | `/analytics/funnel` | analytics.read | → `[{stage, count}]` (ciclo de vida de contactos) |
| POST | `/analytics/insights` | analytics.read | `{days?}` → `{summary, highlights[], risks[], recommendations[]}` (IA) |

- `Overview` = `{period: {from, to}, operations: {tasks_completed, on_time_rate, avg_cleaning_minutes, issues}, sales: {new_contacts, deals_won, revenue, win_rate}, marketing: {leads_captured, engagement_events, campaigns_launched, ad_spend, cpl}, growth: {audits_completed, funnels_designed}, gamification: {points_awarded, active_players}}`
- Métricas para `timeseries`: `tasks_completed, contacts_created, leads_captured, deals_won, revenue, ad_spend, engagement_events, points_awarded`.

---

## billing — Suscripciones (Wompi)

| Método | Ruta | Permiso | Body → Respuesta |
|---|---|---|---|
| GET | `/billing/plans` | público | → `[{key, name, price_cop, period: "month", features[], limits: {properties, contacts, seats}}]` |
| GET | `/billing/subscription` | billing.manage | → `{plan, status: trialing\|active\|past_due\|canceled, current_period_end\|null}` |
| POST | `/billing/checkout` | billing.manage | `{plan}` → `{reference, amount_in_cents, currency, public_key, signature, redirect_url}` |
| POST | `/billing/webhooks/wompi` | público (checksum Wompi) | evento `transaction.updated` → `{ok: true}` |
