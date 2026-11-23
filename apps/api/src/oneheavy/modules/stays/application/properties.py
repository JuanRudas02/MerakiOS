"""Casos de uso de propiedades, comprobantes, personal y configuración.

CU-ST-01  Registrar propiedad (y dar la bienvenida al propietario por WhatsApp)
CU-ST-02  Actualizar propiedad (inventario visual, checklist, cortes, iCal)
CU-ST-03  Listar / consultar propiedades (el propietario sólo ve las suyas)
CU-ST-04  Subir comprobante de pago de servicio (pausa automatización)
CU-ST-05  Revisar comprobante (verificar / rechazar; reanuda automatización)
CU-ST-06  Listar comprobantes de una propiedad
CU-ST-07  Registrar / listar personal operativo
CU-ST-08  Consultar / actualizar configuración operativa del workspace
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from oneheavy.modules.stays.application.notifications import StaysNotifier
from oneheavy.modules.stays.application.ports import StaysUnitOfWork, UploadedFile
from oneheavy.modules.stays.domain.model import (
    BillingCutoffs,
    PhotoMode,
    Property,
    Receipt,
    StaffCategory,
    StaffMember,
    StaysSettings,
)
from oneheavy.shared.application.ports import FileStorage
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain.access import Permission, Principal, Role
from oneheavy.shared.domain.errors import ConflictError, NotFoundError
from oneheavy.shared.domain.value_objects import PhoneNumber


async def owner_phone_scope(uow: StaysUnitOfWork, actor: Principal) -> str | None:
    """Para property_owner devuelve su teléfono (filtro); para los demás roles, None.

    Un propietario sin teléfono registrado no ve ninguna unidad.
    """
    if actor.role is not Role.PROPERTY_OWNER:
        return None
    account = await uow.owners.get(actor.tenant_id, actor.user_id)
    return str(account.phone) if account and account.phone else "__none__"


async def load_property(uow: StaysUnitOfWork, actor: Principal, property_id: uuid.UUID) -> Property:
    prop = await uow.properties.get(actor.tenant_id, property_id)
    scope = await owner_phone_scope(uow, actor)
    if prop is None or (scope is not None and str(prop.owner_phone or "") != scope):
        raise NotFoundError("Propiedad no encontrada")
    return prop


def _property_changes(raw: dict[str, Any]) -> dict[str, Any]:
    """Convierte primitivas del comando en value objects del dominio."""
    changes = dict(raw)
    if "owner_phone" in changes:
        changes["owner_phone"] = PhoneNumber(changes["owner_phone"]) if changes["owner_phone"] else None
    if "billing_cutoffs" in changes:
        changes["billing_cutoffs"] = BillingCutoffs(**(changes["billing_cutoffs"] or {}))
    return changes


# ── CU-ST-01 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CreatePropertyCommand:
    actor: Principal
    code: str
    name: str
    address: str | None = None
    capacity: int = 2
    owner_name: str | None = None
    owner_phone: str | None = None
    default_staff_id: uuid.UUID | None = None
    billing_cutoffs: dict[str, int | None] = field(default_factory=dict)
    checklist_template: list[str] = field(default_factory=list)
    visual_inventory: list[str] = field(default_factory=list)
    ical_url: str | None = None


class CreateProperty(UseCase[CreatePropertyCommand, Property]):
    def __init__(self, uow: StaysUnitOfWork, notifier: StaysNotifier) -> None:
        self.uow, self.notifier = uow, notifier

    async def execute(self, data: CreatePropertyCommand) -> Property:
        data.actor.require(Permission.PROPERTIES_MANAGE)
        fields = {k: v for k, v in data.__dict__.items() if k != "actor"}
        async with self.uow:
            if await self.uow.properties.code_exists(data.actor.tenant_id, data.code.strip()):
                raise ConflictError(
                    f"Ya existe una propiedad con código '{data.code}'", code="property_code_taken"
                )
            if data.default_staff_id and not await self.uow.staff.get(
                data.actor.tenant_id, data.default_staff_id
            ):
                raise NotFoundError("Personal por defecto no encontrado")
            prop = Property(tenant_id=data.actor.tenant_id, **_property_changes(fields))
            await self.uow.properties.add(prop)
            settings = await self.uow.settings.get(data.actor.tenant_id)
            await self.uow.commit()
        await self.notifier.property_welcome(prop, settings)
        return prop


# ── CU-ST-02 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UpdatePropertyCommand:
    actor: Principal
    property_id: uuid.UUID
    changes: dict[str, Any]


class UpdateProperty(UseCase[UpdatePropertyCommand, Property]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: UpdatePropertyCommand) -> Property:
        data.actor.require(Permission.PROPERTIES_MANAGE)
        async with self.uow:
            prop = await load_property(self.uow, data.actor, data.property_id)
            code = data.changes.get("code")
            if code and await self.uow.properties.code_exists(prop.tenant_id, code.strip(), exclude=prop.id):
                raise ConflictError(
                    f"Ya existe una propiedad con código '{code}'", code="property_code_taken"
                )
            staff_id = data.changes.get("default_staff_id")
            if staff_id and not await self.uow.staff.get(prop.tenant_id, staff_id):
                raise NotFoundError("Personal por defecto no encontrado")
            prop.update(_property_changes(data.changes))
            await self.uow.properties.update(prop)
            await self.uow.commit()
        return prop


# ── CU-ST-03 ────────────────────────────────────────────────────────────────


class ListProperties(UseCase[Principal, list[Property]]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[Property]:
        data.require(Permission.PROPERTIES_READ)
        async with self.uow:
            scope = await owner_phone_scope(self.uow, data)
            return await self.uow.properties.list_all(data.tenant_id, owner_phone=scope)


@dataclass(frozen=True)
class GetPropertyQuery:
    actor: Principal
    property_id: uuid.UUID


class GetProperty(UseCase[GetPropertyQuery, Property]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: GetPropertyQuery) -> Property:
        data.actor.require(Permission.PROPERTIES_READ)
        async with self.uow:
            return await load_property(self.uow, data.actor, data.property_id)


# ── CU-ST-04 / 05 / 06 ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class UploadReceiptCommand:
    actor: Principal
    property_id: uuid.UUID
    service: str
    period: str
    file: UploadedFile


class UploadReceipt(UseCase[UploadReceiptCommand, Receipt]):
    def __init__(self, uow: StaysUnitOfWork, storage: FileStorage) -> None:
        self.uow, self.storage = uow, storage

    async def execute(self, data: UploadReceiptCommand) -> Receipt:
        data.actor.require(Permission.RECEIPTS_UPLOAD)
        async with self.uow:
            prop = await load_property(self.uow, data.actor, data.property_id)
            url = await self.storage.save(
                data.file.data,
                folder=f"receipts/{prop.tenant_id}",
                filename=data.file.filename,
                content_type=data.file.content_type,
            )
            receipt = Receipt.upload(
                tenant_id=prop.tenant_id,
                property_id=prop.id,
                service=data.service,
                period=data.period,
                url=url,
            )
            # Mientras el administrador verifica, se pausan los recordatorios de cobro.
            prop.pause_automation()
            await self.uow.receipts.add(receipt)
            await self.uow.properties.update(prop)
            await self.uow.commit()
        return receipt


@dataclass(frozen=True)
class ReviewReceiptCommand:
    actor: Principal
    receipt_id: uuid.UUID
    approved: bool
    note: str | None = None


class ReviewReceipt(UseCase[ReviewReceiptCommand, Receipt]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ReviewReceiptCommand) -> Receipt:
        data.actor.require(Permission.RECEIPTS_VERIFY)
        async with self.uow:
            receipt = await self.uow.receipts.get(data.actor.tenant_id, data.receipt_id)
            if receipt is None:
                raise NotFoundError("Comprobante no encontrado")
            receipt.review(approved=data.approved, reviewer_id=data.actor.user_id, note=data.note)
            await self.uow.receipts.update(receipt)
            prop = await self.uow.properties.get(receipt.tenant_id, receipt.property_id)
            if (
                prop
                and prop.automation_paused
                and not await self.uow.receipts.has_pending(prop.tenant_id, prop.id)
            ):
                prop.resume_automation()
                await self.uow.properties.update(prop)
            self.uow.collect(receipt.pull_events())
            await self.uow.commit()
        return receipt


class ListReceipts(UseCase[GetPropertyQuery, list[Receipt]]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: GetPropertyQuery) -> list[Receipt]:
        data.actor.require(Permission.PROPERTIES_READ)
        async with self.uow:
            prop = await load_property(self.uow, data.actor, data.property_id)
            return await self.uow.receipts.list_by_property(prop.tenant_id, prop.id)


# ── CU-ST-07 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RegisterStaffCommand:
    actor: Principal
    name: str
    phone: str
    category: StaffCategory = StaffCategory.CLEANING


class RegisterStaff(UseCase[RegisterStaffCommand, StaffMember]):
    """Alta de personal sin acceso a la app (opera sólo por WhatsApp)."""

    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: RegisterStaffCommand) -> StaffMember:
        data.actor.require(Permission.TASKS_MANAGE)
        staff = StaffMember(
            tenant_id=data.actor.tenant_id,
            name=data.name.strip(),
            phone=PhoneNumber(data.phone),
            category=data.category,
        )
        async with self.uow:
            await self.uow.staff.upsert(staff)
            await self.uow.commit()
        return staff


class ListStaff(UseCase[Principal, list[StaffMember]]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[StaffMember]:
        data.require(Permission.TASKS_READ)
        async with self.uow:
            return await self.uow.staff.list_all(data.tenant_id)


# ── CU-ST-08 ────────────────────────────────────────────────────────────────


class GetSettings(UseCase[Principal, StaysSettings]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> StaysSettings:
        data.require(Permission.TASKS_MANAGE)
        async with self.uow:
            settings = await self.uow.settings.get(data.tenant_id)
            await self.uow.settings.save(settings)  # materializa el token del webhook
            await self.uow.commit()
            return settings


@dataclass(frozen=True)
class UpdateSettingsCommand:
    actor: Principal
    supervisor_phone: str | None
    daily_reminder_hour: int = 19
    escalation_minutes: int = 10
    photo_mode: PhotoMode = PhotoMode.STANDARD
    whatsapp_instance: str | None = None
    templates: dict[str, str] | None = None


class UpdateSettings(UseCase[UpdateSettingsCommand, StaysSettings]):
    def __init__(self, uow: StaysUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: UpdateSettingsCommand) -> StaysSettings:
        data.actor.require(Permission.TASKS_MANAGE)
        async with self.uow:
            current = await self.uow.settings.get(data.actor.tenant_id)
            updated = StaysSettings(
                id=current.id,
                tenant_id=current.tenant_id,
                supervisor_phone=PhoneNumber(data.supervisor_phone) if data.supervisor_phone else None,
                daily_reminder_hour=data.daily_reminder_hour,
                escalation_minutes=data.escalation_minutes,
                photo_mode=data.photo_mode,
                whatsapp_instance=data.whatsapp_instance or None,
                webhook_token=current.webhook_token,
                templates=data.templates if data.templates is not None else current.templates,
                created_at=current.created_at,
            )
            await self.uow.settings.save(updated)
            await self.uow.commit()
        return updated
