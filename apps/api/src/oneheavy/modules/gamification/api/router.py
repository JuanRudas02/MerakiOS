"""Adaptador REST de Gamificación (/api/v1/gamification)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, model_validator

from oneheavy.modules.gamification.application.use_cases import (
    ChallengeView,
    CreateChallenge,
    CreateChallengeCommand,
    GetFeed,
    GetLeaderboard,
    GetMyProfile,
    LeaderboardQuery,
    ListBadges,
    ListChallenges,
    ListRules,
    Period,
    RuleView,
    UpdateRule,
    UpdateRuleCommand,
)
from oneheavy.modules.gamification.domain.model import Team, level_for
from oneheavy.modules.gamification.domain.rules import RuleEngine
from oneheavy.modules.gamification.infrastructure.persistence import SqlGamificationUnitOfWork
from oneheavy.shared.domain.access import Principal
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, get_principal

router = APIRouter(prefix="/gamification", tags=["Gamification"])


def _uow(container: Container = Depends(get_container)) -> SqlGamificationUnitOfWork:
    return SqlGamificationUnitOfWork(container.session_factory, container.bus)


def _engine(container: Container = Depends(get_container)) -> RuleEngine:
    engine: RuleEngine = container.extras.setdefault("gamification.engine", RuleEngine())
    return engine


# ── Schemas ─────────────────────────────────────────────────────────────────


class LevelOut(BaseModel):
    number: int
    name: str
    min_points: int
    next_level_points: int | None
    progress: float


class EarnedBadgeOut(BaseModel):
    key: str
    name: str
    description: str
    icon: str
    earned_at: datetime


class PlayerProfileOut(BaseModel):
    user_id: uuid.UUID
    name: str
    points: int
    level: LevelOut
    streak_days: int
    badges: list[EarnedBadgeOut]
    rank: int | None


class LeaderboardEntryOut(BaseModel):
    rank: int
    user_id: uuid.UUID
    name: str
    role: str
    points: int
    level: int


class FeedItemOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    points: int
    reason: str
    occurred_at: datetime


class BadgeOut(BaseModel):
    key: str
    name: str
    description: str
    icon: str
    criteria: str


class ChallengeIn(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(default="", max_length=1000)
    metric: str = Field(min_length=2, max_length=60, description='rule_key o "points"')
    target: int = Field(gt=0)
    starts_at: datetime
    ends_at: datetime
    reward_points: int = Field(ge=0, le=100_000)
    team: Team = Team.ALL

    @model_validator(mode="after")
    def _window(self) -> ChallengeIn:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at debe ser posterior a starts_at")
        return self


class ChallengeOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    metric: str
    target: int
    progress: int
    starts_at: datetime
    ends_at: datetime
    reward_points: int
    team: Team
    status: str

    @classmethod
    def of(cls, v: ChallengeView) -> ChallengeOut:
        c = v.challenge
        return cls(
            id=c.id,
            title=c.title,
            description=c.description,
            metric=c.metric,
            target=c.target,
            progress=v.progress,
            starts_at=c.starts_at,
            ends_at=c.ends_at,
            reward_points=c.reward_points,
            team=c.team,
            status=v.status.value,
        )


class RuleOut(BaseModel):
    key: str
    event: str
    description: str
    points: int
    active: bool

    @classmethod
    def of(cls, r: RuleView) -> RuleOut:
        return cls(key=r.key, event=r.event, description=r.description, points=r.points, active=r.active)


class RuleIn(BaseModel):
    points: int = Field(ge=0, le=10_000)
    active: bool = True


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/me", response_model=PlayerProfileOut)
async def me(
    principal: Principal = Depends(get_principal), uow: SqlGamificationUnitOfWork = Depends(_uow)
) -> PlayerProfileOut:
    v = await GetMyProfile(uow).execute(principal)
    lv = v.level
    return PlayerProfileOut(
        user_id=v.user_id,
        name=v.name,
        points=v.points,
        level=LevelOut(
            number=lv.number,
            name=lv.name,
            min_points=lv.min_points,
            next_level_points=lv.next_level_points,
            progress=lv.progress,
        ),
        streak_days=v.streak_days,
        badges=[
            EarnedBadgeOut(
                key=b.definition.key,
                name=b.definition.name,
                description=b.definition.description,
                icon=b.definition.icon,
                earned_at=b.earned_at,
            )
            for b in v.badges
        ],
        rank=v.rank,
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntryOut])
async def leaderboard(
    period: Period = Query(Period.WEEK),
    team: Team = Query(Team.ALL),
    principal: Principal = Depends(get_principal),
    uow: SqlGamificationUnitOfWork = Depends(_uow),
) -> list[LeaderboardEntryOut]:
    rows = await GetLeaderboard(uow).execute(LeaderboardQuery(principal, period, team))
    return [
        LeaderboardEntryOut(
            rank=i + 1,
            user_id=r.user_id,
            name=r.name,
            role=r.role,
            points=r.points,
            level=level_for(r.total_points).number,
        )
        for i, r in enumerate(rows)
    ]


@router.get("/feed", response_model=list[FeedItemOut])
async def feed(
    principal: Principal = Depends(get_principal), uow: SqlGamificationUnitOfWork = Depends(_uow)
) -> list[FeedItemOut]:
    rows = await GetFeed(uow).execute(principal)
    return [
        FeedItemOut(
            id=r.id,
            user_id=r.user_id,
            user_name=r.user_name,
            points=r.points,
            reason=r.reason,
            occurred_at=r.occurred_at,
        )
        for r in rows
    ]


@router.get("/badges", response_model=list[BadgeOut])
async def badges(principal: Principal = Depends(get_principal)) -> list[BadgeOut]:
    return [
        BadgeOut(key=b.key, name=b.name, description=b.description, icon=b.icon, criteria=b.criteria)
        for b in await ListBadges().execute(principal)
    ]


@router.get("/challenges", response_model=list[ChallengeOut])
async def challenges(
    principal: Principal = Depends(get_principal), uow: SqlGamificationUnitOfWork = Depends(_uow)
) -> list[ChallengeOut]:
    return [ChallengeOut.of(v) for v in await ListChallenges(uow).execute(principal)]


@router.post("/challenges", response_model=ChallengeOut, status_code=status.HTTP_201_CREATED)
async def create_challenge(
    body: ChallengeIn,
    principal: Principal = Depends(get_principal),
    uow: SqlGamificationUnitOfWork = Depends(_uow),
) -> ChallengeOut:
    view = await CreateChallenge(uow).execute(CreateChallengeCommand(actor=principal, **body.model_dump()))
    return ChallengeOut.of(view)


@router.get("/rules", response_model=list[RuleOut])
async def rules(
    principal: Principal = Depends(get_principal),
    uow: SqlGamificationUnitOfWork = Depends(_uow),
    engine: RuleEngine = Depends(_engine),
) -> list[RuleOut]:
    return [RuleOut.of(r) for r in await ListRules(uow, engine).execute(principal)]


@router.put("/rules/{key}", response_model=RuleOut)
async def update_rule(
    key: str,
    body: RuleIn,
    principal: Principal = Depends(get_principal),
    uow: SqlGamificationUnitOfWork = Depends(_uow),
    engine: RuleEngine = Depends(_engine),
) -> RuleOut:
    view = await UpdateRule(uow, engine).execute(UpdateRuleCommand(principal, key, body.points, body.active))
    return RuleOut.of(view)
