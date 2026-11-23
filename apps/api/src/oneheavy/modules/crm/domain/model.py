"""Dominio CRM: Contact (ciclo de vida + scoring), Activity (timeline) y Deal (pipeline)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.entity import Entity, TenantEntity
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.domain.time import utc_now
from oneheavy.shared.domain.value_objects import Email, PhoneNumber

# ── Ciclo de vida del contacto ──────────────────────────────────────────────


class LifecycleStage(StrEnum):
    SUBSCRIBER = "subscriber"
    LEAD = "lead"
    MQL = "mql"
    SQL = "sql"
    OPPORTUNITY = "opportunity"
    CUSTOMER = "customer"
    EVANGELIST = "evangelist"
    LOST = "lost"


_S = LifecycleStage

#: Máquina de estados explícita. Se permite avanzar (incluso saltando etapas
#: comerciales cercanas), retroceder un paso para corregir y marcar "lost";
#: un contacto perdido sólo se reactiva como lead o subscriber.
ALLOWED_TRANSITIONS: dict[LifecycleStage, frozenset[LifecycleStage]] = {
    _S.SUBSCRIBER: frozenset({_S.LEAD, _S.MQL, _S.SQL, _S.LOST}),
    _S.LEAD: frozenset({_S.SUBSCRIBER, _S.MQL, _S.SQL, _S.OPPORTUNITY, _S.LOST}),
    _S.MQL: frozenset({_S.LEAD, _S.SQL, _S.OPPORTUNITY, _S.LOST}),
    _S.SQL: frozenset({_S.MQL, _S.OPPORTUNITY, _S.CUSTOMER, _S.LOST}),
    _S.OPPORTUNITY: frozenset({_S.SQL, _S.CUSTOMER, _S.LOST}),
    _S.CUSTOMER: frozenset({_S.EVANGELIST, _S.LOST}),
    _S.EVANGELIST: frozenset({_S.CUSTOMER}),
    _S.LOST: frozenset({_S.SUBSCRIBER, _S.LEAD}),
}

#: Umbral de score con el que un lead pasa automáticamente a MQL.
MQL_THRESHOLD = 50


class ContactSource(StrEnum):
    MANUAL = "manual"
    META_LEAD_ADS = "meta_lead_ads"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    WEB_FORM = "web_form"
    IMPORT = "import"
    MAUTIC = "mautic"


class ActivityKind(StrEnum):
    NOTE = "note"
    CALL = "call"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    MEETING = "meeting"
    MARKETING = "marketing"
    ADS = "ads"
    SYSTEM = "system"


def normalize_tags(tags: list[str] | None) -> list[str]:
    seen: list[str] = []
    for raw in tags or []:
        tag = raw.strip().lower()
        if tag and tag not in seen:
            seen.append(tag)
    return seen


@dataclass(kw_only=True, eq=False)
class Activity(Entity):
    """Entrada inmutable del timeline de un contacto."""

    tenant_id: uuid.UUID
    contact_id: uuid.UUID
    kind: ActivityKind
    summary: str
    actor_id: uuid.UUID | None = None
    occurred_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.summary = self.summary.strip()
        if not self.summary:
            raise BusinessRuleViolation("La actividad necesita un resumen")


@dataclass(kw_only=True, eq=False)
class Contact(TenantEntity):
    first_name: str
    last_name: str | None = None
    email: Email | None = None
    phone: PhoneNumber | None = None
    company: str | None = None
    job_title: str | None = None
    source: ContactSource = ContactSource.MANUAL
    tags: list[str] = field(default_factory=list)
    owner_id: uuid.UUID | None = None
    stage: LifecycleStage = LifecycleStage.LEAD
    score: int = 0
    engagement_points: int = 0
    mautic_id: int | None = None
    last_activity_at: datetime | None = None

    # ── Fábrica ─────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        first_name: str,
        last_name: str | None = None,
        email: Email | None = None,
        phone: PhoneNumber | None = None,
        company: str | None = None,
        job_title: str | None = None,
        source: ContactSource = ContactSource.MANUAL,
        tags: list[str] | None = None,
        owner_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> Contact:
        if email is None and phone is None:
            raise BusinessRuleViolation("El contacto necesita email o teléfono", code="contact_unreachable")
        first = first_name.strip()
        if not first:
            raise BusinessRuleViolation("El nombre del contacto es obligatorio")
        stage = LifecycleStage.SUBSCRIBER if source is ContactSource.MAUTIC else LifecycleStage.LEAD
        contact = cls(
            tenant_id=tenant_id,
            first_name=first,
            last_name=(last_name or "").strip() or None,
            email=email,
            phone=phone,
            company=(company or "").strip() or None,
            job_title=(job_title or "").strip() or None,
            source=source,
            tags=normalize_tags(tags),
            owner_id=owner_id,
            stage=stage,
        )
        contact.record(
            ie.ContactCreated(
                tenant_id=tenant_id,
                actor_id=actor_id,
                contact_id=contact.id,
                email=str(email) if email else None,
                phone=str(phone) if phone else None,
                source=source.value,
                owner_id=owner_id,
                stage=stage.value,
                first_name=contact.first_name,
                last_name=contact.last_name,
                tags=tuple(contact.tags),
            )
        )
        return contact

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p)

    # ── Comportamiento ──────────────────────────────────────────────────────

    def can_move_to(self, stage: LifecycleStage) -> bool:
        return stage in ALLOWED_TRANSITIONS[self.stage]

    def move_to(self, stage: LifecycleStage, *, actor_id: uuid.UUID | None = None) -> None:
        if stage == self.stage:
            return
        if not self.can_move_to(stage):
            raise BusinessRuleViolation(
                f"Transición no permitida: {self.stage.value} → {stage.value}",
                code="invalid_stage_transition",
            )
        previous, self.stage = self.stage, stage
        self.touch()
        self.record(
            ie.ContactLifecycleChanged(
                tenant_id=self.tenant_id,
                actor_id=actor_id,
                contact_id=self.id,
                from_stage=previous.value,
                to_stage=stage.value,
            )
        )

    def apply_score(self, score: int) -> None:
        """Fija el score (0 a 100) y auto-avanza lead → MQL al cruzar el umbral."""
        self.score = max(0, min(100, score))
        if self.stage is LifecycleStage.LEAD and self.score >= MQL_THRESHOLD:
            self.move_to(LifecycleStage.MQL)

    def add_engagement(self, points: int, at: datetime | None = None) -> None:
        self.engagement_points = max(0, self.engagement_points + points)
        self.register_activity(at)

    def register_activity(self, at: datetime | None = None) -> None:
        moment = at or utc_now()
        if self.last_activity_at is None or moment > self.last_activity_at:
            self.last_activity_at = moment
        self.touch()

    def update_profile(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: Email | None = None,
        phone: PhoneNumber | None = None,
        company: str | None = None,
        job_title: str | None = None,
        tags: list[str] | None = None,
        owner_id: uuid.UUID | None = None,
        source: ContactSource | None = None,
    ) -> None:
        if first_name is not None:
            if not first_name.strip():
                raise BusinessRuleViolation("El nombre del contacto es obligatorio")
            self.first_name = first_name.strip()
        if last_name is not None:
            self.last_name = last_name.strip() or None
        if email is not None:
            self.email = email
        if phone is not None:
            self.phone = phone
        if company is not None:
            self.company = company.strip() or None
        if job_title is not None:
            self.job_title = job_title.strip() or None
        if tags is not None:
            self.tags = normalize_tags(tags)
        if owner_id is not None:
            self.owner_id = owner_id
        if source is not None:
            self.source = source
        self.touch()

    def merge_missing(
        self,
        *,
        last_name: str | None = None,
        email: Email | None = None,
        phone: PhoneNumber | None = None,
        company: str | None = None,
        job_title: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Fusión no destructiva: sólo completa los datos vacíos (dedupe)."""
        self.last_name = self.last_name or ((last_name or "").strip() or None)
        self.email = self.email or email
        self.phone = self.phone or phone
        self.company = self.company or ((company or "").strip() or None)
        self.job_title = self.job_title or ((job_title or "").strip() or None)
        self.tags = normalize_tags([*self.tags, *(tags or [])])
        self.touch()


# ── Pipeline de negocios ────────────────────────────────────────────────────


class DealStage(StrEnum):
    NEW = "new"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


@dataclass(frozen=True)
class PipelineStage:
    key: DealStage
    name: str
    order: int
    probability: float


PIPELINE: tuple[PipelineStage, ...] = (
    PipelineStage(DealStage.NEW, "Nuevo", 1, 0.10),
    PipelineStage(DealStage.QUALIFIED, "Calificado", 2, 0.25),
    PipelineStage(DealStage.PROPOSAL, "Propuesta", 3, 0.50),
    PipelineStage(DealStage.NEGOTIATION, "Negociación", 4, 0.75),
    PipelineStage(DealStage.WON, "Ganado", 5, 1.0),
    PipelineStage(DealStage.LOST, "Perdido", 6, 0.0),
)

CLOSED_STAGES = frozenset({DealStage.WON, DealStage.LOST})


@dataclass(kw_only=True, eq=False)
class Deal(TenantEntity):
    title: str
    amount: Decimal
    currency: str = "COP"
    contact_id: uuid.UUID | None = None
    stage: DealStage = DealStage.NEW
    owner_id: uuid.UUID | None = None
    expected_close: date | None = None
    closed_at: datetime | None = None

    @classmethod
    def open(
        cls,
        *,
        tenant_id: uuid.UUID,
        title: str,
        amount: Decimal,
        currency: str = "COP",
        contact_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        expected_close: date | None = None,
    ) -> Deal:
        deal = cls(
            tenant_id=tenant_id,
            title=title,
            amount=amount,
            currency=currency,
            contact_id=contact_id,
            owner_id=owner_id,
            expected_close=expected_close,
        )
        deal._validate()
        return deal

    def _validate(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise BusinessRuleViolation("El negocio necesita un título")
        if self.amount < 0:
            raise BusinessRuleViolation("El monto no puede ser negativo", code="invalid_amount")
        self.currency = self.currency.upper()
        if len(self.currency) != 3:
            raise BusinessRuleViolation("Moneda inválida (ISO-4217)", code="invalid_currency")

    @property
    def is_closed(self) -> bool:
        return self.stage in CLOSED_STAGES

    def edit(
        self,
        *,
        title: str | None = None,
        amount: Decimal | None = None,
        currency: str | None = None,
        contact_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        expected_close: date | None = None,
    ) -> None:
        if self.is_closed:
            raise BusinessRuleViolation("Un negocio cerrado no se puede editar", code="deal_closed")
        if title is not None:
            self.title = title
        if amount is not None:
            self.amount = amount
        if currency is not None:
            self.currency = currency
        if contact_id is not None:
            self.contact_id = contact_id
        if owner_id is not None:
            self.owner_id = owner_id
        if expected_close is not None:
            self.expected_close = expected_close
        self._validate()
        self.touch()

    def move(self, stage: DealStage, *, actor_id: uuid.UUID | None = None, reason: str | None = None) -> None:
        if stage == self.stage:
            return
        if self.is_closed:
            raise BusinessRuleViolation("El negocio ya está cerrado", code="deal_closed")
        self.stage = stage
        self.touch()
        if stage is DealStage.WON:
            self.closed_at = utc_now()
            self.record(
                ie.DealWon(
                    tenant_id=self.tenant_id,
                    actor_id=actor_id,
                    deal_id=self.id,
                    contact_id=self.contact_id,
                    owner_id=self.owner_id,
                    amount=self.amount,
                    currency=self.currency,
                )
            )
        elif stage is DealStage.LOST:
            self.closed_at = utc_now()
            self.record(
                ie.DealLost(
                    tenant_id=self.tenant_id,
                    actor_id=actor_id,
                    deal_id=self.id,
                    owner_id=self.owner_id,
                    reason=reason,
                )
            )
