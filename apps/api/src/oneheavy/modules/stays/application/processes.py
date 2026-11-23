"""Procesos automáticos de Stays (pipelines batch, webhooks y reacciones a eventos).

CU-ST-09  Sincronizar calendario iCal (Airbnb/Booking) → tareas en cada check-out
CU-ST-22  Respuesta de botones WhatsApp (llegué / no han salido / problema)
CU-ST-23  Recordatorio diario al personal (hora configurable por workspace)
CU-ST-24  Recordatorios de cortes de servicios a propietarios (5 días antes + vencido)
CU-ST-25  Confirmación de llegada y escalamiento automático al supervisor
CU-ST-26  Sincronizar personal y propietarios desde Identidad (evento UserRegistered)

Cada proceso batch recorre todos los workspaces, abre su propia UoW y recibe
`now` como parámetro (testeable y sin la fecha congelada del scheduler de Stays).
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from oneheavy.modules.stays.application.notifications import StaysNotifier
from oneheavy.modules.stays.application.ports import CalendarEvent, ReservationCalendar, StaysUnitOfWork
from oneheavy.modules.stays.application.properties import load_property
from oneheavy.modules.stays.domain.model import (
    BillingCutoffs,
    CleaningTask,
    IssueKind,
    OwnerAccount,
    StaffMember,
    TaskStatus,
    to_utc,
)
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import AuthenticationError
from oneheavy.shared.domain.time import utc_now
from oneheavy.shared.domain.value_objects import PhoneNumber

log = logging.getLogger("oneheavy.stays.processes")
UowFactory = Callable[[], StaysUnitOfWork]

DEFAULT_CHECKOUT = time(11, 0)
SYNC_HORIZON_DAYS = 60


# ── CU-ST-09 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SyncCalendarCommand:
    actor: Principal
    property_id: uuid.UUID


class SyncPropertyCalendar(UseCase[SyncCalendarCommand, int]):
    def __init__(
        self, uow: StaysUnitOfWork, calendar: ReservationCalendar, tz: ZoneInfo, now: datetime | None = None
    ) -> None:
        self.uow, self.calendar, self.tz, self.now = uow, calendar, tz, now

    def _checkout_utc(self, event: CalendarEvent) -> datetime:
        if isinstance(event.checkout, datetime):
            return to_utc(event.checkout)
        return datetime.combine(event.checkout, DEFAULT_CHECKOUT, tzinfo=self.tz).astimezone(UTC)

    async def execute(self, data: SyncCalendarCommand) -> int:
        data.actor.require(Permission.PROPERTIES_MANAGE)
        now = self.now or utc_now()
        async with self.uow:
            prop = await load_property(self.uow, data.actor, data.property_id)
            if not prop.ical_url:
                return 0
            events = await self.calendar.fetch(prop.ical_url)
            created: list[CleaningTask] = []
            for event in events:
                checkout = self._checkout_utc(event)
                if not now < checkout <= now + timedelta(days=SYNC_HORIZON_DAYS):
                    continue
                if await self.uow.tasks.find_by_external_ref(prop.tenant_id, event.uid):
                    continue
                local_day = checkout.astimezone(self.tz).replace(hour=0, minute=0, second=0, microsecond=0)
                if await self.uow.tasks.exists_for_property(
                    prop.tenant_id, prop.id, to_utc(local_day), to_utc(local_day + timedelta(days=1))
                ):
                    continue
                task = CleaningTask.schedule(
                    tenant_id=prop.tenant_id,
                    prop=prop,
                    staff_id=prop.default_staff_id,
                    scheduled_at=checkout,
                    observations=f"Generada desde calendario: {event.summary or 'Reserva'}",
                    actor_id=data.actor.user_id,
                    source="ical",
                    external_ref=event.uid,
                )
                await self.uow.tasks.add(task)
                created.append(task)
            for task in created:
                self.uow.collect(task.pull_events())
            await self.uow.commit()
        return len(created)


# ── CU-ST-22 ────────────────────────────────────────────────────────────────


def extract_button_id(payload: dict[str, Any]) -> str | None:
    """Evolution envía la respuesta en distintos formatos según la versión."""
    data = payload.get("data") or {}
    message = data.get("message") or {}
    for key, field_name in (
        ("buttonsResponseMessage", "selectedButtonId"),
        ("templateButtonReplyMessage", "selectedId"),
        ("interactiveResponseMessage", "id"),
    ):
        node = message.get(key)
        if isinstance(node, dict) and node.get(field_name):
            return str(node[field_name])
    return None


@dataclass(frozen=True)
class WhatsAppReplyCommand:
    token: str
    payload: dict[str, Any]


class HandleWhatsAppReply(UseCase[WhatsAppReplyCommand, str]):
    """Devuelve la acción ejecutada (`arrival`, `no_out`, `problem` o `ignored`)."""

    def __init__(self, uow: StaysUnitOfWork, notifier: StaysNotifier) -> None:
        self.uow, self.notifier = uow, notifier

    async def execute(self, data: WhatsAppReplyCommand) -> str:
        async with self.uow:
            settings = await self.uow.settings.find_by_webhook_token(data.token) if data.token else None
            if settings is None:
                raise AuthenticationError("Token de webhook inválido")
            button = extract_button_id(data.payload)
            if not button or "_" not in button:
                return "ignored"
            action, _, raw_id = button.rpartition("_")
            try:
                task_id = uuid.UUID(raw_id)
            except ValueError:
                return "ignored"
            task = await self.uow.tasks.get(settings.tenant_id, task_id)
            if task is None or task.status not in (TaskStatus.PENDING, TaskStatus.ARRIVED):
                return "ignored"
            now = utc_now()
            alert: str | None = None
            if action == "arrival":
                if task.status is not TaskStatus.PENDING:
                    return "ignored"
                task.acknowledge_arrival(now)
            elif action == "no_out":
                task.report_issue(IssueKind.GUESTS_NOT_OUT, "Los huéspedes no han salido", now, task.staff_id)
                alert = "Los huéspedes no han salido"
            elif action == "problem":
                task.report_issue(IssueKind.PROBLEM, "Problema detectado al llegar", now, task.staff_id)
                alert = "El personal reporta un problema al llegar"
            else:
                return "ignored"
            prop = await self.uow.properties.get(task.tenant_id, task.property_id)
            await self.uow.tasks.update(task)
            self.uow.collect(task.pull_events())
            await self.uow.commit()
        if alert:
            await self.notifier.escalate(settings, f"{alert} en {prop.name if prop else task.property_id}.")
        return action


# ── Procesos batch ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class JobResult:
    sent: int = 0
    escalated: int = 0


class StaysJobs:
    def __init__(self, uow_factory: UowFactory, notifier: StaysNotifier, tz: ZoneInfo) -> None:
        self._uow = uow_factory
        self._notifier = notifier
        self._tz = tz

    # CU-ST-23 ──────────────────────────────────────────────────────────────

    async def send_daily_reminders(self, now: datetime | None = None) -> JobResult:
        """Corre cada hora; cada workspace recibe su resumen a su `daily_reminder_hour` local."""
        now = to_utc(now or utc_now())
        local_now = now.astimezone(self._tz)
        tomorrow = (local_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start, end = to_utc(tomorrow), to_utc(tomorrow + timedelta(days=1))
        sent = 0
        async with self._uow() as uow:
            tasks = [
                t
                for t in await uow.tasks.list_between_all_tenants(start, end)
                if t.status is TaskStatus.PENDING and t.staff_id
            ]
            by_tenant: dict[uuid.UUID, list[CleaningTask]] = defaultdict(list)
            for t in tasks:
                by_tenant[t.tenant_id].append(t)
            settings_map = await uow.settings.get_many(set(by_tenant))
            for tenant_id, tenant_tasks in by_tenant.items():
                settings = settings_map[tenant_id]
                if settings.daily_reminder_hour != local_now.hour:
                    continue
                staff = await uow.staff.get_many(tenant_id, {t.staff_id for t in tenant_tasks if t.staff_id})
                props = await uow.properties.get_many(tenant_id, {t.property_id for t in tenant_tasks})
                per_staff: dict[uuid.UUID, list[CleaningTask]] = defaultdict(list)
                for t in tenant_tasks:
                    if t.staff_id:
                        per_staff[t.staff_id].append(t)
                for staff_id, items in per_staff.items():
                    member = staff.get(staff_id)
                    if member and member.active:
                        sent += await self._notifier.daily_summary(member, items, props, settings)
        log.info("daily_reminders_done", extra={"sent": sent})
        return JobResult(sent=sent)

    # CU-ST-24 ──────────────────────────────────────────────────────────────

    async def check_billing_cutoffs(self, now: datetime | None = None) -> JobResult:
        today = to_utc(now or utc_now()).astimezone(self._tz).date()
        in_five = today + timedelta(days=5)
        period = f"{today.year:04d}-{today.month:02d}"
        sent = 0
        async with self._uow() as uow:
            props = await uow.properties.list_all_with_cutoffs()
            if not props:
                return JobResult()
            verified = await uow.receipts.verified_services({p.id for p in props}, period)
            settings_map = await uow.settings.get_many({p.tenant_id for p in props})
            paused_now: list[Any] = []
            for prop in props:
                settings = settings_map[prop.tenant_id]
                for service, day in prop.billing_cutoffs.configured():
                    if BillingCutoffs.due_date(day, in_five.year, in_five.month) == in_five:
                        sent += await self._notifier.billing(prop, service, settings, overdue=False)
                    elif BillingCutoffs.due_date(day, today.year, today.month) == today and (
                        (prop.id, service.value) not in verified
                    ):
                        sent += await self._notifier.billing(prop, service, settings, overdue=True)
                        if not prop.automation_paused:
                            prop.pause_automation()
                            paused_now.append(prop)
            for prop in paused_now:
                await uow.properties.update(prop)
            await uow.commit()
        log.info("billing_cutoffs_done", extra={"sent": sent})
        return JobResult(sent=sent)

    # CU-ST-25 ──────────────────────────────────────────────────────────────

    async def check_arrivals(self, now: datetime | None = None) -> JobResult:
        """Cada 5 min: pide confirmación antes del inicio y escala si nadie confirma."""
        now = to_utc(now or utc_now())
        sent = escalated = 0
        async with self._uow() as uow:
            tasks = await uow.tasks.list_between_all_tenants(
                now - timedelta(hours=2), now + timedelta(minutes=5), status=TaskStatus.PENDING
            )
            if not tasks:
                return JobResult()
            settings_map = await uow.settings.get_many({t.tenant_id for t in tasks})
            touched: list[CleaningTask] = []
            for tenant_id in {t.tenant_id for t in tasks}:
                tenant_tasks = [t for t in tasks if t.tenant_id == tenant_id]
                settings = settings_map[tenant_id]
                staff = await uow.staff.get_many(tenant_id, {t.staff_id for t in tenant_tasks if t.staff_id})
                props = await uow.properties.get_many(tenant_id, {t.property_id for t in tenant_tasks})
                for task in tenant_tasks:
                    prop = props.get(task.property_id)
                    member = staff.get(task.staff_id) if task.staff_id else None
                    if task.arrival_prompted_at is None and now <= task.scheduled_at and member and prop:
                        if await self._notifier.arrival_prompt(task, prop, member, settings):
                            sent += 1
                        task.arrival_prompted_at = now
                        touched.append(task)
                    overdue = now - task.scheduled_at >= timedelta(minutes=settings.escalation_minutes)
                    if overdue and task.escalated_at is None:
                        who = member.name if member else "sin asignar"
                        where = prop.name if prop else str(task.property_id)
                        await self._notifier.escalate(
                            settings,
                            f"El personal ({who}) no ha confirmado llegada a {where} "
                            f"programada a las {task.scheduled_at.astimezone(self._tz):%H:%M}.",
                        )
                        task.escalated_at = now
                        escalated += 1
                        touched.append(task)
            for task in {t.id: t for t in touched}.values():
                await uow.tasks.update(task)
            await uow.commit()
        log.info("arrival_check_done", extra={"prompts": sent, "escalated": escalated})
        return JobResult(sent=sent, escalated=escalated)


# ── CU-ST-26 ────────────────────────────────────────────────────────────────


class SyncDirectoryFromIdentity:
    """Reacciona a `UserRegistered`: el staff con login y los propietarios quedan visibles en Stays."""

    def __init__(self, uow_factory: UowFactory) -> None:
        self._uow = uow_factory

    async def __call__(self, event: ie.UserRegistered) -> None:
        if event.role not in ("staff", "property_owner"):
            return
        phone = PhoneNumber(event.phone) if event.phone else None
        async with self._uow() as uow:
            if event.role == "staff":
                await uow.staff.upsert(
                    StaffMember(
                        id=event.user_id,
                        tenant_id=event.tenant_id,
                        name=event.name,
                        phone=phone,
                        has_login=True,
                    )
                )
            else:
                await uow.owners.upsert(
                    OwnerAccount(id=event.user_id, tenant_id=event.tenant_id, phone=phone)
                )
            await uow.commit()
