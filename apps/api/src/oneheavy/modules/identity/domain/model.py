"""Dominio de Identidad: Workspace (tenant) y User."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.access import Principal, Role
from oneheavy.shared.domain.entity import AggregateRoot, new_id
from oneheavy.shared.domain.errors import BusinessRuleViolation, PermissionDenied
from oneheavy.shared.domain.time import utc_now
from oneheavy.shared.domain.value_objects import Email, PhoneNumber


class Plan(StrEnum):
    TRIAL = "trial"
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "workspace"


@dataclass(frozen=True)
class Branding:
    """White-label: el cliente opera 1heavy con su propia marca (CU-07 de Stays)."""

    business_name: str
    logo_url: str | None = None
    primary_color: str = "#3B5BFD"


@dataclass(kw_only=True, eq=False)
class Workspace(AggregateRoot):
    name: str
    slug: str
    plan: Plan = Plan.TRIAL
    branding: Branding
    whatsapp_instance: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)  # plantillas de mensajes, preferencias

    @classmethod
    def create(cls, name: str, owner_id: uuid.UUID) -> Workspace:
        name = name.strip()
        if len(name) < 2:
            raise BusinessRuleViolation("El nombre del workspace es demasiado corto")
        ws = cls(id=new_id(), name=name, slug=slugify(name), branding=Branding(business_name=name))
        ws.record(
            ie.WorkspaceCreated(tenant_id=ws.id, actor_id=owner_id, workspace_name=name, owner_id=owner_id)
        )
        return ws

    def rebrand(self, business_name: str, logo_url: str | None, primary_color: str | None) -> None:
        self.branding = Branding(
            business_name=business_name.strip() or self.name,
            logo_url=logo_url,
            primary_color=primary_color or self.branding.primary_color,
        )
        self.touch()

    def change_plan(self, plan: Plan) -> None:
        self.plan = plan
        self.touch()

    def message_template(self, key: str, default: str) -> str:
        templates = self.settings.get("templates", {})
        return str(templates.get(key, default))


@dataclass(kw_only=True, eq=False)
class User(AggregateRoot):
    tenant_id: uuid.UUID
    name: str
    username: str
    email: Email | None = None
    phone: PhoneNumber | None = None
    role: Role
    password_hash: str
    active: bool = True
    last_login_at: datetime | None = None

    @classmethod
    def register(
        cls,
        *,
        tenant_id: uuid.UUID,
        name: str,
        role: Role,
        password_hash: str,
        email: Email | None = None,
        phone: PhoneNumber | None = None,
        username: str | None = None,
        invited_by: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> User:
        if email is None and phone is None:
            raise BusinessRuleViolation("El usuario necesita email o teléfono")
        handle = username or (email.value if email else phone.digits)  # type: ignore[union-attr]
        user = cls(
            id=user_id or new_id(),
            tenant_id=tenant_id,
            name=name.strip(),
            username=handle.lower(),
            email=email,
            phone=phone,
            role=role,
            password_hash=password_hash,
        )
        user.record(
            ie.UserRegistered(
                tenant_id=tenant_id,
                actor_id=invited_by or user.id,
                user_id=user.id,
                email=str(email) if email else None,
                phone=str(phone) if phone else None,
                name=user.name,
                role=role.value,
            )
        )
        return user

    def principal(self) -> Principal:
        return Principal.for_role(self.id, self.tenant_id, self.role)

    def mark_login(self) -> None:
        self.last_login_at = utc_now()

    def deactivate(self) -> None:
        if self.role is Role.OWNER:
            raise BusinessRuleViolation("No se puede desactivar al dueño del workspace")
        self.active = False
        self.touch()


def assert_can_assign_role(actor: Principal, role: Role) -> None:
    """Regla: nadie crea OWNERs; sólo OWNER crea ADMINs."""
    if role is Role.OWNER:
        raise PermissionDenied("El rol owner no se puede asignar")
    if role is Role.ADMIN and actor.role is not Role.OWNER:
        raise PermissionDenied("Sólo el dueño del workspace puede crear administradores")
