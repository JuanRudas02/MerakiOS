"""Fixtures compartidas.

- `container`: Composition Root con SQLite en memoria, LLM falso y WhatsApp en consola.
- `client`:    httpx.AsyncClient contra la app real (ASGI, sin red).
- `auth`:      registra un workspace y devuelve headers + datos de sesión.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from oneheavy.main import create_app
from oneheavy.shared.infrastructure.config import Settings
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.db import create_schema
from oneheavy.shared.infrastructure.llm import FakeLLMClient
from oneheavy.shared.infrastructure.messaging import ConsoleMessageSender

PASSWORD = "Sup3rSecreta2026"


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    return Settings(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        scheduler_enabled=False,
        login_rate_limit="1000/minute",
        storage_dir=str(tmp_path / "storage"),
        jwt_secret="test-secret-test-secret-test-secret",  # type: ignore[arg-type]
    )


@pytest.fixture
async def container(settings: Settings) -> AsyncIterator[Container]:
    c = Container.from_settings(settings, llm=FakeLLMClient(), sender=ConsoleMessageSender())
    yield c
    await c.engine.dispose()


@pytest.fixture
async def app(settings: Settings, container: Container) -> Any:
    application = create_app(settings, container)
    await create_schema(container.engine)  # el lifespan no corre con ASGITransport
    return application


@pytest.fixture
async def client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@dataclass
class AuthContext:
    headers: dict[str, str]
    user: dict[str, Any]
    workspace: dict[str, Any]


async def register_workspace(
    client: httpx.AsyncClient, email: str = "ceo@acme.co", workspace: str = "Acme Stays"
) -> AuthContext:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "workspace_name": workspace,
            "owner_name": "Ana Owner",
            "email": email,
            "password": PASSWORD,
            "phone": "3001234567",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return AuthContext({"Authorization": f"Bearer {body['access_token']}"}, body["user"], body["workspace"])


async def login_as(client: httpx.AsyncClient, identifier: str, password: str = PASSWORD) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def auth(client: httpx.AsyncClient) -> AuthContext:
    return await register_workspace(client)
