"""Bounded context: Identidad, workspaces (multi-tenant), roles y marca blanca."""

from __future__ import annotations

from fastapi import APIRouter

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container, Module


class IdentityModule(Module):
    name = "identity"

    def router(self) -> APIRouter:
        from oneheavy.modules.identity.api.router import router

        return router

    def register(self, container: Container) -> None:
        from oneheavy.modules.identity.application.handlers import ApplyPaidPlan
        from oneheavy.modules.identity.infrastructure.persistence import SqlIdentityUnitOfWork

        def uow() -> SqlIdentityUnitOfWork:
            return SqlIdentityUnitOfWork(container.session_factory, container.bus)

        container.bus.subscribe(ie.PaymentApproved, ApplyPaidPlan(uow))
