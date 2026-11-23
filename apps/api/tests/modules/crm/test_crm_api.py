from __future__ import annotations

import httpx
import pytest

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.llm import FakeLLMClient
from tests.conftest import AuthContext, login_as, register_workspace

TEMP = "Temporal12345"


async def invite(client: httpx.AsyncClient, auth: AuthContext, role: str, email: str) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/workspace/members",
        headers=auth.headers,
        json={"name": f"{role} user", "role": role, "temporary_password": TEMP, "email": email},
    )
    assert resp.status_code == 201, resp.text
    return await login_as(client, email, TEMP)


async def create_contact(
    client: httpx.AsyncClient, headers: dict[str, str], **body: object
) -> dict[str, object]:
    payload: dict[str, object] = {"first_name": "Laura", "email": "laura@cliente.co"}
    payload.update(body)
    resp = await client.post("/api/v1/crm/contacts", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()  # type: ignore[no-any-return]


# ── Contactos ───────────────────────────────────────────────────────────────


async def test_create_contact_and_dedupe(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    c = await create_contact(
        client, auth.headers, last_name="Gómez", phone="300 111 2222", tags=["VIP", " vip "]
    )
    assert c["full_name"] == "Laura Gómez"
    assert c["phone"] == "+573001112222"
    assert c["tags"] == ["vip"]
    assert c["stage"] == "lead"
    assert c["score"] == 30  # 25 perfil + 5 fuente manual
    assert any(isinstance(e, ie.ContactCreated) for e in container.bus.published)  # type: ignore[attr-defined]

    dup = await client.post(
        "/api/v1/crm/contacts", headers=auth.headers, json={"first_name": "Otra", "phone": "+57 300-111-2222"}
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "duplicate_contact"


async def test_contact_requires_email_or_phone(client: httpx.AsyncClient, auth: AuthContext) -> None:
    resp = await client.post("/api/v1/crm/contacts", headers=auth.headers, json={"first_name": "Sin datos"})
    assert resp.status_code == 422


async def test_search_filters_and_pagination(client: httpx.AsyncClient, auth: AuthContext) -> None:
    await create_contact(client, auth.headers, email="a@x.co", company="Acme", tags=["vip"])
    await create_contact(client, auth.headers, first_name="Pedro", email="pedro@y.co", company="Globex")
    await create_contact(client, auth.headers, first_name="Marta", phone="3105556677")

    resp = await client.get("/api/v1/crm/contacts", headers=auth.headers, params={"q": "acme"})
    assert [c["email"] for c in resp.json()["items"]] == ["a@x.co"]

    resp = await client.get("/api/v1/crm/contacts", headers=auth.headers, params={"tag": "VIP"})
    assert resp.json()["total"] == 1

    resp = await client.get("/api/v1/crm/contacts", headers=auth.headers, params={"q": "3105556677"})
    assert resp.json()["items"][0]["first_name"] == "Marta"

    page = await client.get("/api/v1/crm/contacts", headers=auth.headers, params={"size": 2, "page": 2})
    body = page.json()
    assert body["total"] == 3 and body["page"] == 2 and len(body["items"]) == 1


async def test_patch_stage_and_timeline(client: httpx.AsyncClient, auth: AuthContext) -> None:
    c = await create_contact(client, auth.headers)
    url = f"/api/v1/crm/contacts/{c['id']}"

    patched = await client.patch(url, headers=auth.headers, json={"company": "Nueva SAS", "job_title": "CMO"})
    assert patched.json()["company"] == "Nueva SAS"
    assert patched.json()["score"] > c["score"]  # type: ignore[operator]

    bad = await client.post(f"{url}/stage", headers=auth.headers, json={"stage": "customer"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "invalid_stage_transition"

    ok = await client.post(f"{url}/stage", headers=auth.headers, json={"stage": "sql"})
    assert ok.json()["stage"] == "sql"

    act = await client.post(
        f"{url}/activities", headers=auth.headers, json={"kind": "call", "summary": "Demo agendada"}
    )
    assert act.status_code == 201

    timeline = (await client.get(f"{url}/timeline", headers=auth.headers)).json()
    assert timeline[0]["summary"] == "Demo agendada"
    assert {t["kind"] for t in timeline} == {"call", "system"}


async def test_insight_uses_ai_and_falls_back(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    c = await create_contact(client, auth.headers)
    url = f"/api/v1/crm/contacts/{c['id']}/insight"

    fallback = (await client.post(url, headers=auth.headers)).json()
    assert fallback["temperature"] == "cold"
    assert fallback["score"] == c["score"]
    assert "Score" in fallback["explanation"]

    assert isinstance(container.llm, FakeLLMClient)
    container.llm.canned["crm.contact_insight"] = {
        "temperature": "warm",
        "explanation": "Abrió 3 correos esta semana.",
        "next_best_action": "Llamar mañana a las 10am",
        "score": 99,  # el LLM no puede pisar el score determinista
    }
    ai = (await client.post(url, headers=auth.headers)).json()
    assert ai["temperature"] == "warm"
    assert ai["next_best_action"] == "Llamar mañana a las 10am"
    assert ai["score"] == c["score"]


async def test_import_counts_created_merged_skipped(client: httpx.AsyncClient, auth: AuthContext) -> None:
    await create_contact(client, auth.headers, email="ya@existe.co")
    resp = await client.post(
        "/api/v1/crm/contacts/import",
        headers=auth.headers,
        json={
            "contacts": [
                {"first_name": "Nuevo", "email": "nuevo@x.co"},
                {"first_name": "Dup", "email": "YA@existe.co", "company": "Llenada"},
                {"first_name": "Mismo lote", "email": "nuevo@x.co"},
                {"first_name": "Sin canal"},
                {"first_name": "Email roto", "email": "no-es-email"},
            ]
        },
    )
    assert resp.json() == {"created": 1, "merged": 2, "skipped": 2}
    found = await client.get("/api/v1/crm/contacts", headers=auth.headers, params={"q": "ya@existe.co"})
    assert found.json()["items"][0]["company"] == "Llenada"


# ── Pipeline ────────────────────────────────────────────────────────────────


async def test_deal_won_promotes_contact_and_emits_event(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    c = await create_contact(client, auth.headers)
    deal = await client.post(
        "/api/v1/crm/deals",
        headers=auth.headers,
        json={"title": "Plan Growth", "contact_id": c["id"], "amount": 2500000, "currency": "cop"},
    )
    assert deal.status_code == 201, deal.text
    d = deal.json()
    assert d["contact_name"] == "Laura" and d["currency"] == "COP" and d["stage"] == "new"

    pipeline = (await client.get("/api/v1/crm/pipeline", headers=auth.headers)).json()
    assert [s["key"] for s in pipeline["stages"]][-2:] == ["won", "lost"]
    assert pipeline["deals"][0]["id"] == d["id"]

    won = await client.post(f"/api/v1/crm/deals/{d['id']}/move", headers=auth.headers, json={"stage": "won"})
    assert won.json()["closed_at"] is not None
    events = [e for e in container.bus.published if isinstance(e, ie.DealWon)]  # type: ignore[attr-defined]
    assert len(events) == 1 and float(events[0].amount) == 2500000

    contact = (await client.get(f"/api/v1/crm/contacts/{c['id']}", headers=auth.headers)).json()
    assert contact["stage"] == "customer"

    again = await client.post(
        f"/api/v1/crm/deals/{d['id']}/move", headers=auth.headers, json={"stage": "new"}
    )
    assert again.status_code == 422
    patch = await client.patch(f"/api/v1/crm/deals/{d['id']}", headers=auth.headers, json={"title": "x"})
    assert patch.status_code == 422


async def test_deal_lost_and_patch(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    d = (
        await client.post("/api/v1/crm/deals", headers=auth.headers, json={"title": "X", "amount": 10})
    ).json()
    assert d["owner_id"] == auth.user["id"]
    patched = await client.patch(
        f"/api/v1/crm/deals/{d['id']}",
        headers=auth.headers,
        json={"amount": 20.5, "expected_close": "2026-12-31"},
    )
    assert patched.json()["amount"] == 20.5 and patched.json()["expected_close"] == "2026-12-31"
    lost = await client.patch(f"/api/v1/crm/deals/{d['id']}", headers=auth.headers, json={"stage": "lost"})
    assert lost.json()["stage"] == "lost"
    assert any(isinstance(e, ie.DealLost) for e in container.bus.published)  # type: ignore[attr-defined]


async def test_deal_with_foreign_contact_is_404(client: httpx.AsyncClient, auth: AuthContext) -> None:
    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    foreign = await create_contact(client, other.headers)
    resp = await client.post(
        "/api/v1/crm/deals",
        headers=auth.headers,
        json={"title": "X", "amount": 1, "contact_id": foreign["id"]},
    )
    assert resp.status_code == 404


# ── Permisos y aislamiento ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("role", "contacts_status", "deal_status"),
    [("sales", 201, 201), ("marketer", 201, 403), ("staff", 403, 403)],
)
async def test_role_permissions(
    client: httpx.AsyncClient, auth: AuthContext, role: str, contacts_status: int, deal_status: int
) -> None:
    headers = await invite(client, auth, role, f"{role}@acme.co")
    c = await client.post(
        "/api/v1/crm/contacts", headers=headers, json={"first_name": "X", "email": "x@x.co"}
    )
    assert c.status_code == contacts_status
    d = await client.post("/api/v1/crm/deals", headers=headers, json={"title": "X", "amount": 1})
    assert d.status_code == deal_status


async def test_tenant_isolation(client: httpx.AsyncClient, auth: AuthContext) -> None:
    c = await create_contact(client, auth.headers)
    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    assert (await client.get(f"/api/v1/crm/contacts/{c['id']}", headers=other.headers)).status_code == 404
    listing = await client.get("/api/v1/crm/contacts", headers=other.headers)
    assert listing.json()["total"] == 0
    # mismo email en otro workspace NO es duplicado
    await create_contact(client, other.headers)


# ── Eventos de integración ──────────────────────────────────────────────────


async def test_lead_captured_creates_then_merges(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    import uuid

    tenant = uuid.UUID(auth.workspace["id"])
    await container.bus.publish(
        ie.LeadCaptured(
            tenant_id=tenant,
            source="meta_lead_ads",
            external_id="lead-1",
            full_name="Carlos Ruiz Díaz",
            email="CARLOS@mail.co",
            phone=None,
            campaign_ref="cmp-42",
            answers={"presupuesto": "alto"},
        )
    )
    page = (await client.get("/api/v1/crm/contacts", headers=auth.headers)).json()
    assert page["total"] == 1
    contact = page["items"][0]
    assert (contact["first_name"], contact["last_name"]) == ("Carlos", "Ruiz Díaz")
    assert contact["source"] == "meta_lead_ads" and "campaign:cmp-42" in contact["tags"]

    await container.bus.publish(
        ie.LeadCaptured(
            tenant_id=tenant,
            source="whatsapp",
            external_id=None,
            full_name="Carlos",
            email="carlos@mail.co",
            phone="3009998877",
        )
    )
    page = (await client.get("/api/v1/crm/contacts", headers=auth.headers)).json()
    assert page["total"] == 1
    assert page["items"][0]["phone"] == "+573009998877"

    timeline = (
        await client.get(f"/api/v1/crm/contacts/{contact['id']}/timeline", headers=auth.headers)
    ).json()
    assert any("presupuesto: alto" in t["summary"] and t["kind"] == "ads" for t in timeline)

    # Lead sin datos de contacto válidos se ignora sin romper el bus
    await container.bus.publish(
        ie.LeadCaptured(
            tenant_id=tenant, source="web_form", external_id="x", full_name="?", email="roto", phone=None
        )
    )
    assert (await client.get("/api/v1/crm/contacts", headers=auth.headers)).json()["total"] == 1


async def test_engagement_rescores_and_auto_advances_to_mql(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    import uuid

    c = await create_contact(client, auth.headers, phone="3001112222", last_name="Gómez", company="Acme")
    assert c["score"] == 35 and c["stage"] == "lead"
    await container.bus.publish(
        ie.MarketingEngagementRecorded(
            tenant_id=uuid.UUID(auth.workspace["id"]),
            contact_id=None,
            email="laura@cliente.co",
            kind="form_submit",
            points=15,
        )
    )
    updated = (await client.get(f"/api/v1/crm/contacts/{c['id']}", headers=auth.headers)).json()
    assert updated["score"] == 50
    assert updated["stage"] == "mql"
    assert updated["last_activity_at"] is not None
    changes = [e for e in container.bus.published if isinstance(e, ie.ContactLifecycleChanged)]  # type: ignore[attr-defined]
    assert changes[-1].to_stage == "mql"
