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


class AnthropicClaudeClient(LLMClient):
    """Claude vía el SDK oficial de Anthropic (`anthropic.AsyncAnthropic`).

    - Modelo por defecto: Claude Opus 5.5. En este modelo el razonamiento
      (thinking) siempre está activo; la profundidad se controla con `effort`.
    - `max_tokens` incluye el razonamiento: se usa un piso alto para que la
      respuesta no quede cortada.
    - Respaldo ante rechazos de seguridad (`fallbacks: "default"`): si el modelo
      declina, la API reintenta dentro de la misma llamada con otro modelo.
    - No se envía `temperature`: los modelos actuales la rechazan.
    """

    MIN_MAX_TOKENS = 16_000
    FALLBACK_BETA = "server-side-fallback-2026-07-01"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-5-5",
        *,
        effort: str = "medium",
        use_fallbacks: bool = True,
        timeout: float = 120.0,
        client: object | None = None,
    ) -> None:
        import anthropic

        self._anthropic = anthropic
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=2)
        self._model = model
        self._effort = effort
        self._use_fallbacks = use_fallbacks

    async def complete(self, request: LLMRequest) -> str:
        a = self._anthropic
        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": max(request.max_tokens, self.MIN_MAX_TOKENS),
            "system": request.system,
            "messages": [{"role": "user", "content": request.prompt}],
            "output_config": {"effort": self._effort},
        }
        if self._use_fallbacks:
            kwargs["betas"] = [self.FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        try:
            response = await self._client.beta.messages.create(**kwargs)  # type: ignore[attr-defined]
        except a.AuthenticationError as exc:
            log.error("llm_auth_failed")
            raise ExternalServiceError("La clave de Anthropic no es válida") from exc
        except a.RateLimitError as exc:
            log.warning("llm_rate_limited")
            raise ExternalServiceError("El proveedor de IA está saturado, intenta en un momento") from exc
        except a.APIStatusError as exc:
            log.exception("llm_api_error", extra={"status": exc.status_code})
            raise ExternalServiceError("El proveedor de IA devolvió un error") from exc
        except a.APIConnectionError as exc:
            log.exception("llm_connection_error")
            raise ExternalServiceError("No fue posible conectar con el proveedor de IA") from exc

        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None) if response.stop_details else None
            log.warning("llm_refusal", extra={"category": category, "task": request.metadata.get("task")})
            raise ExternalServiceError("La IA declinó esta solicitud")
        if response.stop_reason == "max_tokens":
            log.warning("llm_max_tokens", extra={"task": request.metadata.get("task")})
        text = "".join(block.text for block in response.content if block.type == "text")
        if not text.strip():
            raise ExternalServiceError("La IA no devolvió contenido")
        return text


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
