"""Adaptador REST del módulo Meta Business (/api/v1/meta)."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, EmailStr, Field

from oneheavy.modules.meta.application.ports import MetaGraphGateway
from oneheavy.modules.meta.application.use_cases import (
    CampaignPerformance,
    ConnectAccount,
    ConnectAccountCommand,
    DailyInsights,
    GetConnection,
    ListAlerts,
    ListCampaignPerformance,
    PerformanceQuery,
    ProcessLeadAdsWebhook,
    SimulateLead,
    SimulateLeadCommand,
    SyncInsights,
    SyncInsightsCommand,
    lead_notifications_from_payload,
)
from oneheavy.modules.meta.application.webhooks import verify_signature, verify_subscription
from oneheavy.modules.meta.domain.model import MetaConnection, Performance
from oneheavy.modules.meta.infrastructure.persistence import SqlMetaUnitOfWork
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import AuthenticationError, BusinessRuleViolation
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, require

router = APIRouter(prefix="/meta", tags=["Meta Business"])


def _uow(container: Container = Depends(get_container)) -> SqlMetaUnitOfWork:
    return SqlMetaUnitOfWork(container.session_factory, container.bus)


def _gateway(container: Container = Depends(get_container)) -> MetaGraphGateway:
    gateway: MetaGraphGateway = container.extras["meta.graph"]
    return gateway


# ── Schemas ─────────────────────────────────────────────────────────────────


class ConnectionIn(BaseModel):
    ad_account_id: str = Field(min_length=5, max_length=40)
    access_token: str = Field(min_length=10)
    page_id: str | None = Field(default=None, max_length=40)
    pixel_id: str | None = Field(default=None, max_length=40)


class ConnectionOut(BaseModel):
    connected: bool
    ad_account_id: str | None = None
    page_id: str | None = None
    pixel_id: str | None = None
    last_sync_at: datetime | None = None

    @classmethod
    def of(cls, conn: MetaConnection | None) -> ConnectionOut:
        if conn is None:
            return cls(connected=False)
        return cls(
            connected=True,
            ad_account_id=conn.ad_account_id,
            page_id=conn.page_id,
            pixel_id=conn.pixel_id,
            last_sync_at=conn.last_sync_at,
        )


class SyncOut(BaseModel):
    campaigns: int
    days: int


class PerfTotals(BaseModel):
    spend: float
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    cpm: float
    leads: int
    cpl: float
    conversions: int
    roas: float

    @classmethod
    def of_perf(cls, p: Performance) -> PerfTotals:
        return cls(
            spend=float(p.spend),
            impressions=p.impressions,
            clicks=p.clicks,
            ctr=p.ctr,
            cpc=p.cpc,
            cpm=p.cpm,
            leads=p.leads,
            cpl=p.cpl,
            conversions=p.conversions,
            roas=p.roas,
        )


class CampaignPerfOut(PerfTotals):
    id: str
    external_id: str
    name: str
    status: str
    objective: str

    @classmethod
    def of(cls, c: CampaignPerformance) -> CampaignPerfOut:
        return cls(
            id=c.external_id,
            external_id=c.external_id,
            name=c.name,
            status=c.status,
            objective=c.objective,
            **PerfTotals.of_perf(c.performance).model_dump(),
        )


class CampaignsOut(BaseModel):
    items: list[CampaignPerfOut]
    totals: PerfTotals


class DailyOut(BaseModel):
    date: date
    spend: float
    impressions: int
    clicks: int
    leads: int


class AlertOut(BaseModel):
    id: uuid.UUID
    campaign_ref: str
    metric: str
    value: float
    benchmark: float
    severity: str
    message: str
    created_at: datetime


class TestLeadIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr | None = None
    phone: str | None = None


class OkOut(BaseModel):
    ok: bool = True


# ── Endpoints autenticados ──────────────────────────────────────────────────


@router.get("/connection", response_model=ConnectionOut)
async def get_connection(
    principal: Principal = Depends(require(Permission.META_MANAGE)), uow: SqlMetaUnitOfWork = Depends(_uow)
) -> ConnectionOut:
    return ConnectionOut.of(await GetConnection(uow).execute(principal))


@router.put("/connection", response_model=ConnectionOut)
async def put_connection(
    body: ConnectionIn,
    principal: Principal = Depends(require(Permission.META_MANAGE)),
    uow: SqlMetaUnitOfWork = Depends(_uow),
) -> ConnectionOut:
    conn = await ConnectAccount(uow).execute(ConnectAccountCommand(actor=principal, **body.model_dump()))
    return ConnectionOut.of(conn)


@router.post("/sync", response_model=SyncOut)
async def sync(
    days: int = Query(default=30, ge=1, le=90),
    principal: Principal = Depends(require(Permission.META_MANAGE)),
    uow: SqlMetaUnitOfWork = Depends(_uow),
    gateway: MetaGraphGateway = Depends(_gateway),
) -> SyncOut:
    result = await SyncInsights(uow, gateway).execute(
        SyncInsightsCommand(tenant_id=principal.tenant_id, days=days, actor_id=principal.user_id)
    )
    return SyncOut(campaigns=result.campaigns, days=result.days)


@router.get("/campaigns", response_model=CampaignsOut)
async def campaigns(
    days: int = Query(default=30, ge=1, le=365),
    principal: Principal = Depends(require(Permission.META_MANAGE)),
    uow: SqlMetaUnitOfWork = Depends(_uow),
) -> CampaignsOut:
    items, totals = await ListCampaignPerformance(uow).execute(PerformanceQuery(principal, days))
    return CampaignsOut(items=[CampaignPerfOut.of(c) for c in items], totals=PerfTotals.of_perf(totals))


@router.get("/insights/daily", response_model=list[DailyOut])
async def daily(
    days: int = Query(default=30, ge=1, le=365),
    principal: Principal = Depends(require(Permission.META_MANAGE)),
    uow: SqlMetaUnitOfWork = Depends(_uow),
) -> list[DailyOut]:
    points = await DailyInsights(uow).execute(PerformanceQuery(principal, days))
    return [
        DailyOut(date=p.day, spend=float(p.spend), impressions=p.impressions, clicks=p.clicks, leads=p.leads)
        for p in points
    ]


@router.get("/alerts", response_model=list[AlertOut])
async def alerts(
    principal: Principal = Depends(require(Permission.META_MANAGE)), uow: SqlMetaUnitOfWork = Depends(_uow)
) -> list[AlertOut]:
    return [
        AlertOut(
            id=a.id,
            campaign_ref=a.campaign_ref,
            metric=a.metric,
            value=a.value,
            benchmark=a.benchmark,
            severity=a.severity.value,
            message=a.message,
            created_at=a.created_at,
        )
        for a in await ListAlerts(uow).execute(principal)
    ]


@router.post("/leads/test", response_model=OkOut)
async def test_lead(
    body: TestLeadIn,
    principal: Principal = Depends(require(Permission.META_MANAGE)),
    uow: SqlMetaUnitOfWork = Depends(_uow),
) -> OkOut:
    await SimulateLead(uow).execute(SimulateLeadCommand(actor=principal, **body.model_dump()))
    return OkOut()


# ── Webhooks públicos (Lead Ads) ────────────────────────────────────────────


@router.get("/webhooks", response_class=PlainTextResponse)
async def verify_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str = Query(default="", alias="hub.challenge"),
    container: Container = Depends(get_container),
) -> str:
    expected = container.settings.meta_verify_token
    if not verify_subscription(mode, token, expected.get_secret_value() if expected else None):
        raise AuthenticationError("Token de verificación inválido", code="invalid_verify_token")
    return challenge


@router.post("/webhooks", response_model=OkOut, status_code=status.HTTP_200_OK)
async def lead_webhook(
    request: Request,
    container: Container = Depends(get_container),
    uow: SqlMetaUnitOfWork = Depends(_uow),
    gateway: MetaGraphGateway = Depends(_gateway),
) -> OkOut:
    body = await request.body()
    secret = container.settings.meta_app_secret
    verify_signature(
        secret.get_secret_value() if secret else None,
        body,
        request.headers.get("X-Hub-Signature-256"),
        env=container.settings.env,
    )
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise BusinessRuleViolation("Payload de webhook inválido", code="invalid_payload") from exc
    await ProcessLeadAdsWebhook(uow, gateway).execute(lead_notifications_from_payload(payload))
    return OkOut()
