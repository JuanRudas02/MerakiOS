"""Flujos de negocio de punta a punta que atraviesan varios bounded contexts.

Verifican la coreografía por eventos (no hay llamadas directas entre módulos):

  Lead-to-customer:  meta → crm → marketing(Mautic) → crm(mautic_id) → analytics → gamification
"""

from __future__ import annotations

import httpx

from oneheavy.shared.infrastructure.container import Container
from tests.conftest import AuthContext


async def test_lead_to_customer_pipeline(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    container.settings.mautic_enabled = True
    h = auth.headers

    # 1. Meta Lead Ads (simulado) → LeadCaptured
    resp = await client.post(
        "/api/v1/meta/leads/test",
        headers=h,
        json={"full_name": "Laura Gómez", "email": "laura@cliente.co", "phone": "3015550000"},
    )
    assert resp.status_code == 200, resp.text

    # 2. CRM creó el contacto con la fuente correcta…
    page = (await client.get("/api/v1/crm/contacts", headers=h, params={"q": "laura"})).json()
    assert page["total"] == 1
    contact = page["items"][0]
    assert contact["source"] == "meta_lead_ads"
    assert contact["first_name"] == "Laura"

    # 3. …marketing lo empujó a Mautic con su nombre y el CRM recibió el mautic_id
    mautic = container.extras["marketing.mautic"]
    assert any(c.first_name == "Laura" for c in mautic.contacts.values())
    detail = (await client.get(f"/api/v1/crm/contacts/{contact['id']}", headers=h)).json()
    assert detail["mautic_id"] is not None

    # 4. Negocio ganado → DealWon
    deal = (
        await client.post(
            "/api/v1/crm/deals",
            headers=h,
            json={"title": "Plan anual", "contact_id": contact["id"], "amount": 4_500_000, "currency": "COP"},
        )
    ).json()
    moved = await client.post(f"/api/v1/crm/deals/{deal['id']}/move", headers=h, json={"stage": "won"})
    assert moved.status_code == 200, moved.text

    # 5. Analítica proyectó los hechos y el embudo usa la etapa real
    overview = (await client.get("/api/v1/analytics/overview", headers=h)).json()
    assert overview["sales"]["new_contacts"] == 1
    assert overview["sales"]["deals_won"] == 1
    assert overview["marketing"]["leads_captured"] == 1
    funnel = {
        row["stage"]: row["count"] for row in (await client.get("/api/v1/analytics/funnel", headers=h)).json()
    }
    assert funnel.get("customer") == 1

    # 6. Gamificación premió al dueño del workspace por cerrar el negocio
    me = (await client.get("/api/v1/gamification/me", headers=h)).json()
    assert me["points"] > 0
