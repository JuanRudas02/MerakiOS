"""Puertos de aplicación de Marketing: UoW y gateway de Mautic."""

from __future__ import annotations

from abc import ABC, abstractmethod
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
        self, *, name: str, subject: str, html: str, text: str, segment_id: int | None = None
    ) -> int: ...

    @abstractmethod
    async def create_campaign(self, *, name: str, description: str, segment_id: int | None = None) -> int: ...

    @abstractmethod
    async def publish_campaign(self, campaign_id: int) -> None: ...
