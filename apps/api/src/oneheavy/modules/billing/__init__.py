"""Bounded context: Suscripciones y pagos (Wompi)."""

from __future__ import annotations

from fastapi import APIRouter

from oneheavy.shared.infrastructure.container import Module


class BillingModule(Module):
    name = "billing"

    def router(self) -> APIRouter:
        from oneheavy.modules.billing.api.router import router

        return router
