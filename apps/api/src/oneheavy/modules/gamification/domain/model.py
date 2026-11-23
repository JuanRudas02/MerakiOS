"""Dominio de Gamificación: jugadores, ledger de puntos, niveles, insignias y retos."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum

from oneheavy.shared.domain.entity import TenantEntity, new_id
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.domain.time import utc_now


class Team(StrEnum):
    ALL = "all"
    OPERATIONS = "operations"
    SALES = "sales"
    MARKETING = "marketing"


_ROLE_TEAM = {
    "staff": Team.OPERATIONS,
    "coordinator": Team.OPERATIONS,
    "manager": Team.OPERATIONS,
    "sales": Team.SALES,
    "marketer": Team.MARKETING,
}


def team_for_role(role: str) -> Team:
    return _ROLE_TEAM.get(role, Team.ALL)


# ── Niveles ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Level:
    number: int
    name: str
    min_points: int


LEVELS: tuple[Level, ...] = (
    Level(1, "Rookie", 0),
    Level(2, "Pro", 250),
    Level(3, "Expert", 1000),
    Level(4, "Master", 3000),
    Level(5, "Legend", 7500),
    Level(6, "Heavy", 15000),
)


@dataclass(frozen=True)
class LevelProgress:
    number: int
    name: str
    min_points: int
    next_level_points: int | None
    progress: float  # 0-1 dentro del nivel actual


def level_for(points: int) -> LevelProgress:
    current = LEVELS[0]
    for level in LEVELS:
        if points >= level.min_points:
            current = level
    nxt = next((lv for lv in LEVELS if lv.number == current.number + 1), None)
    if nxt is None:
        return LevelProgress(current.number, current.name, current.min_points, None, 1.0)
    span = nxt.min_points - current.min_points
    progress = round(min(1.0, max(0.0, (points - current.min_points) / span)), 4)
    return LevelProgress(current.number, current.name, current.min_points, nxt.min_points, progress)


# ── Insignias ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BadgeStats:
    """Fotografía del jugador usada para evaluar insignias."""

    points: int
    streak_days: int
    counts: dict[str, int]  # rule_key → número de transacciones

    def count(self, *keys: str) -> int:
        return sum(self.counts.get(k, 0) for k in keys)


@dataclass(frozen=True)
class BadgeDefinition:
    key: str
    name: str
    description: str
    icon: str
    criteria: str
    predicate: Callable[[BadgeStats], bool] = field(compare=False, repr=False)


BADGES: tuple[BadgeDefinition, ...] = (
    BadgeDefinition(
        "first_clean",
        "Primera limpieza",
        "Completaste tu primera limpieza",
        "sparkles",
        "1 limpieza completada",
        lambda s: s.count("cleaning_completed_on_time", "cleaning_completed_late") >= 1,
    ),
    BadgeDefinition(
        "ten_cleans_on_time",
        "Puntualidad impecable",
        "10 limpiezas completadas a tiempo",
        "clock",
        "10 limpiezas a tiempo",
        lambda s: s.count("cleaning_completed_on_time") >= 10,
    ),
    BadgeDefinition(
        "eagle_eye",
        "Ojo de águila",
        "Reportaste 5 incidencias",
        "eye",
        "5 incidencias reportadas",
        lambda s: s.count("issue_reported") >= 5,
    ),
    BadgeDefinition(
        "lead_magnet",
        "Imán de leads",
        "Creaste 25 contactos",
        "magnet",
        "25 contactos creados",
        lambda s: s.count("contact_created") >= 25,
    ),
    BadgeDefinition(
        "deal_closer",
        "Cerrador",
        "Ganaste tu primer negocio",
        "trophy",
        "1 negocio ganado",
        lambda s: s.count("deal_won") >= 1,
    ),
    BadgeDefinition(
        "campaign_starter",
        "Lanzador",
        "Lanzaste tu primera campaña",
        "rocket",
        "1 campaña lanzada",
        lambda s: s.count("campaign_launched") >= 1,
    ),
    BadgeDefinition(
        "strategist",
        "Estratega",
        "Completaste una auditoría de mercado con IA",
        "brain",
        "1 auditoría completada",
        lambda s: s.count("market_audit_completed") >= 1,
    ),
    BadgeDefinition(
        "streak_7",
        "Racha de 7 días",
        "Sumaste puntos 7 días seguidos",
        "flame",
        "Racha de 7 días",
        lambda s: s.streak_days >= 7,
    ),
    BadgeDefinition(
        "century",
        "Mil puntos",
        "Alcanzaste 1.000 puntos",
        "medal",
        "1.000 puntos acumulados",
        lambda s: s.points >= 1000,
    ),
)
BADGES_BY_KEY = {b.key: b for b in BADGES}


@dataclass(frozen=True)
class EarnedBadge:
    key: str
    earned_at: datetime


# ── Ledger ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class PointTransaction:
    """Movimiento inmutable del ledger. (user_id, source_ref, rule_key) es único."""

    id: uuid.UUID = field(default_factory=new_id)
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    points: int
    rule_key: str
    reason: str
    source_ref: str  # event_id de origen (idempotencia) o id del reto
    occurred_at: datetime = field(default_factory=utc_now)


# ── Jugador ─────────────────────────────────────────────────────────────────


@dataclass(kw_only=True, eq=False)
class PlayerProfile(TenantEntity):
    """Perfil de juego. `id` == user_id del módulo de identidad."""

    name: str
    role: str
    team: Team
    points: int = 0
    streak_days: int = 0
    last_active_day: date | None = None
    badges: list[EarnedBadge] = field(default_factory=list)

    @classmethod
    def enroll(cls, tenant_id: uuid.UUID, user_id: uuid.UUID, name: str, role: str) -> PlayerProfile:
        return cls(id=user_id, tenant_id=tenant_id, name=name, role=role, team=team_for_role(role))

    @property
    def user_id(self) -> uuid.UUID:
        return self.id

    def apply(self, tx: PointTransaction) -> None:
        """Suma puntos y actualiza la racha diaria."""
        if tx.user_id != self.id:
            raise BusinessRuleViolation("La transacción no pertenece a este jugador")
        self.points += tx.points
        day = tx.occurred_at.date()
        if self.last_active_day is None or day > self.last_active_day:
            if self.last_active_day is not None and day - self.last_active_day == timedelta(days=1):
                self.streak_days += 1
            else:
                self.streak_days = 1
            self.last_active_day = day
        self.touch()

    def has_badge(self, key: str) -> bool:
        return any(b.key == key for b in self.badges)

    def evaluate_badges(self, counts: dict[str, int], now: datetime) -> list[str]:
        stats = BadgeStats(self.points, self.streak_days, counts)
        earned = [b.key for b in BADGES if not self.has_badge(b.key) and b.predicate(stats)]
        self.badges.extend(EarnedBadge(k, now) for k in earned)
        return earned

    @property
    def level(self) -> LevelProgress:
        return level_for(self.points)


# ── Retos ───────────────────────────────────────────────────────────────────


class ChallengeStatus(StrEnum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    FINISHED = "finished"


POINTS_METRIC = "points"


@dataclass(kw_only=True, eq=False)
class Challenge(TenantEntity):
    """Reto con ventana de tiempo. `metric` = rule_key a contar o "points" (suma)."""

    title: str
    description: str
    metric: str
    target: int
    starts_at: datetime
    ends_at: datetime
    reward_points: int
    team: Team = Team.ALL

    def __post_init__(self) -> None:
        if self.target <= 0:
            raise BusinessRuleViolation("La meta del reto debe ser positiva")
        if self.ends_at <= self.starts_at:
            raise BusinessRuleViolation("El reto debe terminar después de empezar")
        if self.reward_points < 0:
            raise BusinessRuleViolation("La recompensa no puede ser negativa")

    def status(self, now: datetime) -> ChallengeStatus:
        if now < self.starts_at:
            return ChallengeStatus.UPCOMING
        if now > self.ends_at:
            return ChallengeStatus.FINISHED
        return ChallengeStatus.ACTIVE

    def applies_to(self, team: Team) -> bool:
        return self.team is Team.ALL or self.team is team

    @property
    def reward_rule_key(self) -> str:
        return "challenge_completed"
