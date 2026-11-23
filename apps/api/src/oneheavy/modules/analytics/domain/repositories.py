"""Puertos de persistencia de Analítica."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime

from oneheavy.modules.analytics.domain.model import Aggregate, Fact, Metric


class FactRepository(ABC):
    @abstractmethod
    async def record(self, fact: Fact) -> bool:
        """Inserta el hecho (o lo reemplaza si `fact.replace`). False si ya existía."""

    @abstractmethod
    async def aggregates(
        self, tenant_id: uuid.UUID, metrics: Iterable[Metric], since: datetime, until: datetime
    ) -> dict[Metric, Aggregate]: ...

    @abstractmethod
    async def distinct_subjects(
        self, tenant_id: uuid.UUID, metric: Metric, since: datetime, until: datetime
    ) -> int: ...

    @abstractmethod
    async def daily_totals(
        self, tenant_id: uuid.UUID, metric: Metric, since: datetime, until: datetime
    ) -> dict[str, float]:
        """{'YYYY-MM-DD': total} sólo para días con datos."""


class ContactStageRepository(ABC):
    @abstractmethod
    async def set_stage(
        self, tenant_id: uuid.UUID, contact_id: uuid.UUID, stage: str, *, only_if_absent: bool = False
    ) -> None: ...

    @abstractmethod
    async def counts(self, tenant_id: uuid.UUID) -> dict[str, int]: ...
