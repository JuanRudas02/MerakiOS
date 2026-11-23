"""Casos de uso de Analítica.

CU-AN-01  Proyectar evento de dominio a hechos (proceso automático, idempotente)
CU-AN-02  Consultar overview unificado del periodo
CU-AN-03  Consultar serie temporal diaria de una métrica (días sin datos = 0)
CU-AN-04  Consultar embudo de ciclo de vida de contactos
CU-AN-05  Generar insights con IA (con fallback determinista)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from oneheavy.modules.analytics.application.ports import AnalyticsUnitOfWork
from oneheavy.modules.analytics.domain.model import (
    FUNNEL_STAGES,
    TIMESERIES_METRICS,
    EventProjector,
    InsightReport,
    Metric,
    Overview,
)
from oneheavy.shared.application.ports import LLMClient, LLMRequest
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.domain.events import DomainEvent
from oneheavy.shared.domain.time import utc_now

log = logging.getLogger("oneheavy.analytics")

MAX_DAYS = 365


def _window(days: int, now: datetime | None = None) -> tuple[datetime, datetime]:
    if not 1 <= days <= MAX_DAYS:
        raise BusinessRuleViolation(f"El periodo debe estar entre 1 y {MAX_DAYS} días", code="invalid_period")
    until = now or utc_now()
    return until - timedelta(days=days), until


# ── CU-AN-01 ────────────────────────────────────────────────────────────────


class ProjectEvent(UseCase[DomainEvent, int]):
    def __init__(self, uow: AnalyticsUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: DomainEvent) -> int:
        projection = EventProjector.project(data)
        if not projection.facts and projection.stage_change is None:
            return 0
        recorded = 0
        async with self.uow:
            for fact in projection.facts:
                recorded += int(await self.uow.facts.record(fact))
            change = projection.stage_change
            if change is not None:
                await self.uow.stages.set_stage(
                    data.tenant_id, change.contact_id, change.stage, only_if_absent=change.only_if_absent
                )
            await self.uow.commit()
        return recorded


# ── CU-AN-02 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PeriodQuery:
    actor: Principal
    days: int = 30


class GetOverview(UseCase[PeriodQuery, Overview]):
    def __init__(self, uow: AnalyticsUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: PeriodQuery) -> Overview:
        data.actor.require(Permission.ANALYTICS_READ)
        since, until = _window(data.days)
        tenant = data.actor.tenant_id
        async with self.uow:
            agg = await self.uow.facts.aggregates(tenant, list(Metric), since, until)
            players = await self.uow.facts.distinct_subjects(tenant, Metric.POINTS_AWARDED, since, until)
        return Overview.compute(since, until, agg, players)


# ── CU-AN-03 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TimeseriesQuery:
    actor: Principal
    metric: str
    days: int = 30


@dataclass(frozen=True)
class Point:
    date: str
    value: float


class GetTimeseries(UseCase[TimeseriesQuery, list[Point]]):
    def __init__(self, uow: AnalyticsUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: TimeseriesQuery) -> list[Point]:
        data.actor.require(Permission.ANALYTICS_READ)
        try:
            metric = Metric(data.metric)
        except ValueError:
            metric = None
        if metric is None or metric not in TIMESERIES_METRICS:
            allowed = ", ".join(sorted(m.value for m in TIMESERIES_METRICS))
            raise BusinessRuleViolation(f"Métrica no soportada. Usa una de: {allowed}", code="invalid_metric")
        _window(data.days)  # valida el rango
        until = utc_now()
        first_day = (until - timedelta(days=data.days - 1)).date()
        since = datetime.combine(first_day, datetime.min.time(), tzinfo=until.tzinfo)
        async with self.uow:
            totals = await self.uow.facts.daily_totals(data.actor.tenant_id, metric, since, until)
        days = [first_day + timedelta(days=i) for i in range(data.days)]
        return [Point(d.isoformat(), round(totals.get(d.isoformat(), 0.0), 2)) for d in days]


# ── CU-AN-04 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FunnelStep:
    stage: str
    count: int


class GetContactFunnel(UseCase[Principal, list[FunnelStep]]):
    def __init__(self, uow: AnalyticsUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[FunnelStep]:
        data.require(Permission.ANALYTICS_READ)
        async with self.uow:
            counts = await self.uow.stages.counts(data.tenant_id)
        return [FunnelStep(stage, counts.get(stage, 0)) for stage in FUNNEL_STAGES]


# ── CU-AN-05 ────────────────────────────────────────────────────────────────

_INSIGHTS_SYSTEM = (
    "Eres el analista de negocio de 1heavy. Analizas KPIs de operación (limpiezas de alquileres "
    "de corta estadía), ventas (CRM), marketing (Mautic, Meta Ads), growth y gamificación. "
    "Respondes en español, con frases cortas y accionables, sin inventar datos."
)


class GenerateInsights(UseCase[PeriodQuery, InsightReport]):
    def __init__(self, uow: AnalyticsUnitOfWork, llm: LLMClient) -> None:
        self.uow, self.llm = uow, llm

    async def execute(self, data: PeriodQuery) -> InsightReport:
        overview = await GetOverview(self.uow).execute(data)
        prompt = (
            "KPIs del periodo (JSON):\n"
            f"{json.dumps(overview.digest(), ensure_ascii=False)}\n\n"
            'Devuelve {"summary": str, "highlights": [str], "risks": [str], "recommendations": [str]} '
            "con máximo 4 elementos por lista."
        )
        try:
            raw = await self.llm.complete_json(
                LLMRequest(prompt=prompt, system=_INSIGHTS_SYSTEM, metadata={"task": "analytics.insights"})
            )
        except Exception:
            log.warning("insights_llm_failed", exc_info=True)
            raw = None
        report = InsightReport.parse(raw)
        if report is None:
            log.info("insights_fallback_rule_based")
            report = InsightReport.rule_based(overview)
        return report
