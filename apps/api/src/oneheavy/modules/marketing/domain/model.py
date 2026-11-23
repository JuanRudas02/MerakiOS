"""Dominio de Marketing: audiencia espejo, segmentos, emails IA y campañas."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from oneheavy.modules.marketing.domain.html import html_to_text, sanitize_html
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.entity import Entity, TenantEntity
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.domain.time import utc_now


class EngagementKind(StrEnum):
    EMAIL_OPEN = "email_open"
    EMAIL_CLICK = "email_click"
    FORM_SUBMIT = "form_submit"
    PAGE_HIT = "page_hit"


#: Puntos de engagement por tipo de interacción (alimentan el lead scoring del CRM).
ENGAGEMENT_POINTS: dict[EngagementKind, int] = {
    EngagementKind.EMAIL_OPEN: 2,
    EngagementKind.EMAIL_CLICK: 5,
    EngagementKind.FORM_SUBMIT: 10,
    EngagementKind.PAGE_HIT: 1,
}


@dataclass(kw_only=True, eq=False)
class AudienceMember(Entity):
    """Proyección local de un contacto del CRM (construida sólo con eventos).

    `engagement_points` es la señal de interés que marketing conoce de primera
    mano (aperturas, clics, formularios) y se usa como `min_score` de segmentos.
    """

    tenant_id: uuid.UUID
    contact_id: uuid.UUID
    email: str | None = None
    phone: str | None = None
    stage: str = "lead"
    tags: list[str] = field(default_factory=list)
    engagement_points: int = 0
    mautic_id: int | None = None
    synced_at: datetime | None = None

    def link_mautic(self, mautic_id: int) -> None:
        self.mautic_id = mautic_id
        self.synced_at = utc_now()
        self.touch()

    def engage(self, points: int) -> None:
        self.engagement_points = max(0, self.engagement_points + points)
        self.touch()


@dataclass(frozen=True)
class SegmentFilters:
    stages: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    min_score: int | None = None

    def matches(self, member: AudienceMember) -> bool:
        if self.stages and member.stage not in self.stages:
            return False
        if self.tags and not set(self.tags) & set(member.tags):
            return False
        return not (self.min_score is not None and member.engagement_points < self.min_score)

    def as_dict(self) -> dict[str, object]:
        return {"stages": list(self.stages), "tags": list(self.tags), "min_score": self.min_score}


@dataclass(kw_only=True, eq=False)
class Segment(TenantEntity):
    name: str
    description: str | None = None
    filters: SegmentFilters = field(default_factory=SegmentFilters)
    contacts_count: int = 0
    mautic_id: int | None = None
    synced_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if len(self.name) < 2:
            raise BusinessRuleViolation("El nombre del segmento es demasiado corto")

    def evaluate(self, audience: list[AudienceMember]) -> list[AudienceMember]:
        members = [m for m in audience if self.filters.matches(m)]
        self.contacts_count = len(members)
        return members

    def mark_synced(self, mautic_id: int) -> None:
        self.mautic_id = mautic_id
        self.synced_at = utc_now()
        self.touch()


class EmailStatus(StrEnum):
    DRAFT = "draft"
    PUSHED = "pushed"
    SENT = "sent"


@dataclass(kw_only=True, eq=False)
class EmailDraft(TenantEntity):
    subject: str
    preheader: str
    body_html: str
    body_text: str
    goal: str
    status: EmailStatus = EmailStatus.DRAFT
    segment_id: uuid.UUID | None = None
    mautic_id: int | None = None

    @classmethod
    def compose(
        cls,
        *,
        tenant_id: uuid.UUID,
        subject: str,
        preheader: str,
        body_html: str,
        body_text: str | None,
        goal: str,
        segment_id: uuid.UUID | None = None,
    ) -> EmailDraft:
        """Normaliza y sanitiza el contenido (el HTML del LLM no es confiable)."""
        subject = " ".join(subject.split())[:150]
        if not subject:
            raise BusinessRuleViolation("El email necesita asunto", code="invalid_email_draft")
        clean_html = sanitize_html(body_html)
        if not clean_html:
            raise BusinessRuleViolation("El email necesita contenido", code="invalid_email_draft")
        return cls(
            tenant_id=tenant_id,
            subject=subject,
            preheader=" ".join(preheader.split())[:200],
            body_html=clean_html,
            body_text=(body_text or "").strip() or html_to_text(clean_html),
            goal=goal.strip(),
            segment_id=segment_id,
        )

    def mark_pushed(self, mautic_id: int) -> None:
        self.mautic_id = mautic_id
        self.status = EmailStatus.PUSHED
        self.touch()


class CampaignStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class Channel(StrEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    ADS = "ads"


@dataclass(frozen=True)
class CampaignStep:
    day: int
    channel: Channel
    subject: str
    intent: str


@dataclass(kw_only=True, eq=False)
class Campaign(TenantEntity):
    name: str
    objective: str
    steps: list[CampaignStep]
    status: CampaignStatus = CampaignStatus.PLANNED
    segment_id: uuid.UUID | None = None
    mautic_id: int | None = None

    def __post_init__(self) -> None:
        if not self.steps:
            raise BusinessRuleViolation("La campaña necesita al menos un paso", code="empty_campaign")
        self.steps = sorted(self.steps, key=lambda s: s.day)

    @property
    def main_channel(self) -> Channel:
        return Counter(s.channel for s in self.steps).most_common(1)[0][0]

    def launch(self, *, actor_id: uuid.UUID | None, mautic_id: int | None = None) -> None:
        if self.status not in (CampaignStatus.PLANNED, CampaignStatus.PAUSED):
            raise BusinessRuleViolation(
                f"No se puede lanzar una campaña en estado {self.status.value}", code="invalid_campaign_state"
            )
        self.status = CampaignStatus.ACTIVE
        if mautic_id is not None:
            self.mautic_id = mautic_id
        self.touch()
        self.record(
            ie.CampaignLaunched(
                tenant_id=self.tenant_id,
                actor_id=actor_id,
                campaign_id=self.id,
                name=self.name,
                channel=self.main_channel.value,
            )
        )
