"""Bounded context: Growth IA (ex MerakiOS) — auditoría de mercado, embudos y copy con IA."""

from __future__ import annotations

from fastapi import APIRouter

from oneheavy.shared.infrastructure.container import Module


class GrowthModule(Module):
    name = "growth"

    def router(self) -> APIRouter:
        from oneheavy.modules.growth.api.router import router

        return router
