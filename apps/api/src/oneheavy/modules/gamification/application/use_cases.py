"""Casos de uso de Gamificación.

CU-GA-01  Otorgar puntos por evento de dominio (proceso automático, idempotente)
CU-GA-02  Inscribir/actualizar jugador al registrarse un usuario
CU-GA-03  Consultar mi perfil (puntos, nivel, racha, insignias, ranking)
CU-GA-04  Consultar leaderboard por periodo y equipo
CU-GA-05  Consultar feed de actividad
CU-GA-06  Consultar catálogo de insignias
CU-GA-07  Listar retos con mi progreso
CU-GA-08  Crear reto
CU-GA-09  Listar reglas de puntos
CU-GA-10  Configurar regla de puntos (puntos / activa)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from oneheavy.modules.gamification.application.ports import GamificationUnitOfWork
from oneheavy.modules.gamification.domain.model import (
    BADGES,
    BADGES_BY_KEY,
    BadgeDefinition,
    Challenge,
    ChallengeStatus,
    LevelProgress,
    PlayerProfile,
    PointTransaction,
    Team,
)
from oneheavy.modules.gamification.domain.repositories import FeedRow, LeaderboardRow
from oneheavy.modules.gamification.domain.rules import RuleEngine, RuleSetting
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import NotFoundError
from oneheavy.shared.domain.events import DomainEvent
from oneheavy.shared.domain.time import utc_now

# ── CU-GA-01 ────────────────────────────────────────────────────────────────


class AwardPointsForEvent(UseCase[DomainEvent, list[PointTransaction]]):
    def __init__(self, uow: GamificationUnitOfWork, engine: RuleEngine) -> None:
        self.uow, self.engine = uow, engine

    async def execute(self, data: DomainEvent) -> list[PointTransaction]:
        applied: list[PointTransaction] = []
        async with self.uow:
            overrides = await self.uow.rules.overrides(data.tenant_id)
            for award in self.engine.evaluate(data, overrides):
                source_ref = str(data.event_id)
                if await self.uow.ledger.exists(award.user_id, source_ref, award.rule_key):
                    continue  # evento repetido: idempotencia
                tx = PointTransaction(
                    tenant_id=data.tenant_id,
                    user_id=award.user_id,
                    points=award.points,
                    rule_key=award.rule_key,
                    reason=award.reason,
                    source_ref=source_ref,
                    occurred_at=data.occurred_at,
                )
                applied.extend(await self._apply(tx, check_challenges=True))
            if applied:
                await self.uow.commit()
        return applied

    async def _apply(self, tx: PointTransaction, *, check_challenges: bool) -> list[PointTransaction]:
        player = await self.uow.players.get(tx.tenant_id, tx.user_id)
        is_new = player is None
        if player is None:
            player = PlayerProfile.enroll(tx.tenant_id, tx.user_id, "Colaborador", "unknown")
        await self.uow.ledger.add(tx)
        player.apply(tx)
        counts = await self.uow.ledger.counts_by_rule(tx.tenant_id, tx.user_id)
        player.evaluate_badges(counts, utc_now())
        if is_new:
            await self.uow.players.add(player)
        else:
            await self.uow.players.update(player)
        self.uow.collect(
            [
                ie.PointsAwarded(
                    tenant_id=tx.tenant_id,
                    actor_id=tx.user_id,
                    user_id=tx.user_id,
                    points=tx.points,
                    reason=tx.reason,
                    rule_key=tx.rule_key,
                )
            ]
        )
        applied = [tx]
        if check_challenges:
            applied.extend(await self._reward_challenges(player))
        return applied

    async def _reward_challenges(self, player: PlayerProfile) -> list[PointTransaction]:
        now = utc_now()
        rewarded: list[PointTransaction] = []
        for challenge in await self.uow.challenges.active(player.tenant_id, now):
            if not challenge.applies_to(player.team) or challenge.reward_points <= 0:
                continue
            ref = str(challenge.id)
            if await self.uow.ledger.exists(player.user_id, ref, challenge.reward_rule_key):
                continue
            progress = await self.uow.ledger.progress(
                player.tenant_id, player.user_id, challenge.metric, challenge.starts_at, challenge.ends_at
            )
            if progress < challenge.target:
                continue
            reward = PointTransaction(
                tenant_id=player.tenant_id,
                user_id=player.user_id,
                points=challenge.reward_points,
                rule_key=challenge.reward_rule_key,
                reason=f"Reto completado: {challenge.title}",
                source_ref=ref,
                occurred_at=now,
            )
            rewarded.extend(await self._apply(reward, check_challenges=False))
        return rewarded


# ── CU-GA-02 ────────────────────────────────────────────────────────────────


class EnrollPlayer(UseCase[ie.UserRegistered, PlayerProfile]):
    def __init__(self, uow: GamificationUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ie.UserRegistered) -> PlayerProfile:
        async with self.uow:
            player = await self.uow.players.get(data.tenant_id, data.user_id)
            if player is None:
                player = PlayerProfile.enroll(data.tenant_id, data.user_id, data.name, data.role)
                await self.uow.players.add(player)
            else:
                updated = PlayerProfile.enroll(data.tenant_id, data.user_id, data.name, data.role)
                player.name, player.role, player.team = updated.name, updated.role, updated.team
                await self.uow.players.update(player)
            await self.uow.commit()
        return player


# ── Consultas ───────────────────────────────────────────────────────────────


class Period(StrEnum):
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


def period_start(period: Period, now: datetime) -> datetime | None:
    if period is Period.WEEK:
        return now - timedelta(days=7)
    if period is Period.MONTH:
        return now - timedelta(days=30)
    return None


@dataclass(frozen=True)
class BadgeView:
    definition: BadgeDefinition
    earned_at: datetime


@dataclass(frozen=True)
class ProfileView:
    user_id: uuid.UUID
    name: str
    points: int
    level: LevelProgress
    streak_days: int
    badges: list[BadgeView]
    rank: int | None


class GetMyProfile(UseCase[Principal, ProfileView]):
    def __init__(self, uow: GamificationUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> ProfileView:
        data.require(Permission.GAMIFICATION_READ)
        async with self.uow:
            player = await self.uow.players.get(data.tenant_id, data.user_id)
            board = await self.uow.ledger.leaderboard(data.tenant_id, None, None, limit=1000)
        if player is None:
            player = PlayerProfile.enroll(data.tenant_id, data.user_id, "", data.role.value)
        rank = next((i + 1 for i, row in enumerate(board) if row.user_id == data.user_id), None)
        badges = [
            BadgeView(BADGES_BY_KEY[b.key], b.earned_at) for b in player.badges if b.key in BADGES_BY_KEY
        ]
        return ProfileView(
            player.user_id, player.name, player.points, player.level, player.streak_days, badges, rank
        )


@dataclass(frozen=True)
class LeaderboardQuery:
    actor: Principal
    period: Period = Period.WEEK
    team: Team = Team.ALL


class GetLeaderboard(UseCase[LeaderboardQuery, list[LeaderboardRow]]):
    def __init__(self, uow: GamificationUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: LeaderboardQuery) -> list[LeaderboardRow]:
        data.actor.require(Permission.GAMIFICATION_READ)
        since = period_start(data.period, utc_now())
        team = None if data.team is Team.ALL else data.team
        async with self.uow:
            return await self.uow.ledger.leaderboard(data.actor.tenant_id, since, team)


class GetFeed(UseCase[Principal, list[FeedRow]]):
    def __init__(self, uow: GamificationUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[FeedRow]:
        data.require(Permission.GAMIFICATION_READ)
        async with self.uow:
            return await self.uow.ledger.feed(data.tenant_id, 50)


class ListBadges(UseCase[Principal, tuple[BadgeDefinition, ...]]):
    async def execute(self, data: Principal) -> tuple[BadgeDefinition, ...]:
        data.require(Permission.GAMIFICATION_READ)
        return BADGES


# ── Retos ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ChallengeView:
    challenge: Challenge
    progress: int
    status: ChallengeStatus


class ListChallenges(UseCase[Principal, list[ChallengeView]]):
    def __init__(self, uow: GamificationUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[ChallengeView]:
        data.require(Permission.GAMIFICATION_READ)
        now = utc_now()
        views: list[ChallengeView] = []
        async with self.uow:
            for ch in await self.uow.challenges.all(data.tenant_id):
                progress = await self.uow.ledger.progress(
                    data.tenant_id, data.user_id, ch.metric, ch.starts_at, ch.ends_at
                )
                views.append(ChallengeView(ch, progress, ch.status(now)))
        return views


@dataclass(frozen=True)
class CreateChallengeCommand:
    actor: Principal
    title: str
    description: str
    metric: str
    target: int
    starts_at: datetime
    ends_at: datetime
    reward_points: int
    team: Team = Team.ALL


class CreateChallenge(UseCase[CreateChallengeCommand, ChallengeView]):
    def __init__(self, uow: GamificationUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: CreateChallengeCommand) -> ChallengeView:
        data.actor.require(Permission.GAMIFICATION_MANAGE)
        challenge = Challenge(
            tenant_id=data.actor.tenant_id,
            title=data.title.strip(),
            description=data.description.strip(),
            metric=data.metric,
            target=data.target,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            reward_points=data.reward_points,
            team=data.team,
        )
        async with self.uow:
            await self.uow.challenges.add(challenge)
            await self.uow.commit()
        return ChallengeView(challenge, 0, challenge.status(utc_now()))


# ── Reglas ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RuleView:
    key: str
    event: str
    description: str
    points: int
    active: bool


class ListRules(UseCase[Principal, list[RuleView]]):
    def __init__(self, uow: GamificationUnitOfWork, engine: RuleEngine) -> None:
        self.uow, self.engine = uow, engine

    async def execute(self, data: Principal) -> list[RuleView]:
        data.require(Permission.GAMIFICATION_READ)
        async with self.uow:
            overrides = await self.uow.rules.overrides(data.tenant_id)
        views = []
        for rule in self.engine.rules:
            s = self.engine.setting_for(rule, overrides)
            views.append(RuleView(rule.key, rule.event_type.__name__, rule.description, s.points, s.active))
        return views


@dataclass(frozen=True)
class UpdateRuleCommand:
    actor: Principal
    key: str
    points: int
    active: bool


class UpdateRule(UseCase[UpdateRuleCommand, RuleView]):
    def __init__(self, uow: GamificationUnitOfWork, engine: RuleEngine) -> None:
        self.uow, self.engine = uow, engine

    async def execute(self, data: UpdateRuleCommand) -> RuleView:
        data.actor.require(Permission.GAMIFICATION_MANAGE)
        rule = self.engine.get(data.key)
        if rule is None:
            raise NotFoundError(f"Regla '{data.key}' no existe")
        async with self.uow:
            await self.uow.rules.save(data.actor.tenant_id, rule.key, RuleSetting(data.points, data.active))
            await self.uow.commit()
        return RuleView(rule.key, rule.event_type.__name__, rule.description, data.points, data.active)
