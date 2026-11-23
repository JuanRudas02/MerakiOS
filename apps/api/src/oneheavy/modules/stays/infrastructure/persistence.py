"""Adaptador de salida: persistencia SQLAlchemy del contexto Stays."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Self

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint, Uuid, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.stays.application.ports import StaysUnitOfWork
from oneheavy.modules.stays.domain.model import (
    BillingCutoffs,
    ChecklistItem,
    CleaningTask,
    IssueKind,
    Luggage,
    OwnerAccount,
    PhotoMode,
    Property,
    Receipt,
    ReceiptStatus,
    StaffCategory,
    StaffMember,
    StaysSettings,
    TaskIssue,
    TaskStatus,
    to_utc,
)
from oneheavy.modules.stays.domain.repositories import (
    OwnerAccountRepository,
    PropertyRepository,
    ReceiptRepository,
    SettingsRepository,
    StaffRepository,
    TaskFilter,
    TaskRepository,
)
from oneheavy.shared.domain.time import ensure_aware
from oneheavy.shared.domain.value_objects import PhoneNumber
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TenantMixin, TimestampMixin


def _aware(value: datetime | None) -> datetime | None:
    return ensure_aware(value) if value else None


def _phone(value: str | None) -> PhoneNumber | None:
    return PhoneNumber(value) if value else None


# ── ORM ─────────────────────────────────────────────────────────────────────


class PropertyRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "stays_properties"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_stays_properties_tenant_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str | None] = mapped_column(String(300))
    capacity: Mapped[int] = mapped_column(Integer, default=2)
    owner_name: Mapped[str | None] = mapped_column(String(160))
    owner_phone: Mapped[str | None] = mapped_column(String(20), index=True)
    default_staff_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    billing_cutoffs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    checklist_template: Mapped[list[str]] = mapped_column(JSON, default=list)
    visual_inventory: Mapped[list[str]] = mapped_column(JSON, default=list)
    ical_url: Mapped[str | None] = mapped_column(String(1000))
    automation_paused: Mapped[bool] = mapped_column(Boolean, default=False)


class StaffRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "stays_staff"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(20), index=True)
    category: Mapped[str] = mapped_column(String(20), default=StaffCategory.CLEANING.value)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    has_login: Mapped[bool] = mapped_column(Boolean, default=False)


class OwnerAccountRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "stays_owner_accounts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # = user_id en identity
    phone: Mapped[str | None] = mapped_column(String(20))


class TaskRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "stays_tasks"
    __table_args__ = (
        Index("ix_stays_tasks_tenant_scheduled", "tenant_id", "scheduled_at"),
        Index("ix_stays_tasks_status_scheduled", "status", "scheduled_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING.value)
    observations: Mapped[str | None] = mapped_column(Text)
    luggage: Mapped[str] = mapped_column(String(10), default=Luggage.NONE.value)
    supplies_required: Mapped[bool] = mapped_column(Boolean, default=False)
    arrival_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    initial_photos: Mapped[list[str]] = mapped_column(JSON, default=list)
    final_photos: Mapped[list[str]] = mapped_column(JSON, default=list)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(10), default="manual")
    external_ref: Mapped[str | None] = mapped_column(String(300), index=True)
    arrival_prompted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(String(500))


class ReceiptRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "stays_receipts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    service: Mapped[str] = mapped_column(String(30))
    period: Mapped[str] = mapped_column(String(7), index=True)
    url: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), default=ReceiptStatus.PENDING.value)
    note: Mapped[str | None] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class SettingsRow(TimestampMixin, Base):
    __tablename__ = "stays_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    supervisor_phone: Mapped[str | None] = mapped_column(String(20))
    daily_reminder_hour: Mapped[int] = mapped_column(Integer, default=19)
    escalation_minutes: Mapped[int] = mapped_column(Integer, default=10)
    photo_mode: Mapped[str] = mapped_column(String(10), default=PhotoMode.STANDARD.value)
    whatsapp_instance: Mapped[str | None] = mapped_column(String(80))
    webhook_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    templates: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)


# ── Mappers ─────────────────────────────────────────────────────────────────


def _prop_domain(r: PropertyRow) -> Property:
    return Property(
        id=r.id, tenant_id=r.tenant_id, code=r.code, name=r.name, address=r.address, capacity=r.capacity,
        owner_name=r.owner_name, owner_phone=_phone(r.owner_phone), default_staff_id=r.default_staff_id,
        billing_cutoffs=BillingCutoffs(**(r.billing_cutoffs or {})),
        checklist_template=list(r.checklist_template or []), visual_inventory=list(r.visual_inventory or []),
        ical_url=r.ical_url, automation_paused=r.automation_paused,
        created_at=ensure_aware(r.created_at), updated_at=ensure_aware(r.updated_at),
    )  # fmt: skip


def _prop_apply(r: PropertyRow, p: Property) -> None:
    r.tenant_id, r.code, r.name, r.address, r.capacity = p.tenant_id, p.code, p.name, p.address, p.capacity
    r.owner_name, r.owner_phone = p.owner_name, str(p.owner_phone) if p.owner_phone else None
    r.default_staff_id, r.billing_cutoffs = p.default_staff_id, p.billing_cutoffs.as_dict()
    r.checklist_template, r.visual_inventory = list(p.checklist_template), list(p.visual_inventory)
    r.ical_url, r.automation_paused = p.ical_url, p.automation_paused
    r.created_at, r.updated_at = p.created_at, p.updated_at


def _staff_domain(r: StaffRow) -> StaffMember:
    return StaffMember(
        id=r.id, tenant_id=r.tenant_id, name=r.name, phone=_phone(r.phone), category=StaffCategory(r.category),
        active=r.active, has_login=r.has_login, created_at=ensure_aware(r.created_at),
        updated_at=ensure_aware(r.updated_at),
    )  # fmt: skip


def _task_domain(r: TaskRow) -> CleaningTask:
    return CleaningTask(
        id=r.id, tenant_id=r.tenant_id, property_id=r.property_id, staff_id=r.staff_id,
        scheduled_at=ensure_aware(r.scheduled_at), status=TaskStatus(r.status), observations=r.observations,
        luggage=Luggage(r.luggage), supplies_required=r.supplies_required,
        arrival_confirmed_at=_aware(r.arrival_confirmed_at), started_at=_aware(r.started_at),
        completed_at=_aware(r.completed_at),
        checklist=[ChecklistItem(c["item"], bool(c["done"])) for c in r.checklist or []],
        initial_photos=list(r.initial_photos or []), final_photos=list(r.final_photos or []),
        issues=[
            TaskIssue(
                IssueKind(i["kind"]), i["description"], ensure_aware(datetime.fromisoformat(i["reported_at"])),
                uuid.UUID(i["reported_by"]) if i.get("reported_by") else None,
            )
            for i in r.issues or []
        ],
        source=r.source, external_ref=r.external_ref, arrival_prompted_at=_aware(r.arrival_prompted_at),
        escalated_at=_aware(r.escalated_at), cancel_reason=r.cancel_reason,
        created_at=ensure_aware(r.created_at), updated_at=ensure_aware(r.updated_at),
    )  # fmt: skip


def _task_apply(r: TaskRow, t: CleaningTask) -> None:
    r.tenant_id, r.property_id, r.staff_id = t.tenant_id, t.property_id, t.staff_id
    r.scheduled_at, r.status, r.observations = to_utc(t.scheduled_at), t.status.value, t.observations
    r.luggage, r.supplies_required = t.luggage.value, t.supplies_required
    r.arrival_confirmed_at, r.started_at, r.completed_at = (
        t.arrival_confirmed_at,
        t.started_at,
        t.completed_at,
    )
    r.checklist = [{"item": c.item, "done": c.done} for c in t.checklist]
    r.initial_photos, r.final_photos = list(t.initial_photos), list(t.final_photos)
    r.issues = [
        {
            "kind": i.kind.value,
            "description": i.description,
            "reported_at": i.reported_at.isoformat(),
            "reported_by": str(i.reported_by) if i.reported_by else None,
        }
        for i in t.issues
    ]
    r.source, r.external_ref = t.source, t.external_ref
    r.arrival_prompted_at, r.escalated_at, r.cancel_reason = (
        t.arrival_prompted_at,
        t.escalated_at,
        t.cancel_reason,
    )
    r.created_at, r.updated_at = t.created_at, t.updated_at


def _receipt_domain(r: ReceiptRow) -> Receipt:
    return Receipt(
        id=r.id, tenant_id=r.tenant_id, property_id=r.property_id, service=r.service, period=r.period, url=r.url,
        status=ReceiptStatus(r.status), note=r.note, uploaded_at=ensure_aware(r.uploaded_at),
        reviewed_at=_aware(r.reviewed_at), reviewed_by=r.reviewed_by,
        created_at=ensure_aware(r.created_at), updated_at=ensure_aware(r.updated_at),
    )  # fmt: skip


def _receipt_apply(r: ReceiptRow, x: Receipt) -> None:
    r.tenant_id, r.property_id, r.service, r.period, r.url = (
        x.tenant_id,
        x.property_id,
        x.service,
        x.period,
        x.url,
    )
    r.status, r.note, r.uploaded_at = x.status.value, x.note, x.uploaded_at
    r.reviewed_at, r.reviewed_by, r.created_at, r.updated_at = (
        x.reviewed_at,
        x.reviewed_by,
        x.created_at,
        x.updated_at,
    )


def _settings_domain(r: SettingsRow) -> StaysSettings:
    return StaysSettings(
        id=r.tenant_id, tenant_id=r.tenant_id, supervisor_phone=_phone(r.supervisor_phone),
        daily_reminder_hour=r.daily_reminder_hour, escalation_minutes=r.escalation_minutes,
        photo_mode=PhotoMode(r.photo_mode), whatsapp_instance=r.whatsapp_instance, webhook_token=r.webhook_token,
        templates=dict(r.templates or {}), created_at=ensure_aware(r.created_at),
        updated_at=ensure_aware(r.updated_at),
    )  # fmt: skip


# ── Repositorios ────────────────────────────────────────────────────────────


class SqlPropertyRepository(PropertyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID, property_id: uuid.UUID) -> Property | None:
        row = await self._s.get(PropertyRow, property_id)
        return _prop_domain(row) if row and row.tenant_id == tenant_id else None

    async def list_all(self, tenant_id: uuid.UUID, *, owner_phone: str | None = None) -> list[Property]:
        stmt = select(PropertyRow).where(PropertyRow.tenant_id == tenant_id)
        if owner_phone is not None:
            stmt = stmt.where(PropertyRow.owner_phone == owner_phone)
        return [_prop_domain(r) for r in await self._s.scalars(stmt.order_by(PropertyRow.code))]

    async def get_many(self, tenant_id: uuid.UUID, ids: set[uuid.UUID]) -> dict[uuid.UUID, Property]:
        if not ids:
            return {}
        stmt = select(PropertyRow).where(PropertyRow.tenant_id == tenant_id, PropertyRow.id.in_(ids))
        return {r.id: _prop_domain(r) for r in await self._s.scalars(stmt)}

    async def code_exists(self, tenant_id: uuid.UUID, code: str, *, exclude: uuid.UUID | None = None) -> bool:
        stmt = select(PropertyRow.id).where(PropertyRow.tenant_id == tenant_id, PropertyRow.code == code)
        if exclude:
            stmt = stmt.where(PropertyRow.id != exclude)
        return (await self._s.scalar(stmt)) is not None

    async def list_all_with_cutoffs(self) -> list[Property]:
        rows = await self._s.scalars(select(PropertyRow).where(PropertyRow.automation_paused.is_(False)))
        return [p for p in map(_prop_domain, rows) if p.billing_cutoffs.configured()]

    async def add(self, prop: Property) -> None:
        row = PropertyRow(id=prop.id)
        _prop_apply(row, prop)
        self._s.add(row)

    async def update(self, prop: Property) -> None:
        row = await self._s.get(PropertyRow, prop.id)
        if row is not None:
            _prop_apply(row, prop)


class SqlStaffRepository(StaffRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> StaffMember | None:
        row = await self._s.get(StaffRow, staff_id)
        return _staff_domain(row) if row and row.tenant_id == tenant_id else None

    async def list_all(self, tenant_id: uuid.UUID) -> list[StaffMember]:
        stmt = select(StaffRow).where(StaffRow.tenant_id == tenant_id).order_by(StaffRow.name)
        return [_staff_domain(r) for r in await self._s.scalars(stmt)]

    async def get_many(self, tenant_id: uuid.UUID, ids: set[uuid.UUID]) -> dict[uuid.UUID, StaffMember]:
        if not ids:
            return {}
        stmt = select(StaffRow).where(StaffRow.tenant_id == tenant_id, StaffRow.id.in_(ids))
        return {r.id: _staff_domain(r) for r in await self._s.scalars(stmt)}

    async def upsert(self, staff: StaffMember) -> None:
        row = await self._s.get(StaffRow, staff.id)
        if row is None:
            row = StaffRow(id=staff.id, created_at=staff.created_at)
            self._s.add(row)
        row.tenant_id, row.name, row.phone = (
            staff.tenant_id,
            staff.name,
            str(staff.phone) if staff.phone else None,
        )
        row.category, row.active, row.has_login = staff.category.value, staff.active, staff.has_login
        row.updated_at = staff.updated_at


class SqlTaskRepository(TaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID, task_id: uuid.UUID) -> CleaningTask | None:
        row = await self._s.get(TaskRow, task_id)
        return _task_domain(row) if row and row.tenant_id == tenant_id else None

    async def search(self, tenant_id: uuid.UUID, flt: TaskFilter) -> list[CleaningTask]:
        stmt = select(TaskRow).where(TaskRow.tenant_id == tenant_id)
        if flt.start:
            stmt = stmt.where(TaskRow.scheduled_at >= to_utc(flt.start))
        if flt.end:
            stmt = stmt.where(TaskRow.scheduled_at < to_utc(flt.end))
        if flt.property_id:
            stmt = stmt.where(TaskRow.property_id == flt.property_id)
        if flt.staff_id:
            stmt = stmt.where(TaskRow.staff_id == flt.staff_id)
        if flt.status:
            stmt = stmt.where(TaskRow.status == flt.status.value)
        stmt = stmt.order_by(TaskRow.scheduled_at)
        if flt.limit:
            stmt = stmt.limit(flt.limit)
        return [_task_domain(r) for r in await self._s.scalars(stmt)]

    async def list_between_all_tenants(
        self, start: datetime, end: datetime, *, status: TaskStatus | None = None
    ) -> list[CleaningTask]:
        stmt = select(TaskRow).where(
            TaskRow.scheduled_at >= to_utc(start), TaskRow.scheduled_at < to_utc(end)
        )
        if status:
            stmt = stmt.where(TaskRow.status == status.value)
        return [_task_domain(r) for r in await self._s.scalars(stmt.order_by(TaskRow.scheduled_at))]

    async def exists_for_property(
        self, tenant_id: uuid.UUID, property_id: uuid.UUID, start: datetime, end: datetime
    ) -> bool:
        stmt = select(TaskRow.id).where(
            TaskRow.tenant_id == tenant_id,
            TaskRow.property_id == property_id,
            TaskRow.scheduled_at >= to_utc(start),
            TaskRow.scheduled_at < to_utc(end),
            TaskRow.status != TaskStatus.CANCELLED.value,
        )
        return (await self._s.scalar(stmt.limit(1))) is not None

    async def find_by_external_ref(self, tenant_id: uuid.UUID, external_ref: str) -> CleaningTask | None:
        stmt = select(TaskRow).where(TaskRow.tenant_id == tenant_id, TaskRow.external_ref == external_ref)
        row = await self._s.scalar(stmt.limit(1))
        return _task_domain(row) if row else None

    async def add(self, task: CleaningTask) -> None:
        row = TaskRow(id=task.id)
        _task_apply(row, task)
        self._s.add(row)

    async def update(self, task: CleaningTask) -> None:
        row = await self._s.get(TaskRow, task.id)
        if row is not None:
            _task_apply(row, task)


class SqlReceiptRepository(ReceiptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID, receipt_id: uuid.UUID) -> Receipt | None:
        row = await self._s.get(ReceiptRow, receipt_id)
        return _receipt_domain(row) if row and row.tenant_id == tenant_id else None

    async def list_by_property(self, tenant_id: uuid.UUID, property_id: uuid.UUID) -> list[Receipt]:
        stmt = (
            select(ReceiptRow)
            .where(ReceiptRow.tenant_id == tenant_id, ReceiptRow.property_id == property_id)
            .order_by(ReceiptRow.uploaded_at.desc())
        )
        return [_receipt_domain(r) for r in await self._s.scalars(stmt)]

    async def has_pending(self, tenant_id: uuid.UUID, property_id: uuid.UUID) -> bool:
        stmt = select(ReceiptRow.id).where(
            ReceiptRow.tenant_id == tenant_id,
            ReceiptRow.property_id == property_id,
            ReceiptRow.status == ReceiptStatus.PENDING.value,
        )
        return (await self._s.scalar(stmt.limit(1))) is not None

    async def verified_services(
        self, property_ids: set[uuid.UUID], period: str
    ) -> set[tuple[uuid.UUID, str]]:
        if not property_ids:
            return set()
        stmt = select(ReceiptRow.property_id, ReceiptRow.service).where(
            ReceiptRow.property_id.in_(property_ids),
            ReceiptRow.period == period,
            ReceiptRow.status == ReceiptStatus.VERIFIED.value,
        )
        return {(pid, svc) for pid, svc in (await self._s.execute(stmt)).all()}

    async def add(self, receipt: Receipt) -> None:
        row = ReceiptRow(id=receipt.id)
        _receipt_apply(row, receipt)
        self._s.add(row)

    async def update(self, receipt: Receipt) -> None:
        row = await self._s.get(ReceiptRow, receipt.id)
        if row is not None:
            _receipt_apply(row, receipt)


class SqlSettingsRepository(SettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID) -> StaysSettings:
        row = await self._s.get(SettingsRow, tenant_id)
        return _settings_domain(row) if row else StaysSettings.default(tenant_id)

    async def get_many(self, tenant_ids: set[uuid.UUID]) -> dict[uuid.UUID, StaysSettings]:
        found: dict[uuid.UUID, StaysSettings] = {}
        if tenant_ids:
            rows = await self._s.scalars(select(SettingsRow).where(SettingsRow.tenant_id.in_(tenant_ids)))
            found = {r.tenant_id: _settings_domain(r) for r in rows}
        return {tid: found.get(tid) or StaysSettings.default(tid) for tid in tenant_ids}

    async def find_by_webhook_token(self, token: str) -> StaysSettings | None:
        row = await self._s.scalar(select(SettingsRow).where(SettingsRow.webhook_token == token))
        return _settings_domain(row) if row else None

    async def save(self, settings: StaysSettings) -> None:
        row = await self._s.get(SettingsRow, settings.tenant_id)
        if row is None:
            row = SettingsRow(tenant_id=settings.tenant_id, created_at=settings.created_at)
            self._s.add(row)
        row.supervisor_phone = str(settings.supervisor_phone) if settings.supervisor_phone else None
        row.daily_reminder_hour, row.escalation_minutes = (
            settings.daily_reminder_hour,
            settings.escalation_minutes,
        )
        row.photo_mode, row.whatsapp_instance = settings.photo_mode.value, settings.whatsapp_instance
        row.webhook_token, row.templates = settings.webhook_token, dict(settings.templates)


class SqlOwnerAccountRepository(OwnerAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> OwnerAccount | None:
        row = await self._s.get(OwnerAccountRow, user_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return OwnerAccount(id=row.id, tenant_id=row.tenant_id, phone=_phone(row.phone))

    async def upsert(self, account: OwnerAccount) -> None:
        row = await self._s.get(OwnerAccountRow, account.id)
        if row is None:
            row = OwnerAccountRow(id=account.id)
            self._s.add(row)
        row.tenant_id, row.phone = account.tenant_id, str(account.phone) if account.phone else None


class SqlStaysUnitOfWork(SqlAlchemyUnitOfWork, StaysUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.properties = SqlPropertyRepository(self.session)
        self.staff = SqlStaffRepository(self.session)
        self.tasks = SqlTaskRepository(self.session)
        self.receipts = SqlReceiptRepository(self.session)
        self.settings = SqlSettingsRepository(self.session)
        self.owners = SqlOwnerAccountRepository(self.session)
        return self
