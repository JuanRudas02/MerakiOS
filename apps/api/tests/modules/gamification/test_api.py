from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

import httpx

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.time import utc_now
from oneheavy.shared.infrastructure.container import Container
from tests.conftest import AuthContext, login_as

STAFF_PWD = "Temporal12345"


async def invite(client: httpx.AsyncClient, auth: AuthContext, name: str, role: str, phone: str) -> dict:
    resp = await client.post(
        "/api/v1/workspace/members",
        headers=auth.headers,
        json={"name": name, "role": role, "temporary_password": STAFF_PWD, "phone": phone},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def cleaning_done(tenant: uuid.UUID, staff: uuid.UUID, photos: int = 2) -> ie.CleaningTaskCompleted:
    return ie.CleaningTaskCompleted(
        tenant_id=tenant,
        task_id=uuid.uuid4(),
        property_id=uuid.uuid4(),
        staff_id=staff,
        duration_minutes=80,
        photos_count=photos,
        on_time=True,
    )


async def test_player_enrolled_and_scored_idempotently(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    staff = await invite(client, auth, "Luz Staff", "staff", "3109998877")
    tenant, staff_id = uuid.UUID(auth.workspace["id"]), uuid.UUID(staff["id"])
    event = cleaning_done(tenant, staff_id, photos=2)

    await container.bus.publish(event)
    await container.bus.publish(event)  # reentrega del mismo evento → no duplica

    headers = await login_as(client, staff["username"], STAFF_PWD)
    me = (await client.get("/api/v1/gamification/me", headers=headers)).json()
    assert me["name"] == "Luz Staff"
    assert me["points"] == 60  # 50 a tiempo + 2 fotos x 5
    assert me["level"]["name"] == "Rookie"
    assert me["streak_days"] == 1
    assert me["rank"] == 1
    assert [b["key"] for b in me["badges"]] == ["first_clean"]

    awarded = [e for e in container.bus.published if isinstance(e, ie.PointsAwarded)]  # type: ignore[attr-defined]
    assert sorted(e.points for e in awarded) == [10, 50]


async def test_leaderboard_feed_and_teams(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    tenant = uuid.UUID(auth.workspace["id"])
    staff = await invite(client, auth, "Luz Staff", "staff", "3109998877")
    seller = await invite(client, auth, "Sol Ventas", "sales", "3115556677")
    await container.bus.publish(cleaning_done(tenant, uuid.UUID(staff["id"]), photos=0))
    await container.bus.publish(
        ie.DealWon(
            tenant_id=tenant,
            deal_id=uuid.uuid4(),
            contact_id=None,
            owner_id=uuid.UUID(seller["id"]),
            amount=Decimal("3000000"),
            currency="COP",
        )
    )

    board = (await client.get("/api/v1/gamification/leaderboard?period=all", headers=auth.headers)).json()
    assert [(r["rank"], r["name"], r["points"]) for r in board] == [
        (1, "Sol Ventas", 103),
        (2, "Luz Staff", 50),
    ]
    assert board[0]["level"] == 1

    ops = (await client.get("/api/v1/gamification/leaderboard?team=operations", headers=auth.headers)).json()
    assert [r["name"] for r in ops] == ["Luz Staff"]

    feed = (await client.get("/api/v1/gamification/feed", headers=auth.headers)).json()
    assert {f["reason"] for f in feed} == {"Negocio ganado", "Limpieza completada a tiempo"}
    assert feed[0]["user_name"] in {"Sol Ventas", "Luz Staff"}


async def test_badges_catalog_and_rules_configuration(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    badges = (await client.get("/api/v1/gamification/badges", headers=auth.headers)).json()
    assert {"first_clean", "deal_closer", "streak_7"} <= {b["key"] for b in badges}

    rules = (await client.get("/api/v1/gamification/rules", headers=auth.headers)).json()
    on_time = next(r for r in rules if r["key"] == "cleaning_completed_on_time")
    assert on_time == {
        "key": "cleaning_completed_on_time",
        "event": "CleaningTaskCompleted",
        "description": "Limpieza completada a tiempo",
        "points": 50,
        "active": True,
    }

    resp = await client.put(
        "/api/v1/gamification/rules/cleaning_completed_on_time",
        headers=auth.headers,
        json={"points": 70, "active": True},
    )
    assert resp.status_code == 200
    missing = await client.put("/api/v1/gamification/rules/nope", headers=auth.headers, json={"points": 1})
    assert missing.status_code == 404

    staff = await invite(client, auth, "Luz Staff", "staff", "3109998877")
    await container.bus.publish(cleaning_done(uuid.UUID(auth.workspace["id"]), uuid.UUID(staff["id"]), 0))
    headers = await login_as(client, staff["username"], STAFF_PWD)
    assert (await client.get("/api/v1/gamification/me", headers=headers)).json()["points"] == 70

    forbidden = await client.put(
        "/api/v1/gamification/rules/cleaning_completed_on_time", headers=headers, json={"points": 999}
    )
    assert forbidden.status_code == 403


async def test_challenge_progress_and_reward(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    tenant = uuid.UUID(auth.workspace["id"])
    staff = await invite(client, auth, "Luz Staff", "staff", "3109998877")
    staff_headers = await login_as(client, staff["username"], STAFF_PWD)
    now = utc_now()
    body = {
        "title": "Semana impecable",
        "description": "2 limpiezas a tiempo",
        "metric": "cleaning_completed_on_time",
        "target": 2,
        "starts_at": (now - timedelta(hours=1)).isoformat(),
        "ends_at": (now + timedelta(days=7)).isoformat(),
        "reward_points": 100,
        "team": "operations",
    }
    forbidden = await client.post("/api/v1/gamification/challenges", headers=staff_headers, json=body)
    assert forbidden.status_code == 403
    created = await client.post("/api/v1/gamification/challenges", headers=auth.headers, json=body)
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "active"

    for _ in range(3):
        await container.bus.publish(cleaning_done(tenant, uuid.UUID(staff["id"]), photos=0))

    challenges = (await client.get("/api/v1/gamification/challenges", headers=staff_headers)).json()
    assert challenges[0]["progress"] == 3
    me = (await client.get("/api/v1/gamification/me", headers=staff_headers)).json()
    assert me["points"] == 3 * 50 + 100  # recompensa una sola vez


async def test_invalid_challenge_window_is_422(client: httpx.AsyncClient, auth: AuthContext) -> None:
    now = utc_now()
    resp = await client.post(
        "/api/v1/gamification/challenges",
        headers=auth.headers,
        json={
            "title": "Mal reto",
            "metric": "points",
            "target": 10,
            "starts_at": now.isoformat(),
            "ends_at": (now - timedelta(days=1)).isoformat(),
            "reward_points": 10,
        },
    )
    assert resp.status_code == 422


async def test_tenant_isolation_in_leaderboard(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    from tests.conftest import register_workspace

    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    staff = await invite(client, auth, "Luz Staff", "staff", "3109998877")
    await container.bus.publish(cleaning_done(uuid.UUID(auth.workspace["id"]), uuid.UUID(staff["id"]), 0))
    board = (await client.get("/api/v1/gamification/leaderboard?period=all", headers=other.headers)).json()
    assert board == []
