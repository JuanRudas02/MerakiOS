from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from oneheavy.modules.analytics.domain.model import InsightReport, Overview
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.time import utc_now
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.llm import FakeLLMClient
from tests.conftest import AuthContext, register_workspace


async def seed(container: Container, tenant: uuid.UUID) -> None:
    bus = container.bus
    staff = uuid.uuid4()
    for on_time, minutes in ((True, 60), (True, 90), (False, 120)):
        await bus.publish(
            ie.CleaningTaskCompleted(
                tenant_id=tenant, task_id=uuid.uuid4(), property_id=uuid.uuid4(), staff_id=staff,
                duration_minutes=minutes, photos_count=0, on_time=on_time,
            )
        )  # fmt: skip
    await bus.publish(
        ie.CleaningIssueReported(
            tenant_id=tenant, task_id=uuid.uuid4(), staff_id=staff, kind="problem", description="fuga"
        )
    )
    contacts = [uuid.uuid4() for _ in range(3)]
    for cid in contacts:
        await bus.publish(
            ie.ContactCreated(tenant_id=tenant, contact_id=cid, email=None, phone=None, source="web")
        )
    await bus.publish(
        ie.ContactLifecycleChanged(
            tenant_id=tenant, contact_id=contacts[0], from_stage="lead", to_stage="customer"
        )
    )
    await bus.publish(
        ie.DealWon(
            tenant_id=tenant, deal_id=uuid.uuid4(), contact_id=contacts[0], owner_id=None,
            amount=Decimal("2500000"), currency="COP",
        )
    )  # fmt: skip
    await bus.publish(ie.DealLost(tenant_id=tenant, deal_id=uuid.uuid4(), owner_id=None))
    for _ in range(2):
        await bus.publish(
            ie.LeadCaptured(
                tenant_id=tenant,
                source="meta_lead_ads",
                external_id=None,
                full_name="X",
                email=None,
                phone=None,
            )
        )
    today = utc_now()
    ads = ie.AdInsightsSynced(
        tenant_id=tenant,
        day=today,
        spend=Decimal("100000"),
        currency="COP",
        impressions=1000,
        clicks=50,
        leads=4,
    )
    await bus.publish(ads)
    # re-sincronización del mismo día: reemplaza, no suma
    await bus.publish(
        ie.AdInsightsSynced(
            tenant_id=tenant, day=today, spend=Decimal("120000"), currency="COP", impressions=1200, clicks=60,
            leads=4,
        )
    )  # fmt: skip
    await bus.publish(
        ie.CampaignLaunched(tenant_id=tenant, campaign_id=uuid.uuid4(), name="Nurturing", channel="email")
    )
    await bus.publish(
        ie.MarketAuditCompleted(tenant_id=tenant, project_id=uuid.uuid4(), awareness_level="problem_aware")
    )


async def test_overview_aggregates_all_contexts(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    await seed(container, uuid.UUID(auth.workspace["id"]))
    resp = await client.get("/api/v1/analytics/overview?days=30", headers=auth.headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body["period"]) == {"from", "to"}
    assert body["operations"] == {
        "tasks_completed": 3,
        "on_time_rate": 0.6667,
        "avg_cleaning_minutes": 90.0,
        "issues": 1,
    }
    assert body["sales"] == {"new_contacts": 3, "deals_won": 1, "revenue": 2500000.0, "win_rate": 0.5}
    assert body["marketing"] == {
        "leads_captured": 2,
        "engagement_events": 0,
        "campaigns_launched": 1,
        "ad_spend": 120000.0,
        "cpl": 30000.0,
    }
    assert body["growth"] == {"audits_completed": 1, "funnels_designed": 0}


async def test_duplicate_events_are_projected_once(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    tenant = uuid.UUID(auth.workspace["id"])
    event = ie.LeadCaptured(
        tenant_id=tenant, source="web_form", external_id=None, full_name=None, email=None, phone=None
    )
    await container.bus.publish(event)
    await container.bus.publish(event)
    body = (await client.get("/api/v1/analytics/overview", headers=auth.headers)).json()
    assert body["marketing"]["leads_captured"] == 1


async def test_timeseries_is_zero_filled(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    tenant = uuid.UUID(auth.workspace["id"])
    await container.bus.publish(
        ie.LeadCaptured(
            tenant_id=tenant, source="web", external_id=None, full_name=None, email=None, phone=None
        )
    )
    old = ie.LeadCaptured(
        tenant_id=tenant, source="web", external_id=None, full_name=None, email=None, phone=None,
        occurred_at=utc_now() - timedelta(days=2),
    )  # fmt: skip
    await container.bus.publish(old)
    points = (
        await client.get("/api/v1/analytics/timeseries?metric=leads_captured&days=7", headers=auth.headers)
    ).json()
    assert len(points) == 7
    assert points[-1] == {"date": utc_now().date().isoformat(), "value": 1.0}
    assert points[-3]["value"] == 1.0
    assert sum(p["value"] for p in points) == 2.0

    bad = await client.get("/api/v1/analytics/timeseries?metric=tasks_on_time", headers=auth.headers)
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "invalid_metric"


async def test_contact_funnel(client: httpx.AsyncClient, auth: AuthContext, container: Container) -> None:
    await seed(container, uuid.UUID(auth.workspace["id"]))
    funnel = (await client.get("/api/v1/analytics/funnel", headers=auth.headers)).json()
    counts = {s["stage"]: s["count"] for s in funnel}
    assert [s["stage"] for s in funnel][:3] == ["subscriber", "lead", "mql"]
    assert counts["lead"] == 2 and counts["customer"] == 1 and counts["subscriber"] == 0


async def test_points_feed_gamification_kpis(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    tenant = uuid.UUID(auth.workspace["id"])
    await container.bus.publish(
        ie.CampaignLaunched(
            tenant_id=tenant,
            actor_id=uuid.UUID(auth.user["id"]),
            campaign_id=uuid.uuid4(),
            name="X",
            channel="email",
        )
    )
    body = (await client.get("/api/v1/analytics/overview", headers=auth.headers)).json()
    assert body["gamification"] == {"points_awarded": 30, "active_players": 1}


async def test_insights_use_llm_when_valid(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    assert isinstance(container.llm, FakeLLMClient)
    container.llm.canned["analytics.insights"] = {
        "summary": "Buen mes",
        "highlights": ["Más leads"],
        "risks": [],
        "recommendations": ["Lanzar nurturing"],
    }
    resp = await client.post("/api/v1/analytics/insights", headers=auth.headers, json={"days": 14})
    assert resp.status_code == 200
    assert resp.json() == {
        "summary": "Buen mes",
        "highlights": ["Más leads"],
        "risks": [],
        "recommendations": ["Lanzar nurturing"],
    }
    assert "KPIs del periodo" in container.llm.calls[-1].prompt


@pytest.mark.parametrize("canned", ["esto no es json", {"summary": 3}, ["lista"]])
async def test_insights_fall_back_to_rules(
    client: httpx.AsyncClient, auth: AuthContext, container: Container, canned: object
) -> None:
    await seed(container, uuid.UUID(auth.workspace["id"]))
    assert isinstance(container.llm, FakeLLMClient)
    container.llm.canned["analytics.insights"] = canned
    body = (await client.post("/api/v1/analytics/insights", headers=auth.headers)).json()
    assert body["summary"].startswith("Periodo")
    assert any("limpiezas completadas" in h for h in body["highlights"])
    assert any("puntualidad" in r for r in body["risks"])


async def test_tenant_isolation_and_permissions(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    await seed(container, uuid.UUID(auth.workspace["id"]))
    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    body = (await client.get("/api/v1/analytics/overview", headers=other.headers)).json()
    assert body["operations"]["tasks_completed"] == 0

    await client.post(
        "/api/v1/workspace/members",
        headers=auth.headers,
        json={
            "name": "Inv",
            "role": "property_owner",
            "temporary_password": "Temporal12345",
            "email": "inv@acme.co",
        },
    )
    from tests.conftest import login_as

    investor = await login_as(client, "inv@acme.co", "Temporal12345")
    assert (await client.get("/api/v1/analytics/overview", headers=investor)).status_code == 403
    assert (await client.get("/api/v1/analytics/overview?days=0", headers=auth.headers)).status_code == 422


def test_rule_based_insights_empty_period() -> None:
    now = utc_now()
    report = InsightReport.rule_based(Overview.compute(now - timedelta(days=7), now, {}, 0))
    assert report.highlights == ["Aún no hay suficiente actividad en el periodo."]
    assert report.recommendations
