"""Persistencia SQLAlchemy del módulo Meta."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from sqlalchemy import BigInteger, Date, DateTime, Float, Integer, String, Text, Uuid, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.meta.application.ports import (
    AlertRepository,
    ConnectionRepository,
    FingerprintRepository,
    MetaUnitOfWork,
    MetricRepository,
)
from oneheavy.modules.meta.domain.model import (
    AdAlert,
    CampaignDailyMetric,
    ContactFingerprint,
    MetaConnection,
    Severity,
)
from oneheavy.shared.domain.time import ensure_aware
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TenantMixin, TimestampMixin


def _to_cents(value: Decimal) -> int:
    return int((value * 100).to_integral_value())


def _from_cents(value: int) -> Decimal:
    return (Decimal(value) / 100).quantize(Decimal("0.01"))


# ── ORM ─────────────────────────────────────────────────────────────────────


class MetaConnectionRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "meta_connections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    ad_account_id: Mapped[str] = mapped_column(String(40))
    access_token: Mapped[str] = mapped_column(Text)
    page_id: Mapped[str | None] = mapped_column(String(40), index=True)
    pixel_id: Mapped[str | None] = mapped_column(String(40))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MetaCampaignMetricRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "meta_campaign_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30))
    objective: Mapped[str] = mapped_column(String(60))
    day: Mapped[date] = mapped_column(Date, index=True)
    spend_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    leads: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    revenue_cents: Mapped[int] = mapped_column(BigInteger, default=0)


class MetaAlertRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "meta_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    campaign_ref: Mapped[str] = mapped_column(String(255))
    metric: Mapped[str] = mapped_column(String(30))
    value: Mapped[float] = mapped_column(Float)
    benchmark: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String(320), index=True)


class MetaContactFingerprintRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "meta_contact_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    hashed_email: Mapped[str | None] = mapped_column(String(64))
    hashed_phone: Mapped[str | None] = mapped_column(String(64))


# ── Repositorios ────────────────────────────────────────────────────────────


def _conn_to_domain(row: MetaConnectionRow) -> MetaConnection:
    return MetaConnection(
        id=row.id,
        tenant_id=row.tenant_id,
        ad_account_id=row.ad_account_id,
        access_token=row.access_token,
        page_id=row.page_id,
        pixel_id=row.pixel_id,
        last_sync_at=ensure_aware(row.last_sync_at) if row.last_sync_at else None,
        created_at=ensure_aware(row.created_at),
        updated_at=ensure_aware(row.updated_at),
    )


class SqlConnectionRepository(ConnectionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID) -> MetaConnection | None:
        row = await self._s.scalar(select(MetaConnectionRow).where(MetaConnectionRow.tenant_id == tenant_id))
        return _conn_to_domain(row) if row else None

    async def find_by_page(self, page_id: str) -> MetaConnection | None:
        row = await self._s.scalar(select(MetaConnectionRow).where(MetaConnectionRow.page_id == page_id))
        return _conn_to_domain(row) if row else None

    async def list_all(self) -> list[MetaConnection]:
        return [_conn_to_domain(r) for r in await self._s.scalars(select(MetaConnectionRow))]

    async def save(self, connection: MetaConnection) -> None:
        row = await self._s.get(MetaConnectionRow, connection.id)
        if row is None:
            row = MetaConnectionRow(id=connection.id, tenant_id=connection.tenant_id)
            self._s.add(row)
        row.ad_account_id = connection.ad_account_id
        row.access_token = connection.access_token
        row.page_id, row.pixel_id = connection.page_id, connection.pixel_id
        row.last_sync_at = connection.last_sync_at
        row.created_at, row.updated_at = connection.created_at, connection.updated_at


class SqlMetricRepository(MetricRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def replace_window(
        self, tenant_id: uuid.UUID, since: date, metrics: list[CampaignDailyMetric]
    ) -> None:
        await self._s.execute(
            delete(MetaCampaignMetricRow).where(
                MetaCampaignMetricRow.tenant_id == tenant_id, MetaCampaignMetricRow.day >= since
            )
        )
        for m in metrics:
            self._s.add(
                MetaCampaignMetricRow(
                    id=m.id,
                    tenant_id=tenant_id,
                    external_id=m.external_id,
                    name=m.name,
                    status=m.status,
                    objective=m.objective,
                    day=m.day,
                    spend_cents=_to_cents(m.spend),
                    impressions=m.impressions,
                    clicks=m.clicks,
                    leads=m.leads,
                    conversions=m.conversions,
                    revenue_cents=_to_cents(m.revenue),
                )
            )

    async def list_since(self, tenant_id: uuid.UUID, since: date) -> list[CampaignDailyMetric]:
        rows = await self._s.scalars(
            select(MetaCampaignMetricRow)
            .where(MetaCampaignMetricRow.tenant_id == tenant_id, MetaCampaignMetricRow.day >= since)
            .order_by(MetaCampaignMetricRow.day)
        )
        return [
            CampaignDailyMetric(
                id=r.id,
                tenant_id=r.tenant_id,
                external_id=r.external_id,
                name=r.name,
                status=r.status,
                objective=r.objective,
                day=r.day,
                spend=_from_cents(r.spend_cents),
                impressions=r.impressions,
                clicks=r.clicks,
                leads=r.leads,
                conversions=r.conversions,
                revenue=_from_cents(r.revenue_cents),
            )
            for r in rows
        ]


class SqlAlertRepository(AlertRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def exists(self, tenant_id: uuid.UUID, dedupe_key: str) -> bool:
        found = await self._s.scalar(
            select(MetaAlertRow.id).where(
                MetaAlertRow.tenant_id == tenant_id, MetaAlertRow.dedupe_key == dedupe_key
            )
        )
        return found is not None

    async def add(self, alert: AdAlert) -> None:
        self._s.add(
            MetaAlertRow(
                id=alert.id,
                tenant_id=alert.tenant_id,
                campaign_ref=alert.campaign_ref,
                metric=alert.metric,
                value=alert.value,
                benchmark=alert.benchmark,
                severity=alert.severity.value,
                message=alert.message,
                dedupe_key=alert.dedupe_key,
                created_at=alert.created_at,
                updated_at=alert.updated_at,
            )
        )

    async def list_recent(self, tenant_id: uuid.UUID, limit: int = 50) -> list[AdAlert]:
        rows = await self._s.scalars(
            select(MetaAlertRow)
            .where(MetaAlertRow.tenant_id == tenant_id)
            .order_by(MetaAlertRow.created_at.desc())
            .limit(limit)
        )
        return [
            AdAlert(
                id=r.id,
                tenant_id=r.tenant_id,
                campaign_ref=r.campaign_ref,
                metric=r.metric,
                value=r.value,
                benchmark=r.benchmark,
                severity=Severity(r.severity),
                message=r.message,
                dedupe_key=r.dedupe_key,
                created_at=ensure_aware(r.created_at),
                updated_at=ensure_aware(r.updated_at),
            )
            for r in rows
        ]


class SqlFingerprintRepository(FingerprintRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _row(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> MetaContactFingerprintRow | None:
        return await self._s.scalar(
            select(MetaContactFingerprintRow).where(
                MetaContactFingerprintRow.tenant_id == tenant_id,
                MetaContactFingerprintRow.contact_id == contact_id,
            )
        )

    async def get(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> ContactFingerprint | None:
        row = await self._row(tenant_id, contact_id)
        if row is None:
            return None
        return ContactFingerprint(
            id=row.id,
            tenant_id=row.tenant_id,
            contact_id=row.contact_id,
            hashed_email=row.hashed_email,
            hashed_phone=row.hashed_phone,
        )

    async def save(self, fingerprint: ContactFingerprint) -> None:
        row = await self._row(fingerprint.tenant_id, fingerprint.contact_id)
        if row is None:
            row = MetaContactFingerprintRow(
                id=fingerprint.id, tenant_id=fingerprint.tenant_id, contact_id=fingerprint.contact_id
            )
            self._s.add(row)
        row.hashed_email, row.hashed_phone = fingerprint.hashed_email, fingerprint.hashed_phone


class SqlMetaUnitOfWork(SqlAlchemyUnitOfWork, MetaUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.connections = SqlConnectionRepository(self.session)
        self.metrics = SqlMetricRepository(self.session)
        self.alerts = SqlAlertRepository(self.session)
        self.fingerprints = SqlFingerprintRepository(self.session)
        return self
