"""Casos de uso Growth (motor de estrategia IA, ex MerakiOS).

CU-GRO-01  Crear proyecto de crecimiento
CU-GRO-02  Listar / consultar proyectos
CU-GRO-03  Solicitar auditoría de mercado (Genesis) → ejecución asíncrona
CU-GRO-04  Solicitar diseño de embudo (Blueprint) → ejecución asíncrona
CU-GRO-05  Generar assets de copy (anuncios, landing, emails)
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from oneheavy.modules.growth.application.agents import Asset, AssetWriter, BlueprintPipeline, GenesisPipeline
from oneheavy.modules.growth.application.ports import GrowthUnitOfWork
from oneheavy.modules.growth.domain.model import Project, ProjectStatus
from oneheavy.shared.application.ports import LLMClient, WebSearch
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import BusinessRuleViolation, DomainError, NotFoundError

log = logging.getLogger("oneheavy.growth")

UowFactory = Callable[[], GrowthUnitOfWork]


async def _load(uow: GrowthUnitOfWork, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = await uow.projects.get(tenant_id, project_id)
    if project is None:
        raise NotFoundError("Proyecto no encontrado")
    return project


# ── CU-GRO-01 / 02 ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CreateProjectCommand:
    actor: Principal
    name: str
    niche: str
    url: str | None = None


class CreateProject(UseCase[CreateProjectCommand, Project]):
    def __init__(self, uow: GrowthUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: CreateProjectCommand) -> Project:
        data.actor.require(Permission.GROWTH_USE)
        project = Project.create(
            tenant_id=data.actor.tenant_id,
            name=data.name,
            niche=data.niche,
            url=data.url,
            created_by=data.actor.user_id,
        )
        async with self.uow:
            await self.uow.projects.save(project)
            await self.uow.commit()
        return project


class ListProjects(UseCase[Principal, list[Project]]):
    def __init__(self, uow: GrowthUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[Project]:
        data.require(Permission.GROWTH_USE)
        async with self.uow:
            return await self.uow.projects.list_by_tenant(data.tenant_id)


@dataclass(frozen=True)
class ProjectRef:
    actor: Principal
    project_id: uuid.UUID


class GetProject(UseCase[ProjectRef, Project]):
    def __init__(self, uow: GrowthUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ProjectRef) -> Project:
        data.actor.require(Permission.GROWTH_USE)
        async with self.uow:
            return await _load(self.uow, data.actor.tenant_id, data.project_id)


# ── CU-GRO-03 ───────────────────────────────────────────────────────────────


class RequestMarketAudit(UseCase[ProjectRef, Project]):
    """Marca el proyecto como `analyzing`; el pipeline corre en segundo plano."""

    def __init__(self, uow: GrowthUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ProjectRef) -> Project:
        data.actor.require(Permission.GROWTH_USE)
        async with self.uow:
            project = await _load(self.uow, data.actor.tenant_id, data.project_id)
            project.start_audit()
            await self.uow.projects.save(project)
            await self.uow.commit()
        return project


@dataclass(frozen=True)
class RunCommand:
    tenant_id: uuid.UUID
    project_id: uuid.UUID


class RunMarketAudit(UseCase[RunCommand, None]):
    """Ejecuta Genesis fuera de transacción y persiste el resultado (o el fallo)."""

    def __init__(self, uow_factory: UowFactory, llm: LLMClient, search: WebSearch) -> None:
        self.uow_factory, self.llm, self.search = uow_factory, llm, search

    async def execute(self, data: RunCommand) -> None:
        async with self.uow_factory() as uow:
            project = await _load(uow, data.tenant_id, data.project_id)
        if project.status is not ProjectStatus.ANALYZING:
            return
        try:
            result = await GenesisPipeline(self.llm, self.search).run(project.niche, project.url)
            if result.audit is None:
                raise BusinessRuleViolation("El auditor no produjo un reporte")
        except Exception as exc:
            log.exception("growth_audit_failed", extra={"project_id": str(project.id)})
            await _mark_failed(self.uow_factory, data, _public_error(exc))
            return
        async with self.uow_factory() as uow:
            project = await _load(uow, data.tenant_id, data.project_id)
            project.complete_audit(result.audit, result.research)
            await uow.projects.save(project)
            uow.collect(project.pull_events())
            await uow.commit()


# ── CU-GRO-04 ───────────────────────────────────────────────────────────────


class RequestFunnelDesign(UseCase[ProjectRef, Project]):
    def __init__(self, uow: GrowthUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ProjectRef) -> Project:
        data.actor.require(Permission.GROWTH_USE)
        async with self.uow:
            project = await _load(self.uow, data.actor.tenant_id, data.project_id)
            project.start_funnel()
            await self.uow.projects.save(project)
            await self.uow.commit()
        return project


class RunFunnelDesign(UseCase[RunCommand, None]):
    def __init__(self, uow_factory: UowFactory, llm: LLMClient) -> None:
        self.uow_factory, self.llm = uow_factory, llm

    async def execute(self, data: RunCommand) -> None:
        async with self.uow_factory() as uow:
            project = await _load(uow, data.tenant_id, data.project_id)
        if project.status is not ProjectStatus.DESIGNING or project.audit is None:
            return
        try:
            result = await BlueprintPipeline(self.llm).run(project.audit, project.niche)
            if result.funnel is None:
                raise BusinessRuleViolation("El arquitecto no produjo un embudo")
        except Exception as exc:
            log.exception("growth_funnel_failed", extra={"project_id": str(project.id)})
            await _mark_failed(self.uow_factory, data, _public_error(exc))
            return
        async with self.uow_factory() as uow:
            project = await _load(uow, data.tenant_id, data.project_id)
            project.complete_funnel(result.funnel)
            await uow.projects.save(project)
            uow.collect(project.pull_events())
            await uow.commit()


def _public_error(exc: Exception) -> str:
    return exc.message if isinstance(exc, DomainError) else "Error inesperado ejecutando el agente de IA"


async def _mark_failed(uow_factory: UowFactory, data: RunCommand, error: str) -> None:
    async with uow_factory() as uow:
        project = await _load(uow, data.tenant_id, data.project_id)
        project.fail(error)
        await uow.projects.save(project)
        await uow.commit()


# ── CU-GRO-05 ───────────────────────────────────────────────────────────────

ASSET_KINDS = frozenset({"ad", "landing", "email"})


@dataclass(frozen=True)
class GenerateAssetsCommand:
    actor: Principal
    project_id: uuid.UUID
    kind: str
    node_id: str | None = None


class GenerateAssets(UseCase[GenerateAssetsCommand, list[Asset]]):
    def __init__(self, uow: GrowthUnitOfWork, llm: LLMClient) -> None:
        self.uow, self.llm = uow, llm

    async def execute(self, data: GenerateAssetsCommand) -> list[Asset]:
        data.actor.require(Permission.GROWTH_USE)
        if data.kind not in ASSET_KINDS:
            raise BusinessRuleViolation("Tipo de asset inválido (ad, landing o email)")
        async with self.uow:
            project = await _load(self.uow, data.actor.tenant_id, data.project_id)
        if project.audit is None:
            raise BusinessRuleViolation(
                "Primero debes completar la auditoría de mercado", code="audit_required"
            )
        label = None
        if data.node_id:
            nodes = project.funnel.nodes if project.funnel else []
            node = next((n for n in nodes if n["id"] == data.node_id), None)
            if node is None:
                raise NotFoundError("Nodo del embudo no encontrado")
            label = str(node["label"])
        return await AssetWriter(self.llm).write(data.kind, project.audit, project.niche, label)
