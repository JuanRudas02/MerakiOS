"""Detección de anomalías publicitarias (patrón Strategy).

Porta la lógica del agente "Director" de MerakiOS (CTR bajo = fatiga creativa)
y la amplía con reglas de CPC, CPL y entrega. Cada regla es independiente y
se puede activar/ajustar sin tocar las demás.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from oneheavy.modules.meta.domain.model import CampaignDailyMetric, Performance, Severity


@dataclass(frozen=True)
class CampaignSeries:
    external_id: str
    name: str
    status: str
    days: list[CampaignDailyMetric]  # ordenados por día ascendente

    @property
    def total(self) -> Performance:
        return Performance.of(self.days)

    @property
    def last(self) -> CampaignDailyMetric | None:
        return self.days[-1] if self.days else None


@dataclass(frozen=True)
class Anomaly:
    campaign_ref: str
    metric: str
    value: float
    benchmark: float
    severity: Severity
    message: str

    def dedupe_key(self, series: CampaignSeries) -> str:
        last_day = series.last.day.isoformat() if series.last else "na"
        return f"{self.campaign_ref}|{self.metric}|{last_day}"


class AnomalyRule(ABC):
    key: str

    @abstractmethod
    def evaluate(self, series: CampaignSeries) -> Anomaly | None: ...


class LowCtrRule(AnomalyRule):
    """CTR < 1% con volumen relevante → fatiga creativa (regla original del Director)."""

    key = "ctr"

    def __init__(self, threshold: float = 1.0, min_impressions: int = 1000) -> None:
        self.threshold, self.min_impressions = threshold, min_impressions

    def evaluate(self, series: CampaignSeries) -> Anomaly | None:
        perf = series.total
        if perf.impressions < self.min_impressions or perf.ctr >= self.threshold:
            return None
        severity = Severity.CRITICAL if perf.ctr < self.threshold / 2 else Severity.WARNING
        return Anomaly(
            series.name,
            self.key,
            perf.ctr,
            self.threshold,
            severity,
            f"CTR bajo ({perf.ctr}%) en '{series.name}': posible fatiga creativa, rota los anuncios.",
        )


class CpcSpikeRule(AnomalyRule):
    """CPC del último día > factor x promedio de los 7 días previos."""

    key = "cpc"

    def __init__(self, factor: float = 1.5) -> None:
        self.factor = factor

    def evaluate(self, series: CampaignSeries) -> Anomaly | None:
        if len(series.days) < 3 or series.last is None:
            return None
        last = Performance.of([series.last])
        baseline = Performance.of(series.days[-8:-1])
        if not last.clicks or not baseline.cpc:
            return None
        limit = baseline.cpc * self.factor
        if last.cpc <= limit:
            return None
        return Anomaly(
            series.name,
            self.key,
            last.cpc,
            round(baseline.cpc, 2),
            Severity.WARNING,
            f"El CPC de '{series.name}' subió a {last.cpc} (promedio 7d: {baseline.cpc}). Revisa audiencia y puja.",
        )


class HighCplRule(AnomalyRule):
    """Costo por lead por encima del benchmark del workspace."""

    key = "cpl"

    def __init__(self, benchmark: float = 30000.0) -> None:
        self.benchmark = benchmark

    def evaluate(self, series: CampaignSeries) -> Anomaly | None:
        perf = series.total
        if not perf.leads or perf.cpl <= self.benchmark:
            return None
        severity = Severity.CRITICAL if perf.cpl > self.benchmark * 2 else Severity.WARNING
        return Anomaly(
            series.name,
            self.key,
            perf.cpl,
            self.benchmark,
            severity,
            f"CPL de '{series.name}' ({perf.cpl}) supera el benchmark ({self.benchmark}).",
        )


class ZeroDeliveryRule(AnomalyRule):
    """Campaña activa sin impresiones en el último día → problema de entrega/pago."""

    key = "delivery"

    def evaluate(self, series: CampaignSeries) -> Anomaly | None:
        if series.status.upper() != "ACTIVE" or series.last is None or series.last.impressions > 0:
            return None
        return Anomaly(
            series.name,
            self.key,
            0.0,
            1.0,
            Severity.CRITICAL,
            f"'{series.name}' está activa pero no entregó impresiones ayer. Revisa pago, aprobación o presupuesto.",
        )


DEFAULT_RULES: tuple[type[AnomalyRule], ...] = (LowCtrRule, CpcSpikeRule, HighCplRule, ZeroDeliveryRule)


class AnomalyDetector:
    def __init__(self, rules: list[AnomalyRule] | None = None) -> None:
        self.rules = rules if rules is not None else [rule() for rule in DEFAULT_RULES]

    def detect(self, series: CampaignSeries) -> list[Anomaly]:
        return [a for rule in self.rules if (a := rule.evaluate(series)) is not None]
