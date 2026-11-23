# Catálogo de casos de uso

Convención de IDs: `CU-<MÓDULO>-NN` · reglas `REG-<MÓDULO>-NN`. Endpoints relativos a `/api/v1`
([contrato](../architecture/api-contract.md)). Todo caso de uso autenticado opera **dentro del workspace del token**.

**Plantilla:** Actor · Precondiciones · Flujo principal · Alternos · Reglas · Postcondiciones · Eventos · Endpoint.

---

## Identity (ID)

### CU-ID-01 Registrar workspace (onboarding self-service)
- **Actor:** visitante → dueño. **Pre:** email no registrado.
- **Flujo:** 1) envía nombre del negocio, su nombre, email, contraseña, teléfono opcional · 2) se crea `Workspace` (plan trial, slug único, branding = nombre) · 3) se crea `User` rol `owner` · 4) se devuelve sesión JWT.
- **Alternos:** email existente → 409 `email_taken`; slug ocupado → sufijo automático; contraseña débil → 422.
- **Reglas:** REG-ID-01 contraseña ≥ 10 caracteres con letras y números · REG-ID-02 rate limit por IP.
- **Post:** workspace y dueño activos. **Eventos:** `WorkspaceCreated`, `UserRegistered`. **Endpoint:** `POST /auth/register`.

### CU-ID-02 Iniciar sesión
- **Actor:** cualquier usuario. **Flujo:** identificador (email o usuario) + contraseña → valida → registra `last_login_at` → JWT.
- **Alternos:** credenciales inválidas o usuario inactivo → 401 con mensaje genérico; exceso de intentos → 429.
- **Reglas:** REG-ID-03 no revelar si el usuario existe. **Endpoint:** `POST /auth/login`.

### CU-ID-03 Consultar sesión actual
- **Actor:** usuario autenticado. **Flujo:** devuelve usuario (con permisos efectivos) y workspace. **Endpoint:** `GET /auth/me`.

### CU-ID-04 Invitar miembro al equipo
- **Actor:** owner/admin/manager. **Pre:** permiso `members.manage`.
- **Flujo:** nombre, rol, email y/o teléfono, contraseña temporal → crea usuario → WhatsApp de bienvenida con su usuario (sin contraseña) desde la instancia del workspace.
- **Alternos:** login ya existe → 409; rol `owner` → 403; `admin` creado por no-owner → 403.
- **Reglas:** REG-ID-04 nadie asigna `owner` · REG-ID-05 sólo `owner` crea `admin` · REG-ID-06 la contraseña nunca viaja por WhatsApp · REG-ID-07 email o teléfono obligatorio.
- **Eventos:** `UserRegistered` (stays lo vuelve `StaffMember` si rol `staff`; gamificación crea su perfil). **Endpoint:** `POST /workspace/members`.

### CU-ID-05 Listar miembros · `GET /workspace/members` (permiso `members.manage`).

### CU-ID-06 Configurar marca blanca
- **Actor:** owner/admin. **Flujo:** nombre comercial, logo, color primario (#RRGGBB), instancia de WhatsApp → los mensajes salen con la marca y el número del cliente.
- **Endpoint:** `PUT /workspace/branding`.

---

## Stays (ST) — operación de alquileres

### CU-ST-01 Registrar propiedad
- **Actor:** manager/admin. **Flujo:** código, nombre, dirección, capacidad, propietario (nombre/teléfono), personal por defecto, días de corte por servicio, checklist, inventario visual, URL iCal → se guarda → WhatsApp de bienvenida al propietario con resumen de cortes.
- **Reglas:** REG-ST-01 días de corte 1–31 · REG-ST-02 código único por workspace. **Endpoint:** `POST /stays/properties`.

### CU-ST-02 Sincronizar calendario iCal (Airbnb/Booking)
- **Actor:** manager o sistema (job). **Flujo:** descarga iCal → por cada reserva futura crea una tarea en el check-out (11:00 si sólo hay fecha) asignada al personal por defecto.
- **Alternos:** URL inválida/no responde → 502; tarea ya existente ese día → se omite.
- **Reglas:** REG-ST-03 sin duplicados por (propiedad, día) · REG-ST-04 sólo URLs http/https públicas. **Endpoint:** `POST /stays/properties/{id}/calendar-sync`.

### CU-ST-03 Programar tarea de limpieza
- **Actor:** coordinador/manager. **Flujo:** propiedad, personal, fecha/hora, observaciones, maletas (none/leave/collect), insumos → tarea `pending` → WhatsApp al personal.
- **Eventos:** `CleaningTaskScheduled`. **Endpoint:** `POST /stays/tasks`.

### CU-ST-04 Editar o cancelar tarea
- **Reglas:** REG-ST-05 sólo se edita en `pending` · REG-ST-06 cancelar exige motivo. **Endpoints:** `PATCH /stays/tasks/{id}`, `POST /stays/tasks/{id}/cancel`.

### CU-ST-05 Confirmar llegada con fotos iniciales
- **Actor:** staff (app o botón de WhatsApp "Ya llegué"). **Pre:** tarea `pending` asignada a él.
- **Flujo:** sube ≥ 1 foto → `arrived`, se registra minutos de retraso.
- **Alternos:** "No han salido" → incidencia `guests_not_out` y aviso al supervisor; sin fotos → 422.
- **Reglas:** REG-ST-07 fotos obligatorias · REG-ST-08 staff sólo opera sus tareas. **Eventos:** `CleaningArrivalConfirmed`. **Endpoint:** `POST /stays/tasks/{id}/arrival`.

### CU-ST-06 Iniciar limpieza · `POST /stays/tasks/{id}/start` (requiere `arrived`).

### CU-ST-07 Completar checklist · `PUT /stays/tasks/{id}/checklist` — REG-ST-09 los ítems provienen de la plantilla de la propiedad.

### CU-ST-08 Reportar incidencia o faltante de insumos
- **Flujo:** tipo (`problem`, `missing_supplies`, `guests_not_out`) + descripción → se agrega a la tarea → WhatsApp al supervisor.
- **Eventos:** `CleaningIssueReported`. **Endpoint:** `POST /stays/tasks/{id}/issues`.

### CU-ST-09 Finalizar tarea con fotos finales
- **Pre:** `in_progress`, checklist 100 %. **Flujo:** fotos finales → `completed`, duración calculada, `on_time` según hora programada.
- **Reglas:** REG-ST-10 checklist completo · REG-ST-11 fotos finales obligatorias. **Eventos:** `CleaningTaskCompleted`. **Endpoint:** `POST /stays/tasks/{id}/complete`.

### CU-ST-10 Fotos requeridas (estándar/aleatorio)
- Modo estándar: cama, baño, cocina, sala. Modo aleatorio: 3–5 ítems del inventario visual (anti-fraude). **Endpoint:** `GET /stays/tasks/{id}/required-photos`.

### CU-ST-11 Recordatorio diario al personal (sistema)
- **Disparador:** job a la hora configurada (def. 19:00). **Flujo:** agrupa tareas de mañana por staff → WhatsApp con lista y horas.
- **Reglas:** REG-ST-12 la fecha se calcula en cada ejecución (zona del workspace).

### CU-ST-12 Confirmación y escalamiento de llegada (sistema)
- **Disparador:** job cada 5 min. **Flujo:** tareas que inician en ≤ 5 min → botones de confirmación; tareas `pending` sin llegada tras `escalation_minutes` → alerta al supervisor del workspace.
- **Reglas:** REG-ST-13 una sola escalación por tarea.

### CU-ST-13 Recordatorio de cortes de servicios (sistema)
- **Disparador:** job 09:00. **Flujo:** 5 días antes del corte → recordatorio al propietario; el día del corte sin comprobante verificado → alerta de vencido y pausa de automatización.

### CU-ST-14 Subir comprobante de pago
- **Actor:** propietario. **Flujo:** archivo (JPG/PNG/WEBP/PDF ≤ 10 MB), servicio, periodo → `pending`.
- **Reglas:** REG-ST-14 validación de tipo real (magic bytes) · REG-ST-15 propietario sólo sobre sus propiedades. **Endpoint:** `POST /stays/properties/{id}/receipts`.

### CU-ST-15 Revisar comprobante
- **Actor:** manager. **Flujo:** aprueba → `verified` y se reanuda la automatización; rechaza → `rejected` con nota y aviso al propietario.
- **Eventos:** `ReceiptVerified`. **Endpoint:** `POST /stays/receipts/{id}/review`.

### CU-ST-16 Gestionar personal · `GET/POST /stays/staff` (también se alimenta de `UserRegistered`).

### CU-ST-17 Tablero operativo · `GET /stays/dashboard` — tareas de hoy por estado, % a tiempo, duración promedio, ranking del personal, próximas tareas.

### CU-ST-18 Configurar operación · `GET/PUT /stays/settings` — teléfono del supervisor, hora de recordatorio, minutos de escalamiento, modo de fotos.

---

## CRM

### CU-CRM-01 Crear contacto
- **Actor:** sales/marketer. **Flujo:** datos + origen + tags → dedupe por email/teléfono normalizado → `Contact` en etapa `lead` (o `subscriber`).
- **Alternos:** duplicado → 409 `duplicate_contact`. **Reglas:** REG-CRM-01 email o teléfono obligatorio · REG-CRM-02 teléfono en E.164.
- **Eventos:** `ContactCreated`. **Endpoint:** `POST /crm/contacts`.

### CU-CRM-02 Capturar lead desde Meta/WhatsApp/web (sistema)
- **Disparador:** `LeadCaptured`. **Flujo:** buscar por email/teléfono → si existe, fusionar datos y registrar actividad `ads`; si no, crear contacto con `source` del lead.
- **Reglas:** REG-CRM-03 idempotente por `external_id`. **Eventos:** `ContactCreated` (si es nuevo).

### CU-CRM-03 Buscar y filtrar contactos · `GET /crm/contacts?q&stage&tag&owner_id&page&size`.

### CU-CRM-04 Actualizar contacto · `PATCH /crm/contacts/{id}`.

### CU-CRM-05 Cambiar etapa del ciclo de vida
- **Reglas:** REG-CRM-04 transiciones hacia adelante libres; retroceso sólo a `lead`; `lost` desde cualquier etapa · REG-CRM-05 `customer` sólo con negocio ganado o acción manual explícita.
- **Eventos:** `ContactLifecycleChanged`. **Endpoint:** `POST /crm/contacts/{id}/stage`.

### CU-CRM-06 Registrar actividad y ver timeline · `POST /crm/contacts/{id}/activities`, `GET /crm/contacts/{id}/timeline`.

### CU-CRM-07 Calcular score (sistema)
- **Disparadores:** creación, actividad, `MarketingEngagementRecorded`. **Flujo:** score 0–100 = perfil (datos completos, cargo) + engagement (aperturas, clics, formularios) + recencia (decaimiento) → si supera umbral, sugiere `mql`/`sql`.

### CU-CRM-08 Insight IA del contacto
- **Flujo:** score, temperatura (cold/warm/hot), explicación en lenguaje natural y siguiente mejor acción generadas por IA a partir del timeline. **Endpoint:** `POST /crm/contacts/{id}/insight`.

### CU-CRM-09 Importar contactos · `POST /crm/contacts/import` → `{created, merged, skipped}`.

### CU-CRM-10 Gestionar pipeline de negocios
- **Flujo:** crear negocio (monto, moneda, contacto, etapa) → mover entre `new → qualified → proposal → negotiation → won | lost`.
- **Reglas:** REG-CRM-06 `won`/`lost` son terminales y fijan `closed_at` · REG-CRM-07 al ganar, el contacto pasa a `customer`.
- **Eventos:** `DealWon`, `DealLost`, `ContactLifecycleChanged`. **Endpoints:** `GET /crm/pipeline`, `POST /crm/deals`, `PATCH /crm/deals/{id}`, `POST /crm/deals/{id}/move`.

---

## Marketing — Mautic + IA (MK)

### CU-MK-01 Ver estado de la integración · `GET /marketing/status`.

### CU-MK-02 Crear segmento
- **Flujo:** nombre + filtros (etapas, tags, score mínimo) → cálculo de contactos. **Endpoint:** `POST /marketing/segments`.

### CU-MK-03 Sincronizar segmento con Mautic
- **Pre:** Mautic habilitado. **Flujo:** crea/actualiza segmento en Mautic y asigna contactos (upsert). **Alternos:** Mautic caído → 502, se reintenta. **Endpoint:** `POST /marketing/segments/{id}/sync`.

### CU-MK-04 Sincronizar contacto nuevo (sistema)
- **Disparador:** `ContactCreated`/`ContactLifecycleChanged`. **Flujo:** upsert en Mautic, guarda `mautic_id`. **Reglas:** REG-MK-01 sin Mautic habilitado, se omite sin error.

### CU-MK-05 Generar email con IA
- **Flujo:** objetivo, audiencia, tono, idioma → IA produce asunto, preheader, HTML y texto plano → borrador.
- **Reglas:** REG-MK-02 salida JSON validada · REG-MK-03 incluye enlace de baja · REG-MK-04 la IA propone, una persona aprueba. **Endpoint:** `POST /marketing/emails/generate`.

### CU-MK-06 Publicar email en Mautic · `POST /marketing/emails/{id}/push` → `pushed` con `mautic_id`.

### CU-MK-07 Planificar campaña con IA
- **Flujo:** objetivo + segmento + duración → IA propone secuencia de pasos (día, canal email/whatsapp/ads, asunto, intención). **Endpoint:** `POST /marketing/campaigns/plan`.

### CU-MK-08 Lanzar campaña · `POST /marketing/campaigns/{id}/launch` → `active`. **Eventos:** `CampaignLaunched`.

### CU-MK-09 Recibir engagement de Mautic (sistema)
- **Disparador:** webhook con `X-Mautic-Secret`. **Flujo:** apertura/clic/formulario/visita → `MarketingEngagementRecorded` con puntos → CRM actualiza score y timeline.
- **Reglas:** REG-MK-05 secreto inválido → 401 · REG-MK-06 idempotente. **Endpoint:** `POST /marketing/webhooks/mautic`.

---

## Meta Business (META)

### CU-META-01 Conectar cuenta publicitaria
- **Actor:** marketer/admin. **Flujo:** ad account, página, pixel, token → se valida contra Graph API → conexión guardada (token nunca se devuelve). **Endpoint:** `PUT /meta/connection`.

### CU-META-02 Sincronizar insights
- **Actor:** marketer o job diario. **Flujo:** campañas + métricas (gasto, impresiones, clics, CTR, CPC, CPM, leads, CPL, conversiones, ROAS) de N días → snapshots diarios.
- **Eventos:** `AdInsightsSynced` (por día). **Endpoint:** `POST /meta/sync`.

### CU-META-03 Ver rendimiento de campañas · `GET /meta/campaigns?days`, `GET /meta/insights/daily?days`.

### CU-META-04 Detectar anomalías (sistema, ex Director de MerakiOS)
- **Flujo:** tras sincronizar, reglas Strategy (CTR < 1 %, CPL > benchmark × 1.5, gasto sin conversiones…) → alertas con severidad.
- **Eventos:** `AdPerformanceAnomalyDetected`. **Endpoint:** `GET /meta/alerts`.

### CU-META-05 Recibir lead de Lead Ads (sistema)
- **Disparador:** webhook `leadgen`. **Flujo:** valida `X-Hub-Signature-256` → obtiene el lead por Graph API → `LeadCaptured`.
- **Reglas:** REG-META-01 firma HMAC obligatoria · REG-META-02 idempotente por `leadgen_id`. **Endpoints:** `GET/POST /meta/webhooks`.

### CU-META-06 Simular lead (demo/QA) · `POST /meta/leads/test`.

### CU-META-07 Enviar conversiones (Conversions API, sistema)
- **Disparador:** `DealWon` (Purchase con valor) y `ContactLifecycleChanged` a `sql` (Lead calificado).
- **Reglas:** REG-META-03 email/teléfono hasheados SHA-256 · REG-META-04 sólo si hay pixel conectado.

---

## Growth IA (GR) — ex MerakiOS

### CU-GR-01 Crear proyecto de growth · `POST /growth/projects` (`name, niche, url?`) → `draft`.

### CU-GR-02 Auditar mercado (Genesis)
- **Flujo (202, asíncrono):** `analyzing` → Planner genera 3 búsquedas → Researcher consulta la web → Auditor aplica niveles de consciencia de Schwartz y Jobs-To-Be-Done → si falta información y < 2 iteraciones, repite → `audited`.
- **Alternos:** error del proveedor → `failed` con mensaje. **Eventos:** `MarketAuditCompleted`. **Endpoint:** `POST /growth/projects/{id}/audit`.

### CU-GR-03 Diseñar embudo (Blueprint)
- **Pre:** `audited`. **Flujo:** Architect elige embudo según consciencia (educativo vs. oferta directa) → grafo de nodos/aristas validado → `completed`.
- **Reglas:** REG-GR-01 grafo conexo, un nodo de entrada · REG-GR-02 tipos de nodo permitidos. **Eventos:** `FunnelDesigned`. **Endpoint:** `POST /growth/projects/{id}/funnel`.

### CU-GR-04 Generar assets (ads, landing, emails) · `POST /growth/projects/{id}/assets`.

### CU-GR-05 Consultar proyectos · `GET /growth/projects`, `GET /growth/projects/{id}` (polling del estado).

---

## Gamificación (GM)

### CU-GM-01 Otorgar puntos por evento (sistema)
- **Disparador:** eventos de integración. **Flujo:** regla activa del workspace → `PointTransaction` → actualiza perfil (puntos, nivel, racha) → evalúa insignias y retos.
- **Reglas por defecto (configurables):** limpieza completada a tiempo +20 · llegada puntual +5 · contacto creado +2 · negocio ganado +50 · campaña lanzada +15 · auditoría completada +10 · embudo diseñado +10 · comprobante verificado (propietario al día) +5.
- **Reglas:** REG-GM-01 idempotente por (`event_id`, `rule_key`) · REG-GM-02 sólo usuarios del workspace. **Eventos:** `PointsAwarded`.

### CU-GM-02 Ver mi perfil · `GET /gamification/me` — puntos, nivel y progreso, racha, insignias, posición.

### CU-GM-03 Ver leaderboard · `GET /gamification/leaderboard?period&team` (equipos: operaciones, ventas, marketing).

### CU-GM-04 Ver feed de logros · `GET /gamification/feed`.

### CU-GM-05 Crear reto
- **Actor:** manager/admin. **Flujo:** métrica, meta, fechas, puntos de recompensa, equipo → al cumplirse se otorgan los puntos. **Endpoints:** `GET/POST /gamification/challenges`.

### CU-GM-06 Configurar reglas · `GET /gamification/rules`, `PUT /gamification/rules/{key}`.

---

## Analytics (AN)

### CU-AN-01 Ver resumen ejecutivo · `GET /analytics/overview?days` — operación, ventas, marketing, growth, gamificación.
### CU-AN-02 Ver series de tiempo · `GET /analytics/timeseries?metric&days`.
### CU-AN-03 Ver embudo de ciclo de vida · `GET /analytics/funnel`.
### CU-AN-04 Generar insights IA
- **Flujo:** KPIs del periodo → IA devuelve resumen, logros, riesgos y recomendaciones accionables. **Reglas:** REG-AN-01 sólo agregados (sin PII) en el prompt. **Endpoint:** `POST /analytics/insights`.
### CU-AN-05 Proyectar eventos (sistema) — cada evento de integración se guarda como hecho (`métrica, valor, dimensiones, fecha`) del workspace.

---

## Billing (BI)

### CU-BI-01 Ver planes · `GET /billing/plans` (público).
### CU-BI-02 Ver suscripción · `GET /billing/subscription`.
### CU-BI-03 Iniciar pago
- **Actor:** owner. **Flujo:** plan → referencia única + firma de integridad SHA-256 (`referencia + monto + moneda + secreto`) → datos para el widget de Wompi. **Endpoint:** `POST /billing/checkout`.
### CU-BI-04 Confirmar pago (sistema)
- **Disparador:** webhook Wompi. **Flujo:** valida checksum → registra pago → `APPROVED` activa suscripción y cambia plan del workspace.
- **Reglas:** REG-BI-01 checksum inválido → 401 · REG-BI-02 idempotente por id de transacción. **Eventos:** `PaymentApproved`. **Endpoint:** `POST /billing/webhooks/wompi`.
