"""Agentes de estrategia como pipelines OOP (port de Genesis y Blueprint de MerakiOS).

GenesisPipeline   : planner → researcher → auditor (↺ planner, máx. 2 iteraciones)
BlueprintPipeline : architect (nivel de consciencia → embudo educativo u oferta directa)
AssetWriter       : copy para anuncios / landing / emails a partir de la auditoría
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from oneheavy.modules.growth.application.pipeline import Pipeline, Step
from oneheavy.modules.growth.domain.model import Audit, AwarenessLevel, Funnel
from oneheavy.shared.application.ports import LLMClient, LLMRequest, WebSearch
from oneheavy.shared.domain.errors import BusinessRuleViolation

log = logging.getLogger("oneheavy.growth.agents")

MAX_AUDIT_ITERATIONS = 2
STRATEGIST = (
    "Eres el estratega senior de 1heavy (marketing de respuesta directa). "
    "Aplicas los niveles de consciencia de Eugene Schwartz y Jobs To Be Done. Respondes en español."
)


async def _ask_json(llm: LLMClient, task: str, prompt: str) -> Any:
    """Pide JSON al LLM; devuelve None si la respuesta no es JSON válido.

    Los errores de red/proveedor (ExternalServiceError) sí se propagan.
    """
    try:
        return await llm.complete_json(LLMRequest(prompt=prompt, system=STRATEGIST, metadata={"task": task}))
    except (json.JSONDecodeError, ValueError):
        log.warning("llm_invalid_json", extra={"task": task})
        return None


# ── Genesis (auditoría de mercado) ──────────────────────────────────────────


@dataclass
class GenesisContext:
    niche: str
    url: str | None = None
    queries: list[str] = field(default_factory=list)
    research: list[str] = field(default_factory=list)
    audit: Audit | None = None
    missing_info: bool = False
    iterations: int = 0
    used_fallback: bool = False


class PlannerStep(Step[GenesisContext]):
    name = "planner"

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, ctx: GenesisContext) -> str | None:
        focus = "Las búsquedas anteriores no bastaron; sé más específico. " if ctx.iterations else ""
        prompt = (
            f"{focus}Debemos auditar el mercado de: {ctx.niche}"
            + (f" (sitio: {ctx.url})" if ctx.url else "")
            + ".\nGenera 3 búsquedas web para encontrar: 1) dolores y deseos, 2) ofertas de competidores, "
            '3) nivel de consciencia del mercado. Devuelve {"queries": ["...", "...", "..."]}.'
        )
        data = await _ask_json(self.llm, "growth.planner", prompt)
        raw = data.get("queries") if isinstance(data, dict) else data
        queries = [str(q).strip() for q in raw if str(q).strip()] if isinstance(raw, list) else []
        ctx.queries = queries[:3] or [
            f"{ctx.niche} dolores y frustraciones de clientes",
            f"{ctx.niche} competidores ofertas y precios",
            f"{ctx.niche} foros opiniones reseñas",
        ]
        return None


class ResearchStep(Step[GenesisContext]):
    name = "researcher"

    def __init__(self, search: WebSearch) -> None:
        self.search = search

    async def run(self, ctx: GenesisContext) -> str | None:
        for query in ctx.queries:
            results = await self.search.search(query, max_results=3)
            snippets = [
                f"- {r.get('title', '')}: {str(r.get('content') or r.get('snippet') or '')[:400]}"
                for r in results
            ]
            if snippets:
                ctx.research.append(f"Búsqueda: {query}\n" + "\n".join(snippets))
        return None


class AuditorStep(Step[GenesisContext]):
    name = "auditor"

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, ctx: GenesisContext) -> str | None:
        ctx.iterations += 1
        evidence = "\n\n".join(ctx.research[-9:]) or "(sin resultados web; usa tu conocimiento del mercado)"
        prompt = (
            f"Analiza el nicho '{ctx.niche}' con esta evidencia:\n{evidence}\n\n"
            "Si la información no alcanza para definir avatar y dolores, missing_info=true.\n"
            'Devuelve {"missing_info": bool, "report": {"avatar": str, "pain_points": [str], '
            '"desires": [str], "awareness_level": "unaware|problem_aware|solution_aware|product_aware|most_aware", '
            '"jobs_to_be_done": [str], "competitors": [str], "market_opportunity": str}}'
        )
        data = await _ask_json(self.llm, "growth.auditor", prompt)
        data = data if isinstance(data, dict) else {}
        ctx.missing_info = bool(data.get("missing_info"))
        if ctx.missing_info and ctx.iterations < MAX_AUDIT_ITERATIONS:
            return PlannerStep.name
        report = data.get("report")
        try:
            ctx.audit = Audit.from_dict(report if isinstance(report, dict) else {})
        except BusinessRuleViolation:
            ctx.audit = heuristic_audit(ctx.niche)
            ctx.used_fallback = True
        return None


def heuristic_audit(niche: str) -> Audit:
    """Auditoría base cuando el LLM no está disponible (modo local sin API key)."""
    return Audit(
        avatar=f"Decisor de negocio interesado en {niche} que busca resultados predecibles sin perder tiempo.",
        pain_points=[
            "Procesos manuales y poca visibilidad de resultados",
            "Costos de adquisición crecientes",
            "Dificultad para diferenciarse de la competencia",
        ],
        desires=[
            "Crecer con un sistema predecible",
            "Ahorrar tiempo operativo",
            "Tomar decisiones con datos",
        ],
        awareness_level=AwarenessLevel.PROBLEM_AWARE,
        jobs_to_be_done=[f"Encontrar una solución confiable de {niche} que pueda implementar rápido"],
        competitors=[],
        market_opportunity="Educar al mercado sobre el costo del problema antes de presentar la oferta.",
    )


class GenesisPipeline:
    def __init__(self, llm: LLMClient, search: WebSearch) -> None:
        self.pipeline: Pipeline[GenesisContext] = Pipeline(
            "genesis", [PlannerStep(llm), ResearchStep(search), AuditorStep(llm)]
        )

    async def run(self, niche: str, url: str | None = None) -> GenesisContext:
        return await self.pipeline.run(GenesisContext(niche=niche, url=url))


# ── Blueprint (arquitecto de embudos) ───────────────────────────────────────


@dataclass
class BlueprintContext:
    audit: Audit
    niche: str
    funnel: Funnel | None = None
    used_fallback: bool = False


EDUCATION_FLOW = [
    ("ad", "Anuncio gancho (problema)"),
    ("landing", "Contenido educativo"),
    ("optin", "Lead magnet / registro"),
    ("email", "Secuencia de nutrición"),
    ("vsl", "Video de ventas"),
    ("checkout", "Checkout"),
    ("thankyou", "Gracias + onboarding"),
]
DIRECT_FLOW = [
    ("ad", "Anuncio de oferta"),
    ("landing", "Página de ventas"),
    ("checkout", "Checkout"),
    ("upsell", "Upsell"),
    ("thankyou", "Gracias + onboarding"),
]


def template_funnel(level: AwarenessLevel) -> Funnel:
    flow = EDUCATION_FLOW if level.needs_education else DIRECT_FLOW
    nodes = [
        {"id": str(i + 1), "type": t, "label": label, "position": {"x": i * 260, "y": 0}}
        for i, (t, label) in enumerate(flow)
    ]
    edges = [{"id": f"e{i + 1}", "source": str(i + 1), "target": str(i + 2)} for i in range(len(flow) - 1)]
    return Funnel.from_dict({"nodes": nodes, "edges": edges})


class ArchitectStep(Step[BlueprintContext]):
    name = "architect"

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, ctx: BlueprintContext) -> str | None:
        level = ctx.audit.awareness_level
        strategy = (
            "embudo educativo (anuncio → contenido → registro)"
            if level.needs_education
            else ("embudo de oferta directa (anuncio → página de ventas → checkout)")
        )
        prompt = (
            f"Nicho: {ctx.niche}. Avatar: {ctx.audit.avatar}. Nivel de consciencia: {level.value}.\n"
            f"Diseña un {strategy}. Tipos de nodo permitidos: ad, landing, optin, vsl, email, checkout, upsell, "
            'thankyou. Devuelve {"nodes": [{"id", "type", "label", "position": {"x", "y"}}], '
            '"edges": [{"id", "source", "target"}]} compatible con React Flow.'
        )
        data = await _ask_json(self.llm, "growth.funnel", prompt)
        try:
            ctx.funnel = Funnel.from_dict(data if isinstance(data, dict) else {})
        except BusinessRuleViolation:
            ctx.funnel = template_funnel(level)
            ctx.used_fallback = True
        return None


class BlueprintPipeline:
    def __init__(self, llm: LLMClient) -> None:
        self.pipeline: Pipeline[BlueprintContext] = Pipeline("blueprint", [ArchitectStep(llm)])

    async def run(self, audit: Audit, niche: str) -> BlueprintContext:
        return await self.pipeline.run(BlueprintContext(audit=audit, niche=niche))


# ── Assets (copy) ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Asset:
    kind: str
    title: str
    body: str


class AssetWriter:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def write(self, kind: str, audit: Audit, niche: str, node_label: str | None = None) -> list[Asset]:
        prompt = (
            f"Escribe 3 variantes de copy tipo '{kind}' para el nicho '{niche}'"
            + (f" (etapa del embudo: {node_label})" if node_label else "")
            + f".\nAvatar: {audit.avatar}\nDolores: {'; '.join(audit.pain_points)}\n"
            f"Deseos: {'; '.join(audit.desires)}\nNivel de consciencia: {audit.awareness_level.value}.\n"
            'Devuelve {"assets": [{"kind": str, "title": str, "body": str}]}'
        )
        data = await _ask_json(self.llm, "growth.assets", prompt)
        raw = data.get("assets") if isinstance(data, dict) else None
        assets = [
            Asset(
                str(a.get("kind") or kind),
                str(a.get("title") or "").strip(),
                str(a.get("body") or "").strip(),
            )
            for a in (raw if isinstance(raw, list) else [])
            if isinstance(a, dict) and a.get("body")
        ]
        if assets:
            return assets[:5]
        pain = audit.pain_points[0] if audit.pain_points else "el problema principal"
        desire = audit.desires[0] if audit.desires else "el resultado que buscas"
        return [
            Asset(
                kind, f"¿Cansado de {pain.lower()}?", f"Descubre cómo lograr {desire.lower()} sin fricción."
            ),
            Asset(kind, f"{desire} en semanas, no meses", f"El sistema probado para {niche}. Empieza hoy."),
            Asset(kind, "Lo que nadie te cuenta", f"El verdadero costo de {pain.lower()} y cómo evitarlo."),
        ]
