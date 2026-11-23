"""Adaptador de entrada REST del contexto Stays (/api/v1/stays/...)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status

from oneheavy.modules.stays.api.schemas import (
    CalendarSyncOut,
    CancelIn,
    ChecklistIn,
    DashboardOut,
    IssueIn,
    PropertyIn,
    PropertyOut,
    PropertyPatch,
    ReceiptOut,
    RequiredPhotosOut,
    ReviewIn,
    SettingsIn,
    SettingsOut,
    StaffIn,
    StaffOut,
    TaskIn,
    TaskOut,
    TaskPatch,
)
from oneheavy.modules.stays.application.notifications import StaysNotifier
from oneheavy.modules.stays.application.ports import ReservationCalendar, UploadedFile
from oneheavy.modules.stays.application.processes import (
    HandleWhatsAppReply,
    SyncCalendarCommand,
    SyncPropertyCalendar,
    WhatsAppReplyCommand,
)
from oneheavy.modules.stays.application.properties import (
    CreateProperty,
    CreatePropertyCommand,
    GetProperty,
    GetPropertyQuery,
    GetSettings,
    ListProperties,
    ListReceipts,
    ListStaff,
    RegisterStaff,
    RegisterStaffCommand,
    ReviewReceipt,
    ReviewReceiptCommand,
    UpdateProperty,
    UpdatePropertyCommand,
    UpdateSettings,
    UpdateSettingsCommand,
    UploadReceipt,
    UploadReceiptCommand,
)
from oneheavy.modules.stays.application.tasks import (
    CancelTask,
    CancelTaskCommand,
    ChecklistCommand,
    CompleteTask,
    ConfirmArrival,
    EditTask,
    EditTaskCommand,
    GetDashboard,
    GetRequiredPhotos,
    GetTask,
    ListTasks,
    ListTasksQuery,
    PhotosCommand,
    ReportIssue,
    ReportIssueCommand,
    RequiredPhotosQuery,
    ScheduleTask,
    ScheduleTaskCommand,
    StartCleaning,
    TaskQuery,
    UpdateChecklist,
)
from oneheavy.modules.stays.domain.model import ChecklistItem, PhotoMode, TaskStatus
from oneheavy.modules.stays.infrastructure.persistence import SqlStaysUnitOfWork
from oneheavy.shared.domain.access import Principal
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, get_principal

router = APIRouter(prefix="/stays", tags=["Stays"])

CALENDAR_KEY = "stays.calendar"


# ── Dependencias ────────────────────────────────────────────────────────────


def _uow(c: Container = Depends(get_container)) -> SqlStaysUnitOfWork:
    return SqlStaysUnitOfWork(c.session_factory, c.bus)


def _tz(c: Container = Depends(get_container)) -> ZoneInfo:
    return ZoneInfo(c.settings.scheduler_timezone)


def build_notifier(c: Container) -> StaysNotifier:
    return StaysNotifier(
        c.sender, login_url=f"{c.settings.public_app_url}/login", tz=ZoneInfo(c.settings.scheduler_timezone)
    )


def _notifier(c: Container = Depends(get_container)) -> StaysNotifier:
    return build_notifier(c)


def _calendar(c: Container = Depends(get_container)) -> ReservationCalendar:
    calendar: ReservationCalendar = c.extras[CALENDAR_KEY]
    return calendar


async def _files(files: list[UploadFile]) -> list[UploadedFile]:
    return [
        UploadedFile(await f.read(), f.filename or "upload", f.content_type or "application/octet-stream")
        for f in files
    ]


# ── Propiedades ─────────────────────────────────────────────────────────────


@router.get("/properties", response_model=list[PropertyOut])
async def list_properties(
    p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> list[PropertyOut]:
    return [PropertyOut.of(x) for x in await ListProperties(uow).execute(p)]


@router.post("/properties", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
async def create_property(
    body: PropertyIn,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    notifier: StaysNotifier = Depends(_notifier),
) -> PropertyOut:
    data = body.model_dump()
    prop = await CreateProperty(uow, notifier).execute(CreatePropertyCommand(actor=p, **data))
    return PropertyOut.of(prop)


@router.get("/properties/{property_id}", response_model=PropertyOut)
async def get_property(
    property_id: uuid.UUID, p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> PropertyOut:
    return PropertyOut.of(await GetProperty(uow).execute(GetPropertyQuery(p, property_id)))


@router.patch("/properties/{property_id}", response_model=PropertyOut)
async def update_property(
    property_id: uuid.UUID,
    body: PropertyPatch,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
) -> PropertyOut:
    changes = body.model_dump(exclude_unset=True)
    return PropertyOut.of(await UpdateProperty(uow).execute(UpdatePropertyCommand(p, property_id, changes)))


@router.post("/properties/{property_id}/calendar-sync", response_model=CalendarSyncOut)
async def calendar_sync(
    property_id: uuid.UUID,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    calendar: ReservationCalendar = Depends(_calendar),
    tz: ZoneInfo = Depends(_tz),
) -> CalendarSyncOut:
    created = await SyncPropertyCalendar(uow, calendar, tz).execute(SyncCalendarCommand(p, property_id))
    return CalendarSyncOut(created=created)


# ── Comprobantes ────────────────────────────────────────────────────────────


@router.get("/properties/{property_id}/receipts", response_model=list[ReceiptOut])
async def list_receipts(
    property_id: uuid.UUID, p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> list[ReceiptOut]:
    return [ReceiptOut.of(r) for r in await ListReceipts(uow).execute(GetPropertyQuery(p, property_id))]


@router.post(
    "/properties/{property_id}/receipts", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED
)
async def upload_receipt(
    property_id: uuid.UUID,
    file: UploadFile = File(...),
    service: str = Form(...),
    period: str = Form(...),
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    c: Container = Depends(get_container),
) -> ReceiptOut:
    uploaded = (await _files([file]))[0]
    receipt = await UploadReceipt(uow, c.storage).execute(
        UploadReceiptCommand(p, property_id, service, period, uploaded)
    )
    return ReceiptOut.of(receipt)


@router.post("/receipts/{receipt_id}/review", response_model=ReceiptOut)
async def review_receipt(
    receipt_id: uuid.UUID,
    body: ReviewIn,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
) -> ReceiptOut:
    receipt = await ReviewReceipt(uow).execute(ReviewReceiptCommand(p, receipt_id, body.approved, body.note))
    return ReceiptOut.of(receipt)


# ── Personal ────────────────────────────────────────────────────────────────


@router.get("/staff", response_model=list[StaffOut])
async def list_staff(
    p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> list[StaffOut]:
    return [StaffOut.of(s) for s in await ListStaff(uow).execute(p)]


@router.post("/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
async def create_staff(
    body: StaffIn, p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> StaffOut:
    return StaffOut.of(
        await RegisterStaff(uow).execute(RegisterStaffCommand(p, body.name, body.phone, body.category))
    )


# ── Tareas ──────────────────────────────────────────────────────────────────


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    property_id: uuid.UUID | None = None,
    staff_id: uuid.UUID | None = None,
    status_: TaskStatus | None = Query(default=None, alias="status"),
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
) -> list[TaskOut]:
    views = await ListTasks(uow).execute(ListTasksQuery(p, from_, to, property_id, staff_id, status_))
    return [TaskOut.of(v) for v in views]


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def schedule_task(
    body: TaskIn,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    notifier: StaysNotifier = Depends(_notifier),
) -> TaskOut:
    view = await ScheduleTask(uow, notifier).execute(ScheduleTaskCommand(actor=p, **body.model_dump()))
    return TaskOut.of(view)


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: uuid.UUID, p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> TaskOut:
    return TaskOut.of(await GetTask(uow).execute(TaskQuery(p, task_id)))


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def edit_task(
    task_id: uuid.UUID,
    body: TaskPatch,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
) -> TaskOut:
    changes: dict[str, Any] = body.model_dump(exclude_unset=True)
    return TaskOut.of(await EditTask(uow).execute(EditTaskCommand(p, task_id, changes)))


@router.post("/tasks/{task_id}/cancel", response_model=TaskOut)
async def cancel_task(
    task_id: uuid.UUID,
    body: CancelIn,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
) -> TaskOut:
    return TaskOut.of(await CancelTask(uow).execute(CancelTaskCommand(p, task_id, body.reason)))


@router.get("/tasks/{task_id}/required-photos", response_model=RequiredPhotosOut)
async def required_photos(
    task_id: uuid.UUID,
    mode: PhotoMode | None = None,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
) -> RequiredPhotosOut:
    return RequiredPhotosOut(
        items=await GetRequiredPhotos(uow).execute(RequiredPhotosQuery(p, task_id, mode))
    )


@router.post("/tasks/{task_id}/arrival", response_model=TaskOut)
async def confirm_arrival(
    task_id: uuid.UUID,
    photos: list[UploadFile] = File(default=[]),
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    c: Container = Depends(get_container),
) -> TaskOut:
    cmd = PhotosCommand(p, task_id, await _files(photos))
    return TaskOut.of(await ConfirmArrival(uow, c.storage).execute(cmd))


@router.post("/tasks/{task_id}/start", response_model=TaskOut)
async def start_task(
    task_id: uuid.UUID, p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> TaskOut:
    return TaskOut.of(await StartCleaning(uow).execute(TaskQuery(p, task_id)))


@router.put("/tasks/{task_id}/checklist", response_model=TaskOut)
async def update_checklist(
    task_id: uuid.UUID,
    body: ChecklistIn,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
) -> TaskOut:
    items = [ChecklistItem(i.item, i.done) for i in body.items]
    return TaskOut.of(await UpdateChecklist(uow).execute(ChecklistCommand(p, task_id, items)))


@router.post("/tasks/{task_id}/issues", response_model=TaskOut)
async def report_issue(
    task_id: uuid.UUID,
    body: IssueIn,
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    notifier: StaysNotifier = Depends(_notifier),
) -> TaskOut:
    cmd = ReportIssueCommand(p, task_id, body.kind, body.description)
    return TaskOut.of(await ReportIssue(uow, notifier).execute(cmd))


@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
async def complete_task(
    task_id: uuid.UUID,
    photos: list[UploadFile] = File(default=[]),
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    c: Container = Depends(get_container),
) -> TaskOut:
    cmd = PhotosCommand(p, task_id, await _files(photos))
    return TaskOut.of(await CompleteTask(uow, c.storage).execute(cmd))


# ── Tablero y configuración ─────────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(
    p: Principal = Depends(get_principal),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    tz: ZoneInfo = Depends(_tz),
) -> DashboardOut:
    return DashboardOut.of(await GetDashboard(uow, tz).execute(p))


@router.get("/settings", response_model=SettingsOut)
async def get_settings(
    p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> SettingsOut:
    return SettingsOut.of(await GetSettings(uow).execute(p))


@router.put("/settings", response_model=SettingsOut)
async def put_settings(
    body: SettingsIn, p: Principal = Depends(get_principal), uow: SqlStaysUnitOfWork = Depends(_uow)
) -> SettingsOut:
    settings = await UpdateSettings(uow).execute(UpdateSettingsCommand(actor=p, **body.model_dump()))
    return SettingsOut.of(settings)


# ── Webhook WhatsApp (Evolution API) ────────────────────────────────────────


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(
    request: Request,
    token: str = Query(default=""),
    uow: SqlStaysUnitOfWork = Depends(_uow),
    notifier: StaysNotifier = Depends(_notifier),
) -> dict[str, Any]:
    payload = await request.json()
    action = await HandleWhatsAppReply(uow, notifier).execute(
        WhatsAppReplyCommand(token, payload if isinstance(payload, dict) else {})
    )
    return {"ok": True, "action": action}
