"""Motor de pipelines (Chain of Responsibility con contexto tipado compartido).

Reemplaza a LangGraph: cada `Step` lee/escribe el contexto y puede devolver el
nombre de otro paso para saltar (p. ej. el auditor vuelve al planner si falta
información). `max_transitions` evita bucles infinitos.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from oneheavy.shared.domain.errors import DomainError

log = logging.getLogger("oneheavy.growth.pipeline")


class PipelineError(DomainError):
    code = "pipeline_error"


class Step[C](ABC):
    name: str

    @abstractmethod
    async def run(self, ctx: C) -> str | None:
        """Ejecuta el paso. Devuelve `None` para continuar o el nombre del paso al que saltar."""


class Pipeline[C]:
    def __init__(self, name: str, steps: list[Step[C]], *, max_transitions: int = 20) -> None:
        if not steps:
            raise ValueError("Un pipeline necesita al menos un paso")
        names = [s.name for s in steps]
        if len(set(names)) != len(names):
            raise ValueError("Los nombres de los pasos deben ser únicos")
        self.name = name
        self._steps = steps
        self._index = {s.name: i for i, s in enumerate(steps)}
        self._max = max_transitions
        self.trace: list[str] = []

    async def run(self, ctx: C) -> C:
        self.trace = []
        i = 0
        while i < len(self._steps):
            if len(self.trace) >= self._max:
                raise PipelineError(f"El pipeline '{self.name}' excedió {self._max} transiciones")
            step = self._steps[i]
            self.trace.append(step.name)
            log.info("pipeline_step", extra={"pipeline": self.name, "step": step.name})
            jump = await step.run(ctx)
            if jump is None:
                i += 1
            elif jump in self._index:
                i = self._index[jump]
            else:
                raise PipelineError(f"Paso desconocido '{jump}' en '{self.name}'")
        return ctx
