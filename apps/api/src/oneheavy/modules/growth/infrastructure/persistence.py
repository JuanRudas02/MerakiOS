"""Persistencia SQLAlchemy del módulo Growth."""

from __future__ import annotations

import uuid
from typing import Any, Self

from sqlalchemy import JSON, String, Text, Uuid, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.growth.application.ports import GrowthUnitOfWork, ProjectRepository
from oneheavy.modules.growth.domain.model import Audit, Funnel, Project, ProjectStatus
from oneheavy.shared.domain.time import ensure_aware
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TenantMixin, TimestampMixin


class GrowthProjectRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "growth_projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    niche: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), index=True)
    audit: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    funnel: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    research_notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)


def _to_domain(row: GrowthProjectRow) -> Project:
    return Project(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        niche=row.niche,
        url=row.url,
        status=ProjectStatus(row.status),
        audit=Audit.from_dict(row.audit) if row.audit else None,
        funnel=Funnel.from_dict(row.funnel) if row.funnel else None,
        research_notes=list(row.research_notes or []),
        error=row.error,
        created_by=row.created_by,
        created_at=ensure_aware(row.created_at),
        updated_at=ensure_aware(row.updated_at),
    )


class SqlProjectRepository(ProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
        row = await self._s.get(GrowthProjectRow, project_id)
        return _to_domain(row) if row and row.tenant_id == tenant_id else None

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Project]:
        rows = await self._s.scalars(
            select(GrowthProjectRow)
            .where(GrowthProjectRow.tenant_id == tenant_id)
            .order_by(GrowthProjectRow.created_at.desc())
        )
        return [_to_domain(r) for r in rows]

    async def save(self, project: Project) -> None:
        row = await self._s.get(GrowthProjectRow, project.id)
        if row is None:
            row = GrowthProjectRow(id=project.id, tenant_id=project.tenant_id)
            self._s.add(row)
        row.name, row.niche, row.url = project.name, project.niche, project.url
        row.status = project.status.value
        row.audit = project.audit.to_dict() if project.audit else None
        row.funnel = project.funnel.to_dict() if project.funnel else None
        row.research_notes = list(project.research_notes)
        row.error, row.created_by = project.error, project.created_by
        row.created_at, row.updated_at = project.created_at, project.updated_at


class SqlGrowthUnitOfWork(SqlAlchemyUnitOfWork, GrowthUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.projects = SqlProjectRepository(self.session)
        return self
