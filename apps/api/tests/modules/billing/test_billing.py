from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from oneheavy.modules.billing.domain.signatures import event_checksum, integrity_signature, verify_event
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container
from tests.conftest import AuthContext, login_as

EVENTS_SECRET = "test_events_secret"
INTEGRITY_SECRET = "test_integrity_secret"


def wompi_event(
    reference: str, amount: int, status: str = "APPROVED", tx_id: str = "1234-1610641025-49201"
) -> dict:
    event: dict[str, Any] = {
        "event": "transaction.updated",
        "data": {
            "transaction": {
                "id": tx_id,
                "amount_in_cents": amount,
                "reference": reference,
                "customer_email": "ceo@acme.co",
                "currency": "COP",
                "payment_method_type": "NEQUI",
                "status": status,
            }
        },
        "environment": "test",
        "signature": {"properties": ["transaction.id", "transaction.status", "transaction.amount_in_cents"]},
        "timestamp": 1530291411,
        "sent_at": "2026-11-22T16:45:05.000Z",
    }
    event["signature"]["checksum"] = event_checksum(event, EVENTS_SECRET).upper()
    return event


@pytest.fixture
def wompi(container: Container) -> Container:
    container.settings.wompi_public_key = "pub_test_123"
    container.settings.wompi_integrity_secret = SecretStr(INTEGRITY_SECRET)
    container.settings.wompi_events_secret = SecretStr(EVENTS_SECRET)
    return container


class TestSignatures:
    def test_integrity_signature_matches_wompi_formula(self) -> None:
        expected = hashlib.sha256(b"REF-1" + b"8900000" + b"COP" + b"secret").hexdigest()
        assert integrity_signature("REF-1", 8900000, "COP", "secret") == expected

    def test_event_checksum_matches_wompi_formula(self) -> None:
        event = wompi_event("REF-1", 100)
        raw = "1234-1610641025-49201" + "APPROVED" + "100" + "1530291411" + EVENTS_SECRET
        assert event["signature"]["checksum"] == hashlib.sha256(raw.encode()).hexdigest().upper()
        assert verify_event(event, EVENTS_SECRET)
        assert verify_event(event, EVENTS_SECRET, header_checksum=event["signature"]["checksum"])

    def test_tampered_or_wrong_secret_fails(self) -> None:
        event = wompi_event("REF-1", 100)
        assert not verify_event(event, "otro-secreto")
        event["data"]["transaction"]["amount_in_cents"] = 1
        assert not verify_event(event, EVENTS_SECRET)

    def test_header_mismatch_and_malformed_fail(self) -> None:
        event = wompi_event("REF-1", 100)
        assert not verify_event(event, EVENTS_SECRET, header_checksum="deadbeef")
        assert not verify_event({"data": {}}, EVENTS_SECRET)
        broken = wompi_event("REF-1", 100)
        broken["signature"]["properties"] = ["transaction.nope"]
        assert not verify_event(broken, EVENTS_SECRET)


async def test_plans_are_public(client: httpx.AsyncClient) -> None:
    plans = (await client.get("/api/v1/billing/plans")).json()
    assert [p["key"] for p in plans] == ["starter", "growth", "scale"]
    assert plans[1]["price_cop"] == 249000
    assert set(plans[0]["limits"]) == {"properties", "contacts", "seats"}


async def test_default_subscription_is_trial(client: httpx.AsyncClient, auth: AuthContext) -> None:
    sub = (await client.get("/api/v1/billing/subscription", headers=auth.headers)).json()
    assert sub == {"plan": "trial", "status": "trialing", "current_period_end": None}


async def test_checkout_requires_configuration(client: httpx.AsyncClient, auth: AuthContext) -> None:
    resp = await client.post("/api/v1/billing/checkout", headers=auth.headers, json={"plan": "growth"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payments_disabled"


async def test_checkout_and_approved_webhook_activate_plan(
    client: httpx.AsyncClient, auth: AuthContext, wompi: Container
) -> None:
    resp = await client.post("/api/v1/billing/checkout", headers=auth.headers, json={"plan": "growth"})
    assert resp.status_code == 200, resp.text
    co = resp.json()
    assert co["reference"].startswith("1H-") and "-GROWTH-" in co["reference"]
    assert co["amount_in_cents"] == 24_900_000
    assert co["public_key"] == "pub_test_123"
    assert co["redirect_url"].endswith("/app/ajustes/facturacion")
    assert co["signature"] == integrity_signature(
        co["reference"], co["amount_in_cents"], "COP", INTEGRITY_SECRET
    )

    event = wompi_event(co["reference"], co["amount_in_cents"])
    hook = await client.post(
        "/api/v1/billing/webhooks/wompi",
        content=json.dumps(event),
        headers={"X-Event-Checksum": event["signature"]["checksum"]},
    )
    assert hook.status_code == 200, hook.text
    assert hook.json() == {"ok": True, "outcome": "processed"}

    me = (await client.get("/api/v1/auth/me", headers=auth.headers)).json()
    assert me["workspace"]["plan"] == "growth"
    sub = (await client.get("/api/v1/billing/subscription", headers=auth.headers)).json()
    assert sub["plan"] == "growth" and sub["status"] == "active" and sub["current_period_end"]

    approved = [e for e in wompi.bus.published if isinstance(e, ie.PaymentApproved)]  # type: ignore[attr-defined]
    assert len(approved) == 1 and approved[0].plan == "growth"

    retry = await client.post("/api/v1/billing/webhooks/wompi", json=event)
    assert retry.json()["outcome"] == "duplicate"
    assert len([e for e in wompi.bus.published if isinstance(e, ie.PaymentApproved)]) == 1  # type: ignore[attr-defined]


async def test_pending_then_approved(client: httpx.AsyncClient, auth: AuthContext, wompi: Container) -> None:
    co = (
        await client.post("/api/v1/billing/checkout", headers=auth.headers, json={"plan": "starter"})
    ).json()
    pending = await client.post(
        "/api/v1/billing/webhooks/wompi", json=wompi_event(co["reference"], co["amount_in_cents"], "PENDING")
    )
    assert pending.json()["outcome"] == "processed"
    sub = (await client.get("/api/v1/billing/subscription", headers=auth.headers)).json()
    assert sub["status"] == "trialing"
    approved = await client.post(
        "/api/v1/billing/webhooks/wompi", json=wompi_event(co["reference"], co["amount_in_cents"], "APPROVED")
    )
    assert approved.json()["outcome"] == "processed"
    me = (await client.get("/api/v1/auth/me", headers=auth.headers)).json()
    assert me["workspace"]["plan"] == "starter"


async def test_tampered_webhook_rejected(
    client: httpx.AsyncClient, auth: AuthContext, wompi: Container
) -> None:
    co = (await client.post("/api/v1/billing/checkout", headers=auth.headers, json={"plan": "scale"})).json()
    event = wompi_event(co["reference"], co["amount_in_cents"])
    event["data"]["transaction"]["status"] = "DECLINED"  # cambia sin recalcular firma
    resp = await client.post("/api/v1/billing/webhooks/wompi", json=event)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_signature"


async def test_unknown_reference_and_amount_mismatch_ignored(
    client: httpx.AsyncClient, auth: AuthContext, wompi: Container
) -> None:
    unknown = await client.post("/api/v1/billing/webhooks/wompi", json=wompi_event("1H-NOPE", 100))
    assert unknown.json()["outcome"] == "ignored"
    co = (await client.post("/api/v1/billing/checkout", headers=auth.headers, json={"plan": "growth"})).json()
    cheap = await client.post("/api/v1/billing/webhooks/wompi", json=wompi_event(co["reference"], 100))
    assert cheap.json()["outcome"] == "ignored"
    me = (await client.get("/api/v1/auth/me", headers=auth.headers)).json()
    assert me["workspace"]["plan"] == "trial"


async def test_unsigned_events_rejected_outside_local(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    container.settings.env = "production"
    resp = await client.post("/api/v1/billing/webhooks/wompi", json={"event": "transaction.updated"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "webhook_unverified"


async def test_billing_requires_permission_and_valid_plan(
    client: httpx.AsyncClient, auth: AuthContext, wompi: Container
) -> None:
    await client.post(
        "/api/v1/workspace/members",
        headers=auth.headers,
        json={"name": "Adm", "role": "admin", "temporary_password": "Temporal12345", "email": "adm@acme.co"},
    )
    admin = await login_as(client, "adm@acme.co", "Temporal12345")
    assert (await client.get("/api/v1/billing/subscription", headers=admin)).status_code == 403
    bad = await client.post("/api/v1/billing/checkout", headers=auth.headers, json={"plan": "platinum"})
    assert bad.status_code == 404
