"""Puertos de persistencia del CRM."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from oneheavy.modules.crm.domain.model import Activity, Contact, Deal, LifecycleStage


@dataclass(frozen=True)
class ContactQuery:
    tenant_id: uuid.UUID
    q: str | None = None
    stage: LifecycleStage | None = None
    tag: str | None = None
    owner_id: uuid.UUID | None = None
    page: int = 1
    size: int = 25


class ContactRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Contact | None: ...

    @abstractmethod
    async def get_many(self, tenant_id: uuid.UUID, ids: set[uuid.UUID]) -> dict[uuid.UUID, Contact]: ...

    @abstractmethod
    async def find_duplicate(
        self, tenant_id: uuid.UUID, email: str | None, phone: str | None, *, exclude: uuid.UUID | None = None
    ) -> Contact | None:
        """Busca por email o teléfono normalizados dentro del workspace."""

    @abstractmethod
    async def search(self, query: ContactQuery) -> tuple[list[Contact], int]: ...

    @abstractmethod
    async def add(self, contact: Contact) -> None: ...

    @abstractmethod
    async def update(self, contact: Contact) -> None: ...


class ActivityRepository(ABC):
    @abstractmethod
    async def add(self, activity: Activity) -> None: ...

    @abstractmethod
    async def list_for_contact(
        self, tenant_id: uuid.UUID, contact_id: uuid.UUID, limit: int = 200
    ) -> list[Activity]: ...


class DealRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, deal_id: uuid.UUID) -> Deal | None: ...

    @abstractmethod
    async def list(self, tenant_id: uuid.UUID) -> list[Deal]: ...

    @abstractmethod
    async def add(self, deal: Deal) -> None: ...

    @abstractmethod
    async def update(self, deal: Deal) -> None: ...
