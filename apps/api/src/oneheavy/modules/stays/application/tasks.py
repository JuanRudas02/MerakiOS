"""Casos de uso de tareas de limpieza (programación, ejecución y tablero).

Administración
  CU-ST-10  Programar limpieza (notifica al personal por WhatsApp)
  CU-ST-11  Consultar calendario de tareas (el staff sólo ve las suyas)
  CU-ST-12  Consultar detalle / historial de una tarea
  CU-ST-13  Editar tarea (sólo pendiente)
  CU-ST-14  Cancelar tarea
Ejecución (personal operativo)
  CU-ST-15  Consultar fotos requeridas (modo estándar / aleatorio)
  CU-ST-16  Confirmar llegada con fotos
  CU-ST-17  Iniciar limpieza
  CU-ST-18  Completar checklist
  CU-ST-19  Reportar problema / faltante de insumos / huéspedes sin salir
  CU-ST-20  Finalizar con fotos
Seguimiento
  CU-ST-21  Tablero operativo (hoy, semana, ranking del personal, próximas)
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from oneheavy.modules.stays.application.notifications import StaysNotifier
from oneheavy.modules.stays.application.ports import StaysUnitOfWork, UploadedFile
from oneheavy.modules.stays.domain.model import (
    STANDARD_PHOTOS,
    ChecklistItem,
    CleaningTask,
    IssueKind,
    Luggage,
    PhotoMode,
    StaffMember,
    TaskStatus,
    to_utc,
)
from oneheavy.modules.stays.domain.repositories import TaskFilter
from oneheavy.shared.application.ports import FileStorage
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain.access import Permission, Principal, Role
from oneheavy.shared.domain.errors import NotFoundError
from oneheavy.shared.domain.time import utc_now

# ── Vista de lectura ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TaskView:
    task: CleaningTask
    property_name: str | None
    staff_name: str | None


async def to_views(uow: StaysUnitOfWork, tenant_id: uuid.UUID, tasks: list[CleaningTask]) -> list[TaskView]:
    """Enriquece con nombres usando 2 consultas en lote (evita el N+1 de Stays)."""
    props = await uow.properties.get_many(tenant_id, {t.property_id for t in tasks})
    staff = await uow.staff.get_many(tenant_id, {t.staff_id for t in tasks if t.staff_id})
    return [
        TaskView(
            t,
            props[t.property_id].name if t.property_id in props else None,
            staff[t.staff_id].name if t.staff_id and t.staff_id in staff else None,
        )
        for t in tasks
    ]


def _is_staff(actor: Principal) -> bool:
    return actor.role is Role.STAFF


async def load_task(uow: StaysUnitOfWork, actor: Principal, task_id: uuid.UUID) -> CleaningTask:
    task = await uow.tasks.get(actor.tenant_id, task_id)
    # El personal sólo accede a sus tareas; para él, una tarea ajena "no existe".
    if task is None or (_is_staff(actor) and task.staff_id != actor.user_id):
        raise NotFoundError("Tarea no encontrada")
    return task


# ── CU-ST-10 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScheduleTaskCommand:
    actor: Principal
    property_id: uuid.UUID
    scheduled_at: datetime
    staff_id: uuid.UUID | None = None
    observations: str | None = None
    luggage: Luggage = Luggage.NONE
    supplies_required: bool = False


class ScheduleTask(UseCase[ScheduleTaskCommand, TaskView]):
    def __init__(self, uow: StaysUnitOfWork, notifier: StaysNotifier) -> None:
        self.uow, self.notifier = uow, notifier

    async def execute(self, data: ScheduleTaskCommand) -> TaskView:
        data.actor.require(Permission.TASKS_MANAGE)
        tenant = data.actor.tenant_id
        async with self.uow:
            prop = await self.uow.properties.get(tenant, data.property_id)
            if prop is None:
                raise NotFoundError("Propiedad no encontrada")
            staff_id = data.staff_id or prop.default_staff_id
            staff = await self.uow.staff.get(tenant, staff_id) if staff_id else None
            if staff_id and staff is None:
                raise NotFoundError("Personal no encontrado")
            task = CleaningTask.schedule(
                tenant_id=tenant,
                prop=prop,
                staff_id=staff_id,
                scheduled_at=data.scheduled_at,
                observations=data.observations,
                luggage=data.luggage,
                supplies_required=data.supplies_required,
                actor_id=data.actor.user_id,
            )
            await self.uow.tasks.add(task)
            settings = await self.uow.settings.get(tenant)
            self.uow.collect(task.pull_events())
            await self.uow.commit()
        if staff:
            await self.notifier.task_assigned(task, prop, staff, settings)
        return TaskView(task, prop.name, staff.name if staff else None)


# ── CU-ST-11 / 12 ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ListTasksQuery:
    actor: Principal
    start: datetime | None = None
    end: datetime | None = None
    property_id: uuid.UUID | None = None
    staff_id: uuid.UUID | None = None
    status: TaskStatus | None = None


class ListTasks(UseCase[ListTasksQuery, list[TaskView]]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ListTasksQuery) -> list[TaskView]:
        data.actor.require(Permission.TASKS_READ)
        staff_id = data.actor.user_id if _is_staff(data.actor) else data.staff_id
        flt = TaskFilter(
            start=to_utc(data.start) if data.start else None,
            end=to_utc(data.end) if data.end else None,
            property_id=data.property_id,
            staff_id=staff_id,
            status=data.status,
        )
        async with self.uow:
            tasks = await self.uow.tasks.search(data.actor.tenant_id, flt)
            return await to_views(self.uow, data.actor.tenant_id, tasks)


@dataclass(frozen=True)
class TaskQuery:
    actor: Principal
    task_id: uuid.UUID


class GetTask(UseCase[TaskQuery, TaskView]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: TaskQuery) -> TaskView:
        data.actor.require(Permission.TASKS_READ)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            return (await to_views(self.uow, task.tenant_id, [task]))[0]


# ── CU-ST-13 / 14 ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EditTaskCommand:
    actor: Principal
    task_id: uuid.UUID
    changes: dict[str, object]


class EditTask(UseCase[EditTaskCommand, TaskView]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: EditTaskCommand) -> TaskView:
        data.actor.require(Permission.TASKS_MANAGE)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            changes = dict(data.changes)
            staff_id = changes.get("staff_id")
            if isinstance(staff_id, uuid.UUID) and not await self.uow.staff.get(task.tenant_id, staff_id):
                raise NotFoundError("Personal no encontrado")
            task.edit(**changes)  # type: ignore[arg-type]
            await self.uow.tasks.update(task)
            await self.uow.commit()
            return (await to_views(self.uow, task.tenant_id, [task]))[0]


@dataclass(frozen=True)
class CancelTaskCommand:
    actor: Principal
    task_id: uuid.UUID
    reason: str


class CancelTask(UseCase[CancelTaskCommand, TaskView]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: CancelTaskCommand) -> TaskView:
        data.actor.require(Permission.TASKS_MANAGE)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            task.cancel(data.reason)
            await self.uow.tasks.update(task)
            await self.uow.commit()
            return (await to_views(self.uow, task.tenant_id, [task]))[0]


# ── CU-ST-15 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RequiredPhotosQuery:
    actor: Principal
    task_id: uuid.UUID
    mode: PhotoMode | None = None


class GetRequiredPhotos(UseCase[RequiredPhotosQuery, list[str]]):
    def __init__(self, uow: StaysUnitOfWork, rng: random.Random | None = None) -> None:
        self.uow = uow
        self.rng = rng or random.Random()

    async def execute(self, data: RequiredPhotosQuery) -> list[str]:
        data.actor.require(Permission.TASKS_EXECUTE)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            prop = await self.uow.properties.get(task.tenant_id, task.property_id)
            mode = data.mode or (await self.uow.settings.get(task.tenant_id)).photo_mode
        if mode is PhotoMode.STANDARD:
            return list(STANDARD_PHOTOS)
        inventory = prop.visual_inventory if prop else []
        if not inventory:
            return ["Foto general 1", "Foto general 2"]
        count = min(len(inventory), self.rng.randint(3, 5))
        return self.rng.sample(inventory, count)


# ── CU-ST-16 … 20: ejecución ────────────────────────────────────────────────


@dataclass(frozen=True)
class PhotosCommand:
    actor: Principal
    task_id: uuid.UUID
    photos: list[UploadedFile] = field(default_factory=list)


class _ExecutionUseCase:
    def __init__(self, uow: StaysUnitOfWork, storage: FileStorage | None = None) -> None:
        self.uow, self.storage = uow, storage

    async def _store(self, task: CleaningTask, photos: list[UploadedFile], stage: str) -> list[str]:
        assert self.storage is not None
        return [
            await self.storage.save(
                p.data, folder=f"tasks/{task.tenant_id}/{task.id}/{stage}", filename=p.filename,
                content_type=p.content_type,
            )
            for p in photos
        ]  # fmt: skip

    async def _finish(self, task: CleaningTask) -> TaskView:
        await self.uow.tasks.update(task)
        self.uow.collect(task.pull_events())
        await self.uow.commit()
        return (await to_views(self.uow, task.tenant_id, [task]))[0]


class ConfirmArrival(_ExecutionUseCase, UseCase[PhotosCommand, TaskView]):
    async def execute(self, data: PhotosCommand) -> TaskView:
        data.actor.require(Permission.TASKS_EXECUTE)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            urls = await self._store(task, data.photos, "arrival") if data.photos else []
            task.confirm_arrival(urls, utc_now(), data.actor.user_id)
            return await self._finish(task)


class StartCleaning(_ExecutionUseCase, UseCase[TaskQuery, TaskView]):
    async def execute(self, data: TaskQuery) -> TaskView:
        data.actor.require(Permission.TASKS_EXECUTE)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            task.start(utc_now())
            return await self._finish(task)


@dataclass(frozen=True)
class ChecklistCommand:
    actor: Principal
    task_id: uuid.UUID
    items: list[ChecklistItem]


class UpdateChecklist(_ExecutionUseCase, UseCase[ChecklistCommand, TaskView]):
    async def execute(self, data: ChecklistCommand) -> TaskView:
        data.actor.require(Permission.TASKS_EXECUTE)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            task.update_checklist(data.items)
            return await self._finish(task)


@dataclass(frozen=True)
class ReportIssueCommand:
    actor: Principal
    task_id: uuid.UUID
    kind: IssueKind
    description: str


class ReportIssue(_ExecutionUseCase, UseCase[ReportIssueCommand, TaskView]):
    def __init__(self, uow: StaysUnitOfWork, notifier: StaysNotifier) -> None:
        super().__init__(uow)
        self.notifier = notifier

    async def execute(self, data: ReportIssueCommand) -> TaskView:
        data.actor.require(Permission.TASKS_EXECUTE)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            task.report_issue(data.kind, data.description, utc_now(), data.actor.user_id)
            settings = await self.uow.settings.get(task.tenant_id)
            view = await self._finish(task)
        await self.notifier.escalate(
            settings,
            f"Reporte en {view.property_name or task.property_id} ({data.kind.value}): {data.description}",
        )
        return view


class CompleteTask(_ExecutionUseCase, UseCase[PhotosCommand, TaskView]):
    async def execute(self, data: PhotosCommand) -> TaskView:
        data.actor.require(Permission.TASKS_EXECUTE)
        async with self.uow:
            task = await load_task(self.uow, data.actor, data.task_id)
            settings = await self.uow.settings.get(task.tenant_id)
            urls = await self._store(task, data.photos, "final") if data.photos else []
            task.complete(
                urls, utc_now(), on_time_minutes=settings.escalation_minutes, actor_id=data.actor.user_id
            )
            return await self._finish(task)


# ── CU-ST-21 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StaffRank:
    staff_id: uuid.UUID
    name: str
    completed: int
    on_time_rate: float
    avg_minutes: float


@dataclass(frozen=True)
class Dashboard:
    today: dict[str, int]
    week: dict[str, float | int]
    staff_ranking: list[StaffRank]
    upcoming: list[TaskView]


class GetDashboard(UseCase[Principal, Dashboard]):
    def __init__(self, uow: StaysUnitOfWork, tz: ZoneInfo) -> None:
        self.uow, self.tz = uow, tz

    async def execute(self, data: Principal) -> Dashboard:
        data.require(Permission.TASKS_READ)
        now = utc_now()
        local_today = now.astimezone(self.tz).replace(hour=0, minute=0, second=0, microsecond=0)
        day_start, day_end = to_utc(local_today), to_utc(local_today + timedelta(days=1))
        week_start = now - timedelta(days=7)
        staff_scope = data.user_id if _is_staff(data) else None
        async with self.uow:
            settings = await self.uow.settings.get(data.tenant_id)
            # Una sola consulta por rango; las agregaciones se hacen en memoria.
            window = await self.uow.tasks.search(
                data.tenant_id,
                TaskFilter(
                    start=min(week_start, day_start), end=now + timedelta(days=30), staff_id=staff_scope
                ),
            )
            today = [t for t in window if day_start <= t.scheduled_at < day_end]
            week = [t for t in window if week_start <= t.scheduled_at <= now]
            completed = [t for t in week if t.status is TaskStatus.COMPLETED]
            upcoming = [
                t
                for t in window
                if t.scheduled_at >= now and t.status in (TaskStatus.PENDING, TaskStatus.ARRIVED)
            ][:8]
            staff = await self.uow.staff.get_many(
                data.tenant_id, {t.staff_id for t in completed if t.staff_id}
            )
            upcoming_views = await to_views(self.uow, data.tenant_id, upcoming)

        def on_time(t: CleaningTask) -> bool:
            late = t.minutes_late()
            return late is not None and late <= settings.escalation_minutes

        def avg(values: list[int]) -> float:
            return round(sum(values) / len(values), 1) if values else 0.0

        ranking: list[StaffRank] = []
        by_staff: dict[uuid.UUID, list[CleaningTask]] = {}
        for t in completed:
            if t.staff_id:
                by_staff.setdefault(t.staff_id, []).append(t)
        for sid, items in by_staff.items():
            member: StaffMember | None = staff.get(sid)
            ranking.append(
                StaffRank(
                    staff_id=sid,
                    name=member.name if member else "—",
                    completed=len(items),
                    on_time_rate=round(sum(on_time(t) for t in items) / len(items), 3),
                    avg_minutes=avg([d for t in items if (d := t.duration_minutes()) is not None]),
                )
            )
        ranking.sort(key=lambda r: (-r.completed, -r.on_time_rate))

        return Dashboard(
            today={
                "total": len(today),
                "pending": sum(t.status in (TaskStatus.PENDING, TaskStatus.ARRIVED) for t in today),
                "in_progress": sum(t.status is TaskStatus.IN_PROGRESS for t in today),
                "completed": sum(t.status is TaskStatus.COMPLETED for t in today),
                "cancelled": sum(t.status is TaskStatus.CANCELLED for t in today),
            },
            week={
                "completed": len(completed),
                "on_time_rate": round(sum(on_time(t) for t in completed) / len(completed), 3)
                if completed
                else 0.0,
                "avg_cleaning_minutes": avg(
                    [d for t in completed if (d := t.duration_minutes()) is not None]
                ),
                "issues": sum(len(t.issues) for t in week),
            },
            staff_ranking=ranking,
            upcoming=upcoming_views,
        )
