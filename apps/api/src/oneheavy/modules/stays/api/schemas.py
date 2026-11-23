"""Esquemas HTTP (Pydantic) del contexto Stays — ver docs/architecture/api-contract.md."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from oneheavy.modules.stays.application.tasks import Dashboard, TaskView
from oneheavy.modules.stays.domain.model import (
    IssueKind,
    Luggage,
    PhotoMode,
    Property,
    Receipt,
    StaffCategory,
    StaffMember,
    StaysSettings,
    TaskStatus,
)


class BillingCutoffsIO(BaseModel):
    administration: int | None = Field(default=None, ge=1, le=31)
    electricity: int | None = Field(default=None, ge=1, le=31)
    water: int | None = Field(default=None, ge=1, le=31)
    gas: int | None = Field(default=None, ge=1, le=31)
    internet: int | None = Field(default=None, ge=1, le=31)
    insurance: int | None = Field(default=None, ge=1, le=31)


class PropertyIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    address: str | None = Field(default=None, max_length=300)
    capacity: int = Field(default=2, ge=1, le=100)
    owner_name: str | None = Field(default=None, max_length=160)
    owner_phone: str | None = None
    default_staff_id: uuid.UUID | None = None
    billing_cutoffs: BillingCutoffsIO = Field(default_factory=BillingCutoffsIO)
    checklist_template: list[str] = Field(default_factory=list)
    visual_inventory: list[str] = Field(default_factory=list)
    ical_url: str | None = Field(default=None, max_length=1000)


class PropertyPatch(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    address: str | None = None
    capacity: int | None = Field(default=None, ge=1, le=100)
    owner_name: str | None = None
    owner_phone: str | None = None
    default_staff_id: uuid.UUID | None = None
    billing_cutoffs: BillingCutoffsIO | None = None
    checklist_template: list[str] | None = None
    visual_inventory: list[str] | None = None
    ical_url: str | None = None


class PropertyOut(PropertyIn):
    id: uuid.UUID
    automation_paused: bool
    created_at: datetime

    @classmethod
    def of(cls, p: Property) -> PropertyOut:
        return cls(
            id=p.id, code=p.code, name=p.name, address=p.address, capacity=p.capacity, owner_name=p.owner_name,
            owner_phone=str(p.owner_phone) if p.owner_phone else None, default_staff_id=p.default_staff_id,
            billing_cutoffs=BillingCutoffsIO(**p.billing_cutoffs.as_dict()),
            checklist_template=p.checklist_template, visual_inventory=p.visual_inventory, ical_url=p.ical_url,
            automation_paused=p.automation_paused, created_at=p.created_at,
        )  # fmt: skip


class ReceiptOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    service: str
    period: str
    url: str
    status: str
    note: str | None
    uploaded_at: datetime
    reviewed_at: datetime | None

    @classmethod
    def of(cls, r: Receipt) -> ReceiptOut:
        return cls(
            id=r.id, property_id=r.property_id, service=r.service, period=r.period, url=r.url,
            status=r.status.value, note=r.note, uploaded_at=r.uploaded_at, reviewed_at=r.reviewed_at,
        )  # fmt: skip


class ReviewIn(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=500)


class StaffIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    phone: str
    category: StaffCategory = StaffCategory.CLEANING


class StaffOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    category: StaffCategory
    active: bool
    has_login: bool

    @classmethod
    def of(cls, s: StaffMember) -> StaffOut:
        return cls(
            id=s.id, name=s.name, phone=str(s.phone) if s.phone else "", category=s.category, active=s.active,
            has_login=s.has_login,
        )  # fmt: skip


class TaskIn(BaseModel):
    property_id: uuid.UUID
    staff_id: uuid.UUID | None = None
    scheduled_at: datetime
    observations: str | None = Field(default=None, max_length=2000)
    luggage: Luggage = Luggage.NONE
    supplies_required: bool = False


class TaskPatch(BaseModel):
    staff_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None
    observations: str | None = Field(default=None, max_length=2000)
    luggage: Luggage | None = None
    supplies_required: bool | None = None


class CancelIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ChecklistItemIO(BaseModel):
    item: str
    done: bool


class ChecklistIn(BaseModel):
    items: list[ChecklistItemIO]


class IssueIn(BaseModel):
    kind: IssueKind
    description: str = Field(min_length=3, max_length=1000)


class IssueOut(BaseModel):
    kind: IssueKind
    description: str
    reported_at: datetime


class TaskOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    property_name: str | None
    staff_id: uuid.UUID | None
    staff_name: str | None
    scheduled_at: datetime
    status: TaskStatus
    observations: str | None
    luggage: Luggage
    supplies_required: bool
    arrival_confirmed_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    checklist: list[ChecklistItemIO]
    initial_photos: list[str]
    final_photos: list[str]
    issues: list[IssueOut]

    @classmethod
    def of(cls, v: TaskView) -> TaskOut:
        t = v.task
        return cls(
            id=t.id, property_id=t.property_id, property_name=v.property_name, staff_id=t.staff_id,
            staff_name=v.staff_name, scheduled_at=t.scheduled_at, status=t.status, observations=t.observations,
            luggage=t.luggage, supplies_required=t.supplies_required, arrival_confirmed_at=t.arrival_confirmed_at,
            started_at=t.started_at, completed_at=t.completed_at,
            checklist=[ChecklistItemIO(item=c.item, done=c.done) for c in t.checklist],
            initial_photos=t.initial_photos, final_photos=t.final_photos,
            issues=[IssueOut(kind=i.kind, description=i.description, reported_at=i.reported_at) for i in t.issues],
        )  # fmt: skip


class RequiredPhotosOut(BaseModel):
    items: list[str]


class CalendarSyncOut(BaseModel):
    created: int


class StaffRankOut(BaseModel):
    staff_id: uuid.UUID
    name: str
    completed: int
    on_time_rate: float
    avg_minutes: float


class TodayOut(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    cancelled: int


class WeekOut(BaseModel):
    completed: int
    on_time_rate: float
    avg_cleaning_minutes: float
    issues: int


class DashboardOut(BaseModel):
    today: TodayOut
    week: WeekOut
    staff_ranking: list[StaffRankOut]
    upcoming: list[TaskOut]

    @classmethod
    def of(cls, d: Dashboard) -> DashboardOut:
        return cls(
            today=TodayOut(**d.today),
            week=WeekOut(**d.week),  # type: ignore[arg-type]
            staff_ranking=[StaffRankOut(**r.__dict__) for r in d.staff_ranking],
            upcoming=[TaskOut.of(v) for v in d.upcoming],
        )


class SettingsIn(BaseModel):
    supervisor_phone: str | None = None
    daily_reminder_hour: int = Field(default=19, ge=0, le=23)
    escalation_minutes: int = Field(default=10, ge=1, le=240)
    photo_mode: PhotoMode = PhotoMode.STANDARD
    whatsapp_instance: str | None = Field(default=None, max_length=80)


class SettingsOut(SettingsIn):
    webhook_token: str

    @classmethod
    def of(cls, s: StaysSettings) -> SettingsOut:
        return cls(
            supervisor_phone=str(s.supervisor_phone) if s.supervisor_phone else None,
            daily_reminder_hour=s.daily_reminder_hour, escalation_minutes=s.escalation_minutes,
            photo_mode=s.photo_mode, whatsapp_instance=s.whatsapp_instance, webhook_token=s.webhook_token,
        )  # fmt: skip
