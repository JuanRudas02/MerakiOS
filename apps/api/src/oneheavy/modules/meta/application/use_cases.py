"""Casos de uso de Meta Business.

CU-META-01  Conectar cuenta publicitaria (ad account, página, pixel, token)
CU-META-02  Consultar estado de la conexión
CU-META-03  Sincronizar insights + detectar anomalías (manual o job diario 06:00)
CU-META-04  Consultar rendimiento por campaña
CU-META-05  Consultar serie diaria de la cuenta
CU-META-06  Consultar alertas de rendimiento
CU-META-07  Recibir Lead Ads (webhook) → LeadCaptured → CRM
CU-META-08  Simular lead (demo / QA)
CU-META-09  Enviar conversiones offline (Conversions API) al ganar negocios / calificar leads
CU-META-10  Mantener huellas hasheadas de contactos (para CAPI)
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from oneheavy.modules.meta.application.ports import (
    ConversionEvent,
    MetaGraphGateway,
    MetaUnitOfWork,
)
from oneheavy.modules.meta.domain.anomalies import AnomalyDetector, CampaignSeries
from oneheavy.modules.meta.domain.model import (
    AdAlert,
    CampaignDailyMetric,
    ContactFingerprint,
    MetaConnection,
    Performance,
    hash_email,
    hash_phone,
)
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import BusinessRuleViolation, NotFoundError
from oneheavy.shared.domain.time import utc_now

log = logging.getLogger("oneheavy.meta")


# ── CU-META-01 / 02 ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConnectAccountCommand:
    actor: Principal
    ad_account_id: str
    access_token: str
    page_id: str | None = None
    pixel_id: str | None = None


class ConnectAccount(UseCase[ConnectAccountCommand, MetaConnection]):
    def __init__(self, uow: MetaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ConnectAccountCommand) -> MetaConnection:
        data.actor.require(Permission.META_MANAGE)
        async with self.uow:
            conn = await self.uow.connections.get(data.actor.tenant_id)
            if data.page_id:
                owner = await self.uow.connections.find_by_page(data.page_id.strip())
                if owner is not None and owner.tenant_id != data.actor.tenant_id:
                    raise BusinessRuleViolation(
                        "Esa página ya está conectada a otro workspace", code="page_already_connected"
                    )
            if conn is None:
                conn = MetaConnection.connect(
                    tenant_id=data.actor.tenant_id,
                    ad_account_id=data.ad_account_id,
                    access_token=data.access_token,
                    page_id=data.page_id,
                    pixel_id=data.pixel_id,
                )
            else:
                conn.update(
                    ad_account_id=data.ad_account_id,
                    access_token=data.access_token,
                    page_id=data.page_id,
                    pixel_id=data.pixel_id,
                )
            await self.uow.connections.save(conn)
            await self.uow.commit()
        return conn


class GetConnection(UseCase[Principal, MetaConnection | None]):
    def __init__(self, uow: MetaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> MetaConnection | None:
        data.require(Permission.META_MANAGE)
        async with self.uow:
            return await self.uow.connections.get(data.tenant_id)


# ── CU-META-03 ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SyncInsightsCommand:
    tenant_id: uuid.UUID
    days: int = 30
    actor_id: uuid.UUID | None = None


@dataclass(frozen=True)
class SyncResult:
    campaigns: int
    days: int
    alerts: int


class SyncInsights(UseCase[SyncInsightsCommand, SyncResult]):
    def __init__(
        self, uow: MetaUnitOfWork, gateway: MetaGraphGateway, detector: AnomalyDetector | None = None
    ) -> None:
        self.uow, self.gateway = uow, gateway
        self.detector = detector or AnomalyDetector()

    async def execute(self, data: SyncInsightsCommand) -> SyncResult:
        if not 1 <= data.days <= 90:
            raise BusinessRuleViolation("El rango de sincronización debe estar entre 1 y 90 días")
        until = utc_now().date() - timedelta(days=1)
        since = until - timedelta(days=data.days - 1)
        async with self.uow:
            conn = await self.uow.connections.get(data.tenant_id)
            if conn is None:
                raise BusinessRuleViolation("Conecta primero tu cuenta de Meta", code="meta_not_connected")
            # La llamada externa ocurre fuera de cualquier escritura pendiente.
            rows = await self.gateway.fetch_campaign_insights(
                conn.ad_account_id, conn.access_token, since, until
            )
            daily = await self.gateway.fetch_daily_insights(
                conn.ad_account_id, conn.access_token, since, until
            )

            metrics = [
                CampaignDailyMetric(
                    tenant_id=data.tenant_id,
                    external_id=r.campaign_id,
                    name=r.campaign_name,
                    status=r.status,
                    objective=r.objective,
                    day=r.day,
                    spend=r.spend,
                    impressions=r.impressions,
                    clicks=r.clicks,
                    leads=r.leads,
                    conversions=r.conversions,
                    revenue=r.revenue,
                )
                for r in rows
            ]
            await self.uow.metrics.replace_window(data.tenant_id, since, metrics)

            events: list[Any] = [
                ie.AdInsightsSynced(
                    tenant_id=data.tenant_id,
                    actor_id=data.actor_id,
                    day=datetime.combine(d.day, time.min).replace(tzinfo=utc_now().tzinfo),
                    spend=d.spend,
                    currency=d.currency,
                    impressions=d.impressions,
                    clicks=d.clicks,
                    leads=d.leads,
                )
                for d in daily
            ]

            new_alerts = 0
            for series in _group_series(metrics):
                for anomaly in self.detector.detect(series):
                    key = anomaly.dedupe_key(series)
                    if await self.uow.alerts.exists(data.tenant_id, key):
                        continue
                    await self.uow.alerts.add(
                        AdAlert(
                            tenant_id=data.tenant_id,
                            campaign_ref=anomaly.campaign_ref,
                            metric=anomaly.metric,
                            value=anomaly.value,
                            benchmark=anomaly.benchmark,
                            severity=anomaly.severity,
                            message=anomaly.message,
                            dedupe_key=key,
                        )
                    )
                    new_alerts += 1
                    events.append(
                        ie.AdPerformanceAnomalyDetected(
                            tenant_id=data.tenant_id,
                            campaign_ref=anomaly.campaign_ref,
                            metric=anomaly.metric,
                            value=anomaly.value,
                            benchmark=anomaly.benchmark,
                            severity=anomaly.severity.value,
                        )
                    )

            conn.mark_synced()
            await self.uow.connections.save(conn)
            self.uow.collect(events)
            await self.uow.commit()
        return SyncResult(len({m.external_id for m in metrics}), data.days, new_alerts)


def _group_series(metrics: list[CampaignDailyMetric]) -> list[CampaignSeries]:
    grouped: dict[str, list[CampaignDailyMetric]] = defaultdict(list)
    for m in metrics:
        grouped[m.external_id].append(m)
    series = []
    for external_id, days in grouped.items():
        days.sort(key=lambda m: m.day)
        latest = days[-1]
        series.append(CampaignSeries(external_id, latest.name, latest.status, days))
    return series


# ── CU-META-04 / 05 / 06 ────────────────────────────────────────────────────


@dataclass(frozen=True)
class CampaignPerformance:
    external_id: str
    name: str
    status: str
    objective: str
    performance: Performance


@dataclass(frozen=True)
class PerformanceQuery:
    actor: Principal
    days: int = 30


def _since(days: int) -> date:
    if not 1 <= days <= 365:
        raise BusinessRuleViolation("`days` debe estar entre 1 y 365")
    return utc_now().date() - timedelta(days=days)


class ListCampaignPerformance(UseCase[PerformanceQuery, tuple[list[CampaignPerformance], Performance]]):
    def __init__(self, uow: MetaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: PerformanceQuery) -> tuple[list[CampaignPerformance], Performance]:
        data.actor.require(Permission.META_MANAGE)
        async with self.uow:
            metrics = await self.uow.metrics.list_since(data.actor.tenant_id, _since(data.days))
        items = [
            CampaignPerformance(s.external_id, s.name, s.status, s.days[-1].objective, s.total)
            for s in _group_series(metrics)
        ]
        items.sort(key=lambda c: c.performance.spend, reverse=True)
        return items, Performance.of(metrics)


@dataclass(frozen=True)
class DailyPoint:
    day: date
    spend: Decimal
    impressions: int
    clicks: int
    leads: int


class DailyInsights(UseCase[PerformanceQuery, list[DailyPoint]]):
    def __init__(self, uow: MetaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: PerformanceQuery) -> list[DailyPoint]:
        data.actor.require(Permission.META_MANAGE)
        async with self.uow:
            metrics = await self.uow.metrics.list_since(data.actor.tenant_id, _since(data.days))
        by_day: dict[date, list[CampaignDailyMetric]] = defaultdict(list)
        for m in metrics:
            by_day[m.day].append(m)
        points = []
        for day in sorted(by_day):
            perf = Performance.of(by_day[day])
            points.append(DailyPoint(day, perf.spend, perf.impressions, perf.clicks, perf.leads))
        return points


class ListAlerts(UseCase[Principal, list[AdAlert]]):
    def __init__(self, uow: MetaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[AdAlert]:
        data.require(Permission.META_MANAGE)
        async with self.uow:
            return await self.uow.alerts.list_recent(data.tenant_id)


# ── CU-META-07 / 08 ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LeadNotification:
    page_id: str
    leadgen_id: str


class ProcessLeadAdsWebhook(UseCase[list[LeadNotification], int]):
    """Resuelve página → workspace, descarga el lead y publica LeadCaptured."""

    def __init__(self, uow: MetaUnitOfWork, gateway: MetaGraphGateway) -> None:
        self.uow, self.gateway = uow, gateway

    async def execute(self, data: list[LeadNotification]) -> int:
        captured = 0
        async with self.uow:
            events = []
            for note in data:
                conn = await self.uow.connections.find_by_page(note.page_id)
                if conn is None:
                    log.warning("meta_lead_unknown_page", extra={"page_id": note.page_id})
                    continue
                lead = await self.gateway.fetch_lead(note.leadgen_id, conn.access_token)
                events.append(
                    ie.LeadCaptured(
                        tenant_id=conn.tenant_id,
                        source="meta_lead_ads",
                        external_id=lead.leadgen_id,
                        full_name=lead.full_name,
                        email=lead.email,
                        phone=lead.phone,
                        campaign_ref=lead.campaign_ref,
                        answers=dict(lead.answers),
                    )
                )
                captured += 1
            self.uow.collect(events)
            await self.uow.commit()
        return captured


@dataclass(frozen=True)
class SimulateLeadCommand:
    actor: Principal
    full_name: str
    email: str | None = None
    phone: str | None = None


class SimulateLead(UseCase[SimulateLeadCommand, None]):
    def __init__(self, uow: MetaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: SimulateLeadCommand) -> None:
        data.actor.require(Permission.META_MANAGE)
        if not data.email and not data.phone:
            raise BusinessRuleViolation("El lead de prueba necesita email o teléfono")
        async with self.uow:
            self.uow.collect(
                [
                    ie.LeadCaptured(
                        tenant_id=data.actor.tenant_id,
                        actor_id=data.actor.user_id,
                        source="meta_lead_ads",
                        external_id=f"test-{uuid.uuid4().hex[:12]}",
                        full_name=data.full_name,
                        email=data.email,
                        phone=data.phone,
                        campaign_ref="test",
                    )
                ]
            )
            await self.uow.commit()


# ── CU-META-09 / 10 (reacciones a eventos del CRM) ──────────────────────────


class RememberContact(UseCase[ie.ContactCreated, None]):
    def __init__(self, uow: MetaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ie.ContactCreated) -> None:
        async with self.uow:
            fp = await self.uow.fingerprints.get(data.tenant_id, data.contact_id) or ContactFingerprint(
                tenant_id=data.tenant_id, contact_id=data.contact_id
            )
            fp.hashed_email = hash_email(data.email) or fp.hashed_email
            fp.hashed_phone = hash_phone(data.phone) or fp.hashed_phone
            await self.uow.fingerprints.save(fp)
            await self.uow.commit()


@dataclass(frozen=True)
class SendConversionCommand:
    tenant_id: uuid.UUID
    event_name: str
    event_id: str
    contact_id: uuid.UUID | None
    occurred_at: datetime
    value: Decimal | None = None
    currency: str | None = None


class SendConversion(UseCase[SendConversionCommand, bool]):
    """Devuelve False si el workspace no tiene pixel (no se envía nada)."""

    def __init__(self, uow: MetaUnitOfWork, gateway: MetaGraphGateway) -> None:
        self.uow, self.gateway = uow, gateway

    async def execute(self, data: SendConversionCommand) -> bool:
        async with self.uow:
            conn = await self.uow.connections.get(data.tenant_id)
            if conn is None or not conn.pixel_id:
                return False
            fp = await self.uow.fingerprints.get(data.tenant_id, data.contact_id) if data.contact_id else None
        user_data: dict[str, Any] = {}
        if fp and fp.hashed_email:
            user_data["em"] = [fp.hashed_email]
        if fp and fp.hashed_phone:
            user_data["ph"] = [fp.hashed_phone]
        if data.contact_id:
            user_data["external_id"] = [hash_email(str(data.contact_id))]
        custom: dict[str, Any] = {}
        if data.value is not None:
            custom = {"value": float(data.value), "currency": data.currency or "COP"}
        event = ConversionEvent(
            event_name=data.event_name,
            event_id=data.event_id,
            event_time=int(data.occurred_at.timestamp()),
            user_data=user_data,
            custom_data=custom,
        )
        await self.gateway.send_conversion_events(conn.pixel_id, conn.access_token, [event])
        return True


def lead_notifications_from_payload(payload: dict[str, Any]) -> list[LeadNotification]:
    """Extrae los `leadgen` de un webhook de Meta (object=page)."""
    if payload.get("object") != "page":
        return []
    notes = []
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            if change.get("field") == "leadgen" and value.get("leadgen_id"):
                notes.append(
                    LeadNotification(str(value.get("page_id") or entry.get("id")), str(value["leadgen_id"]))
                )
    return notes


def ensure_found(conn: MetaConnection | None) -> MetaConnection:
    if conn is None:
        raise NotFoundError("Meta no está conectado")
    return conn
