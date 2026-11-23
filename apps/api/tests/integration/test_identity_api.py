from __future__ import annotations

import httpx

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.messaging import ConsoleMessageSender
from tests.conftest import PASSWORD, AuthContext, login_as, register_workspace


async def test_register_creates_workspace_owner_and_events(
    client: httpx.AsyncClient, container: Container
) -> None:
    ctx = await register_workspace(client)
    assert ctx.user["role"] == "owner"
    assert ctx.workspace["slug"] == "acme-stays"
    names = [e.event_name for e in container.bus.published]  # type: ignore[attr-defined]
    assert names == ["WorkspaceCreated", "UserRegistered"]
    assert isinstance(container.bus.published[1], ie.UserRegistered)  # type: ignore[attr-defined]


async def test_duplicate_email_conflict(client: httpx.AsyncClient) -> None:
    await register_workspace(client)
    resp = await client.post(
        "/api/v1/auth/register",
        json={"workspace_name": "Otro", "owner_name": "X Y", "email": "CEO@acme.co", "password": PASSWORD},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"


async def test_weak_password_rejected(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "workspace_name": "Otro",
            "owner_name": "X Y",
            "email": "x@y.co",
            "password": "soloLetrasLargas",
        },
    )
    assert resp.status_code == 422


async def test_login_and_me(client: httpx.AsyncClient, auth: AuthContext) -> None:
    headers = await login_as(client, "ceo@acme.co")
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["workspace"]["name"] == "Acme Stays"
    assert "billing.manage" in me.json()["user"]["permissions"]


async def test_login_wrong_password_is_generic_401(client: httpx.AsyncClient, auth: AuthContext) -> None:
    resp = await client.post(
        "/api/v1/auth/login", json={"identifier": "ceo@acme.co", "password": "malamala123"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["message"] == "Credenciales inválidas"


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    bad = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


async def test_invite_staff_sends_whatsapp_without_password(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    resp = await client.post(
        "/api/v1/workspace/members",
        headers=auth.headers,
        json={
            "name": "Luz Staff",
            "role": "staff",
            "temporary_password": "Temporal12345",
            "phone": "3109998877",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["username"] == "573109998877"
    sender = container.sender
    assert isinstance(sender, ConsoleMessageSender)
    assert sender.outbox[-1].to == "573109998877"
    assert "Temporal12345" not in sender.outbox[-1].body

    staff_headers = await login_as(client, "573109998877", "Temporal12345")
    forbidden = await client.get("/api/v1/workspace/members", headers=staff_headers)
    assert forbidden.status_code == 403


async def test_admin_cannot_create_admin(client: httpx.AsyncClient, auth: AuthContext) -> None:
    await client.post(
        "/api/v1/workspace/members",
        headers=auth.headers,
        json={"name": "Adm", "role": "admin", "temporary_password": "Temporal12345", "email": "adm@acme.co"},
    )
    admin_headers = await login_as(client, "adm@acme.co", "Temporal12345")
    resp = await client.post(
        "/api/v1/workspace/members",
        headers=admin_headers,
        json={
            "name": "Adm2",
            "role": "admin",
            "temporary_password": "Temporal12345",
            "email": "adm2@acme.co",
        },
    )
    assert resp.status_code == 403


async def test_tenants_are_isolated(client: httpx.AsyncClient, auth: AuthContext) -> None:
    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    members = await client.get("/api/v1/workspace/members", headers=other.headers)
    assert [m["email"] for m in members.json()] == ["boss@globex.co"]


async def test_branding_update(client: httpx.AsyncClient, auth: AuthContext) -> None:
    resp = await client.put(
        "/api/v1/workspace/branding",
        headers=auth.headers,
        json={"business_name": "Acme Pro", "primary_color": "#112233", "whatsapp_instance": "acme-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["business_name"] == "Acme Pro"
    assert resp.json()["whatsapp_instance"] == "acme-01"
