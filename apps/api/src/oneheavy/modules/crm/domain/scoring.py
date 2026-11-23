"""Lead scoring (patrón Strategy).

El caso de uso depende de `ScoringPolicy`; hoy usamos reglas explicables y
mañana podemos enchufar un modelo predictivo sin tocar el dominio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from oneheavy.modules.crm.domain.model import Contact, ContactSource
from oneheavy.shared.domain.time import ensure_aware, utc_now


@dataclass(frozen=True)
class ScoreResult:
    score: int
    breakdown: dict[str, int] = field(default_factory=dict)

    def explain(self) -> str:
        parts = [f"{k.replace('_', ' ')}: {v}" for k, v in self.breakdown.items() if v]
        return "Score {s}/100 ({p}).".format(s=self.score, p=", ".join(parts) or "sin señales")


class ScoringPolicy(ABC):
    @abstractmethod
    def score(self, contact: Contact, now: datetime | None = None) -> ScoreResult: ...


class RuleBasedScoringPolicy(ScoringPolicy):
    """Score = completitud de perfil (≤35) + peso de la fuente (≤15) + engagement con decaimiento (≤50)."""

    SOURCE_WEIGHT: dict[ContactSource, int] = {
        ContactSource.META_LEAD_ADS: 15,
        ContactSource.WEB_FORM: 15,
        ContactSource.WHATSAPP: 12,
        ContactSource.INSTAGRAM: 10,
        ContactSource.MAUTIC: 8,
        ContactSource.IMPORT: 5,
        ContactSource.MANUAL: 5,
    }
    ENGAGEMENT_CAP = 50

    def score(self, contact: Contact, now: datetime | None = None) -> ScoreResult:
        now = now or utc_now()
        completeness = (
            (10 if contact.email else 0)
            + (10 if contact.phone else 0)
            + (5 if contact.last_name else 0)
            + (5 if contact.company else 0)
            + (5 if contact.job_title else 0)
        )
        source = self.SOURCE_WEIGHT.get(contact.source, 5)
        engagement = min(contact.engagement_points, self.ENGAGEMENT_CAP)
        decay = self._decay_factor(contact.last_activity_at, now)
        engagement_effective = round(engagement * decay)
        total = min(100, completeness + source + engagement_effective)
        return ScoreResult(
            total,
            {
                "perfil": completeness,
                "fuente": source,
                "engagement": engagement_effective,
            },
        )

    @staticmethod
    def _decay_factor(last_activity: datetime | None, now: datetime) -> float:
        if last_activity is None:
            return 1.0
        days = (now - ensure_aware(last_activity)).days
        if days > 90:
            return 0.2
        if days > 30:
            return 0.5
        return 1.0
