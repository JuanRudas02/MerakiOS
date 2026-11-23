"""Puertos de aplicación de Marketing: UoW y gateway de Mautic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from oneheavy.modules.marketing.domain.repositories import (
    AudienceRepository,
    CampaignRepository,
    EmailRepository,
    SegmentRepository,
)
from oneheavy.shared.application.ports import UnitOfWork


class MarketingUnitOfWork(UnitOfWork, ABC):
    audience: AudienceRepository
    segments: SegmentRepository
    emails: EmailRepository
    campaigns: CampaignRepository


@dataclass(frozen=True)
class MauticContactData:
    email: str | None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MauticCampaignEmail:
    """Paso de una campaña en Mautic: enviar `email_id` el día `day` (1 = al entrar)."""

    day: int
    name: str
    email_id: int


class MauticGateway(ABC):
    """Puerto hacia Mautic (marketing automation open source).

    Devuelve siempre los IDs numéricos de Mautic para guardar el mapeo local.
    """

    @abstractmethod
    async def ping(self) -> bool: ...

    @abstractmethod
    async def upsert_contact(self, data: MauticContactData, mautic_id: int | None = None) -> int: ...

    @abstractmethod
    async def create_segment(self, name: str, description: str | None = None) -> int: ...

    @abstractmethod
    async def add_contacts_to_segment(self, segment_id: int, contact_ids: list[int]) -> None: ...

    @abstractmethod
    async def create_email(
        self,
        *,
        name: str,
        subject: str,
        html: str,
        text: str,
        segment_id: int | None = None,
        published: bool = False,
    ) -> int:
        """Email de segmento (`segment_id`) o plantilla para campañas (sin segmento)."""

    @abstractmethod
    async def create_campaign(
        self,
        *,
        name: str,
        description: str,
        emails: Sequence[MauticCampaignEmail],
        segment_id: int | None = None,
    ) -> int:
        """Mautic 5 exige al menos un paso: `emails` no puede estar vacío."""

    @abstractmethod
    async def publish_campaign(self, campaign_id: int) -> None: ...
