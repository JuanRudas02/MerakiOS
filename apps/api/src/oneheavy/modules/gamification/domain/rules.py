"""Motor de reglas de puntos (patrón Strategy).

Cada `PointRule` sabe: a qué evento reacciona, si aplica, a quién premia y
cuántos puntos otorga a partir de su valor base. El valor base y la activación
son configurables por workspace (`RuleSetting`).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.events import DomainEvent


@dataclass(frozen=True)
class RuleSetting:
    points: int
    active: bool = True


@dataclass(frozen=True)
class Award:
    user_id: uuid.UUID
    points: int
    rule_key: str
    reason: str


class PointRule(ABC):
    key: ClassVar[str]
    event_type: ClassVar[type[DomainEvent]]
    description: ClassVar[str]
    default_points: ClassVar[int]

    def applies(self, event: DomainEvent) -> bool:
        return True

    def beneficiary(self, event: DomainEvent) -> uuid.UUID | None:
        return event.actor_id

    def compute(self, event: DomainEvent, base: int) -> int:
        return base

    @abstractmethod
    def reason(self, event: DomainEvent) -> str: ...

    def evaluate(self, event: DomainEvent, setting: RuleSetting) -> Award | None:
        if not setting.active or not isinstance(event, self.event_type) or not self.applies(event):
            return None
        user_id = self.beneficiary(event)
        points = self.compute(event, setting.points)
        if user_id is None or points <= 0:
            return None
        return Award(user_id, points, self.key, self.reason(event))


# ── Operación (Stays) ───────────────────────────────────────────────────────


class _CleaningRule(PointRule):
    def beneficiary(self, event: DomainEvent) -> uuid.UUID | None:
        staff = getattr(event, "staff_id", None)
        return staff if staff is not None else event.actor_id


class CleaningOnTimeRule(_CleaningRule):
    key = "cleaning_completed_on_time"
    event_type = ie.CleaningTaskCompleted
    description = "Limpieza completada a tiempo"
    default_points = 50

    def applies(self, event: DomainEvent) -> bool:
        return isinstance(event, ie.CleaningTaskCompleted) and event.on_time

    def reason(self, event: DomainEvent) -> str:
        return "Limpieza completada a tiempo"


class CleaningLateRule(_CleaningRule):
    key = "cleaning_completed_late"
    event_type = ie.CleaningTaskCompleted
    description = "Limpieza completada con retraso"
    default_points = 20

    def applies(self, event: DomainEvent) -> bool:
        return isinstance(event, ie.CleaningTaskCompleted) and not event.on_time

    def reason(self, event: DomainEvent) -> str:
        return "Limpieza completada"


class CleaningPhotosRule(_CleaningRule):
    key = "cleaning_photos"
    event_type = ie.CleaningTaskCompleted
    description = "Puntos por foto de evidencia (máx. 30 por tarea)"
    default_points = 5
    cap: ClassVar[int] = 30

    def compute(self, event: DomainEvent, base: int) -> int:
        photos = event.photos_count if isinstance(event, ie.CleaningTaskCompleted) else 0
        return min(self.cap, base * photos)

    def reason(self, event: DomainEvent) -> str:
        return "Evidencia fotográfica"


class ArrivalOnTimeRule(_CleaningRule):
    key = "arrival_on_time"
    event_type = ie.CleaningArrivalConfirmed
    description = "Llegada confirmada a tiempo"
    default_points = 10

    def applies(self, event: DomainEvent) -> bool:
        return isinstance(event, ie.CleaningArrivalConfirmed) and event.minutes_late <= 0

    def reason(self, event: DomainEvent) -> str:
        return "Llegada puntual"


class IssueReportedRule(_CleaningRule):
    key = "issue_reported"
    event_type = ie.CleaningIssueReported
    description = "Reportar incidencias protege la operación"
    default_points = 5

    def reason(self, event: DomainEvent) -> str:
        return "Incidencia reportada"


# ── Comercial / Marketing / Growth ──────────────────────────────────────────


class ContactCreatedRule(PointRule):
    key = "contact_created"
    event_type = ie.ContactCreated
    description = "Nuevo contacto en el CRM"
    default_points = 5

    def beneficiary(self, event: DomainEvent) -> uuid.UUID | None:
        owner = getattr(event, "owner_id", None)
        return owner if owner is not None else event.actor_id

    def reason(self, event: DomainEvent) -> str:
        return "Nuevo contacto"


class ContactConvertedRule(PointRule):
    key = "contact_converted"
    event_type = ie.ContactLifecycleChanged
    description = "Contacto convertido en cliente"
    default_points = 40

    def applies(self, event: DomainEvent) -> bool:
        return isinstance(event, ie.ContactLifecycleChanged) and event.to_stage == "customer"

    def reason(self, event: DomainEvent) -> str:
        return "Contacto convertido en cliente"


class DealWonRule(PointRule):
    key = "deal_won"
    event_type = ie.DealWon
    description = "Negocio ganado (+1 por cada millón COP, máx. +100)"
    default_points = 100
    bonus_cap: ClassVar[int] = 100

    def beneficiary(self, event: DomainEvent) -> uuid.UUID | None:
        owner = getattr(event, "owner_id", None)
        return owner if owner is not None else event.actor_id

    def compute(self, event: DomainEvent, base: int) -> int:
        if not isinstance(event, ie.DealWon):
            return 0
        amount = Decimal(event.amount)
        if event.currency.upper() != "COP":
            return base
        return base + min(self.bonus_cap, int(amount // Decimal(1_000_000)))

    def reason(self, event: DomainEvent) -> str:
        return "Negocio ganado"


class CampaignLaunchedRule(PointRule):
    key = "campaign_launched"
    event_type = ie.CampaignLaunched
    description = "Campaña de marketing lanzada"
    default_points = 30

    def reason(self, event: DomainEvent) -> str:
        name = getattr(event, "name", "")
        return f"Campaña lanzada: {name}" if name else "Campaña lanzada"


class MarketAuditRule(PointRule):
    key = "market_audit_completed"
    event_type = ie.MarketAuditCompleted
    description = "Auditoría de mercado con IA completada"
    default_points = 25

    def reason(self, event: DomainEvent) -> str:
        return "Auditoría de mercado completada"


class FunnelDesignedRule(PointRule):
    key = "funnel_designed"
    event_type = ie.FunnelDesigned
    description = "Embudo diseñado con IA"
    default_points = 25

    def reason(self, event: DomainEvent) -> str:
        return "Embudo diseñado"


DEFAULT_RULES: tuple[PointRule, ...] = (
    CleaningOnTimeRule(),
    CleaningLateRule(),
    CleaningPhotosRule(),
    ArrivalOnTimeRule(),
    IssueReportedRule(),
    ContactCreatedRule(),
    ContactConvertedRule(),
    DealWonRule(),
    CampaignLaunchedRule(),
    MarketAuditRule(),
    FunnelDesignedRule(),
)


class RuleEngine:
    def __init__(self, rules: Iterable[PointRule] = DEFAULT_RULES) -> None:
        self.rules: tuple[PointRule, ...] = tuple(rules)
        keys = [r.key for r in self.rules]
        if len(keys) != len(set(keys)):
            raise ValueError("Claves de reglas duplicadas")

    def event_types(self) -> set[type[DomainEvent]]:
        return {r.event_type for r in self.rules}

    def get(self, key: str) -> PointRule | None:
        return next((r for r in self.rules if r.key == key), None)

    def setting_for(self, rule: PointRule, overrides: Mapping[str, RuleSetting]) -> RuleSetting:
        return overrides.get(rule.key, RuleSetting(rule.default_points, True))

    def evaluate(self, event: DomainEvent, overrides: Mapping[str, RuleSetting]) -> list[Award]:
        awards = (r.evaluate(event, self.setting_for(r, overrides)) for r in self.rules)
        return [a for a in awards if a is not None]
