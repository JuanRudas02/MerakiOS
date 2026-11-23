"""Contrato contra un Mautic 5 REAL (no simulado).

Se ejecuta sólo si existen MAUTIC_TEST_URL, MAUTIC_TEST_USER y MAUTIC_TEST_PASSWORD:
    MAUTIC_TEST_URL=http://localhost:8081 MAUTIC_TEST_USER=admin MAUTIC_TEST_PASSWORD=... pytest tests/integration/test_mautic_live.py
En CI se omite. Crea datos en esa instancia: úsese sólo con un Mautic de pruebas.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

from oneheavy.modules.marketing.application.ports import MauticCampaignEmail, MauticContactData
from oneheavy.modules.marketing.infrastructure.mautic import HttpMauticGateway

URL = os.environ.get("MAUTIC_TEST_URL")
USER = os.environ.get("MAUTIC_TEST_USER", "")
PASSWORD = os.environ.get("MAUTIC_TEST_PASSWORD", "")

pytestmark = pytest.mark.skipif(not URL, reason="sin Mautic de pruebas (MAUTIC_TEST_URL)")


@pytest.fixture
def gw() -> HttpMauticGateway:
    assert URL
    return HttpMauticGateway(URL, USER, PASSWORD)


def _get(path: str) -> dict:
    resp = httpx.get(f"{URL}{path}", auth=(USER, PASSWORD), timeout=20)
    resp.raise_for_status()
    return resp.json()


async def test_ping(gw: HttpMauticGateway) -> None:
    assert await gw.ping() is True


async def test_contact_upsert_dedupes_by_email_and_updates(gw: HttpMauticGateway) -> None:
    email = f"live-{uuid.uuid4().hex[:8]}@1heavy.test"
    first = await gw.upsert_contact(
        MauticContactData(
            email=email, phone="+573001234567", first_name="Laura", tags=["source:meta_lead_ads"]
        )
    )
    again = await gw.upsert_contact(MauticContactData(email=email, first_name="Laura"))
    assert again == first, "Mautic debe deduplicar por email"

    await gw.upsert_contact(MauticContactData(email=email, last_name="Gómez"), mautic_id=first)
    fields = _get(f"/api/contacts/{first}")["contact"]["fields"]["all"]
    assert fields["email"] == email
    assert fields["firstname"] == "Laura"
    assert fields["lastname"] == "Gómez"
    assert fields["mobile"] == "+573001234567"
    tags = [t["tag"] for t in _get(f"/api/contacts/{first}")["contact"]["tags"]]
    assert "source:meta_lead_ads" in tags


async def test_segment_email_and_campaign_flow(gw: HttpMauticGateway) -> None:
    contact = await gw.upsert_contact(MauticContactData(email=f"seg-{uuid.uuid4().hex[:8]}@1heavy.test"))
    segment = await gw.create_segment("1heavy · prueba en vivo", "Creado por la prueba de contrato")
    await gw.add_contacts_to_segment(segment, [contact])
    members = _get(f"/api/contacts?search=segment:{_get(f'/api/segments/{segment}')['list']['alias']}")
    assert str(contact) in members["contacts"]

    email = await gw.create_email(
        name="Demo 1heavy",
        subject="¿Cuántas horas te roban tus Airbnb?",
        html="<p>Hola {contactfield=firstname}</p>",
        text="Hola {contactfield=firstname}",
        segment_id=segment,
    )
    created = _get(f"/api/emails/{email}")["email"]
    assert created["subject"].startswith("¿Cuántas")
    assert created["emailType"] == "list"

    day1 = await gw.create_email(name="Paso 1", subject="Hola", html="<p>1</p>", text="1", published=True)
    day3 = await gw.create_email(name="Paso 3", subject="Seguimos", html="<p>3</p>", text="3", published=True)
    campaign = await gw.create_campaign(
        name="Campaña 1heavy",
        description="Prueba",
        segment_id=segment,
        emails=[
            MauticCampaignEmail(day=3, name="Día 3 · Seguimos", email_id=day3),
            MauticCampaignEmail(day=1, name="Día 1 · Hola", email_id=day1),
        ],
    )
    await gw.publish_campaign(campaign)
    created = _get(f"/api/campaigns/{campaign}")["campaign"]
    assert created["isPublished"] is True
    by_name = {e["name"]: e for e in created["events"]}
    assert by_name["Día 1 · Hola"]["triggerMode"] == "immediate"
    assert by_name["Día 3 · Seguimos"]["triggerMode"] == "interval"
    assert by_name["Día 3 · Seguimos"]["triggerInterval"] == 2
    assert by_name["Día 3 · Seguimos"]["triggerIntervalUnit"] == "d"
    assert len(created["canvasSettings"]["connections"]) == 2  # visible en el constructor de Mautic
    assert [s["id"] for s in created["lists"]] == [segment]
