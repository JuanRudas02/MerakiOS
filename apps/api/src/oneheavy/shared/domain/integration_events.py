"""Catálogo de eventos de integración (Published Language entre módulos).

Regla de arquitectura: un módulo NUNCA importa el dominio de otro módulo.
Si necesita reaccionar a algo que pasó en otro contexto, se suscribe a uno de
estos eventos. Agregar un evento aquí es un cambio de contrato: documentarlo
en docs/architecture/events.md.

Productores → Consumidores típicos:
    identity     → gamification, crm, marketing
    stays        → gamification, analytics
    crm          → gamification, marketing, analytics
    meta         → crm (leads), analytics
    marketing    → crm (engagement, mautic_id), gamification, analytics
    growth       → gamification, analytics
    billing      → identity (plan), analytics
    gamification → analytics
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from oneheavy.shared.domain.events import DomainEvent

# ── identity ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class WorkspaceCreated(DomainEvent):
    workspace_name: str
    owner_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    user_id: uuid.UUID
    email: str | None
    name: str
    role: str
    phone: str | None = None


# ── stays (operación de alquileres de corta estadía) ───────────────────────


@dataclass(frozen=True, kw_only=True)
class CleaningTaskScheduled(DomainEvent):
    task_id: uuid.UUID
    property_id: uuid.UUID
    staff_id: uuid.UUID | None
    scheduled_at: datetime


@dataclass(frozen=True, kw_only=True)
class CleaningArrivalConfirmed(DomainEvent):
    task_id: uuid.UUID
    staff_id: uuid.UUID | None
    minutes_late: int  # negativo = llegó antes


@dataclass(frozen=True, kw_only=True)
class CleaningTaskCompleted(DomainEvent):
    task_id: uuid.UUID
    property_id: uuid.UUID
    staff_id: uuid.UUID | None
    duration_minutes: int | None
    photos_count: int
    on_time: bool


@dataclass(frozen=True, kw_only=True)
class CleaningIssueReported(DomainEvent):
    task_id: uuid.UUID
    staff_id: uuid.UUID | None
    kind: str  # problem | missing_supplies | guests_not_out
    description: str


@dataclass(frozen=True, kw_only=True)
class ReceiptVerified(DomainEvent):
    property_id: uuid.UUID
    receipt_id: uuid.UUID
    service: str


# ── crm ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class ContactCreated(DomainEvent):
    contact_id: uuid.UUID
    email: str | None
    phone: str | None
    source: str
    owner_id: uuid.UUID | None = None
    stage: str = "lead"  # etapa inicial del ciclo de vida
    first_name: str | None = None
    last_name: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class ContactLifecycleChanged(DomainEvent):
    contact_id: uuid.UUID
    from_stage: str
    to_stage: str


@dataclass(frozen=True, kw_only=True)
class DealWon(DomainEvent):
    deal_id: uuid.UUID
    contact_id: uuid.UUID | None
    owner_id: uuid.UUID | None
    amount: Decimal
    currency: str


@dataclass(frozen=True, kw_only=True)
class DealLost(DomainEvent):
    deal_id: uuid.UUID
    owner_id: uuid.UUID | None
    reason: str | None = None


# ── meta business ───────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class LeadCaptured(DomainEvent):
    """Lead entrante desde Meta Lead Ads / WhatsApp / Instagram DM / formulario."""

    source: str  # meta_lead_ads | whatsapp | instagram | web_form
    external_id: str | None
    full_name: str | None
    email: str | None
    phone: str | None
    campaign_ref: str | None = None
    answers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class AdPerformanceAnomalyDetected(DomainEvent):
    campaign_ref: str
    metric: str
    value: float
    benchmark: float
    severity: str  # info | warning | critical


@dataclass(frozen=True, kw_only=True)
class AdInsightsSynced(DomainEvent):
    """Métricas diarias agregadas de la cuenta publicitaria (una por día sincronizado)."""

    day: datetime
    spend: Decimal
    currency: str
    impressions: int
    clicks: int
    leads: int


# ── marketing (Mautic) ──────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class MarketingEngagementRecorded(DomainEvent):
    contact_id: uuid.UUID | None
    email: str | None
    kind: str  # email_open | email_click | form_submit | page_hit
    points: int = 0


@dataclass(frozen=True, kw_only=True)
class MarketingContactSynced(DomainEvent):
    """El contacto quedó vinculado a Mautic (el CRM guarda `mautic_id`)."""

    contact_id: uuid.UUID
    mautic_id: int


@dataclass(frozen=True, kw_only=True)
class CampaignLaunched(DomainEvent):
    campaign_id: uuid.UUID
    name: str
    channel: str


# ── growth (motor de estrategia IA, ex-MerakiOS) ────────────────────────────


@dataclass(frozen=True, kw_only=True)
class MarketAuditCompleted(DomainEvent):
    project_id: uuid.UUID
    awareness_level: str


@dataclass(frozen=True, kw_only=True)
class FunnelDesigned(DomainEvent):
    project_id: uuid.UUID
    nodes_count: int


# ── gamification ────────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class PointsAwarded(DomainEvent):
    user_id: uuid.UUID
    points: int
    reason: str
    rule_key: str


# ── billing ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class PaymentApproved(DomainEvent):
    payment_id: uuid.UUID
    reference: str
    amount_in_cents: int
    currency: str
    plan: str | None = None
