"""Puertos de persistencia del módulo de identidad."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from oneheavy.modules.identity.domain.model import User, Workspace


class WorkspaceRepository(ABC):
    @abstractmethod
    async def get(self, workspace_id: uuid.UUID) -> Workspace | None: ...

    @abstractmethod
    async def slug_exists(self, slug: str) -> bool: ...

    @abstractmethod
    async def add(self, workspace: Workspace) -> None: ...

    @abstractmethod
    async def update(self, workspace: Workspace) -> None: ...


class UserRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def find_by_login(self, identifier: str) -> User | None:
        """Busca por email o username (global: el login no conoce el tenant)."""

    @abstractmethod
    async def exists_login(self, identifier: str) -> bool: ...

    @abstractmethod
    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[User]: ...

    @abstractmethod
    async def add(self, user: User) -> None: ...

    @abstractmethod
    async def update(self, user: User) -> None: ...
