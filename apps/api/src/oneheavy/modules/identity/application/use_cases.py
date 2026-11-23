"""Casos de uso de Identidad y Acceso.

CU-ID-01  Registrar workspace (self-service onboarding)
CU-ID-02  Iniciar sesión
CU-ID-03  Consultar sesión actual
CU-ID-04  Invitar miembro al equipo (staff, propietario, marketer, ventas...)
CU-ID-05  Listar miembros
CU-ID-06  Configurar marca blanca (white-label)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from oneheavy.modules.identity.application.ports import IdentityUnitOfWork
from oneheavy.modules.identity.domain.model import User, Workspace, assert_can_assign_role
from oneheavy.shared.application.ports import MessageSender
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain.access import Permission, Principal, Role
from oneheavy.shared.domain.errors import AuthenticationError, ConflictError, NotFoundError
from oneheavy.shared.domain.value_objects import Email, PhoneNumber


class PasswordHasherPort(Protocol):
    def hash(self, plain: str) -> str: ...
    def verify(self, plain: str, hashed: str) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, principal: Principal) -> str: ...


@dataclass(frozen=True)
class Session:
    token: str
    user: User
    workspace: Workspace


# ── CU-ID-01 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RegisterWorkspaceCommand:
    workspace_name: str
    owner_name: str
    email: str
    password: str
    phone: str | None = None


class RegisterWorkspace(UseCase[RegisterWorkspaceCommand, Session]):
    def __init__(self, uow: IdentityUnitOfWork, hasher: PasswordHasherPort, tokens: TokenIssuer) -> None:
        self.uow, self.hasher, self.tokens = uow, hasher, tokens

    async def execute(self, data: RegisterWorkspaceCommand) -> Session:
        email = Email(data.email)
        phone = PhoneNumber(data.phone) if data.phone else None
        password_hash = self.hasher.hash(data.password)
        async with self.uow:
            if await self.uow.users.exists_login(email.value):
                raise ConflictError("Ya existe una cuenta con ese email", code="email_taken")
            owner_id = uuid.uuid4()
            workspace = Workspace.create(data.workspace_name, owner_id=owner_id)
            if await self.uow.workspaces.slug_exists(workspace.slug):
                workspace.slug = f"{workspace.slug}-{workspace.id.hex[:6]}"
            owner = User.register(
                user_id=owner_id,
                tenant_id=workspace.id,
                name=data.owner_name,
                email=email,
                phone=phone,
                role=Role.OWNER,
                password_hash=password_hash,
            )
            owner.mark_login()
            await self.uow.workspaces.add(workspace)
            await self.uow.users.add(owner)
            self.uow.collect(workspace.pull_events() + owner.pull_events())
            await self.uow.commit()
        return Session(self.tokens.issue(owner.principal()), owner, workspace)


# ── CU-ID-02 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LoginCommand:
    identifier: str  # email o usuario
    password: str


class Login(UseCase[LoginCommand, Session]):
    def __init__(self, uow: IdentityUnitOfWork, hasher: PasswordHasherPort, tokens: TokenIssuer) -> None:
        self.uow, self.hasher, self.tokens = uow, hasher, tokens

    async def execute(self, data: LoginCommand) -> Session:
        async with self.uow:
            user = await self.uow.users.find_by_login(data.identifier)
            # Mensaje genérico: no revelar si el usuario existe.
            if user is None or not user.active or not self.hasher.verify(data.password, user.password_hash):
                raise AuthenticationError("Credenciales inválidas")
            workspace = await self.uow.workspaces.get(user.tenant_id)
            if workspace is None:
                raise AuthenticationError("Credenciales inválidas")
            user.mark_login()
            await self.uow.users.update(user)
            await self.uow.commit()
        return Session(self.tokens.issue(user.principal()), user, workspace)


# ── CU-ID-03 ────────────────────────────────────────────────────────────────


class GetCurrentSession(UseCase[Principal, tuple[User, Workspace]]):
    def __init__(self, uow: IdentityUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> tuple[User, Workspace]:
        async with self.uow:
            user = await self.uow.users.get(data.tenant_id, data.user_id)
            workspace = await self.uow.workspaces.get(data.tenant_id)
        if user is None or workspace is None or not user.active:
            raise AuthenticationError("Sesión inválida")
        return user, workspace


# ── CU-ID-04 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class InviteMemberCommand:
    actor: Principal
    name: str
    role: Role
    temporary_password: str
    email: str | None = None
    phone: str | None = None
    username: str | None = None


class InviteMember(UseCase[InviteMemberCommand, User]):
    """Crea un miembro del equipo y le avisa por WhatsApp.

    A diferencia de Stays, la contraseña NUNCA viaja por WhatsApp: el
    administrador la entrega por un canal seguro y el usuario la cambia.
    """

    def __init__(self, uow: IdentityUnitOfWork, hasher: PasswordHasherPort, sender: MessageSender) -> None:
        self.uow, self.hasher, self.sender = uow, hasher, sender

    async def execute(self, data: InviteMemberCommand) -> User:
        data.actor.require(Permission.MEMBERS_MANAGE)
        assert_can_assign_role(data.actor, data.role)
        email = Email(data.email) if data.email else None
        phone = PhoneNumber(data.phone) if data.phone else None
        async with self.uow:
            logins = [i for i in (email.value if email else None, data.username) if i]
            for ident in logins:
                if await self.uow.users.exists_login(ident):
                    raise ConflictError(f"El usuario '{ident}' ya existe", code="login_taken")
            workspace = await self.uow.workspaces.get(data.actor.tenant_id)
            if workspace is None:
                raise NotFoundError("Workspace no encontrado")
            user = User.register(
                tenant_id=data.actor.tenant_id,
                name=data.name,
                email=email,
                phone=phone,
                username=data.username,
                role=data.role,
                password_hash=self.hasher.hash(data.temporary_password),
                invited_by=data.actor.user_id,
            )
            await self.uow.users.add(user)
            self.uow.collect(user.pull_events())
            await self.uow.commit()

        if user.phone:
            default = (
                "👋 Hola *{name}*, *{business}* te invitó a su equipo en 1heavy como *{role}*.\n"
                "Usuario: `{username}`\nTu administrador te compartirá la clave temporal."
            )
            message = workspace.message_template("member_invited", default).format(
                name=user.name,
                business=workspace.branding.business_name,
                role=user.role.value,
                username=user.username,
            )
            await self.sender.send_whatsapp(user.phone.digits, message, instance=workspace.whatsapp_instance)
        return user


# ── CU-ID-05 / CU-ID-06 ─────────────────────────────────────────────────────


class ListMembers(UseCase[Principal, list[User]]):
    def __init__(self, uow: IdentityUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[User]:
        async with self.uow:
            return await self.uow.users.list_by_tenant(data.tenant_id)


@dataclass(frozen=True)
class UpdateBrandingCommand:
    actor: Principal
    business_name: str
    logo_url: str | None = None
    primary_color: str | None = None
    whatsapp_instance: str | None = None


class UpdateBranding(UseCase[UpdateBrandingCommand, Workspace]):
    def __init__(self, uow: IdentityUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: UpdateBrandingCommand) -> Workspace:
        data.actor.require(Permission.WORKSPACE_MANAGE)
        async with self.uow:
            workspace = await self.uow.workspaces.get(data.actor.tenant_id)
            if workspace is None:
                raise NotFoundError("Workspace no encontrado")
            workspace.rebrand(data.business_name, data.logo_url, data.primary_color)
            if data.whatsapp_instance is not None:
                workspace.whatsapp_instance = data.whatsapp_instance or None
            await self.uow.workspaces.update(workspace)
            await self.uow.commit()
        return workspace
