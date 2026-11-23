from __future__ import annotations

import httpx

from oneheavy.shared.application.ports import LLMClient, LLMRequest
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.errors import ExternalServiceError
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.llm import FakeLLMClient
from tests.conftest import AuthContext, login_as, register_workspace

AUDIT = {
    "avatar": "Administrador de 20 apartamentos en Airbnb",
    "pain_points": ["Coordinar limpiezas por WhatsApp"],
    "desires": ["Operación sin fricción"],
    "awareness_level": "problem_aware",
    "jobs_to_be_done": ["Que cada check-in esté impecable"],
    "competitors": ["Guesty"],
    "market_opportunity": "LATAM sin herramientas en español",
}


class FailingLLM(LLMClient):
    async def complete(self, request: LLMRequest) -> str:
        raise ExternalServiceError("El proveedor de IA no respondió")


def fake_llm(container: Container) -> FakeLLMClient:
    assert isinstance(container.llm, FakeLLMClient)
    return container.llm


async def create_project(client: httpx.AsyncClient, headers: dict[str, str]) -> dict:
    resp = await client.post(
        "/api/v1/growth/projects",
        headers=headers,
        json={"name": "Stays LATAM", "niche": "property managers Airbnb"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_list_get(client: httpx.AsyncClient, auth: AuthContext) -> None:
    project = await create_project(client, auth.headers)
    assert project["status"] == "draft" and project["audit"] is None and project["funnel"] is None
    listed = (await client.get("/api/v1/growth/projects", headers=auth.headers)).json()
    assert [p["id"] for p in listed] == [project["id"]]
    fetched = await client.get(f"/api/v1/growth/projects/{project['id']}", headers=auth.headers)
    assert fetched.json()["name"] == "Stays LATAM"
    invalid = await client.post(
        "/api/v1/growth/projects", headers=auth.headers, json={"name": "X", "niche": "y"}
    )
    assert invalid.status_code == 422


async def test_full_flow_audit_funnel_assets(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    fake_llm(container).canned["growth.auditor"] = {"missing_info": False, "report": AUDIT}
    project = await create_project(client, auth.headers)
    pid = project["id"]

    early = await client.post(f"/api/v1/growth/projects/{pid}/funnel", headers=auth.headers)
    assert early.status_code == 422 and early.json()["error"]["code"] == "audit_required"

    resp = await client.post(f"/api/v1/growth/projects/{pid}/audit", headers=auth.headers)
    assert resp.status_code == 202 and resp.json() == {"status": "accepted"}
    audited = (await client.get(f"/api/v1/growth/projects/{pid}", headers=auth.headers)).json()
    assert audited["status"] == "audited"
    assert audited["audit"]["awareness_level"] == "problem_aware"
    assert audited["audit"]["jobs_to_be_done"] == ["Que cada check-in esté impecable"]

    resp = await client.post(f"/api/v1/growth/projects/{pid}/funnel", headers=auth.headers)
    assert resp.status_code == 202
    done = (await client.get(f"/api/v1/growth/projects/{pid}", headers=auth.headers)).json()
    assert done["status"] == "completed"
    types = [n["type"] for n in done["funnel"]["nodes"]]
    assert types[:3] == ["ad", "landing", "optin"]  # problem_aware → embudo educativo
    assert all({"x", "y"} == set(n["position"]) for n in done["funnel"]["nodes"])

    names = [e.event_name for e in container.bus.published]  # type: ignore[attr-defined]
    assert "MarketAuditCompleted" in names and "FunnelDesigned" in names
    funnel_event = next(e for e in container.bus.published if isinstance(e, ie.FunnelDesigned))  # type: ignore[attr-defined]
    assert funnel_event.nodes_count == len(types)

    node_id = done["funnel"]["nodes"][1]["id"]
    assets = await client.post(
        f"/api/v1/growth/projects/{pid}/assets",
        headers=auth.headers,
        json={"kind": "landing", "node_id": node_id},
    )
    assert assets.status_code == 200 and len(assets.json()["assets"]) == 3
    missing_node = await client.post(
        f"/api/v1/growth/projects/{pid}/assets", headers=auth.headers, json={"kind": "ad", "node_id": "nope"}
    )
    assert missing_node.status_code == 404


async def test_assets_require_audit(client: httpx.AsyncClient, auth: AuthContext) -> None:
    project = await create_project(client, auth.headers)
    resp = await client.post(
        f"/api/v1/growth/projects/{project['id']}/assets", headers=auth.headers, json={"kind": "email"}
    )
    assert resp.status_code == 422


async def test_audit_failure_marks_project_failed(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    project = await create_project(client, auth.headers)
    container.llm = FailingLLM()
    resp = await client.post(f"/api/v1/growth/projects/{project['id']}/audit", headers=auth.headers)
    assert resp.status_code == 202
    failed = (await client.get(f"/api/v1/growth/projects/{project['id']}", headers=auth.headers)).json()
    assert failed["status"] == "failed" and failed["error"] == "El proveedor de IA no respondió"
    # Un proyecto fallido se puede re-auditar.
    container.llm = FakeLLMClient()
    await client.post(f"/api/v1/growth/projects/{project['id']}/audit", headers=auth.headers)
    retried = (await client.get(f"/api/v1/growth/projects/{project['id']}", headers=auth.headers)).json()
    assert retried["status"] == "audited" and retried["error"] is None


async def test_permissions(client: httpx.AsyncClient, auth: AuthContext) -> None:
    for role, email in [("marketer", "mkt@acme.co"), ("staff", "staff@acme.co")]:
        await client.post(
            "/api/v1/workspace/members",
            headers=auth.headers,
            json={"name": role, "role": role, "temporary_password": "Temporal12345", "email": email},
        )
    marketer = await login_as(client, "mkt@acme.co", "Temporal12345")
    assert (
        await client.post("/api/v1/growth/projects", headers=marketer, json={"name": "Mkt", "niche": "nicho"})
    ).status_code == 201
    staff = await login_as(client, "staff@acme.co", "Temporal12345")
    assert (await client.get("/api/v1/growth/projects", headers=staff)).status_code == 403
    assert (await client.get("/api/v1/growth/projects")).status_code == 401


async def test_tenant_isolation(client: httpx.AsyncClient, auth: AuthContext) -> None:
    project = await create_project(client, auth.headers)
    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    assert (await client.get("/api/v1/growth/projects", headers=other.headers)).json() == []
    for method, suffix in [("get", ""), ("post", "/audit"), ("post", "/funnel")]:
        resp = await client.request(
            method, f"/api/v1/growth/projects/{project['id']}{suffix}", headers=other.headers
        )
        assert resp.status_code == 404
