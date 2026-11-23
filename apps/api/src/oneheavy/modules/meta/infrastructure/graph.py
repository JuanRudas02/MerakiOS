"""Adaptadores de la Graph API de Meta (HTTP real y fake determinista)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx

from oneheavy.modules.meta.application.ports import (
    CampaignInsightRow,
    ConversionEvent,
    DailyInsightRow,
    MetaGraphGateway,
)
from oneheavy.modules.meta.domain.model import LeadData
from oneheavy.shared.domain.errors import ExternalServiceError

log = logging.getLogger("oneheavy.meta.graph")

LEAD_ACTIONS = {"lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead", "leadgen.other"}
PURCHASE_ACTIONS = {"purchase", "offsite_conversion.fb_pixel_purchase", "omni_purchase"}
INSIGHT_FIELDS = "campaign_id,campaign_name,spend,impressions,clicks,ctr,cpc,cpm,actions,action_values"


def _sum_actions(items: list[dict[str, Any]] | None, types: set[str]) -> Decimal:
    return sum(
        (Decimal(str(a.get("value", "0"))) for a in items or [] if a.get("action_type") in types), Decimal(0)
    )


def parse_lead_fields(field_data: list[dict[str, Any]]) -> dict[str, str]:
    return {str(f.get("name")): ", ".join(map(str, f.get("values") or [])) for f in field_data}


class HttpMetaGraphGateway(MetaGraphGateway):
    def __init__(self, graph_version: str = "v21.0", *, timeout: float = 30.0) -> None:
        self._base = f"https://graph.facebook.com/{graph_version}"
        self._timeout = timeout

    async def _get(self, path: str, token: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._base}/{path}", params={**params, "access_token": token})
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                return data
        except httpx.HTTPError as exc:
            log.exception("meta_graph_get_failed", extra={"path": path})
            raise ExternalServiceError("Meta Graph API no respondió correctamente") from exc

    async def _paged(self, path: str, token: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        data = await self._get(path, token, params)
        out.extend(data.get("data", []))
        pages = 0
        while (cursor := (data.get("paging") or {}).get("cursors", {}).get("after")) and pages < 20:
            if not (data.get("paging") or {}).get("next"):
                break
            data = await self._get(path, token, {**params, "after": cursor})
            out.extend(data.get("data", []))
            pages += 1
        return out

    async def fetch_campaign_insights(
        self, ad_account_id: str, access_token: str, since: date, until: date
    ) -> list[CampaignInsightRow]:
        campaigns = await self._paged(
            f"act_{ad_account_id}/campaigns",
            access_token,
            {"fields": "id,name,status,objective", "limit": 200},
        )
        meta = {c["id"]: c for c in campaigns}
        rows = await self._paged(
            f"act_{ad_account_id}/insights",
            access_token,
            {
                "level": "campaign",
                "time_increment": 1,
                "fields": INSIGHT_FIELDS,
                "time_range": json.dumps({"since": since.isoformat(), "until": until.isoformat()}),
                "limit": 500,
            },
        )
        result = []
        for r in rows:
            info = meta.get(r.get("campaign_id"), {})
            result.append(
                CampaignInsightRow(
                    campaign_id=str(r.get("campaign_id")),
                    campaign_name=str(r.get("campaign_name") or info.get("name") or ""),
                    status=str(info.get("status") or "UNKNOWN"),
                    objective=str(info.get("objective") or "UNKNOWN"),
                    day=date.fromisoformat(r["date_start"]),
                    spend=Decimal(str(r.get("spend", "0"))),
                    impressions=int(r.get("impressions", 0)),
                    clicks=int(r.get("clicks", 0)),
                    leads=int(_sum_actions(r.get("actions"), LEAD_ACTIONS)),
                    conversions=int(_sum_actions(r.get("actions"), PURCHASE_ACTIONS)),
                    revenue=_sum_actions(r.get("action_values"), PURCHASE_ACTIONS),
                )
            )
        return result

    async def fetch_daily_insights(
        self, ad_account_id: str, access_token: str, since: date, until: date
    ) -> list[DailyInsightRow]:
        rows = await self._paged(
            f"act_{ad_account_id}/insights",
            access_token,
            {
                "level": "account",
                "time_increment": 1,
                "fields": "spend,impressions,clicks,actions,account_currency",
                "time_range": json.dumps({"since": since.isoformat(), "until": until.isoformat()}),
            },
        )
        return [
            DailyInsightRow(
                day=date.fromisoformat(r["date_start"]),
                spend=Decimal(str(r.get("spend", "0"))),
                impressions=int(r.get("impressions", 0)),
                clicks=int(r.get("clicks", 0)),
                leads=int(_sum_actions(r.get("actions"), LEAD_ACTIONS)),
                currency=str(r.get("account_currency") or "COP"),
            )
            for r in rows
        ]

    async def fetch_lead(self, leadgen_id: str, access_token: str) -> LeadData:
        data = await self._get(
            leadgen_id, access_token, {"fields": "field_data,campaign_id,ad_id,created_time"}
        )
        answers = parse_lead_fields(data.get("field_data", []))
        name = answers.pop("full_name", None) or " ".join(
            filter(None, [answers.pop("first_name", ""), answers.pop("last_name", "")])
        )
        return LeadData(
            leadgen_id=leadgen_id,
            full_name=name or None,
            email=answers.pop("email", None),
            phone=answers.pop("phone_number", None),
            campaign_ref=data.get("campaign_id"),
            answers=answers,
        )

    async def send_conversion_events(
        self, pixel_id: str, access_token: str, events: list[ConversionEvent]
    ) -> None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base}/{pixel_id}/events",
                    params={"access_token": access_token},
                    json={"data": [asdict(e) for e in events]},
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.exception("meta_capi_failed", extra={"pixel_id": pixel_id})
            raise ExternalServiceError("Meta Conversions API rechazó el evento") from exc


class FakeMetaGraphGateway(MetaGraphGateway):
    """Datos de muestra deterministas (desarrollo local, demos y tests).

    - "Prospección · Video" rinde bien.
    - "Remarketing · Carrusel" tiene CTR bajo (dispara alerta de fatiga creativa).
    - "Lead Ads · Formulario" genera leads.
    """

    CAMPAIGNS = (
        ("120001", "Prospección · Video", "ACTIVE", "OUTCOME_AWARENESS", 2.2),
        ("120002", "Remarketing · Carrusel", "ACTIVE", "OUTCOME_SALES", 0.4),
        ("120003", "Lead Ads · Formulario", "ACTIVE", "OUTCOME_LEADS", 1.6),
    )

    def __init__(self) -> None:
        self.sent_events: list[tuple[str, ConversionEvent]] = []
        self.leads: dict[str, LeadData] = {}

    async def fetch_campaign_insights(
        self, ad_account_id: str, access_token: str, since: date, until: date
    ) -> list[CampaignInsightRow]:
        rows = []
        day = since
        while day <= until:
            seed = day.toordinal() % 7
            for cid, name, status, objective, ctr in self.CAMPAIGNS:
                impressions = 4000 + seed * 250
                clicks = int(impressions * ctr / 100)
                leads = clicks // 8 if objective == "OUTCOME_LEADS" else 0
                conversions = clicks // 40 if objective == "OUTCOME_SALES" else 0
                rows.append(
                    CampaignInsightRow(
                        campaign_id=cid,
                        campaign_name=name,
                        status=status,
                        objective=objective,
                        day=day,
                        spend=Decimal(60000 + seed * 5000),
                        impressions=impressions,
                        clicks=clicks,
                        leads=leads,
                        conversions=conversions,
                        revenue=Decimal(conversions * 250000),
                    )
                )
            day += timedelta(days=1)
        return rows

    async def fetch_daily_insights(
        self, ad_account_id: str, access_token: str, since: date, until: date
    ) -> list[DailyInsightRow]:
        rows = await self.fetch_campaign_insights(ad_account_id, access_token, since, until)
        by_day: dict[date, list[CampaignInsightRow]] = {}
        for r in rows:
            by_day.setdefault(r.day, []).append(r)
        return [
            DailyInsightRow(
                day=d,
                spend=sum((r.spend for r in rs), Decimal(0)),
                impressions=sum(r.impressions for r in rs),
                clicks=sum(r.clicks for r in rs),
                leads=sum(r.leads for r in rs),
            )
            for d, rs in sorted(by_day.items())
        ]

    async def fetch_lead(self, leadgen_id: str, access_token: str) -> LeadData:
        return self.leads.get(
            leadgen_id,
            LeadData(
                leadgen_id=leadgen_id,
                full_name="Lead de Prueba",
                email=f"lead-{leadgen_id}@example.com",
                phone="+573001112233",
                campaign_ref="120003",
                answers={"presupuesto": "5-10M"},
            ),
        )

    async def send_conversion_events(
        self, pixel_id: str, access_token: str, events: list[ConversionEvent]
    ) -> None:
        self.sent_events.extend((pixel_id, e) for e in events)
