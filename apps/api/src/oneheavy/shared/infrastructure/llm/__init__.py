"""Adaptadores de IA generativa (implementan `LLMClient`)."""

from __future__ import annotations

import json
import logging

import httpx

from oneheavy.shared.application.ports import LLMClient, LLMRequest
from oneheavy.shared.domain.errors import ExternalServiceError

log = logging.getLogger("oneheavy.llm")


class FakeLLMClient(LLMClient):
    """LLM determinista para desarrollo local y tests.

    Si el prompt pide JSON y se registró una respuesta para una "tarea"
    (`metadata["task"]`), la devuelve; si no, responde un eco corto.
    """

    def __init__(self, canned: dict[str, object] | None = None) -> None:
        self.canned: dict[str, object] = canned or {}
        self.calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> str:
        self.calls.append(request)
        task = str(request.metadata.get("task", ""))
        if task in self.canned:
            value = self.canned[task]
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return json.dumps({"text": f"[fake-llm] {request.prompt[:120]}"}, ensure_ascii=False)


class OpenAIChatClient(LLMClient):
    """Cliente mínimo sobre la API REST de Chat Completions (sin SDK)."""

    def __init__(self, api_key: str, model: str, *, timeout: float = 60.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def complete(self, request: LLMRequest) -> str:
        body = {
            "model": self._model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=body,
                )
                resp.raise_for_status()
                return str(resp.json()["choices"][0]["message"]["content"])
        except httpx.HTTPError as exc:
            log.exception("llm_request_failed")
            raise ExternalServiceError("El proveedor de IA no respondió") from exc
