"""Dominio de Analítica: hechos normalizados (proyección de eventos) y KPIs."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Any

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.events import DomainEvent
from oneheavy.shared.domain.time import ensure_aware


class Metric(StrEnum):
    TASKS_COMPLETED = "tasks_completed"
    TASKS_ON_TIME = "tasks_on_time"
    CLEANING_MINUTES = "cleaning_minutes"
    ISSUES = "issues"
    CONTACTS_CREATED = "contacts_created"
    CUSTOMERS_WON = "customers_won"
    DEALS_WON = "deals_won"
    DEALS_LOST = "deals_lost"
    REVENUE = "revenue"
    LEADS_CAPTURED = "leads_captured"
    AD_SPEND = "ad_spend"
    AD_IMPRESSIONS = "ad_impressions"
    AD_CLICKS = "ad_clicks"
    AD_LEADS = "ad_leads"
    ENGAGEMENT_EVENTS = "engagement_events"
    CAMPAIGNS_LAUNCHED = "campaigns_launched"
    AUDITS_COMPLETED = "audits_completed"
    FUNNELS_DESIGNED = "funnels_designed"
    POINTS_AWARDED = "points_awarded"


TIMESERIES_METRICS: frozenset[Metric] = frozenset(
    {
        Metric.TASKS_COMPLETED,
        Metric.CONTACTS_CREATED,
        Metric.LEADS_CAPTURED,
        Metric.DEALS_WON,
        Metric.REVENUE,
        Metric.AD_SPEND,
        Metric.ENGAGEMENT_EVENTS,
        Metric.POINTS_AWARDED,
    }
)

FUNNEL_STAGES: tuple[str, ...] = (
    "subscriber",
    "lead",
    "mql",
    "sql",
    "opportunity",
    "customer",
    "evangelist",
    "lost",
)
DEFAULT_NEW_CONTACT_STAGE = "lead"


@dataclass(frozen=True, kw_only=True)
class Fact:
    """Medición atómica. Única por (tenant_id, source_key, metric).

    `replace=True` indica que una nueva medición con la misma clave reemplaza la
    anterior (p. ej. re-sincronizar el gasto publicitario de un día).
    """

    tenant_id: uuid.UUID
    metric: Metric
    value: float
    occurred_at: datetime
    source_key: str
    subject_id: uuid.UUID | None = None
    dims: dict[str, Any] = field(default_factory=dict)
    replace: bool = False


@dataclass(frozen=True)
class StageChange:
    contact_id: uuid.UUID
    stage: str
    only_if_absent: bool = False


@dataclass(frozen=True)
class Projection:
    facts: list[Fact]
    stage_change: StageChange | None = None


# ── Proyector (Strategy por tipo de evento) ─────────────────────────────────


def _fact(event: DomainEvent, metric: Metric, value: float = 1.0, **kw: Any) -> Fact:
    return Fact(
        tenant_id=event.tenant_id,
        metric=metric,
        value=value,
        occurred_at=event.occurred_at,
        source_key=str(event.event_id),
        **kw,
    )


def _cleaning_completed(e: ie.CleaningTaskCompleted) -> Projection:
    facts = [_fact(e, Metric.TASKS_COMPLETED, subject_id=e.staff_id, dims={"on_time": e.on_time})]
    if e.on_time:
        facts.append(_fact(e, Metric.TASKS_ON_TIME, subject_id=e.staff_id))
    if e.duration_minutes is not None:
        facts.append(_fact(e, Metric.CLEANING_MINUTES, float(e.duration_minutes), subject_id=e.staff_id))
    return Projection(facts)


def _issue(e: ie.CleaningIssueReported) -> Projection:
    return Projection([_fact(e, Metric.ISSUES, subject_id=e.staff_id, dims={"kind": e.kind})])


def _contact_created(e: ie.ContactCreated) -> Projection:
    return Projection(
        [_fact(e, Metric.CONTACTS_CREATED, subject_id=e.owner_id, dims={"source": e.source})],
        StageChange(e.contact_id, e.stage or DEFAULT_NEW_CONTACT_STAGE, only_if_absent=True),
    )


def _lifecycle(e: ie.ContactLifecycleChanged) -> Projection:
    facts = [_fact(e, Metric.CUSTOMERS_WON)] if e.to_stage == "customer" else []
    return Projection(facts, StageChange(e.contact_id, e.to_stage))


def _deal_won(e: ie.DealWon) -> Projection:
    dims = {"currency": e.currency}
    return Projection(
        [
            _fact(e, Metric.DEALS_WON, subject_id=e.owner_id, dims=dims),
            _fact(e, Metric.REVENUE, float(Decimal(e.amount)), subject_id=e.owner_id, dims=dims),
        ]
    )


def _deal_lost(e: ie.DealLost) -> Projection:
    return Projection([_fact(e, Metric.DEALS_LOST, subject_id=e.owner_id)])


def _lead(e: ie.LeadCaptured) -> Projection:
    return Projection([_fact(e, Metric.LEADS_CAPTURED, dims={"source": e.source})])


def _ads(e: ie.AdInsightsSynced) -> Projection:
    day = ensure_aware(e.day)
    at = datetime.combine(day.date(), time(0), tzinfo=day.tzinfo)  # inicio del día
    key = f"ads:{day.date().isoformat()}"

    def ad(metric: Metric, value: float) -> Fact:
        return Fact(
            tenant_id=e.tenant_id,
            metric=metric,
            value=value,
            occurred_at=at,
            source_key=key,
            dims={"currency": e.currency},
            replace=True,
        )

    return Projection(
        [
            ad(Metric.AD_SPEND, float(Decimal(e.spend))),
            ad(Metric.AD_IMPRESSIONS, float(e.impressions)),
            ad(Metric.AD_CLICKS, float(e.clicks)),
            ad(Metric.AD_LEADS, float(e.leads)),
        ]
    )


def _engagement(e: ie.MarketingEngagementRecorded) -> Projection:
    return Projection([_fact(e, Metric.ENGAGEMENT_EVENTS, dims={"kind": e.kind})])


def _campaign(e: ie.CampaignLaunched) -> Projection:
    return Projection([_fact(e, Metric.CAMPAIGNS_LAUNCHED, dims={"channel": e.channel})])


def _audit(e: ie.MarketAuditCompleted) -> Projection:
    return Projection([_fact(e, Metric.AUDITS_COMPLETED, dims={"awareness": e.awareness_level})])


def _funnel(e: ie.FunnelDesigned) -> Projection:
    return Projection([_fact(e, Metric.FUNNELS_DESIGNED)])


def _points(e: ie.PointsAwarded) -> Projection:
    return Projection(
        [_fact(e, Metric.POINTS_AWARDED, float(e.points), subject_id=e.user_id, dims={"rule": e.rule_key})]
    )


_PROJECTORS: dict[type[DomainEvent], Callable[[Any], Projection]] = {
    ie.CleaningTaskCompleted: _cleaning_completed,
    ie.CleaningIssueReported: _issue,
    ie.ContactCreated: _contact_created,
    ie.ContactLifecycleChanged: _lifecycle,
    ie.DealWon: _deal_won,
    ie.DealLost: _deal_lost,
    ie.LeadCaptured: _lead,
    ie.AdInsightsSynced: _ads,
    ie.MarketingEngagementRecorded: _engagement,
    ie.CampaignLaunched: _campaign,
    ie.MarketAuditCompleted: _audit,
    ie.FunnelDesigned: _funnel,
    ie.PointsAwarded: _points,
}


class EventProjector:
    @staticmethod
    def event_types() -> tuple[type[DomainEvent], ...]:
        return tuple(_PROJECTORS)

    @staticmethod
    def project(event: DomainEvent) -> Projection:
        fn = _PROJECTORS.get(type(event))
        return fn(event) if fn else Projection([])


# ── KPIs ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Aggregate:
    total: float = 0.0
    count: int = 0

    @property
    def avg(self) -> float:
        return self.total / self.count if self.count else 0.0


def _ratio(num: float, den: float) -> float:
    return round(num / den, 4) if den else 0.0


@dataclass(frozen=True)
class Overview:
    period_from: datetime
    period_to: datetime
    operations: dict[str, float]
    sales: dict[str, float]
    marketing: dict[str, float]
    growth: dict[str, float]
    gamification: dict[str, float]

    @classmethod
    def compute(
        cls, since: datetime, until: datetime, agg: dict[Metric, Aggregate], active_players: int
    ) -> Overview:
        def t(m: Metric) -> float:
            return agg.get(m, Aggregate()).total

        tasks = t(Metric.TASKS_COMPLETED)
        won, lost = t(Metric.DEALS_WON), t(Metric.DEALS_LOST)
        spend = t(Metric.AD_SPEND)
        leads_for_cpl = t(Metric.AD_LEADS) or t(Metric.LEADS_CAPTURED)
        return cls(
            period_from=since,
            period_to=until,
            operations={
                "tasks_completed": int(tasks),
                "on_time_rate": _ratio(t(Metric.TASKS_ON_TIME), tasks),
                "avg_cleaning_minutes": round(agg.get(Metric.CLEANING_MINUTES, Aggregate()).avg, 1),
                "issues": int(t(Metric.ISSUES)),
            },
            sales={
                "new_contacts": int(t(Metric.CONTACTS_CREATED)),
                "deals_won": int(won),
                "revenue": round(t(Metric.REVENUE), 2),
                "win_rate": _ratio(won, won + lost),
            },
            marketing={
                "leads_captured": int(t(Metric.LEADS_CAPTURED)),
                "engagement_events": int(t(Metric.ENGAGEMENT_EVENTS)),
                "campaigns_launched": int(t(Metric.CAMPAIGNS_LAUNCHED)),
                "ad_spend": round(spend, 2),
                "cpl": round(spend / leads_for_cpl, 2) if leads_for_cpl else 0.0,
            },
            growth={
                "audits_completed": int(t(Metric.AUDITS_COMPLETED)),
                "funnels_designed": int(t(Metric.FUNNELS_DESIGNED)),
            },
            gamification={
                "points_awarded": int(t(Metric.POINTS_AWARDED)),
                "active_players": active_players,
            },
        )

    def digest(self) -> dict[str, Any]:
        return {
            "periodo": {
                "desde": self.period_from.date().isoformat(),
                "hasta": self.period_to.date().isoformat(),
            },
            "operacion": self.operations,
            "ventas": self.sales,
            "marketing": self.marketing,
            "growth": self.growth,
            "gamificacion": self.gamification,
        }


# ── Insights ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class InsightReport:
    summary: str
    highlights: list[str]
    risks: list[str]
    recommendations: list[str]

    @classmethod
    def parse(cls, raw: object) -> InsightReport | None:
        """Valida la forma devuelta por el LLM; None si no es utilizable."""
        if not isinstance(raw, dict):
            return None
        summary = raw.get("summary")
        lists = [raw.get(k) for k in ("highlights", "risks", "recommendations")]
        if not isinstance(summary, str) or not summary.strip():
            return None
        if not all(isinstance(lst, list) and all(isinstance(x, str) for x in lst) for lst in lists):
            return None
        h, r, rec = (list(x) for x in lists)  # type: ignore[arg-type]
        return cls(summary.strip(), h, r, rec)

    @classmethod
    def rule_based(cls, ov: Overview) -> InsightReport:
        """Insights deterministas cuando la IA no está disponible."""
        ops, sales, mkt = ov.operations, ov.sales, ov.marketing
        highlights: list[str] = []
        risks: list[str] = []
        recs: list[str] = []
        if ops["tasks_completed"]:
            highlights.append(
                f"{int(ops['tasks_completed'])} limpiezas completadas, {ops['on_time_rate']:.0%} a tiempo."
            )
            if ops["on_time_rate"] < 0.85:
                risks.append("La puntualidad operativa está por debajo del 85%.")
                recs.append(
                    "Revisa rutas y asignaciones del personal con más retrasos; activa retos de puntualidad."
                )
        if ops["issues"] > 0:
            risks.append(f"Se reportaron {int(ops['issues'])} incidencias en la operación.")
        if sales["new_contacts"]:
            highlights.append(f"{int(sales['new_contacts'])} contactos nuevos en el CRM.")
        if sales["deals_won"]:
            highlights.append(f"{int(sales['deals_won'])} negocios ganados por {sales['revenue']:,.0f}.")
        if sales["deals_won"] + sales["new_contacts"] and sales["win_rate"] < 0.2:
            risks.append("La tasa de cierre es inferior al 20%.")
            recs.append("Prioriza contactos 'hot' con el lead scoring y automatiza seguimientos en Mautic.")
        if mkt["ad_spend"] and not mkt["leads_captured"]:
            risks.append("Hay inversión publicitaria sin leads capturados.")
            recs.append("Conecta los formularios de Meta Lead Ads al CRM y revisa la segmentación.")
        if not mkt["campaigns_launched"]:
            recs.append("Lanza una campaña de nurturing con emails generados por IA para tus leads.")
        if not highlights:
            highlights.append("Aún no hay suficiente actividad en el periodo.")
        if not recs:
            recs.append("Mantén el ritmo: define un reto de equipo para la próxima semana.")
        summary = (
            f"Periodo {ov.period_from.date()} a {ov.period_to.date()}: "
            f"{int(ops['tasks_completed'])} limpiezas, {int(sales['new_contacts'])} contactos, "
            f"{int(mkt['leads_captured'])} leads y {int(sales['deals_won'])} negocios ganados."
        )
        return cls(summary, highlights, risks, recs)
