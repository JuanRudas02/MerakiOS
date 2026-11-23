"""Puertos del módulo Meta: repositorios, UoW y gateway de la Graph API."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from oneheavy.modules.meta.domain.model import (
    AdAlert,
    CampaignDailyMetric,
    ContactFingerprint,
    LeadData,
    MetaConnection,
)
from oneheavy.shared.application.ports import UnitOfWork

# ── Gateway (Graph API / Marketing API / Conversions API) ───────────────────


@dataclass(frozen=True)
class CampaignInsightRow:
    campaign_id: str
    campaign_name: str
    status: str
    objective: str
    day: date
    spend: Decimal
    impressions: int
    clicks: int
    leads: int
    conversions: int
    revenue: Decimal


@dataclass(frozen=True)
class DailyInsightRow:
    day: date
    spend: Decimal
    impressions: int
    clicks: int
    leads: int
    currency: str = "COP"


@dataclass(frozen=True)
class ConversionEvent:
    event_name: str  # Purchase | Lead
    event_id: str
    event_time: int  # epoch seconds
    user_data: dict[str, Any] = field(default_factory=dict)
    custom_data: dict[str, Any] = field(default_factory=dict)
    action_source: str = "system_generated"


class MetaGraphGateway(ABC):
    @abstractmethod
    async def fetch_campaign_insights(
        self, ad_account_id: str, access_token: str, since: date, until: date
    ) -> list[CampaignInsightRow]: ...

    @abstractmethod
    async def fetch_daily_insights(
        self, ad_account_id: str, access_token: str, since: date, until: date
    ) -> list[DailyInsightRow]: ...

    @abstractmethod
    async def fetch_lead(self, leadgen_id: str, access_token: str) -> LeadData: ...

    @abstractmethod
    async def send_conversion_events(
        self, pixel_id: str, access_token: str, events: list[ConversionEvent]
    ) -> None: ...


# ── Repositorios ────────────────────────────────────────────────────────────


class ConnectionRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID) -> MetaConnection | None: ...

    @abstractmethod
    async def find_by_page(self, page_id: str) -> MetaConnection | None: ...

    @abstractmethod
    async def list_all(self) -> list[MetaConnection]: ...

    @abstractmethod
    async def save(self, connection: MetaConnection) -> None: ...


class MetricRepository(ABC):
    @abstractmethod
    async def replace_window(
        self, tenant_id: uuid.UUID, since: date, metrics: list[CampaignDailyMetric]
    ) -> None:
        """Borra las métricas del tenant desde `since` e inserta las nuevas (idempotente)."""

    @abstractmethod
    async def list_since(self, tenant_id: uuid.UUID, since: date) -> list[CampaignDailyMetric]: ...


class AlertRepository(ABC):
    @abstractmethod
    async def exists(self, tenant_id: uuid.UUID, dedupe_key: str) -> bool: ...

    @abstractmethod
    async def add(self, alert: AdAlert) -> None: ...

    @abstractmethod
    async def list_recent(self, tenant_id: uuid.UUID, limit: int = 50) -> list[AdAlert]: ...


class FingerprintRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> ContactFingerprint | None: ...

    @abstractmethod
    async def save(self, fingerprint: ContactFingerprint) -> None: ...


class MetaUnitOfWork(UnitOfWork, ABC):
    connections: ConnectionRepository
    metrics: MetricRepository
    alerts: AlertRepository
    fingerprints: FingerprintRepository
