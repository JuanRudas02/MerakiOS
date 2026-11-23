"""Adaptador REST del módulo Growth (/api/v1/growth)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, status
from pydantic import BaseModel, Field

from oneheavy.modules.growth.application.use_cases import (
    CreateProject,
    CreateProjectCommand,
    GenerateAssets,
    GenerateAssetsCommand,
    GetProject,
    ListProjects,
    ProjectRef,
    RequestFunnelDesign,
    RequestMarketAudit,
    RunCommand,
    RunFunnelDesign,
    RunMarketAudit,
)
from oneheavy.modules.growth.domain.model import Project
from oneheavy.modules.growth.infrastructure.persistence import SqlGrowthUnitOfWork
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, require

router = APIRouter(prefix="/growth", tags=["Growth IA"])
_can_use = require(Permission.GROWTH_USE)


def _uow(container: Container = Depends(get_container)) -> SqlGrowthUnitOfWork:
    return SqlGrowthUnitOfWork(container.session_factory, container.bus)


def _factory(container: Container) -> SqlGrowthUnitOfWork:
    return SqlGrowthUnitOfWork(container.session_factory, container.bus)


# ── Schemas ─────────────────────────────────────────────────────────────────


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    niche: str = Field(min_length=2, max_length=255)
    url: str | None = Field(default=None, max_length=500)


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    niche: str
    url: str | None
    status: str
    audit: dict[str, Any] | None
    funnel: dict[str, Any] | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, p: Project) -> ProjectOut:
        return cls(
            id=p.id,
            name=p.name,
            niche=p.niche,
            url=p.url,
            status=p.status.value,
            audit=p.audit.to_dict() if p.audit else None,
            funnel=p.funnel.to_dict() if p.funnel else None,
            error=p.error,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )


class AcceptedOut(BaseModel):
    status: str = "accepted"


class AssetsIn(BaseModel):
    kind: Literal["ad", "landing", "email"]
    node_id: str | None = None


class AssetOut(BaseModel):
    kind: str
    title: str
    body: str


class AssetsOut(BaseModel):
    assets: list[AssetOut]


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(
    principal: Principal = Depends(_can_use), uow: SqlGrowthUnitOfWork = Depends(_uow)
) -> list[ProjectOut]:
    return [ProjectOut.of(p) for p in await ListProjects(uow).execute(principal)]


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectIn, principal: Principal = Depends(_can_use), uow: SqlGrowthUnitOfWork = Depends(_uow)
) -> ProjectOut:
    return ProjectOut.of(
        await CreateProject(uow).execute(CreateProjectCommand(actor=principal, **body.model_dump()))
    )


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID, principal: Principal = Depends(_can_use), uow: SqlGrowthUnitOfWork = Depends(_uow)
) -> ProjectOut:
    return ProjectOut.of(await GetProject(uow).execute(ProjectRef(principal, project_id)))


@router.post("/projects/{project_id}/audit", response_model=AcceptedOut, status_code=status.HTTP_202_ACCEPTED)
async def request_audit(
    project_id: uuid.UUID,
    background: BackgroundTasks,
    principal: Principal = Depends(_can_use),
    uow: SqlGrowthUnitOfWork = Depends(_uow),
    container: Container = Depends(get_container),
) -> AcceptedOut:
    await RequestMarketAudit(uow).execute(ProjectRef(principal, project_id))
    runner = RunMarketAudit(lambda: _factory(container), container.llm, container.search)
    background.add_task(runner.execute, RunCommand(principal.tenant_id, project_id))
    return AcceptedOut()


@router.post(
    "/projects/{project_id}/funnel", response_model=AcceptedOut, status_code=status.HTTP_202_ACCEPTED
)
async def request_funnel(
    project_id: uuid.UUID,
    background: BackgroundTasks,
    principal: Principal = Depends(_can_use),
    uow: SqlGrowthUnitOfWork = Depends(_uow),
    container: Container = Depends(get_container),
) -> AcceptedOut:
    await RequestFunnelDesign(uow).execute(ProjectRef(principal, project_id))
    runner = RunFunnelDesign(lambda: _factory(container), container.llm)
    background.add_task(runner.execute, RunCommand(principal.tenant_id, project_id))
    return AcceptedOut()


@router.post("/projects/{project_id}/assets", response_model=AssetsOut)
async def generate_assets(
    project_id: uuid.UUID,
    body: AssetsIn,
    principal: Principal = Depends(_can_use),
    uow: SqlGrowthUnitOfWork = Depends(_uow),
    container: Container = Depends(get_container),
) -> AssetsOut:
    assets = await GenerateAssets(uow, container.llm).execute(
        GenerateAssetsCommand(actor=principal, project_id=project_id, kind=body.kind, node_id=body.node_id)
    )
    return AssetsOut(assets=[AssetOut(kind=a.kind, title=a.title, body=a.body) for a in assets])
