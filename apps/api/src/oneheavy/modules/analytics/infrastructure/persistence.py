"""Adaptador de salida: persistencia SQLAlchemy de Analítica (agregados SQL portables)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Self

from sqlalchemy import JSON, DateTime, Float, String, UniqueConstraint, Uuid, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.analytics.application.ports import AnalyticsUnitOfWork
from oneheavy.modules.analytics.domain.model import Aggregate, Fact, Metric
from oneheavy.modules.analytics.domain.repositories import ContactStageRepository, FactRepository
from oneheavy.shared.domain.time import utc_now
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TenantMixin, TimestampMixin


class FactRow(TenantMixin, Base):
    __tablename__ = "analytics_facts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_key", "metric", name="uq_analytics_facts_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    metric: Mapped[str] = mapped_column(String(40), index=True)
    value: Mapped[float] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_key: Mapped[str] = mapped_column(String(64))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    dims: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ContactStageRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "analytics_contact_stages"

    contact_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    stage: Mapped[str] = mapped_column(String(20), index=True)


class SqlFactRepository(FactRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def record(self, fact: Fact) -> bool:
        existing = await self._s.scalar(
            select(FactRow).where(
                FactRow.tenant_id == fact.tenant_id,
                FactRow.source_key == fact.source_key,
                FactRow.metric == fact.metric.value,
            )
        )
        if existing is not None:
            if not fact.replace:
                return False
            existing.value, existing.occurred_at, existing.dims = fact.value, fact.occurred_at, fact.dims
            return True
        self._s.add(
            FactRow(
                tenant_id=fact.tenant_id,
                metric=fact.metric.value,
                value=fact.value,
                occurred_at=fact.occurred_at,
                source_key=fact.source_key,
                subject_id=fact.subject_id,
                dims=fact.dims,
            )
        )
        return True

    async def aggregates(
        self, tenant_id: uuid.UUID, metrics: Iterable[Metric], since: datetime, until: datetime
    ) -> dict[Metric, Aggregate]:
        keys = [m.value for m in metrics]
        stmt = (
            select(FactRow.metric, func.coalesce(func.sum(FactRow.value), 0.0), func.count())
            .where(
                FactRow.tenant_id == tenant_id,
                FactRow.metric.in_(keys),
                FactRow.occurred_at >= since,
                FactRow.occurred_at <= until,
            )
            .group_by(FactRow.metric)
        )
        return {
            Metric(metric): Aggregate(float(total), int(count))
            for metric, total, count in (await self._s.execute(stmt)).all()
        }

    async def distinct_subjects(
        self, tenant_id: uuid.UUID, metric: Metric, since: datetime, until: datetime
    ) -> int:
        stmt = select(func.count(func.distinct(FactRow.subject_id))).where(
            FactRow.tenant_id == tenant_id,
            FactRow.metric == metric.value,
            FactRow.subject_id.is_not(None),
            FactRow.occurred_at >= since,
            FactRow.occurred_at <= until,
        )
        return int(await self._s.scalar(stmt) or 0)

    async def daily_totals(
        self, tenant_id: uuid.UUID, metric: Metric, since: datetime, until: datetime
    ) -> dict[str, float]:
        day = func.date(FactRow.occurred_at)
        stmt = (
            select(day, func.sum(FactRow.value))
            .where(
                FactRow.tenant_id == tenant_id,
                FactRow.metric == metric.value,
                FactRow.occurred_at >= since,
                FactRow.occurred_at <= until,
            )
            .group_by(day)
        )
        # SQLite devuelve 'YYYY-MM-DD' (str); Postgres devuelve date.
        return {str(d)[:10]: float(v or 0) for d, v in (await self._s.execute(stmt)).all()}


class SqlContactStageRepository(ContactStageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def set_stage(
        self, tenant_id: uuid.UUID, contact_id: uuid.UUID, stage: str, *, only_if_absent: bool = False
    ) -> None:
        row = await self._s.get(ContactStageRow, contact_id)
        if row is None:
            self._s.add(ContactStageRow(contact_id=contact_id, tenant_id=tenant_id, stage=stage))
        elif not only_if_absent and row.tenant_id == tenant_id:
            row.stage, row.updated_at = stage, utc_now()

    async def counts(self, tenant_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(ContactStageRow.stage, func.count())
            .where(ContactStageRow.tenant_id == tenant_id)
            .group_by(ContactStageRow.stage)
        )
        return {stage: int(n) for stage, n in (await self._s.execute(stmt)).all()}


class SqlAnalyticsUnitOfWork(SqlAlchemyUnitOfWork, AnalyticsUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.facts = SqlFactRepository(self.session)
        self.stages = SqlContactStageRepository(self.session)
        return self
