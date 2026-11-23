"""Adaptador de salida: persistencia SQLAlchemy del módulo de identidad."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Self

from sqlalchemy import JSON, Boolean, DateTime, String, Uuid, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.identity.application.ports import IdentityUnitOfWork
from oneheavy.modules.identity.domain.model import Branding, Plan, User, Workspace
from oneheavy.modules.identity.domain.repositories import UserRepository, WorkspaceRepository
from oneheavy.shared.domain.access import Role
from oneheavy.shared.domain.time import ensure_aware
from oneheavy.shared.domain.value_objects import Email, PhoneNumber
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TimestampMixin

# ── ORM ─────────────────────────────────────────────────────────────────────


class WorkspaceRow(TimestampMixin, Base):
    __tablename__ = "identity_workspaces"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20), default=Plan.TRIAL.value)
    business_name: Mapped[str] = mapped_column(String(120))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    primary_color: Mapped[str] = mapped_column(String(9), default="#3B5BFD")
    whatsapp_instance: Mapped[str | None] = mapped_column(String(80))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class UserRow(TimestampMixin, Base):
    __tablename__ = "identity_users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    name: Mapped[str] = mapped_column(String(120))
    username: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), index=True)
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ── Mappers ─────────────────────────────────────────────────────────────────


def _ws_to_domain(row: WorkspaceRow) -> Workspace:
    return Workspace(
        id=row.id,
        name=row.name,
        slug=row.slug,
        plan=Plan(row.plan),
        branding=Branding(row.business_name, row.logo_url, row.primary_color),
        whatsapp_instance=row.whatsapp_instance,
        settings=dict(row.settings or {}),
        created_at=ensure_aware(row.created_at),
        updated_at=ensure_aware(row.updated_at),
    )


def _ws_apply(row: WorkspaceRow, ws: Workspace) -> None:
    row.name, row.slug, row.plan = ws.name, ws.slug, ws.plan.value
    row.business_name, row.logo_url = ws.branding.business_name, ws.branding.logo_url
    row.primary_color = ws.branding.primary_color
    row.whatsapp_instance, row.settings = ws.whatsapp_instance, ws.settings
    row.created_at, row.updated_at = ws.created_at, ws.updated_at


def _user_to_domain(row: UserRow) -> User:
    return User(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        username=row.username,
        email=Email(row.email) if row.email else None,
        phone=PhoneNumber(row.phone) if row.phone else None,
        role=Role(row.role),
        password_hash=row.password_hash,
        active=row.active,
        last_login_at=ensure_aware(row.last_login_at) if row.last_login_at else None,
        created_at=ensure_aware(row.created_at),
        updated_at=ensure_aware(row.updated_at),
    )


def _user_apply(row: UserRow, user: User) -> None:
    row.tenant_id, row.name, row.username = user.tenant_id, user.name, user.username
    row.email = str(user.email) if user.email else None
    row.phone = str(user.phone) if user.phone else None
    row.role, row.password_hash, row.active = user.role.value, user.password_hash, user.active
    row.last_login_at, row.created_at, row.updated_at = user.last_login_at, user.created_at, user.updated_at


# ── Repositorios ────────────────────────────────────────────────────────────


class SqlWorkspaceRepository(WorkspaceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, workspace_id: uuid.UUID) -> Workspace | None:
        row = await self._s.get(WorkspaceRow, workspace_id)
        return _ws_to_domain(row) if row else None

    async def slug_exists(self, slug: str) -> bool:
        return (await self._s.scalar(select(WorkspaceRow.id).where(WorkspaceRow.slug == slug))) is not None

    async def add(self, workspace: Workspace) -> None:
        row = WorkspaceRow(id=workspace.id)
        _ws_apply(row, workspace)
        self._s.add(row)

    async def update(self, workspace: Workspace) -> None:
        row = await self._s.get(WorkspaceRow, workspace.id)
        if row is not None:
            _ws_apply(row, workspace)


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
        row = await self._s.get(UserRow, user_id)
        return _user_to_domain(row) if row and row.tenant_id == tenant_id else None

    async def find_by_login(self, identifier: str) -> User | None:
        ident = identifier.strip().lower()
        row = await self._s.scalar(
            select(UserRow).where(or_(UserRow.email == ident, UserRow.username == ident))
        )
        return _user_to_domain(row) if row else None

    async def exists_login(self, identifier: str) -> bool:
        return await self.find_by_login(identifier) is not None

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[User]:
        rows = await self._s.scalars(
            select(UserRow).where(UserRow.tenant_id == tenant_id).order_by(UserRow.name)
        )
        return [_user_to_domain(r) for r in rows]

    async def add(self, user: User) -> None:
        row = UserRow(id=user.id)
        _user_apply(row, user)
        self._s.add(row)

    async def update(self, user: User) -> None:
        row = await self._s.get(UserRow, user.id)
        if row is not None:
            _user_apply(row, user)


class SqlIdentityUnitOfWork(SqlAlchemyUnitOfWork, IdentityUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.workspaces = SqlWorkspaceRepository(self.session)
        self.users = SqlUserRepository(self.session)
        return self
