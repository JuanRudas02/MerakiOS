"""Puertos del módulo Growth."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from oneheavy.modules.growth.domain.model import Project
from oneheavy.shared.application.ports import UnitOfWork


class ProjectRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Project | None: ...

    @abstractmethod
    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Project]: ...

    @abstractmethod
    async def save(self, project: Project) -> None: ...


class GrowthUnitOfWork(UnitOfWork, ABC):
    projects: ProjectRepository
