"""Dominio de Stays: operación de alquileres de corta estadía.

Agregados:
- Property      unidad administrada (ex "Apartment" de 1heavy Stays) con cortes de servicios.
- Receipt       comprobante de pago de un servicio subido por el propietario.
- StaffMember   personal operativo (limpieza / mantenimiento).
- CleaningTask  tarea de limpieza con máquina de estados explícita.
- StaysSettings configuración operativa por workspace (supervisor, horarios, plantillas).

Reglas de negocio (REG) heredadas del levantamiento original de Stays:
- REG-07/15  La llegada se confirma con fotos de evidencia.
- REG-10     El checklist debe estar completo antes de finalizar.
- REG-11     Las fotos finales son obligatorias para finalizar.
- REG-03     Una tarea sólo se edita mientras está pendiente.
"""

from __future__ import annotations

import calendar
import re
import secrets
import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.entity import Entity, TenantEntity
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.domain.time import ensure_aware, utc_now
from oneheavy.shared.domain.value_objects import PhoneNumber

DEFAULT_CHECKLIST = ["Cama", "Baño", "Cocina", "Sala"]
STANDARD_PHOTOS = ["Cama", "Baño", "Cocina", "Sala"]


def to_utc(value: datetime) -> datetime:
    return ensure_aware(value).astimezone(UTC)


# ── Property ────────────────────────────────────────────────────────────────


class Service(StrEnum):
    ADMINISTRATION = "administration"
    ELECTRICITY = "electricity"
    WATER = "water"
    GAS = "gas"
    INTERNET = "internet"
    INSURANCE = "insurance"

    @property
    def label(self) -> str:
        return SERVICE_LABELS[self]


SERVICE_LABELS = {
    Service.ADMINISTRATION: "Administración",
    Service.ELECTRICITY: "Luz / Energía",
    Service.WATER: "Agua",
    Service.GAS: "Gas",
    Service.INTERNET: "Internet",
    Service.INSURANCE: "Seguro / Póliza",
}


@dataclass(frozen=True)
class BillingCutoffs:
    """Día de corte (1-31) de cada servicio. `None` = servicio no gestionado."""

    administration: int | None = None
    electricity: int | None = None
    water: int | None = None
    gas: int | None = None
    internet: int | None = None
    insurance: int | None = None

    def __post_init__(self) -> None:
        for service, day in self.items():
            if day is not None and not 1 <= day <= 31:
                raise BusinessRuleViolation(
                    f"Día de corte inválido para {service.label}: {day}", code="invalid_cutoff"
                )

    def items(self) -> list[tuple[Service, int | None]]:
        return [(s, getattr(self, s.value)) for s in Service]

    def configured(self) -> list[tuple[Service, int]]:
        return [(s, d) for s, d in self.items() if d is not None]

    def as_dict(self) -> dict[str, int | None]:
        return {s.value: d for s, d in self.items()}

    @staticmethod
    def due_date(day: int, year: int, month: int) -> date:
        """Si el mes no tiene ese día (p. ej. 31 en febrero) vence el último día."""
        return date(year, month, min(day, calendar.monthrange(year, month)[1]))


@dataclass(kw_only=True, eq=False)
class Property(TenantEntity):
    code: str
    name: str
    address: str | None = None
    capacity: int = 2
    owner_name: str | None = None
    owner_phone: PhoneNumber | None = None
    default_staff_id: uuid.UUID | None = None
    billing_cutoffs: BillingCutoffs = field(default_factory=BillingCutoffs)
    checklist_template: list[str] = field(default_factory=list)
    visual_inventory: list[str] = field(default_factory=list)
    ical_url: str | None = None
    automation_paused: bool = False

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        self.code = self.code.strip()
        self.name = self.name.strip()
        if not self.code or not self.name:
            raise BusinessRuleViolation("La propiedad necesita código y nombre")
        if self.capacity < 1:
            raise BusinessRuleViolation("La capacidad debe ser al menos 1")
        if self.ical_url and not re.match(r"^(https?|webcal)://", self.ical_url):
            raise BusinessRuleViolation("La URL del calendario iCal no es válida", code="invalid_ical_url")
        self.checklist_template = [i.strip() for i in self.checklist_template if i.strip()]
        self.visual_inventory = [i.strip() for i in self.visual_inventory if i.strip()]

    _EDITABLE = frozenset(
        {
            "code", "name", "address", "capacity", "owner_name", "owner_phone", "default_staff_id",
            "billing_cutoffs", "checklist_template", "visual_inventory", "ical_url",
        }
    )  # fmt: skip

    def update(self, changes: dict[str, Any]) -> None:
        unknown = set(changes) - self._EDITABLE
        if unknown:
            raise BusinessRuleViolation(f"Campos no editables: {sorted(unknown)}")
        for key, value in changes.items():
            setattr(self, key, value)
        self._validate()
        self.touch()

    def effective_checklist(self) -> list[str]:
        return list(self.checklist_template) or list(DEFAULT_CHECKLIST)

    def pause_automation(self) -> None:
        self.automation_paused = True
        self.touch()

    def resume_automation(self) -> None:
        self.automation_paused = False
        self.touch()


# ── Receipt ─────────────────────────────────────────────────────────────────


class ReceiptStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@dataclass(kw_only=True, eq=False)
class Receipt(TenantEntity):
    property_id: uuid.UUID
    service: str
    period: str  # YYYY-MM
    url: str
    status: ReceiptStatus = ReceiptStatus.PENDING
    note: str | None = None
    uploaded_at: datetime = field(default_factory=utc_now)
    reviewed_at: datetime | None = None
    reviewed_by: uuid.UUID | None = None

    @classmethod
    def upload(
        cls, *, tenant_id: uuid.UUID, property_id: uuid.UUID, service: str, period: str, url: str
    ) -> Receipt:
        if service not in {s.value for s in Service} and service != "general":
            raise BusinessRuleViolation(f"Servicio desconocido: {service}", code="invalid_service")
        if not _PERIOD_RE.match(period):
            raise BusinessRuleViolation("El periodo debe tener formato YYYY-MM", code="invalid_period")
        return cls(tenant_id=tenant_id, property_id=property_id, service=service, period=period, url=url)

    def review(self, *, approved: bool, reviewer_id: uuid.UUID, note: str | None = None) -> None:
        if self.status is not ReceiptStatus.PENDING:
            raise BusinessRuleViolation("El comprobante ya fue revisado", code="receipt_already_reviewed")
        self.status = ReceiptStatus.VERIFIED if approved else ReceiptStatus.REJECTED
        self.note = note
        self.reviewed_at = utc_now()
        self.reviewed_by = reviewer_id
        self.touch()
        if approved:
            self.record(
                ie.ReceiptVerified(
                    tenant_id=self.tenant_id,
                    actor_id=reviewer_id,
                    property_id=self.property_id,
                    receipt_id=self.id,
                    service=self.service,
                )
            )


# ── Staff ───────────────────────────────────────────────────────────────────


class StaffCategory(StrEnum):
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"


@dataclass(kw_only=True, eq=False)
class StaffMember(Entity):
    tenant_id: uuid.UUID
    name: str
    phone: PhoneNumber | None = None
    category: StaffCategory = StaffCategory.CLEANING
    active: bool = True
    has_login: bool = False


@dataclass(kw_only=True, eq=False)
class OwnerAccount(Entity):
    """Usuario con rol property_owner y su teléfono (para filtrar sus unidades)."""

    tenant_id: uuid.UUID
    phone: PhoneNumber | None = None


# ── Settings ────────────────────────────────────────────────────────────────


class PhotoMode(StrEnum):
    STANDARD = "standard"
    RANDOM = "random"


@dataclass(kw_only=True, eq=False)
class StaysSettings(Entity):
    """Configuración por workspace. Reemplaza la variable global SUPERVISOR_PHONE."""

    tenant_id: uuid.UUID
    supervisor_phone: PhoneNumber | None = None
    daily_reminder_hour: int = 19
    escalation_minutes: int = 10
    photo_mode: PhotoMode = PhotoMode.STANDARD
    whatsapp_instance: str | None = None
    webhook_token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    templates: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.daily_reminder_hour <= 23:
            raise BusinessRuleViolation("La hora de recordatorio debe estar entre 0 y 23")
        if not 1 <= self.escalation_minutes <= 240:
            raise BusinessRuleViolation("Los minutos de escalamiento deben estar entre 1 y 240")

    @classmethod
    def default(cls, tenant_id: uuid.UUID) -> StaysSettings:
        return cls(id=tenant_id, tenant_id=tenant_id)

    def template(self, key: str, default: str) -> str:
        return self.templates.get(key, default)


# ── CleaningTask ────────────────────────────────────────────────────────────


class TaskStatus(StrEnum):
    PENDING = "pending"
    ARRIVED = "arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


TERMINAL = {TaskStatus.COMPLETED, TaskStatus.CANCELLED}


class Luggage(StrEnum):
    NONE = "none"
    LEAVE = "leave"
    COLLECT = "collect"


class IssueKind(StrEnum):
    PROBLEM = "problem"
    MISSING_SUPPLIES = "missing_supplies"
    GUESTS_NOT_OUT = "guests_not_out"


@dataclass(frozen=True)
class ChecklistItem:
    item: str
    done: bool = False


@dataclass(frozen=True)
class TaskIssue:
    kind: IssueKind
    description: str
    reported_at: datetime
    reported_by: uuid.UUID | None = None


@dataclass(kw_only=True, eq=False)
class CleaningTask(TenantEntity):
    property_id: uuid.UUID
    staff_id: uuid.UUID | None
    scheduled_at: datetime
    status: TaskStatus = TaskStatus.PENDING
    observations: str | None = None
    luggage: Luggage = Luggage.NONE
    supplies_required: bool = False
    arrival_confirmed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    checklist: list[ChecklistItem] = field(default_factory=list)
    initial_photos: list[str] = field(default_factory=list)
    final_photos: list[str] = field(default_factory=list)
    issues: list[TaskIssue] = field(default_factory=list)
    source: str = "manual"  # manual | ical
    external_ref: str | None = None  # UID del evento iCal (deduplicación)
    arrival_prompted_at: datetime | None = None
    escalated_at: datetime | None = None
    cancel_reason: str | None = None

    # ── creación ─────────────────────────────────────────────────────────

    @classmethod
    def schedule(
        cls,
        *,
        tenant_id: uuid.UUID,
        prop: Property,
        staff_id: uuid.UUID | None,
        scheduled_at: datetime,
        observations: str | None = None,
        luggage: Luggage = Luggage.NONE,
        supplies_required: bool = False,
        actor_id: uuid.UUID | None = None,
        source: str = "manual",
        external_ref: str | None = None,
    ) -> CleaningTask:
        task = cls(
            tenant_id=tenant_id,
            property_id=prop.id,
            staff_id=staff_id,
            scheduled_at=to_utc(scheduled_at),
            observations=(observations or "").strip() or None,
            luggage=luggage,
            supplies_required=supplies_required,
            checklist=[ChecklistItem(i) for i in prop.effective_checklist()],
            source=source,
            external_ref=external_ref,
        )
        task.record(
            ie.CleaningTaskScheduled(
                tenant_id=tenant_id,
                actor_id=actor_id,
                task_id=task.id,
                property_id=prop.id,
                staff_id=staff_id,
                scheduled_at=task.scheduled_at,
            )
        )
        return task

    # ── administración ───────────────────────────────────────────────────

    def _require(self, *allowed: TaskStatus, action: str) -> None:
        if self.status not in allowed:
            raise BusinessRuleViolation(
                f"No se puede {action} una tarea en estado '{self.status}'", code="invalid_task_state"
            )

    def edit(
        self,
        *,
        staff_id: uuid.UUID | object | None = ...,
        scheduled_at: datetime | None = None,
        observations: str | object | None = ...,
        luggage: Luggage | None = None,
        supplies_required: bool | None = None,
    ) -> None:
        """REG-03: sólo se edita en estado pendiente."""
        self._require(TaskStatus.PENDING, action="editar")
        if staff_id is not ...:
            self.staff_id = staff_id  # type: ignore[assignment]
        if scheduled_at is not None:
            self.scheduled_at = to_utc(scheduled_at)
            self.arrival_prompted_at = None
            self.escalated_at = None
        if observations is not ...:
            self.observations = observations  # type: ignore[assignment]
        if luggage is not None:
            self.luggage = luggage
        if supplies_required is not None:
            self.supplies_required = supplies_required
        self.touch()

    def cancel(self, reason: str) -> None:
        if self.status in TERMINAL:
            raise BusinessRuleViolation("La tarea ya está cerrada", code="invalid_task_state")
        if not reason.strip():
            raise BusinessRuleViolation("Se requiere un motivo de cancelación")
        self.status = TaskStatus.CANCELLED
        self.cancel_reason = reason.strip()
        self.touch()

    # ── ejecución ────────────────────────────────────────────────────────

    def minutes_late(self) -> int | None:
        if self.arrival_confirmed_at is None:
            return None
        return int((self.arrival_confirmed_at - self.scheduled_at).total_seconds() // 60)

    def _mark_arrival(self, now: datetime, actor_id: uuid.UUID | None) -> None:
        self.arrival_confirmed_at = to_utc(now)
        self.status = TaskStatus.ARRIVED
        self.record(
            ie.CleaningArrivalConfirmed(
                tenant_id=self.tenant_id,
                actor_id=actor_id,
                task_id=self.id,
                staff_id=self.staff_id,
                minutes_late=self.minutes_late() or 0,
            )
        )

    def confirm_arrival(self, photos: list[str], now: datetime, actor_id: uuid.UUID | None = None) -> None:
        """CU-07/CU-10. Desde pendiente registra llegada; si ya llegó por WhatsApp adjunta las fotos."""
        if not photos:
            raise BusinessRuleViolation(
                "Las fotos de llegada son obligatorias (REG-07)", code="photos_required"
            )
        if self.status is TaskStatus.ARRIVED and not self.initial_photos:
            self.initial_photos = list(photos)
            self.touch()
            return
        self._require(TaskStatus.PENDING, action="confirmar llegada de")
        self.initial_photos = list(photos)
        self._mark_arrival(now, actor_id)
        self.touch()

    def acknowledge_arrival(self, now: datetime) -> None:
        """Llegada confirmada con el botón de WhatsApp: las fotos se exigen antes de iniciar."""
        self._require(TaskStatus.PENDING, action="confirmar llegada de")
        self._mark_arrival(now, self.staff_id)
        self.touch()

    def start(self, now: datetime) -> None:
        """CU-08."""
        self._require(TaskStatus.ARRIVED, action="iniciar")
        if not self.initial_photos:
            raise BusinessRuleViolation(
                "Sube las fotos de llegada antes de iniciar (REG-15)", code="photos_required"
            )
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = to_utc(now)
        self.touch()

    def update_checklist(self, items: list[ChecklistItem]) -> None:
        """CU-16."""
        self._require(TaskStatus.ARRIVED, TaskStatus.IN_PROGRESS, action="actualizar el checklist de")
        known = {c.item for c in self.checklist}
        unknown = [i.item for i in items if i.item not in known]
        if unknown:
            raise BusinessRuleViolation(
                f"Ítems fuera del checklist: {unknown}", code="unknown_checklist_item"
            )
        updates = {i.item: i.done for i in items}
        self.checklist = [replace(c, done=updates.get(c.item, c.done)) for c in self.checklist]
        self.touch()

    @property
    def checklist_completed(self) -> bool:
        return all(c.done for c in self.checklist)

    def report_issue(
        self, kind: IssueKind, description: str, now: datetime, actor_id: uuid.UUID | None = None
    ) -> TaskIssue:
        """CU-09 / CU-22. Antes se concatenaba en `observations`; ahora es una lista tipada."""
        if self.status in TERMINAL:
            raise BusinessRuleViolation("La tarea ya está cerrada", code="invalid_task_state")
        if not description.strip():
            raise BusinessRuleViolation("Describe el problema")
        issue = TaskIssue(kind, description.strip(), to_utc(now), actor_id)
        self.issues.append(issue)
        self.touch()
        self.record(
            ie.CleaningIssueReported(
                tenant_id=self.tenant_id,
                actor_id=actor_id,
                task_id=self.id,
                staff_id=self.staff_id,
                kind=kind.value,
                description=issue.description,
            )
        )
        return issue

    def complete(
        self, photos: list[str], now: datetime, *, on_time_minutes: int, actor_id: uuid.UUID | None = None
    ) -> None:
        """CU-11: REG-10 checklist completo + REG-11 fotos finales."""
        self._require(TaskStatus.IN_PROGRESS, action="finalizar")
        if not self.checklist_completed:
            raise BusinessRuleViolation(
                "Completa el checklist antes de finalizar (REG-10)", code="checklist_incomplete"
            )
        if not photos:
            raise BusinessRuleViolation("Las fotos finales son obligatorias (REG-11)", code="photos_required")
        self.final_photos = list(photos)
        self.completed_at = to_utc(now)
        self.status = TaskStatus.COMPLETED
        self.touch()
        begin = self.arrival_confirmed_at or self.started_at
        duration = int((self.completed_at - begin).total_seconds() // 60) if begin else None
        late = self.minutes_late()
        self.record(
            ie.CleaningTaskCompleted(
                tenant_id=self.tenant_id,
                actor_id=actor_id,
                task_id=self.id,
                property_id=self.property_id,
                staff_id=self.staff_id,
                duration_minutes=duration,
                photos_count=len(self.initial_photos) + len(self.final_photos),
                on_time=late is not None and late <= on_time_minutes,
            )
        )

    def duration_minutes(self) -> int | None:
        begin = self.arrival_confirmed_at or self.started_at
        if begin is None or self.completed_at is None:
            return None
        return int((self.completed_at - begin).total_seconds() // 60)
