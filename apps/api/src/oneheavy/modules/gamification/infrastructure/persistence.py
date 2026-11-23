"""Adaptador de salida: persistencia SQLAlchemy de Gamificación."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Self

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.gamification.application.ports import GamificationUnitOfWork
from oneheavy.modules.gamification.domain.model import (
    POINTS_METRIC,
    Challenge,
    EarnedBadge,
    PlayerProfile,
    PointTransaction,
    Team,
)
from oneheavy.modules.gamification.domain.repositories import (
    ChallengeRepository,
    FeedRow,
    LeaderboardRow,
    LedgerRepository,
    PlayerRepository,
    RuleSettingsRepository,
)
from oneheavy.modules.gamification.domain.rules import RuleSetting
from oneheavy.shared.domain.time import ensure_aware
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TenantMixin, TimestampMixin

# ── ORM ─────────────────────────────────────────────────────────────────────


class PlayerRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "gamification_players"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # == user_id
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    team: Mapped[str] = mapped_column(String(20), index=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active_day: Mapped[date | None] = mapped_column(Date)
    badges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class LedgerRow(TenantMixin, Base):
    __tablename__ = "gamification_ledger"
    __table_args__ = (
        UniqueConstraint("user_id", "source_ref", "rule_key", name="uq_gamification_ledger_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    points: Mapped[int] = mapped_column(Integer)
    rule_key: Mapped[str] = mapped_column(String(60), index=True)
    reason: Mapped[str] = mapped_column(String(200))
    source_ref: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RuleSettingRow(TenantMixin, Base):
    __tablename__ = "gamification_rule_settings"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_gamification_rule_settings_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(60))
    points: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ChallengeRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "gamification_challenges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(String(1000), default="")
    metric: Mapped[str] = mapped_column(String(60))
    target: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reward_points: Mapped[int] = mapped_column(Integer, default=0)
    team: Mapped[str] = mapped_column(String(20), default=Team.ALL.value)


# ── Mappers ─────────────────────────────────────────────────────────────────


def _player_to_domain(row: PlayerRow) -> PlayerProfile:
    return PlayerProfile(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        role=row.role,
        team=Team(row.team),
        points=row.points,
        streak_days=row.streak_days,
        last_active_day=row.last_active_day,
        badges=[
            EarnedBadge(b["key"], ensure_aware(datetime.fromisoformat(b["earned_at"])))
            for b in row.badges or []
        ],
        created_at=ensure_aware(row.created_at),
        updated_at=ensure_aware(row.updated_at),
    )


def _player_apply(row: PlayerRow, p: PlayerProfile) -> None:
    row.tenant_id, row.name, row.role, row.team = p.tenant_id, p.name, p.role, p.team.value
    row.points, row.streak_days, row.last_active_day = p.points, p.streak_days, p.last_active_day
    row.badges = [{"key": b.key, "earned_at": b.earned_at.isoformat()} for b in p.badges]
    row.created_at, row.updated_at = p.created_at, p.updated_at


def _challenge_to_domain(row: ChallengeRow) -> Challenge:
    return Challenge(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        description=row.description,
        metric=row.metric,
        target=row.target,
        starts_at=ensure_aware(row.starts_at),
        ends_at=ensure_aware(row.ends_at),
        reward_points=row.reward_points,
        team=Team(row.team),
        created_at=ensure_aware(row.created_at),
        updated_at=ensure_aware(row.updated_at),
    )


# ── Repositorios ────────────────────────────────────────────────────────────


class SqlPlayerRepository(PlayerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> PlayerProfile | None:
        row = await self._s.get(PlayerRow, user_id)
        return _player_to_domain(row) if row and row.tenant_id == tenant_id else None

    async def add(self, player: PlayerProfile) -> None:
        row = PlayerRow(id=player.id)
        _player_apply(row, player)
        self._s.add(row)

    async def update(self, player: PlayerProfile) -> None:
        row = await self._s.get(PlayerRow, player.id)
        if row is not None:
            _player_apply(row, player)


class SqlLedgerRepository(LedgerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def exists(self, user_id: uuid.UUID, source_ref: str, rule_key: str) -> bool:
        stmt = select(LedgerRow.id).where(
            LedgerRow.user_id == user_id, LedgerRow.source_ref == source_ref, LedgerRow.rule_key == rule_key
        )
        return (await self._s.scalar(stmt)) is not None

    async def add(self, tx: PointTransaction) -> None:
        self._s.add(
            LedgerRow(
                id=tx.id,
                tenant_id=tx.tenant_id,
                user_id=tx.user_id,
                points=tx.points,
                rule_key=tx.rule_key,
                reason=tx.reason,
                source_ref=tx.source_ref,
                occurred_at=tx.occurred_at,
            )
        )

    async def counts_by_rule(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(LedgerRow.rule_key, func.count())
            .where(LedgerRow.tenant_id == tenant_id, LedgerRow.user_id == user_id)
            .group_by(LedgerRow.rule_key)
        )
        return {key: int(n) for key, n in (await self._s.execute(stmt)).all()}

    async def progress(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, metric: str, since: datetime, until: datetime
    ) -> int:
        agg = func.coalesce(func.sum(LedgerRow.points), 0) if metric == POINTS_METRIC else func.count()
        stmt = select(agg).where(
            LedgerRow.tenant_id == tenant_id,
            LedgerRow.user_id == user_id,
            LedgerRow.occurred_at >= since,
            LedgerRow.occurred_at <= until,
        )
        if metric != POINTS_METRIC:
            stmt = stmt.where(LedgerRow.rule_key == metric)
        return int(await self._s.scalar(stmt) or 0)

    async def leaderboard(
        self, tenant_id: uuid.UUID, since: datetime | None, team: Team | None, limit: int = 50
    ) -> list[LeaderboardRow]:
        total = func.sum(LedgerRow.points).label("period_points")
        stmt = (
            select(LedgerRow.user_id, PlayerRow.name, PlayerRow.role, PlayerRow.points, total)
            .join(PlayerRow, PlayerRow.id == LedgerRow.user_id)
            .where(LedgerRow.tenant_id == tenant_id)
            .group_by(LedgerRow.user_id, PlayerRow.name, PlayerRow.role, PlayerRow.points)
            .order_by(total.desc(), PlayerRow.name)
            .limit(limit)
        )
        if since is not None:
            stmt = stmt.where(LedgerRow.occurred_at >= since)
        if team is not None:
            stmt = stmt.where(PlayerRow.team == team.value)
        rows = (await self._s.execute(stmt)).all()
        return [LeaderboardRow(uid, name, role, int(pts), int(tot)) for uid, name, role, tot, pts in rows]

    async def feed(self, tenant_id: uuid.UUID, limit: int = 50) -> list[FeedRow]:
        stmt = (
            select(LedgerRow, PlayerRow.name)
            .join(PlayerRow, PlayerRow.id == LedgerRow.user_id)
            .where(LedgerRow.tenant_id == tenant_id)
            .order_by(LedgerRow.occurred_at.desc())
            .limit(limit)
        )
        return [
            FeedRow(r.id, r.user_id, name, r.points, r.reason, ensure_aware(r.occurred_at))
            for r, name in (await self._s.execute(stmt)).all()
        ]


class SqlRuleSettingsRepository(RuleSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def overrides(self, tenant_id: uuid.UUID) -> dict[str, RuleSetting]:
        rows = await self._s.scalars(select(RuleSettingRow).where(RuleSettingRow.tenant_id == tenant_id))
        return {r.key: RuleSetting(r.points, r.active) for r in rows}

    async def save(self, tenant_id: uuid.UUID, key: str, setting: RuleSetting) -> None:
        row = await self._s.scalar(
            select(RuleSettingRow).where(RuleSettingRow.tenant_id == tenant_id, RuleSettingRow.key == key)
        )
        if row is None:
            self._s.add(
                RuleSettingRow(tenant_id=tenant_id, key=key, points=setting.points, active=setting.active)
            )
        else:
            row.points, row.active = setting.points, setting.active


class SqlChallengeRepository(ChallengeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, challenge: Challenge) -> None:
        c = challenge
        self._s.add(
            ChallengeRow(
                id=c.id,
                tenant_id=c.tenant_id,
                title=c.title,
                description=c.description,
                metric=c.metric,
                target=c.target,
                starts_at=c.starts_at,
                ends_at=c.ends_at,
                reward_points=c.reward_points,
                team=c.team.value,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    async def all(self, tenant_id: uuid.UUID) -> list[Challenge]:
        rows = await self._s.scalars(
            select(ChallengeRow)
            .where(ChallengeRow.tenant_id == tenant_id)
            .order_by(ChallengeRow.starts_at.desc())
        )
        return [_challenge_to_domain(r) for r in rows]

    async def active(self, tenant_id: uuid.UUID, now: datetime) -> list[Challenge]:
        rows = await self._s.scalars(
            select(ChallengeRow).where(
                ChallengeRow.tenant_id == tenant_id,
                ChallengeRow.starts_at <= now,
                ChallengeRow.ends_at >= now,
            )
        )
        return [_challenge_to_domain(r) for r in rows]


class SqlGamificationUnitOfWork(SqlAlchemyUnitOfWork, GamificationUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.players = SqlPlayerRepository(self.session)
        self.ledger = SqlLedgerRepository(self.session)
        self.rules = SqlRuleSettingsRepository(self.session)
        self.challenges = SqlChallengeRepository(self.session)
        return self
