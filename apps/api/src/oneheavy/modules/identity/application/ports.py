"""Puertos de aplicación del módulo de identidad."""

from __future__ import annotations

from abc import ABC

from oneheavy.modules.identity.domain.repositories import UserRepository, WorkspaceRepository
from oneheavy.shared.application.ports import UnitOfWork


class IdentityUnitOfWork(UnitOfWork, ABC):
    """UoW con los repositorios del contexto, listos tras `async with`."""

    workspaces: WorkspaceRepository
    users: UserRepository
