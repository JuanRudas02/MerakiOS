"""Puertos de persistencia del contexto Stays.

Todas las consultas de lectura reciben `tenant_id` (aislamiento multi-tenant),
excepto las marcadas como *cross-tenant*, usadas sólo por procesos batch.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from oneheavy.modules.stays.domain.model import (
    CleaningTask,
    OwnerAccount,
    Property,
    Receipt,
    StaffMember,
    StaysSettings,
    TaskStatus,
)


class PropertyRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, property_id: uuid.UUID) -> Property | None: ...

    @abstractmethod
    async def list_all(self, tenant_id: uuid.UUID, *, owner_phone: str | None = None) -> list[Property]: ...

    @abstractmethod
    async def get_many(self, tenant_id: uuid.UUID, ids: set[uuid.UUID]) -> dict[uuid.UUID, Property]: ...

    @abstractmethod
    async def code_exists(
        self, tenant_id: uuid.UUID, code: str, *, exclude: uuid.UUID | None = None
    ) -> bool: ...

    @abstractmethod
    async def list_all_with_cutoffs(self) -> list[Property]:
        """Cross-tenant: propiedades con automatización activa."""

    @abstractmethod
    async def add(self, prop: Property) -> None: ...

    @abstractmethod
    async def update(self, prop: Property) -> None: ...


class StaffRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> StaffMember | None: ...

    @abstractmethod
    async def list_all(self, tenant_id: uuid.UUID) -> list[StaffMember]: ...

    @abstractmethod
    async def get_many(self, tenant_id: uuid.UUID, ids: set[uuid.UUID]) -> dict[uuid.UUID, StaffMember]: ...

    @abstractmethod
    async def upsert(self, staff: StaffMember) -> None: ...


@dataclass(frozen=True)
class TaskFilter:
    start: datetime | None = None
    end: datetime | None = None
    property_id: uuid.UUID | None = None
    staff_id: uuid.UUID | None = None
    status: TaskStatus | None = None
    limit: int | None = None


class TaskRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, task_id: uuid.UUID) -> CleaningTask | None: ...

    @abstractmethod
    async def search(self, tenant_id: uuid.UUID, flt: TaskFilter) -> list[CleaningTask]: ...

    @abstractmethod
    async def list_between_all_tenants(
        self, start: datetime, end: datetime, *, status: TaskStatus | None = None
    ) -> list[CleaningTask]:
        """Cross-tenant (procesos batch)."""

    @abstractmethod
    async def exists_for_property(
        self, tenant_id: uuid.UUID, property_id: uuid.UUID, start: datetime, end: datetime
    ) -> bool: ...

    @abstractmethod
    async def find_by_external_ref(self, tenant_id: uuid.UUID, external_ref: str) -> CleaningTask | None: ...

    @abstractmethod
    async def add(self, task: CleaningTask) -> None: ...

    @abstractmethod
    async def update(self, task: CleaningTask) -> None: ...


class ReceiptRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, receipt_id: uuid.UUID) -> Receipt | None: ...

    @abstractmethod
    async def list_by_property(self, tenant_id: uuid.UUID, property_id: uuid.UUID) -> list[Receipt]: ...

    @abstractmethod
    async def has_pending(self, tenant_id: uuid.UUID, property_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def verified_services(
        self, property_ids: set[uuid.UUID], period: str
    ) -> set[tuple[uuid.UUID, str]]:
        """Cross-tenant: pares (propiedad, servicio) con pago verificado en el periodo."""

    @abstractmethod
    async def add(self, receipt: Receipt) -> None: ...

    @abstractmethod
    async def update(self, receipt: Receipt) -> None: ...


class SettingsRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID) -> StaysSettings:
        """Devuelve la configuración o los valores por defecto (sin persistir)."""

    @abstractmethod
    async def get_many(self, tenant_ids: set[uuid.UUID]) -> dict[uuid.UUID, StaysSettings]: ...

    @abstractmethod
    async def find_by_webhook_token(self, token: str) -> StaysSettings | None: ...

    @abstractmethod
    async def save(self, settings: StaysSettings) -> None: ...


class OwnerAccountRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> OwnerAccount | None: ...

    @abstractmethod
    async def upsert(self, account: OwnerAccount) -> None: ...
