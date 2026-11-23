"""Adaptador de entrada REST del módulo de identidad (/api/v1/auth, /api/v1/workspace)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field

from oneheavy.modules.identity.application.use_cases import (
    GetCurrentSession,
    InviteMember,
    InviteMemberCommand,
    ListMembers,
    Login,
    LoginCommand,
    RegisterWorkspace,
    RegisterWorkspaceCommand,
    Session,
    UpdateBranding,
    UpdateBrandingCommand,
)
from oneheavy.modules.identity.domain.model import User, Workspace
from oneheavy.modules.identity.infrastructure.persistence import SqlIdentityUnitOfWork
from oneheavy.shared.domain.access import Permission, Principal, Role
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, get_principal, require
from oneheavy.shared.infrastructure.http.rate_limit import rate_limited

router = APIRouter(tags=["Identity"])


def _uow(container: Container = Depends(get_container)) -> SqlIdentityUnitOfWork:
    return SqlIdentityUnitOfWork(container.session_factory, container.bus)


# ── Schemas ─────────────────────────────────────────────────────────────────


class RegisterIn(BaseModel):
    workspace_name: str = Field(min_length=2, max_length=120)
    owner_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    phone: str | None = None


class LoginIn(BaseModel):
    identifier: str = Field(min_length=3, description="Email o usuario")
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    username: str
    email: str | None
    phone: str | None
    role: Role
    active: bool
    permissions: list[str]
    last_login_at: datetime | None

    @classmethod
    def of(cls, u: User) -> UserOut:
        return cls(
            id=u.id,
            name=u.name,
            username=u.username,
            email=str(u.email) if u.email else None,
            phone=str(u.phone) if u.phone else None,
            role=u.role,
            active=u.active,
            permissions=sorted(p.value for p in u.principal().permissions),
            last_login_at=u.last_login_at,
        )


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    business_name: str
    logo_url: str | None
    primary_color: str
    whatsapp_instance: str | None

    @classmethod
    def of(cls, w: Workspace) -> WorkspaceOut:
        return cls(
            id=w.id,
            name=w.name,
            slug=w.slug,
            plan=w.plan.value,
            business_name=w.branding.business_name,
            logo_url=w.branding.logo_url,
            primary_color=w.branding.primary_color,
            whatsapp_instance=w.whatsapp_instance,
        )


class SessionOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    workspace: WorkspaceOut

    @classmethod
    def of(cls, s: Session) -> SessionOut:
        return cls(access_token=s.token, user=UserOut.of(s.user), workspace=WorkspaceOut.of(s.workspace))


class MeOut(BaseModel):
    user: UserOut
    workspace: WorkspaceOut


class InviteIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    role: Role
    temporary_password: str = Field(min_length=10, max_length=128)
    email: EmailStr | None = None
    phone: str | None = None
    username: str | None = Field(default=None, min_length=3, max_length=60)


class BrandingIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)
    logo_url: str | None = None
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    whatsapp_instance: str | None = None


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post(
    "/auth/register",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limited("register"))],
)
async def register(
    body: RegisterIn, uow: SqlIdentityUnitOfWork = Depends(_uow), c: Container = Depends(get_container)
) -> SessionOut:
    session = await RegisterWorkspace(uow, c.hasher, c.tokens).execute(
        RegisterWorkspaceCommand(**body.model_dump())
    )
    return SessionOut.of(session)


@router.post("/auth/login", response_model=SessionOut, dependencies=[Depends(rate_limited("login"))])
async def login(
    body: LoginIn, uow: SqlIdentityUnitOfWork = Depends(_uow), c: Container = Depends(get_container)
) -> SessionOut:
    return SessionOut.of(
        await Login(uow, c.hasher, c.tokens).execute(LoginCommand(body.identifier, body.password))
    )


@router.get("/auth/me", response_model=MeOut)
async def me(
    principal: Principal = Depends(get_principal), uow: SqlIdentityUnitOfWork = Depends(_uow)
) -> MeOut:
    user, workspace = await GetCurrentSession(uow).execute(principal)
    return MeOut(user=UserOut.of(user), workspace=WorkspaceOut.of(workspace))


@router.get("/workspace/members", response_model=list[UserOut])
async def members(
    principal: Principal = Depends(require(Permission.MEMBERS_MANAGE)),
    uow: SqlIdentityUnitOfWork = Depends(_uow),
) -> list[UserOut]:
    return [UserOut.of(u) for u in await ListMembers(uow).execute(principal)]


@router.post("/workspace/members", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def invite(
    body: InviteIn,
    principal: Principal = Depends(get_principal),
    uow: SqlIdentityUnitOfWork = Depends(_uow),
    c: Container = Depends(get_container),
) -> UserOut:
    user = await InviteMember(uow, c.hasher, c.sender).execute(
        InviteMemberCommand(actor=principal, **body.model_dump())
    )
    return UserOut.of(user)


@router.put("/workspace/branding", response_model=WorkspaceOut)
async def branding(
    body: BrandingIn,
    principal: Principal = Depends(get_principal),
    uow: SqlIdentityUnitOfWork = Depends(_uow),
) -> WorkspaceOut:
    workspace = await UpdateBranding(uow).execute(UpdateBrandingCommand(actor=principal, **body.model_dump()))
    return WorkspaceOut.of(workspace)
