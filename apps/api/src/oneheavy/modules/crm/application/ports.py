"""Puertos de aplicación del CRM."""

from __future__ import annotations

from abc import ABC

from oneheavy.modules.crm.domain.repositories import ActivityRepository, ContactRepository, DealRepository
from oneheavy.shared.application.ports import UnitOfWork


class CrmUnitOfWork(UnitOfWork, ABC):
    contacts: ContactRepository
    activities: ActivityRepository
    deals: DealRepository
