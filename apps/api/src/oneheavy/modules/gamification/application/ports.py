"""Puertos de aplicación de Gamificación."""

from __future__ import annotations

from abc import ABC

from oneheavy.modules.gamification.domain.repositories import (
    ChallengeRepository,
    LedgerRepository,
    PlayerRepository,
    RuleSettingsRepository,
)
from oneheavy.shared.application.ports import UnitOfWork


class GamificationUnitOfWork(UnitOfWork, ABC):
    players: PlayerRepository
    ledger: LedgerRepository
    rules: RuleSettingsRepository
    challenges: ChallengeRepository
