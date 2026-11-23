"""Bounded context: CRM — contactos, ciclo de vida, pipeline de negocios, timeline y lead scoring."""

from __future__ import annotations

from fastapi import APIRouter

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container, Module


class CrmModule(Module):
    name = "crm"

    def router(self) -> APIRouter:
        from oneheavy.modules.crm.api.router import router

        return router

    def register(self, container: Container) -> None:
        from oneheavy.modules.crm.application.use_cases import CaptureLead, RecordEngagement
        from oneheavy.modules.crm.infrastructure.persistence import SqlCrmUnitOfWork

        def uow() -> SqlCrmUnitOfWork:
            return SqlCrmUnitOfWork(container.session_factory, container.bus)

        async def on_lead_captured(event: ie.LeadCaptured) -> None:
            await CaptureLead(uow()).execute(event)

        async def on_engagement(event: ie.MarketingEngagementRecorded) -> None:
            await RecordEngagement(uow()).execute(event)

        async def on_mautic_synced(event: ie.MarketingContactSynced) -> None:
            async with uow() as tx:
                contact = await tx.contacts.get(event.tenant_id, event.contact_id)
                if contact is not None and contact.mautic_id != event.mautic_id:
                    contact.mautic_id = event.mautic_id
                    await tx.contacts.update(contact)
                    await tx.commit()

        container.bus.subscribe(ie.LeadCaptured, on_lead_captured)
        container.bus.subscribe(ie.MarketingContactSynced, on_mautic_synced)
        container.bus.subscribe(ie.MarketingEngagementRecorded, on_engagement)
