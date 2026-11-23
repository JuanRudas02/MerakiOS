"""Puertos de aplicación de Analítica."""

from __future__ import annotations

from abc import ABC

from oneheavy.modules.analytics.domain.repositories import ContactStageRepository, FactRepository
from oneheavy.shared.application.ports import UnitOfWork


class AnalyticsUnitOfWork(UnitOfWork, ABC):
    facts: FactRepository
    stages: ContactStageRepository
