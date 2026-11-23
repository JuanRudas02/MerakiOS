"""Puertos de persistencia de Marketing."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from oneheavy.modules.marketing.domain.model import AudienceMember, Campaign, EmailDraft, Segment


class AudienceRepository(ABC):
    @abstractmethod
    async def get_by_contact(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> AudienceMember | None: ...

    @abstractmethod
    async def find_by_mautic_id(self, mautic_id: int) -> AudienceMember | None:
        """Global: los webhooks de Mautic no traen tenant, el id de Mautic sí es único."""

    @abstractmethod
    async def find_by_email(self, tenant_id: uuid.UUID, email: str) -> AudienceMember | None: ...

    @abstractmethod
    async def list(self, tenant_id: uuid.UUID) -> list[AudienceMember]: ...

    @abstractmethod
    async def save(self, member: AudienceMember) -> None: ...


class SegmentRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, segment_id: uuid.UUID) -> Segment | None: ...

    @abstractmethod
    async def list(self, tenant_id: uuid.UUID) -> list[Segment]: ...

    @abstractmethod
    async def save(self, segment: Segment) -> None: ...


class EmailRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, email_id: uuid.UUID) -> EmailDraft | None: ...

    @abstractmethod
    async def list(self, tenant_id: uuid.UUID) -> list[EmailDraft]: ...

    @abstractmethod
    async def save(self, email: EmailDraft) -> None: ...


class CampaignRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign | None: ...

    @abstractmethod
    async def list(self, tenant_id: uuid.UUID) -> list[Campaign]: ...

    @abstractmethod
    async def save(self, campaign: Campaign) -> None: ...
