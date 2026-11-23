"""Puertos de persistencia de Gamificación."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from oneheavy.modules.gamification.domain.model import Challenge, PlayerProfile, PointTransaction, Team
from oneheavy.modules.gamification.domain.rules import RuleSetting


@dataclass(frozen=True)
class LeaderboardRow:
    user_id: uuid.UUID
    name: str
    role: str
    points: int
    total_points: int


@dataclass(frozen=True)
class FeedRow:
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    points: int
    reason: str
    occurred_at: datetime


class PlayerRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> PlayerProfile | None: ...

    @abstractmethod
    async def add(self, player: PlayerProfile) -> None: ...

    @abstractmethod
    async def update(self, player: PlayerProfile) -> None: ...


class LedgerRepository(ABC):
    @abstractmethod
    async def exists(self, user_id: uuid.UUID, source_ref: str, rule_key: str) -> bool: ...

    @abstractmethod
    async def add(self, tx: PointTransaction) -> None: ...

    @abstractmethod
    async def counts_by_rule(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, int]: ...

    @abstractmethod
    async def progress(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        metric: str,
        since: datetime,
        until: datetime,
    ) -> int:
        """Suma de puntos si metric == "points"; si no, cantidad de transacciones de esa regla."""

    @abstractmethod
    async def leaderboard(
        self, tenant_id: uuid.UUID, since: datetime | None, team: Team | None, limit: int = 50
    ) -> list[LeaderboardRow]: ...

    @abstractmethod
    async def feed(self, tenant_id: uuid.UUID, limit: int = 50) -> list[FeedRow]: ...


class RuleSettingsRepository(ABC):
    @abstractmethod
    async def overrides(self, tenant_id: uuid.UUID) -> dict[str, RuleSetting]: ...

    @abstractmethod
    async def save(self, tenant_id: uuid.UUID, key: str, setting: RuleSetting) -> None: ...


class ChallengeRepository(ABC):
    @abstractmethod
    async def add(self, challenge: Challenge) -> None: ...

    @abstractmethod
    async def all(self, tenant_id: uuid.UUID) -> list[Challenge]: ...

    @abstractmethod
    async def active(self, tenant_id: uuid.UUID, now: datetime) -> list[Challenge]: ...
