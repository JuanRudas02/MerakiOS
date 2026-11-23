from __future__ import annotations

import json
import uuid
from decimal import Decimal

import httpx
from pydantic import SecretStr

from oneheavy.modules.meta.application.webhooks import compute_signature
from oneheavy.modules.meta.domain.model import hash_email
from oneheavy.modules.meta.infrastructure.graph import FakeMetaGraphGateway
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container
from tests.conftest import AuthContext, login_as, register_workspace

CONNECTION = {
    "ad_account_id": "act_1234567890",
    "access_token": "EAAB-super-secret-token-4321",
    "page_id": "998877",
    "pixel_id": "556677",
}


async def connect(
    client: httpx.AsyncClient, headers: dict[str, str], **overrides: str | None
) -> httpx.Response:
    resp = await client.put("/api/v1/meta/connection", headers=headers, json={**CONNECTION, **overrides})
    assert resp.status_code == 200, resp.text
    return resp


async def member(client: httpx.AsyncClient, auth: AuthContext, role: str, email: str) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/workspace/members",
        headers=auth.headers,
        json={"name": role.title(), "role": role, "temporary_password": "Temporal12345", "email": email},
    )
    assert resp.status_code == 201, resp.text
    return await login_as(client, email, "Temporal12345")


def published(container: Container, kind: type) -> list:
    return [e for e in container.bus.published if isinstance(e, kind)]  # type: ignore[attr-defined]


def gateway(container: Container) -> FakeMetaGraphGateway:
    gw = container.extras["meta.graph"]
    assert isinstance(gw, FakeMetaGraphGateway)
    return gw


async def test_connection_lifecycle_never_exposes_token(client: httpx.AsyncClient, auth: AuthContext) -> None:
    empty = await client.get("/api/v1/meta/connection", headers=auth.headers)
    assert empty.json() == {
        "connected": False,
        "ad_account_id": None,
        "page_id": None,
        "pixel_id": None,
        "last_sync_at": None,
    }
    resp = await connect(client, auth.headers)
    assert resp.json()["connected"] is True
    assert resp.json()["ad_account_id"] == "1234567890"
    assert "EAAB" not in resp.text
    again = await client.get("/api/v1/meta/connection", headers=auth.headers)
    assert "EAAB" not in again.text and again.json()["pixel_id"] == "556677"


async def test_sync_requires_connection(client: httpx.AsyncClient, auth: AuthContext) -> None:
    resp = await client.post("/api/v1/meta/sync", headers=auth.headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "meta_not_connected"


async def test_sync_insights_alerts_and_queries(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    await connect(client, auth.headers)
    resp = await client.post("/api/v1/meta/sync?days=14", headers=auth.headers)
    assert resp.json() == {"campaigns": 3, "days": 14}

    synced = published(container, ie.AdInsightsSynced)
    assert len(synced) == 14 and all(e.spend > 0 for e in synced)
    anomalies = published(container, ie.AdPerformanceAnomalyDetected)
    assert [a.metric for a in anomalies] == ["ctr"]
    assert anomalies[0].campaign_ref == "Remarketing · Carrusel"

    # Re-sincronizar es idempotente: no duplica alertas.
    await client.post("/api/v1/meta/sync?days=14", headers=auth.headers)
    alerts = (await client.get("/api/v1/meta/alerts", headers=auth.headers)).json()
    assert len(alerts) == 1 and alerts[0]["severity"] == "critical" and alerts[0]["message"]

    campaigns = (await client.get("/api/v1/meta/campaigns?days=30", headers=auth.headers)).json()
    assert len(campaigns["items"]) == 3
    leads_campaign = next(c for c in campaigns["items"] if c["objective"] == "OUTCOME_LEADS")
    assert leads_campaign["leads"] > 0 and leads_campaign["cpl"] > 0
    totals = campaigns["totals"]
    assert totals["spend"] == round(sum(c["spend"] for c in campaigns["items"]), 2)
    assert set(campaigns["items"][0]) >= {"id", "external_id", "ctr", "cpc", "cpm", "roas", "conversions"}

    daily = (await client.get("/api/v1/meta/insights/daily?days=30", headers=auth.headers)).json()
    assert len(daily) == 14
    assert set(daily[0]) == {"date", "spend", "impressions", "clicks", "leads"}

    conn = (await client.get("/api/v1/meta/connection", headers=auth.headers)).json()
    assert conn["last_sync_at"] is not None


async def test_permissions_marketer_allowed_staff_forbidden(
    client: httpx.AsyncClient, auth: AuthContext
) -> None:
    marketer = await member(client, auth, "marketer", "mkt@acme.co")
    assert (await client.get("/api/v1/meta/connection", headers=marketer)).status_code == 200
    staff = await member(client, auth, "staff", "staff@acme.co")
    for method, url in [
        ("get", "/api/v1/meta/connection"),
        ("post", "/api/v1/meta/sync"),
        ("get", "/api/v1/meta/alerts"),
    ]:
        assert (await client.request(method, url, headers=staff)).status_code == 403
    assert (await client.get("/api/v1/meta/campaigns")).status_code == 401


async def test_tenant_isolation(client: httpx.AsyncClient, auth: AuthContext) -> None:
    await connect(client, auth.headers)
    await client.post("/api/v1/meta/sync?days=7", headers=auth.headers)
    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    assert (await client.get("/api/v1/meta/campaigns", headers=other.headers)).json()["items"] == []
    assert (await client.get("/api/v1/meta/alerts", headers=other.headers)).json() == []
    # La misma página no puede quedar conectada a otro workspace.
    resp = await client.put("/api/v1/meta/connection", headers=other.headers, json=CONNECTION)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "page_already_connected"


async def test_test_lead_publishes_lead_captured(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    resp = await client.post(
        "/api/v1/meta/leads/test",
        headers=auth.headers,
        json={"full_name": "Carla Lead", "email": "carla@x.co"},
    )
    assert resp.json() == {"ok": True}
    [lead] = published(container, ie.LeadCaptured)
    assert lead.source == "meta_lead_ads" and lead.email == "carla@x.co"
    assert str(lead.tenant_id) == auth.workspace["id"]
    bad = await client.post("/api/v1/meta/leads/test", headers=auth.headers, json={"full_name": "Sin datos"})
    assert bad.status_code == 422


async def test_webhook_verification(client: httpx.AsyncClient, container: Container) -> None:
    container.settings.meta_verify_token = SecretStr("verify-me")
    ok = await client.get(
        "/api/v1/meta/webhooks",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"},
    )
    assert ok.status_code == 200 and ok.text == "42"
    bad = await client.get(
        "/api/v1/meta/webhooks",
        params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "42"},
    )
    assert bad.status_code == 401


async def test_lead_ads_webhook_routes_lead_to_tenant(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    container.settings.meta_app_secret = SecretStr("app-secret")
    await connect(client, auth.headers)
    body = json.dumps(
        {
            "object": "page",
            "entry": [
                {
                    "id": "998877",
                    "changes": [{"field": "leadgen", "value": {"leadgen_id": "L-1", "page_id": "998877"}}],
                },
                {
                    "id": "000",
                    "changes": [{"field": "leadgen", "value": {"leadgen_id": "L-2", "page_id": "000"}}],
                },
            ],
        }
    ).encode()

    rejected = await client.post(
        "/api/v1/meta/webhooks", content=body, headers={"X-Hub-Signature-256": "sha256=bad"}
    )
    assert rejected.status_code == 401
    assert published(container, ie.LeadCaptured) == []

    resp = await client.post(
        "/api/v1/meta/webhooks",
        content=body,
        headers={
            "X-Hub-Signature-256": compute_signature("app-secret", body),
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    [lead] = published(container, ie.LeadCaptured)  # la página desconocida se ignora
    assert lead.external_id == "L-1" and lead.email == "lead-L-1@example.com"
    assert str(lead.tenant_id) == auth.workspace["id"]
    assert lead.answers == {"presupuesto": "5-10M"}


async def test_conversions_api_on_deal_won_and_qualified_lead(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    await connect(client, auth.headers)
    tenant = uuid.UUID(auth.workspace["id"])
    contact_id = uuid.uuid4()
    await container.bus.publish(
        ie.ContactCreated(
            tenant_id=tenant, contact_id=contact_id, email="Buyer@Acme.co", phone=None, source="manual"
        )
    )
    await container.bus.publish(
        ie.DealWon(
            tenant_id=tenant,
            deal_id=uuid.uuid4(),
            contact_id=contact_id,
            owner_id=None,
            amount=Decimal("1500000"),
            currency="COP",
        )
    )
    await container.bus.publish(
        ie.ContactLifecycleChanged(tenant_id=tenant, contact_id=contact_id, from_stage="lead", to_stage="mql")
    )
    await container.bus.publish(
        ie.ContactLifecycleChanged(
            tenant_id=tenant, contact_id=contact_id, from_stage="mql", to_stage="customer"
        )
    )
    sent = gateway(container).sent_events
    assert [(pixel, e.event_name) for pixel, e in sent] == [("556677", "Purchase"), ("556677", "Lead")]
    purchase = sent[0][1]
    assert purchase.user_data["em"] == [hash_email("buyer@acme.co")]
    assert purchase.custom_data == {"value": 1500000.0, "currency": "COP"}


async def test_conversions_skipped_without_pixel(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    await connect(client, auth.headers, pixel_id=None)
    await container.bus.publish(
        ie.DealWon(
            tenant_id=uuid.UUID(auth.workspace["id"]),
            deal_id=uuid.uuid4(),
            contact_id=None,
            owner_id=None,
            amount=Decimal("10"),
            currency="COP",
        )
    )
    assert gateway(container).sent_events == []
