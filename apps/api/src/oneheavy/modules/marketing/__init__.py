"""Bounded context: Marketing automation con Mautic + IA (segmentos, emails y campañas)."""

from __future__ import annotations

from fastapi import APIRouter

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container, Module


class MarketingModule(Module):
    name = "marketing"

    def router(self) -> APIRouter:
        from oneheavy.modules.marketing.api.router import router

        return router

    def register(self, container: Container) -> None:
        from oneheavy.modules.marketing.api.router import GATEWAY_KEY
        from oneheavy.modules.marketing.application.ports import MauticGateway
        from oneheavy.modules.marketing.application.use_cases import (
            ProjectContactCreated,
            ProjectLifecycleChanged,
        )
        from oneheavy.modules.marketing.infrastructure.mautic import HttpMauticGateway, InMemoryMauticGateway
        from oneheavy.modules.marketing.infrastructure.persistence import SqlMarketingUnitOfWork

        s = container.settings
        if GATEWAY_KEY not in container.extras:
            gateway: MauticGateway
            if s.mautic_enabled and s.mautic_username and s.mautic_password:
                gateway = HttpMauticGateway(
                    s.mautic_base_url, s.mautic_username, s.mautic_password.get_secret_value()
                )
            else:
                gateway = InMemoryMauticGateway()  # sandbox: misma interfaz, sin red
            container.extras[GATEWAY_KEY] = gateway

        def uow() -> SqlMarketingUnitOfWork:
            return SqlMarketingUnitOfWork(container.session_factory, container.bus)

        async def on_contact_created(event: ie.ContactCreated) -> None:
            # Se resuelven en tiempo de ejecución para respetar overrides (tests / feature flags).
            await ProjectContactCreated(
                uow(), container.extras[GATEWAY_KEY], container.settings.mautic_enabled
            ).execute(event)

        async def on_lifecycle_changed(event: ie.ContactLifecycleChanged) -> None:
            await ProjectLifecycleChanged(uow()).execute(event)

        container.bus.subscribe(ie.ContactCreated, on_contact_created)
        container.bus.subscribe(ie.ContactLifecycleChanged, on_lifecycle_changed)
