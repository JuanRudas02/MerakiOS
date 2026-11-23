"""Dominio Growth (ex MerakiOS): proyectos de estrategia, auditoría de mercado y embudos."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.entity import TenantEntity
from oneheavy.shared.domain.errors import BusinessRuleViolation


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    AUDITED = "audited"
    DESIGNING = "designing"
    COMPLETED = "completed"
    FAILED = "failed"


class AwarenessLevel(StrEnum):
    """Niveles de consciencia de Eugene Schwartz."""

    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"

    @classmethod
    def parse(cls, raw: object) -> AwarenessLevel:
        text = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
        for level in cls:
            if level.value in text:
                return level
        return cls.PROBLEM_AWARE

    @property
    def needs_education(self) -> bool:
        return self in (AwarenessLevel.UNAWARE, AwarenessLevel.PROBLEM_AWARE)


def _str_list(value: object, limit: int = 10) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:limit]


@dataclass(frozen=True)
class Audit:
    """Reporte estratégico (Schwartz + Jobs To Be Done)."""

    avatar: str
    pain_points: list[str]
    desires: list[str]
    awareness_level: AwarenessLevel
    jobs_to_be_done: list[str]
    competitors: list[str]
    market_opportunity: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Audit:
        avatar = str(data.get("avatar") or "").strip()
        if not avatar:
            raise BusinessRuleViolation("La auditoría no definió el avatar", code="incomplete_audit")
        return cls(
            avatar=avatar,
            pain_points=_str_list(data.get("pain_points")),
            desires=_str_list(data.get("desires")),
            awareness_level=AwarenessLevel.parse(data.get("awareness_level")),
            jobs_to_be_done=_str_list(data.get("jobs_to_be_done") or data.get("jtbd")),
            competitors=_str_list(data.get("competitors")),
            market_opportunity=str(data.get("market_opportunity") or "").strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["awareness_level"] = self.awareness_level.value
        return data


NODE_TYPES = frozenset({"ad", "landing", "optin", "vsl", "email", "checkout", "upsell", "thankyou"})


@dataclass(frozen=True)
class Funnel:
    """Mapa del embudo compatible con React Flow."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Funnel:
        raw_nodes, raw_edges = data.get("nodes"), data.get("edges")
        if not isinstance(raw_nodes, list) or not raw_nodes or not isinstance(raw_edges, list):
            raise BusinessRuleViolation("El embudo debe tener nodos y conexiones", code="invalid_funnel")
        nodes = []
        for i, n in enumerate(raw_nodes):
            if not isinstance(n, dict) or n.get("type") not in NODE_TYPES:
                raise BusinessRuleViolation(f"Nodo inválido en la posición {i}", code="invalid_funnel")
            raw_pos = n.get("position")
            pos: dict[str, Any] = raw_pos if isinstance(raw_pos, dict) else {}
            nodes.append(
                {
                    "id": str(n.get("id") or i + 1),
                    "type": n["type"],
                    "label": str(n.get("label") or n["type"]).strip(),
                    "position": {"x": float(pos.get("x", i * 260)), "y": float(pos.get("y", 0))},
                }
            )
        ids = {n["id"] for n in nodes}
        if len(ids) != len(nodes):
            raise BusinessRuleViolation("IDs de nodo duplicados", code="invalid_funnel")
        edges = []
        for j, e in enumerate(raw_edges):
            if not isinstance(e, dict) or str(e.get("source")) not in ids or str(e.get("target")) not in ids:
                raise BusinessRuleViolation(f"Conexión inválida en la posición {j}", code="invalid_funnel")
            edges.append(
                {
                    "id": str(e.get("id") or f"e{j + 1}"),
                    "source": str(e["source"]),
                    "target": str(e["target"]),
                }
            )
        return cls(nodes, edges)

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "edges": self.edges}


_AUDIT_FROM = frozenset(
    {ProjectStatus.DRAFT, ProjectStatus.AUDITED, ProjectStatus.COMPLETED, ProjectStatus.FAILED}
)
_FUNNEL_FROM = frozenset({ProjectStatus.AUDITED, ProjectStatus.COMPLETED})


@dataclass(kw_only=True, eq=False)
class Project(TenantEntity):
    """Proyecto de crecimiento. Máquina de estados:

    draft → analyzing → audited → designing → completed
    analyzing/designing → failed ; failed/audited/completed → analyzing (re-auditar)
    """

    name: str
    niche: str
    url: str | None = None
    status: ProjectStatus = ProjectStatus.DRAFT
    audit: Audit | None = None
    funnel: Funnel | None = None
    error: str | None = None
    created_by: uuid.UUID | None = None
    research_notes: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls, *, tenant_id: uuid.UUID, name: str, niche: str, url: str | None, created_by: uuid.UUID | None
    ) -> Project:
        if len(name.strip()) < 2 or len(niche.strip()) < 2:
            raise BusinessRuleViolation("Nombre y nicho son obligatorios")
        return cls(
            tenant_id=tenant_id,
            name=name.strip(),
            niche=niche.strip(),
            url=(url or "").strip() or None,
            created_by=created_by,
        )

    def _transition(self, allowed: frozenset[ProjectStatus], target: ProjectStatus) -> None:
        if self.status not in allowed:
            raise BusinessRuleViolation(
                f"No se puede pasar de '{self.status}' a '{target}'", code="invalid_project_transition"
            )
        self.status = target
        self.touch()

    def start_audit(self) -> None:
        self._transition(_AUDIT_FROM, ProjectStatus.ANALYZING)
        self.error = None

    def complete_audit(self, audit: Audit, research_notes: list[str] | None = None) -> None:
        self._transition(frozenset({ProjectStatus.ANALYZING}), ProjectStatus.AUDITED)
        self.audit = audit
        self.funnel = None
        self.research_notes = list(research_notes or [])
        self.record(
            ie.MarketAuditCompleted(
                tenant_id=self.tenant_id,
                actor_id=self.created_by,
                project_id=self.id,
                awareness_level=audit.awareness_level.value,
            )
        )

    def start_funnel(self) -> None:
        if self.audit is None:
            raise BusinessRuleViolation(
                "Primero debes completar la auditoría de mercado", code="audit_required"
            )
        self._transition(_FUNNEL_FROM, ProjectStatus.DESIGNING)
        self.error = None

    def complete_funnel(self, funnel: Funnel) -> None:
        self._transition(frozenset({ProjectStatus.DESIGNING}), ProjectStatus.COMPLETED)
        self.funnel = funnel
        self.record(
            ie.FunnelDesigned(
                tenant_id=self.tenant_id,
                actor_id=self.created_by,
                project_id=self.id,
                nodes_count=len(funnel.nodes),
            )
        )

    def fail(self, error: str) -> None:
        self._transition(frozenset({ProjectStatus.ANALYZING, ProjectStatus.DESIGNING}), ProjectStatus.FAILED)
        self.error = error[:500]
