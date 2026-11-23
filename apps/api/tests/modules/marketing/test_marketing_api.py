from __future__ import annotations

import base64
import hashlib
import hmac
import json
import pathlib
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from oneheavy.modules.marketing.infrastructure.mautic import InMemoryMauticGateway
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.llm import FakeLLMClient
from tests.conftest import AuthContext, login_as

TEMP = "Temporal12345"


@pytest.fixture
def mautic(container: Container) -> InMemoryMauticGateway:
    gateway = container.extras["marketing.mautic"]
    assert isinstance(gateway, InMemoryMauticGateway)
    return gateway


@pytest.fixture
def mautic_on(container: Container, mautic: InMemoryMauticGateway) -> InMemoryMauticGateway:
    container.settings.mautic_enabled = True
    return mautic


async def add_contact(client: httpx.AsyncClient, auth: AuthContext, **body: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"first_name": "Ana", "email": "ana@cliente.co"}
    payload.update(body)
    resp = await client.post("/api/v1/crm/contacts", headers=auth.headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()  # type: ignore[no-any-return]


async def test_status_sandbox(client: httpx.AsyncClient, auth: AuthContext) -> None:
    body = (await client.get("/api/v1/marketing/status", headers=auth.headers)).json()
    assert body == {"mautic_enabled": False, "connected": False, "last_sync_at": None, "synced_contacts": 0}


async def test_segments_evaluate_mirrored_audience(client: httpx.AsyncClient, auth: AuthContext) -> None:
    await add_contact(client, auth)
    c2 = await add_contact(client, auth, email="b@cliente.co", source="meta_lead_ads")
    await client.post(f"/api/v1/crm/contacts/{c2['id']}/stage", headers=auth.headers, json={"stage": "sql"})

    seg = await client.post(
        "/api/v1/marketing/segments",
        headers=auth.headers,
        json={"name": "SQL de Meta", "filters": {"stages": ["sql"], "tags": ["source:meta_lead_ads"]}},
    )
    assert seg.status_code == 201, seg.text
    assert seg.json()["contacts_count"] == 1
    assert seg.json()["filters"] == {"stages": ["sql"], "tags": ["source:meta_lead_ads"], "min_score": None}

    everyone = await client.post("/api/v1/marketing/segments", headers=auth.headers, json={"name": "Todos"})
    assert everyone.json()["contacts_count"] == 2

    await add_contact(client, auth, email="c@cliente.co")
    listed = (await client.get("/api/v1/marketing/segments", headers=auth.headers)).json()
    assert {s["name"]: s["contacts_count"] for s in listed} == {"SQL de Meta": 1, "Todos": 3}


async def test_sync_requires_mautic(client: httpx.AsyncClient, auth: AuthContext) -> None:
    seg = (
        await client.post("/api/v1/marketing/segments", headers=auth.headers, json={"name": "Todos"})
    ).json()
    resp = await client.post(f"/api/v1/marketing/segments/{seg['id']}/sync", headers=auth.headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "mautic_disabled"


async def test_mautic_flow_upsert_sync_push_launch(
    client: httpx.AsyncClient, auth: AuthContext, container: Container, mautic_on: InMemoryMauticGateway
) -> None:
    await add_contact(client, auth)
    assert [c.email for c in mautic_on.contacts.values()] == ["ana@cliente.co"]

    # Contacto creado mientras Mautic caía: el espejo se guarda y el sync reintenta.
    mautic_on.healthy = False
    await add_contact(client, auth, email="b@cliente.co")
    mautic_on.healthy = True

    seg = (
        await client.post("/api/v1/marketing/segments", headers=auth.headers, json={"name": "Todos"})
    ).json()
    synced = (await client.post(f"/api/v1/marketing/segments/{seg['id']}/sync", headers=auth.headers)).json()
    assert synced["mautic_id"] is not None and synced["synced_at"] is not None
    assert len(mautic_on.segments[synced["mautic_id"]]["contacts"]) == 2

    status = (await client.get("/api/v1/marketing/status", headers=auth.headers)).json()
    assert status["mautic_enabled"] and status["connected"] and status["synced_contacts"] == 2

    email = (
        await client.post(
            "/api/v1/marketing/emails/generate",
            headers=auth.headers,
            json={"goal": "Agendar demo", "audience": "Property managers", "segment_id": seg["id"]},
        )
    ).json()
    pushed = (await client.post(f"/api/v1/marketing/emails/{email['id']}/push", headers=auth.headers)).json()
    assert pushed["status"] == "pushed"
    assert mautic_on.emails[pushed["mautic_id"]]["segment_id"] == synced["mautic_id"]

    campaign = (
        await client.post(
            "/api/v1/marketing/campaigns/plan",
            headers=auth.headers,
            json={"objective": "Convertir leads de Meta", "segment_id": seg["id"], "duration_days": 14},
        )
    ).json()
    launched = (
        await client.post(f"/api/v1/marketing/campaigns/{campaign['id']}/launch", headers=auth.headers)
    ).json()
    assert launched["status"] == "active"
    created = mautic_on.campaigns[launched["mautic_id"]]
    assert created["published"] is True
    email_days = sorted(st["day"] for st in campaign["steps"] if st["channel"] == "email")
    events = created["payload"]["events"]
    assert len(events) == len(email_days) >= 1  # un paso de Mautic por cada email del plan
    assert events[0]["triggerMode"] == "immediate" or email_days[0] > 1
    assert created["payload"]["lists"] == [{"id": synced["mautic_id"]}]
    step_emails = [mautic_on.emails[e["properties"]["email"]] for e in events]
    assert all(e["published"] and e["segment_id"] is None for e in step_emails)  # plantillas publicadas
    assert all("{unsubscribe_url}" in e["html"] for e in step_emails)
    launched_events = [e for e in container.bus.published if isinstance(e, ie.CampaignLaunched)]  # type: ignore[attr-defined]
    assert len(launched_events) == 1 and launched_events[0].name == campaign["name"]

    again = await client.post(f"/api/v1/marketing/campaigns/{campaign['id']}/launch", headers=auth.headers)
    assert again.status_code == 422


async def test_generate_email_sanitizes_ai_html(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    assert isinstance(container.llm, FakeLLMClient)
    container.llm.canned["marketing.email"] = {
        "subject": "Tu operación en piloto automático",
        "preheader": "Menos WhatsApp manual, más reservas",
        "body_html": '<p onclick="x()">Hola</p><script>steal()</script><a href="javascript:alert(1)">mal</a>',
        "body_text": "Hola",
    }
    resp = await client.post(
        "/api/v1/marketing/emails/generate",
        headers=auth.headers,
        json={"goal": "Agendar demo", "audience": "Administradores Airbnb", "tone": "directo"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["subject"] == "Tu operación en piloto automático"
    assert "script" not in body["body_html"] and "onclick" not in body["body_html"]
    assert "javascript" not in body["body_html"]
    assert body["status"] == "draft"
    request = container.llm.calls[-1]
    assert "Administradores Airbnb" in request.prompt and request.metadata["task"] == "marketing.email"

    listed = (await client.get("/api/v1/marketing/emails", headers=auth.headers)).json()
    assert [e["id"] for e in listed] == [body["id"]]


async def test_generate_email_falls_back_without_ai(client: httpx.AsyncClient, auth: AuthContext) -> None:
    resp = await client.post(
        "/api/v1/marketing/emails/generate",
        headers=auth.headers,
        json={"goal": "Reactivar clientes", "audience": "Ex clientes"},
    )
    assert resp.status_code == 201
    assert "{unsubscribe_url}" in resp.json()["body_html"]


async def test_plan_campaign_uses_ai_steps(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    assert isinstance(container.llm, FakeLLMClient)
    container.llm.canned["marketing.campaign"] = {
        "name": "Nurturing Stays",
        "steps": [
            {"day": 5, "channel": "whatsapp", "subject": "Caso de éxito", "intent": "Prueba social"},
            {"day": 0, "channel": "email", "subject": "Bienvenida", "intent": "Activar"},
            {"day": 40, "channel": "email", "subject": "Fuera de rango", "intent": "x"},
        ],
    }
    resp = await client.post(
        "/api/v1/marketing/campaigns/plan",
        headers=auth.headers,
        json={"objective": "Onboarding", "duration_days": 7},
    )
    body = resp.json()
    assert body["name"] == "Nurturing Stays" and body["status"] == "planned"
    assert [s["day"] for s in body["steps"]] == [0, 5]

    launched = await client.post(f"/api/v1/marketing/campaigns/{body['id']}/launch", headers=auth.headers)
    assert launched.json()["mautic_id"] is None  # sin Mautic se lanza igual (canal propio)
    assert len((await client.get("/api/v1/marketing/campaigns", headers=auth.headers)).json()) == 1


async def test_unknown_segment_is_404(client: httpx.AsyncClient, auth: AuthContext) -> None:
    import uuid

    resp = await client.post(
        "/api/v1/marketing/campaigns/plan",
        headers=auth.headers,
        json={"objective": "x y z", "duration_days": 7, "segment_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


async def test_mautic_webhook_records_engagement_in_crm(
    client: httpx.AsyncClient, auth: AuthContext, container: Container, mautic_on: InMemoryMauticGateway
) -> None:
    contact = await add_contact(client, auth)
    mautic_id = next(iter(mautic_on.contacts))
    container.settings.mautic_webhook_secret = SecretStr("s3cr3t")

    payload = {
        "mautic.email_on_open": [{"stat": {"lead": {"id": mautic_id}}}],
        "mautic.form_on_submit": [{"submission": {"lead": {"id": mautic_id}}}],
        "mautic.page_on_hit": [{"hit": {"lead": {"id": 9999}}}],
    }
    body = json.dumps(payload).encode()

    def signed(secret: str, data: bytes = body) -> dict[str, str]:
        # Igual que Mautic 5: base64(HMAC-SHA256(cuerpo exacto, secreto del webhook))
        sig = base64.b64encode(hmac.new(secret.encode(), data, hashlib.sha256).digest()).decode()
        return {"Webhook-Signature": sig, "Content-Type": "application/json"}

    url = "/api/v1/marketing/webhooks/mautic"
    assert (await client.post(url, content=body, headers=signed("otro-secreto"))).status_code == 401
    assert (await client.post(url, content=body)).status_code == 401  # sin firma
    tampered = body.replace(b"9999", b"9998")
    assert (await client.post(url, content=tampered, headers=signed("s3cr3t"))).status_code == 401

    ok = await client.post(url, content=body, headers=signed("s3cr3t"))
    assert ok.json() == {"ok": True, "processed": 2, "skipped": 1}

    updated = (await client.get(f"/api/v1/crm/contacts/{contact['id']}", headers=auth.headers)).json()
    assert updated["score"] == contact["score"] + 12
    timeline = (
        await client.get(f"/api/v1/crm/contacts/{contact['id']}/timeline", headers=auth.headers)
    ).json()
    assert {t["summary"] for t in timeline if t["kind"] == "marketing"} == {
        "Abrió un email (+2 pts)",
        "Envió un formulario (+10 pts)",
    }

    seg = await client.post(
        "/api/v1/marketing/segments",
        headers=auth.headers,
        json={"name": "Enganchados", "filters": {"min_score": 12}},
    )
    assert seg.json()["contacts_count"] == 1


async def test_webhook_by_email_with_tenant_hint(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    contact = await add_contact(client, auth)
    payload = {
        "mautic.page_on_hit": [
            {
                "hit": {
                    "email": {"id": 3},
                    "lead": {"fields": {"core": {"email": {"value": "ANA@cliente.co"}}}},
                }
            }
        ]
    }
    no_hint = await client.post("/api/v1/marketing/webhooks/mautic", json=payload)
    assert no_hint.json()["processed"] == 0
    hinted = await client.post(
        "/api/v1/marketing/webhooks/mautic", json=payload, params={"tenant_id": auth.workspace["id"]}
    )
    assert hinted.json()["processed"] == 1
    updated = (await client.get(f"/api/v1/crm/contacts/{contact['id']}", headers=auth.headers)).json()
    assert updated["score"] == contact["score"] + 5


async def test_webhook_requires_secret_outside_local(client: httpx.AsyncClient, container: Container) -> None:
    container.settings.env = "production"
    resp = await client.post("/api/v1/marketing/webhooks/mautic", json={})
    assert resp.status_code == 401


async def test_marketing_requires_permission(client: httpx.AsyncClient, auth: AuthContext) -> None:
    for role, expected in (("sales", 403), ("marketer", 200)):
        await client.post(
            "/api/v1/workspace/members",
            headers=auth.headers,
            json={"name": role, "role": role, "temporary_password": TEMP, "email": f"{role}@acme.co"},
        )
        headers = await login_as(client, f"{role}@acme.co", TEMP)
        assert (await client.get("/api/v1/marketing/segments", headers=headers)).status_code == expected


async def test_marketing_tenant_isolation(client: httpx.AsyncClient, auth: AuthContext) -> None:
    from tests.conftest import register_workspace

    seg = (
        await client.post("/api/v1/marketing/segments", headers=auth.headers, json={"name": "Todos"})
    ).json()
    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    assert (await client.get("/api/v1/marketing/segments", headers=other.headers)).json() == []
    container_404 = await client.post(
        "/api/v1/marketing/emails/generate",
        headers=other.headers,
        json={"goal": "x y z", "audience": "a b c", "segment_id": seg["id"]},
    )
    assert container_404.status_code == 404


FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _sign(body: bytes, secret: str) -> dict[str, str]:
    sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    return {"Webhook-Signature": sig, "Content-Type": "application/json"}


@pytest.mark.parametrize(
    ("fixture", "summary"),
    [("real_email_on_open.json", "Abrió un email"), ("real_form_on_submit.json", "Envió un formulario")],
)
async def test_real_mautic_payloads_are_processed(
    client: httpx.AsyncClient,
    auth: AuthContext,
    container: Container,
    mautic_on: InMemoryMauticGateway,
    fixture: str,
    summary: str,
) -> None:
    """Cuerpos capturados de un Mautic 5 real (anonimizados). Mautic había fusionado
    el contacto y cambiado su id: 1heavy lo reconoce por email y re-vincula el id."""
    contact = await add_contact(client, auth)
    container.settings.mautic_webhook_secret = SecretStr("s3cr3t")
    body = (FIXTURES / fixture).read_bytes()
    resp = await client.post(
        "/api/v1/marketing/webhooks/mautic",
        content=body,
        params={"tenant_id": auth.workspace["id"]},
        headers=_sign(body, "s3cr3t"),
    )
    assert resp.json() == {"ok": True, "processed": 1, "skipped": 0}, resp.text
    timeline = (
        await client.get(f"/api/v1/crm/contacts/{contact['id']}/timeline", headers=auth.headers)
    ).json()
    assert any(t["summary"].startswith(summary) for t in timeline if t["kind"] == "marketing")
    real_lead_id = next(iter(json.loads(body).values()))[0]
    real_lead_id = (real_lead_id.get("stat") or real_lead_id.get("submission"))["lead"]["id"]
    updated = (await client.get(f"/api/v1/crm/contacts/{contact['id']}", headers=auth.headers)).json()
    assert updated["mautic_id"] == real_lead_id  # re-vinculado tras la fusión en Mautic
