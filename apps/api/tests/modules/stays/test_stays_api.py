from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from oneheavy.modules.stays.application.ports import CalendarEvent, ReservationCalendar
from oneheavy.modules.stays.application.processes import StaysJobs
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.time import utc_now
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.messaging import ConsoleMessageSender
from tests.conftest import AuthContext, login_as, register_workspace

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
STAFF_PHONE = "3109998877"
OWNER_PHONE = "3205551234"


def _outbox(container: Container) -> ConsoleMessageSender:
    sender = container.sender
    assert isinstance(sender, ConsoleMessageSender)
    return sender


def _events(container: Container, kind: type) -> list[Any]:
    return [e for e in container.bus.published if isinstance(e, kind)]  # type: ignore[attr-defined]


async def _invite(
    client: httpx.AsyncClient, auth: AuthContext, role: str, phone: str, name: str
) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/workspace/members",
        headers=auth.headers,
        json={"name": name, "role": role, "temporary_password": "Temporal12345", "phone": phone},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()  # type: ignore[no-any-return]


async def _property(client: httpx.AsyncClient, auth: AuthContext, **overrides: Any) -> dict[str, Any]:
    body = {
        "code": "SKY-05",
        "name": "Sky 05",
        "capacity": 4,
        "owner_name": "Olga Owner",
        "owner_phone": OWNER_PHONE,
        "billing_cutoffs": {"electricity": 15, "water": 10},
        "checklist_template": ["Cama", "Baño"],
        "visual_inventory": ["TV", "Sofá", "Nevera", "Cafetera"],
    } | overrides
    resp = await client.post("/api/v1/stays/properties", headers=auth.headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()  # type: ignore[no-any-return]


async def _task(
    client: httpx.AsyncClient, auth: AuthContext, prop_id: str, staff_id: str | None, when: datetime
) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/stays/tasks",
        headers=auth.headers,
        json={
            "property_id": prop_id,
            "staff_id": staff_id,
            "scheduled_at": when.isoformat(),
            "luggage": "collect",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()  # type: ignore[no-any-return]


async def _setup(client: httpx.AsyncClient, auth: AuthContext) -> tuple[dict[str, Any], dict[str, Any]]:
    await client.put("/api/v1/stays/settings", headers=auth.headers, json={"supervisor_phone": "3000000001"})
    staff = await _invite(client, auth, "staff", STAFF_PHONE, "Luz Staff")
    prop = await _property(client, auth, default_staff_id=staff["id"])
    return staff, prop


# ── Propiedades ─────────────────────────────────────────────────────────────


async def test_property_crud_and_owner_welcome(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    prop = await _property(client, auth)
    assert prop["owner_phone"] == "+573205551234"
    assert prop["billing_cutoffs"]["electricity"] == 15
    welcome = _outbox(container).outbox[-1]
    assert welcome.to == "573205551234" and "Sky 05" in welcome.body

    dup = await client.post(
        "/api/v1/stays/properties", headers=auth.headers, json={"code": "SKY-05", "name": "X"}
    )
    assert dup.status_code == 409

    patched = await client.patch(
        f"/api/v1/stays/properties/{prop['id']}",
        headers=auth.headers,
        json={"name": "Sky 05 Plus", "capacity": 6},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Sky 05 Plus" and patched.json()["checklist_template"] == [
        "Cama",
        "Baño",
    ]
    listed = await client.get("/api/v1/stays/properties", headers=auth.headers)
    assert [p["code"] for p in listed.json()] == ["SKY-05"]


async def test_tenant_isolation(client: httpx.AsyncClient, auth: AuthContext) -> None:
    prop = await _property(client, auth)
    other = await register_workspace(client, email="boss@globex.co", workspace="Globex")
    assert (
        await client.get(f"/api/v1/stays/properties/{prop['id']}", headers=other.headers)
    ).status_code == 404
    assert (await client.get("/api/v1/stays/properties", headers=other.headers)).json() == []


async def test_staff_is_synced_from_identity(client: httpx.AsyncClient, auth: AuthContext) -> None:
    staff = await _invite(client, auth, "staff", STAFF_PHONE, "Luz Staff")
    resp = await client.post(
        "/api/v1/stays/staff", headers=auth.headers, json={"name": "Pedro WhatsApp", "phone": "3111111111"}
    )
    assert resp.status_code == 201 and resp.json()["has_login"] is False
    listed = {s["id"]: s for s in (await client.get("/api/v1/stays/staff", headers=auth.headers)).json()}
    assert listed[staff["id"]]["has_login"] is True
    assert listed[staff["id"]]["phone"] == "+573109998877"


# ── Ciclo de vida de la tarea ───────────────────────────────────────────────


async def test_task_lifecycle_end_to_end(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    staff, prop = await _setup(client, auth)
    task = await _task(
        client, auth, prop["id"], None, utc_now() + timedelta(hours=1)
    )  # usa staff por defecto
    assert task["staff_id"] == staff["id"] and task["staff_name"] == "Luz Staff"
    assert [c["item"] for c in task["checklist"]] == ["Cama", "Baño"]
    assert "NUEVA TAREA" in _outbox(container).outbox[-1].body
    tid = task["id"]

    sh = await login_as(client, "573109998877", "Temporal12345")
    assert len((await client.get("/api/v1/stays/tasks", headers=sh)).json()) == 1
    photos = await client.get(f"/api/v1/stays/tasks/{tid}/required-photos?mode=random", headers=sh)
    assert 3 <= len(photos.json()["items"]) <= 4

    no_photo = await client.post(f"/api/v1/stays/tasks/{tid}/arrival", headers=sh)
    assert no_photo.status_code == 422 and no_photo.json()["error"]["code"] == "photos_required"
    bad_file = await client.post(
        f"/api/v1/stays/tasks/{tid}/arrival",
        headers=sh,
        files=[("photos", ("x.png", b"<script>", "image/png"))],
    )
    assert bad_file.status_code == 422

    arrived = await client.post(
        f"/api/v1/stays/tasks/{tid}/arrival", headers=sh, files=[("photos", ("a.png", PNG, "image/png"))]
    )
    assert arrived.status_code == 200 and arrived.json()["status"] == "arrived"
    assert arrived.json()["initial_photos"][0].startswith("/storage/tasks/")
    assert (await client.post(f"/api/v1/stays/tasks/{tid}/start", headers=sh)).json()[
        "status"
    ] == "in_progress"

    early = await client.post(
        f"/api/v1/stays/tasks/{tid}/complete", headers=sh, files=[("photos", ("b.png", PNG, "image/png"))]
    )
    assert early.json()["error"]["code"] == "checklist_incomplete"
    checklist = await client.put(
        f"/api/v1/stays/tasks/{tid}/checklist",
        headers=sh,
        json={"items": [{"item": "Cama", "done": True}, {"item": "Baño", "done": True}]},
    )
    assert all(c["done"] for c in checklist.json()["checklist"])
    issue = await client.post(
        f"/api/v1/stays/tasks/{tid}/issues",
        headers=sh,
        json={"kind": "missing_supplies", "description": "Sin jabón"},
    )
    assert issue.json()["issues"][0]["kind"] == "missing_supplies"
    assert _outbox(container).outbox[-1].to == "573000000001"  # escalado al supervisor

    done = await client.post(
        f"/api/v1/stays/tasks/{tid}/complete", headers=sh, files=[("photos", ("b.png", PNG, "image/png"))]
    )
    assert done.status_code == 200 and done.json()["status"] == "completed"

    completed = _events(container, ie.CleaningTaskCompleted)
    assert len(completed) == 1 and completed[0].on_time and completed[0].photos_count == 2
    assert len(_events(container, ie.CleaningTaskScheduled)) == 1
    assert len(_events(container, ie.CleaningArrivalConfirmed)) == 1
    assert len(_events(container, ie.CleaningIssueReported)) == 1

    dash = (await client.get("/api/v1/stays/dashboard", headers=auth.headers)).json()
    assert dash["week"]["issues"] >= 0 and "staff_ranking" in dash and "today" in dash


async def test_staff_permissions_and_visibility(client: httpx.AsyncClient, auth: AuthContext) -> None:
    _staff, prop = await _setup(client, auth)
    other_staff = await _invite(client, auth, "staff", "3157777777", "Otro Staff")
    task = await _task(client, auth, prop["id"], other_staff["id"], utc_now() + timedelta(hours=2))
    sh = await login_as(client, "573109998877", "Temporal12345")
    assert (await client.get(f"/api/v1/stays/tasks/{task['id']}", headers=sh)).status_code == 404
    assert (await client.get("/api/v1/stays/tasks", headers=sh)).json() == []
    forbidden = await client.post("/api/v1/stays/properties", headers=sh, json={"code": "X", "name": "X"})
    assert forbidden.status_code == 403


async def test_edit_and_cancel(client: httpx.AsyncClient, auth: AuthContext) -> None:
    _staff, prop = await _setup(client, auth)
    task = await _task(client, auth, prop["id"], None, utc_now() + timedelta(days=1))
    edited = await client.patch(
        f"/api/v1/stays/tasks/{task['id']}", headers=auth.headers, json={"observations": "Check-in temprano"}
    )
    assert edited.json()["observations"] == "Check-in temprano"
    cancelled = await client.post(
        f"/api/v1/stays/tasks/{task['id']}/cancel", headers=auth.headers, json={"reason": "Reserva cancelada"}
    )
    assert cancelled.json()["status"] == "cancelled"
    again = await client.patch(
        f"/api/v1/stays/tasks/{task['id']}", headers=auth.headers, json={"observations": "x"}
    )
    assert again.status_code == 422


# ── Comprobantes y propietario ──────────────────────────────────────────────


async def test_receipts_flow_with_property_owner(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    mine = await _property(client, auth)
    await _property(client, auth, code="OTHER-1", owner_phone="3009990000")
    await _invite(client, auth, "property_owner", OWNER_PHONE, "Olga Owner")
    oh = await login_as(client, "573205551234", "Temporal12345")

    visible = (await client.get("/api/v1/stays/properties", headers=oh)).json()
    assert [p["code"] for p in visible] == ["SKY-05"]

    up = await client.post(
        f"/api/v1/stays/properties/{mine['id']}/receipts",
        headers=oh,
        data={"service": "electricity", "period": "2026-05"},
        files={"file": ("recibo.png", PNG, "image/png")},
    )
    assert up.status_code == 201, up.text
    receipt = up.json()
    assert receipt["status"] == "pending"
    prop = (await client.get(f"/api/v1/stays/properties/{mine['id']}", headers=auth.headers)).json()
    assert prop["automation_paused"] is True

    assert (
        await client.post(
            f"/api/v1/stays/receipts/{receipt['id']}/review", headers=oh, json={"approved": True}
        )
    ).status_code == 403
    reviewed = await client.post(
        f"/api/v1/stays/receipts/{receipt['id']}/review", headers=auth.headers, json={"approved": True}
    )
    assert reviewed.json()["status"] == "verified"
    prop = (await client.get(f"/api/v1/stays/properties/{mine['id']}", headers=auth.headers)).json()
    assert prop["automation_paused"] is False
    assert len(_events(container, ie.ReceiptVerified)) == 1
    listed = await client.get(f"/api/v1/stays/properties/{mine['id']}/receipts", headers=oh)
    assert len(listed.json()) == 1


# ── iCal ────────────────────────────────────────────────────────────────────


class FakeCalendar(ReservationCalendar):
    def __init__(self, events: list[CalendarEvent]) -> None:
        self.events = events

    async def fetch(self, url: str) -> list[CalendarEvent]:
        return self.events


async def test_calendar_sync_creates_deduplicated_tasks(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    _staff, prop = await _setup(client, auth)
    await client.patch(
        f"/api/v1/stays/properties/{prop['id']}",
        headers=auth.headers,
        json={"ical_url": "https://www.airbnb.com/calendar/ical/1.ics"},
    )
    soon = utc_now().date() + timedelta(days=3)
    container.extras["stays.calendar"] = FakeCalendar(
        [
            CalendarEvent("uid-1", soon, "Reserved"),
            CalendarEvent("uid-2", utc_now() + timedelta(days=5), "Reserved"),
            CalendarEvent("uid-old", date(2020, 1, 1), "Pasada"),
            CalendarEvent("uid-far", utc_now().date() + timedelta(days=200), "Lejana"),
        ]
    )
    url = f"/api/v1/stays/properties/{prop['id']}/calendar-sync"
    assert (await client.post(url, headers=auth.headers)).json() == {"created": 2}
    assert (await client.post(url, headers=auth.headers)).json() == {"created": 0}
    tasks = (await client.get(f"/api/v1/stays/tasks?property_id={prop['id']}", headers=auth.headers)).json()
    assert len(tasks) == 2 and all(t["staff_id"] for t in tasks)


# ── Webhook WhatsApp ────────────────────────────────────────────────────────


async def test_whatsapp_buttons_webhook(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    _staff, prop = await _setup(client, auth)
    task = await _task(client, auth, prop["id"], None, utc_now() + timedelta(minutes=3))
    token = (await client.get("/api/v1/stays/settings", headers=auth.headers)).json()["webhook_token"]

    def payload(button: str) -> dict[str, Any]:
        return {
            "event": "messages.upsert",
            "data": {"message": {"buttonsResponseMessage": {"selectedButtonId": button}}},
        }

    denied = await client.post(
        "/api/v1/stays/webhooks/whatsapp?token=nope", json=payload(f"arrival_{task['id']}")
    )
    assert denied.status_code == 401

    ok = await client.post(
        f"/api/v1/stays/webhooks/whatsapp?token={token}", json=payload(f"arrival_{task['id']}")
    )
    assert ok.json() == {"ok": True, "action": "arrival"}
    got = (await client.get(f"/api/v1/stays/tasks/{task['id']}", headers=auth.headers)).json()
    assert got["status"] == "arrived" and got["initial_photos"] == []

    problem = await client.post(
        f"/api/v1/stays/webhooks/whatsapp?token={token}", json=payload(f"no_out_{task['id']}")
    )
    assert problem.json()["action"] == "no_out"
    assert "no han salido" in _outbox(container).outbox[-1].body
    ignored = await client.post(f"/api/v1/stays/webhooks/whatsapp?token={token}", json={"event": "x"})
    assert ignored.json()["action"] == "ignored"


# ── Procesos batch ──────────────────────────────────────────────────────────


def _jobs(container: Container) -> StaysJobs:
    jobs = container.extras["stays.jobs"]
    assert isinstance(jobs, StaysJobs)
    return jobs


async def test_arrival_prompt_then_escalation(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    _staff, prop = await _setup(client, auth)
    start = datetime(2030, 6, 1, 15, 0, tzinfo=UTC)
    await _task(client, auth, prop["id"], None, start)
    out = _outbox(container).outbox

    result = await _jobs(container).check_arrivals(now=start - timedelta(minutes=3))
    assert result.sent == 1 and out[-1].to == "573109998877" and len(out[-1].buttons) == 3
    assert out[-1].buttons[0].id.startswith("arrival_")
    again = await _jobs(container).check_arrivals(now=start - timedelta(minutes=1))
    assert again.sent == 0  # no se repite el aviso

    late = await _jobs(container).check_arrivals(now=start + timedelta(minutes=11))
    assert late.escalated == 1 and out[-1].to == "573000000001" and "no ha confirmado" in out[-1].body
    assert (await _jobs(container).check_arrivals(now=start + timedelta(minutes=16))).escalated == 0


async def test_daily_reminders_at_tenant_hour(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    _staff, prop = await _setup(client, auth)
    # 2030-06-01 19:00 en Bogotá (UTC-5) = 2030-06-02 00:00 UTC; la tarea es el 2 a las 10:00 local.
    await _task(client, auth, prop["id"], None, datetime(2030, 6, 2, 15, 0, tzinfo=UTC))
    jobs = _jobs(container)
    assert (await jobs.send_daily_reminders(now=datetime(2030, 6, 1, 20, 0, tzinfo=UTC))).sent == 0
    result = await jobs.send_daily_reminders(now=datetime(2030, 6, 2, 0, 0, tzinfo=UTC))
    assert result.sent == 1
    msg = _outbox(container).outbox[-1]
    assert msg.to == "573109998877" and "1 limpieza" in msg.body and "Sky 05 a las 10:00" in msg.body


async def test_billing_cutoffs_reminder_and_overdue(
    client: httpx.AsyncClient, auth: AuthContext, container: Container
) -> None:
    prop = await _property(client, auth)  # electricity=15, water=10
    out = _outbox(container).outbox
    before = len(out)
    # 2030-03-10 09:00 Bogotá: luz vence en 5 días; agua vence hoy sin comprobante.
    result = await _jobs(container).check_billing_cutoffs(now=datetime(2030, 3, 10, 14, 0, tzinfo=UTC))
    assert result.sent == 2
    bodies = [m.body for m in out[before:]]
    assert any("RECORDATORIO DE PAGO" in b and "Luz" in b for b in bodies)
    assert any("PAGO VENCIDO" in b and "Agua" in b for b in bodies)
    paused = (await client.get(f"/api/v1/stays/properties/{prop['id']}", headers=auth.headers)).json()
    assert paused["automation_paused"] is True
    # Pausada: no se vuelve a notificar
    assert (
        await _jobs(container).check_billing_cutoffs(now=datetime(2030, 3, 10, 14, 0, tzinfo=UTC))
    ).sent == 0
