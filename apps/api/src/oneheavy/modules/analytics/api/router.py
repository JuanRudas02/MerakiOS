"""Adaptador REST de Analítica (/api/v1/analytics)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from oneheavy.modules.analytics.application.use_cases import (
    GenerateInsights,
    GetContactFunnel,
    GetOverview,
    GetTimeseries,
    PeriodQuery,
    TimeseriesQuery,
)
from oneheavy.modules.analytics.infrastructure.persistence import SqlAnalyticsUnitOfWork
from oneheavy.shared.domain.access import Principal
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, get_principal

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _uow(container: Container = Depends(get_container)) -> SqlAnalyticsUnitOfWork:
    return SqlAnalyticsUnitOfWork(container.session_factory, container.bus)


class PeriodOut(BaseModel):
    from_: datetime = Field(serialization_alias="from")
    to: datetime


class OverviewOut(BaseModel):
    period: PeriodOut
    operations: dict[str, float]
    sales: dict[str, float]
    marketing: dict[str, float]
    growth: dict[str, float]
    gamification: dict[str, float]


class PointOut(BaseModel):
    date: str
    value: float


class FunnelStepOut(BaseModel):
    stage: str
    count: int


class InsightsIn(BaseModel):
    days: int = Field(default=30, ge=1, le=365)


class InsightsOut(BaseModel):
    summary: str
    highlights: list[str]
    risks: list[str]
    recommendations: list[str]


@router.get("/overview", response_model=OverviewOut, response_model_by_alias=True)
async def overview(
    days: int = Query(30, ge=1, le=365),
    principal: Principal = Depends(get_principal),
    uow: SqlAnalyticsUnitOfWork = Depends(_uow),
) -> OverviewOut:
    ov = await GetOverview(uow).execute(PeriodQuery(principal, days))
    return OverviewOut(
        period=PeriodOut(from_=ov.period_from, to=ov.period_to),
        operations=ov.operations,
        sales=ov.sales,
        marketing=ov.marketing,
        growth=ov.growth,
        gamification=ov.gamification,
    )


@router.get("/timeseries", response_model=list[PointOut])
async def timeseries(
    metric: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    principal: Principal = Depends(get_principal),
    uow: SqlAnalyticsUnitOfWork = Depends(_uow),
) -> list[PointOut]:
    points = await GetTimeseries(uow).execute(TimeseriesQuery(principal, metric, days))
    return [PointOut(date=p.date, value=p.value) for p in points]


@router.get("/funnel", response_model=list[FunnelStepOut])
async def funnel(
    principal: Principal = Depends(get_principal), uow: SqlAnalyticsUnitOfWork = Depends(_uow)
) -> list[FunnelStepOut]:
    return [
        FunnelStepOut(stage=s.stage, count=s.count) for s in await GetContactFunnel(uow).execute(principal)
    ]


@router.post("/insights", response_model=InsightsOut)
async def insights(
    body: InsightsIn | None = None,
    principal: Principal = Depends(get_principal),
    uow: SqlAnalyticsUnitOfWork = Depends(_uow),
    container: Container = Depends(get_container),
) -> InsightsOut:
    days = body.days if body else 30
    report = await GenerateInsights(uow, container.llm).execute(PeriodQuery(principal, days))
    return InsightsOut(
        summary=report.summary,
        highlights=report.highlights,
        risks=report.risks,
        recommendations=report.recommendations,
    )
