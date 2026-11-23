from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import pytest

from oneheavy.modules.growth.application.agents import (
    AssetWriter,
    BlueprintPipeline,
    GenesisPipeline,
    heuristic_audit,
    template_funnel,
)
from oneheavy.modules.growth.application.pipeline import Pipeline, PipelineError, Step
from oneheavy.modules.growth.domain.model import Audit, AwarenessLevel, Funnel, Project, ProjectStatus
from oneheavy.shared.application.ports import LLMClient, LLMRequest, WebSearch
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.infrastructure.adapters import NullWebSearch
from oneheavy.shared.infrastructure.llm import FakeLLMClient

AUDIT = {
    "avatar": "Dueña de clínica estética de 35-50 años",
    "pain_points": ["Agenda vacía entre semana"],
    "desires": ["Agenda llena"],
    "awareness_level": "Solution Aware",
    "jobs_to_be_done": ["Atraer pacientes de alto valor"],
    "competitors": ["Clínica X"],
    "market_opportunity": "Paquetes recurrentes",
}


class ScriptedLLM(LLMClient):
    """Devuelve respuestas en secuencia por tarea (para probar bucles)."""

    def __init__(self, script: dict[str, list[object]]) -> None:
        self.script = script
        self.calls: list[str] = []

    async def complete(self, request: LLMRequest) -> str:
        task = str(request.metadata["task"])
        self.calls.append(task)
        queue = self.script[task]
        value = queue.pop(0) if len(queue) > 1 else queue[0]
        return value if isinstance(value, str) else json.dumps(value)


class RecordingSearch(WebSearch):
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str, max_results: int = 3) -> list[dict[str, object]]:
        self.queries.append(query)
        return [{"title": f"Resultado {query}", "content": "dolor real del mercado"}]


# ── Pipeline genérico ───────────────────────────────────────────────────────


@dataclass
class Counter:
    visits: list[str]
    loops: int = 0


class Visit(Step[Counter]):
    def __init__(self, name: str, jump: str | None = None, times: int = 0) -> None:
        self.name, self.jump, self.times = name, jump, times

    async def run(self, ctx: Counter) -> str | None:
        ctx.visits.append(self.name)
        if self.jump and ctx.loops < self.times:
            ctx.loops += 1
            return self.jump
        return None


async def test_pipeline_runs_in_order_and_supports_jumps() -> None:
    pipe: Pipeline[Counter] = Pipeline("p", [Visit("a"), Visit("b", jump="a", times=1), Visit("c")])
    ctx = await pipe.run(Counter([]))
    assert ctx.visits == ["a", "b", "a", "b", "c"]
    assert pipe.trace == ctx.visits


async def test_pipeline_guards_infinite_loops_and_unknown_steps() -> None:
    with pytest.raises(PipelineError):
        await Pipeline("p", [Visit("a", jump="a", times=99)], max_transitions=5).run(Counter([]))
    with pytest.raises(PipelineError):
        await Pipeline("p", [Visit("a", jump="zzz", times=1)]).run(Counter([]))
    with pytest.raises(ValueError):
        Pipeline("p", [Visit("a"), Visit("a")])


# ── Value objects / agregado ────────────────────────────────────────────────


def test_audit_parsing_normalizes_awareness() -> None:
    audit = Audit.from_dict(AUDIT)
    assert audit.awareness_level is AwarenessLevel.SOLUTION_AWARE
    assert not audit.awareness_level.needs_education
    assert (
        Audit.from_dict({**AUDIT, "awareness_level": "???"}).awareness_level is AwarenessLevel.PROBLEM_AWARE
    )
    with pytest.raises(BusinessRuleViolation):
        Audit.from_dict({"pain_points": []})


def test_funnel_validation() -> None:
    with pytest.raises(BusinessRuleViolation):
        Funnel.from_dict({"nodes": [{"id": "1", "type": "rocket"}], "edges": []})
    with pytest.raises(BusinessRuleViolation):
        Funnel.from_dict({"nodes": [{"id": "1", "type": "ad"}], "edges": [{"source": "1", "target": "9"}]})
    funnel = Funnel.from_dict(
        {
            "nodes": [{"id": "1", "type": "ad"}, {"id": "2", "type": "checkout"}],
            "edges": [{"source": "1", "target": "2"}],
        }
    )
    assert funnel.nodes[1]["position"] == {"x": 260.0, "y": 0.0}
    assert funnel.edges == [{"id": "e1", "source": "1", "target": "2"}]


def test_template_funnels_by_awareness() -> None:
    education = template_funnel(AwarenessLevel.UNAWARE)
    direct = template_funnel(AwarenessLevel.MOST_AWARE)
    assert [n["type"] for n in education.nodes][:3] == ["ad", "landing", "optin"]
    assert [n["type"] for n in direct.nodes] == ["ad", "landing", "checkout", "upsell", "thankyou"]
    assert len(direct.edges) == len(direct.nodes) - 1


def test_project_state_machine_and_events() -> None:
    project = Project.create(
        tenant_id=uuid.uuid4(), name="Clínica", niche="estética", url=None, created_by=None
    )
    with pytest.raises(BusinessRuleViolation):
        project.start_funnel()  # sin auditoría
    with pytest.raises(BusinessRuleViolation):
        project.fail("x")  # no está corriendo
    project.start_audit()
    with pytest.raises(BusinessRuleViolation):
        project.start_audit()  # ya está analizando
    project.complete_audit(Audit.from_dict(AUDIT))
    assert project.status is ProjectStatus.AUDITED
    project.start_funnel()
    project.fail("timeout")
    assert project.status is ProjectStatus.FAILED and project.error == "timeout"
    project.start_audit()
    project.complete_audit(Audit.from_dict(AUDIT))
    project.start_funnel()
    project.complete_funnel(template_funnel(AwarenessLevel.UNAWARE))
    assert project.status is ProjectStatus.COMPLETED
    events = project.pull_events()
    assert [type(e) for e in events] == [ie.MarketAuditCompleted, ie.MarketAuditCompleted, ie.FunnelDesigned]


# ── Agentes ─────────────────────────────────────────────────────────────────


async def test_genesis_happy_path_with_canned_llm() -> None:
    llm = FakeLLMClient(
        {
            "growth.planner": {"queries": ["q1", "q2", "q3"]},
            "growth.auditor": {"missing_info": False, "report": AUDIT},
        }
    )
    search = RecordingSearch()
    ctx = await GenesisPipeline(llm, search).run("clínicas estéticas")
    assert search.queries == ["q1", "q2", "q3"]
    assert ctx.audit is not None and ctx.audit.avatar.startswith("Dueña")
    assert ctx.iterations == 1 and not ctx.used_fallback and len(ctx.research) == 3


async def test_genesis_loops_back_to_planner_when_info_missing() -> None:
    llm = ScriptedLLM(
        {
            "growth.planner": [["a", "b", "c"]],
            "growth.auditor": [{"missing_info": True}, {"missing_info": False, "report": AUDIT}],
        }
    )
    ctx = await GenesisPipeline(llm, NullWebSearch()).run("nicho")
    assert llm.calls == ["growth.planner", "growth.auditor", "growth.planner", "growth.auditor"]
    assert ctx.iterations == 2 and ctx.audit is not None and not ctx.used_fallback


async def test_genesis_stops_after_max_iterations_and_falls_back() -> None:
    llm = ScriptedLLM({"growth.planner": ["no-json"], "growth.auditor": [{"missing_info": True}]})
    ctx = await GenesisPipeline(llm, NullWebSearch()).run("nicho raro")
    assert llm.calls.count("growth.auditor") == 2
    assert ctx.used_fallback and ctx.audit == heuristic_audit("nicho raro")
    assert len(ctx.queries) == 3  # queries de respaldo


async def test_blueprint_uses_llm_or_template() -> None:
    audit = Audit.from_dict(AUDIT)
    llm = FakeLLMClient({"growth.funnel": {"nodes": [{"id": "x", "type": "ad", "label": "Ad"}], "edges": []}})
    ctx = await BlueprintPipeline(llm).run(audit, "nicho")
    assert ctx.funnel is not None and [n["id"] for n in ctx.funnel.nodes] == ["x"] and not ctx.used_fallback
    fallback = await BlueprintPipeline(FakeLLMClient()).run(audit, "nicho")
    assert fallback.used_fallback and fallback.funnel == template_funnel(AwarenessLevel.SOLUTION_AWARE)


async def test_asset_writer_fallback_and_llm() -> None:
    audit = Audit.from_dict(AUDIT)
    assets = await AssetWriter(FakeLLMClient()).write("ad", audit, "estética")
    assert len(assets) == 3 and all(a.kind == "ad" and a.body for a in assets)
    llm = FakeLLMClient({"growth.assets": {"assets": [{"kind": "email", "title": "Hola", "body": "Cuerpo"}]}})
    assert [a.title for a in await AssetWriter(llm).write("email", audit, "estética")] == ["Hola"]
