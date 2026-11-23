"""Bounded context: Meta Business (Ads insights, alertas, Lead Ads, Conversions API)."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container, Module, ScheduledJob

log = logging.getLogger("oneheavy.meta")

CAPI_LEAD_STAGES = frozenset({"mql", "sql"})


class MetaModule(Module):
    name = "meta"

    def router(self) -> APIRouter:
        from oneheavy.modules.meta.api.router import router

        return router

    def register(self, container: Container) -> None:
        from oneheavy.modules.meta.application.use_cases import (
            RememberContact,
            SendConversion,
            SendConversionCommand,
        )
        from oneheavy.modules.meta.infrastructure.graph import FakeMetaGraphGateway, HttpMetaGraphGateway
        from oneheavy.modules.meta.infrastructure.persistence import SqlMetaUnitOfWork

        settings = container.settings
        container.extras.setdefault(
            "meta.graph",
            HttpMetaGraphGateway(settings.meta_graph_version)
            if settings.meta_enabled
            else FakeMetaGraphGateway(),
        )

        def uow() -> SqlMetaUnitOfWork:
            return SqlMetaUnitOfWork(container.session_factory, container.bus)

        async def on_contact_created(event: ie.ContactCreated) -> None:
            await RememberContact(uow()).execute(event)

        async def on_deal_won(event: ie.DealWon) -> None:
            await SendConversion(uow(), container.extras["meta.graph"]).execute(
                SendConversionCommand(
                    tenant_id=event.tenant_id,
                    event_name="Purchase",
                    event_id=f"deal-{event.deal_id}",
                    contact_id=event.contact_id,
                    occurred_at=event.occurred_at,
                    value=event.amount,
                    currency=event.currency,
                )
            )

        async def on_lifecycle(event: ie.ContactLifecycleChanged) -> None:
            if event.to_stage not in CAPI_LEAD_STAGES:
                return
            await SendConversion(uow(), container.extras["meta.graph"]).execute(
                SendConversionCommand(
                    tenant_id=event.tenant_id,
                    event_name="Lead",
                    event_id=f"lead-{event.contact_id}-{event.to_stage}",
                    contact_id=event.contact_id,
                    occurred_at=event.occurred_at,
                )
            )

        container.bus.subscribe(ie.ContactCreated, on_contact_created)
        container.bus.subscribe(ie.DealWon, on_deal_won)
        container.bus.subscribe(ie.ContactLifecycleChanged, on_lifecycle)

    def jobs(self, container: Container) -> list[ScheduledJob]:
        from oneheavy.modules.meta.application.use_cases import SyncInsights, SyncInsightsCommand
        from oneheavy.modules.meta.infrastructure.persistence import SqlMetaUnitOfWork

        async def sync_all() -> None:
            async with SqlMetaUnitOfWork(container.session_factory, container.bus) as uow:
                tenants = [c.tenant_id for c in await uow.connections.list_all()]
            for tenant_id in tenants:
                try:
                    await SyncInsights(
                        SqlMetaUnitOfWork(container.session_factory, container.bus),
                        container.extras["meta.graph"],
                    ).execute(SyncInsightsCommand(tenant_id=tenant_id, days=7))
                except Exception:
                    log.exception("meta_daily_sync_failed", extra={"tenant_id": str(tenant_id)})

        return [ScheduledJob("meta.daily_sync", sync_all, "cron", {"hour": 6, "minute": 0})]
