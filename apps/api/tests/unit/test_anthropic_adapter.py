"""Adaptador de Claude: se prueba con un cliente simulado (sin red ni costo)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from oneheavy.shared.application.ports import LLMRequest
from oneheavy.shared.domain.errors import ExternalServiceError
from oneheavy.shared.infrastructure.config import Settings
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.llm import AnthropicClaudeClient


class _FakeMessages:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.response


def _client(response: Any) -> tuple[AnthropicClaudeClient, _FakeMessages]:
    messages = _FakeMessages(response)
    fake = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return AnthropicClaudeClient("sk-test", client=fake), messages


def _response(*blocks: Any, stop_reason: str = "end_turn", stop_details: Any = None) -> Any:
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason, stop_details=stop_details)


def _text(t: str) -> Any:
    return SimpleNamespace(type="text", text=t)


async def test_returns_only_text_blocks() -> None:
    thinking = SimpleNamespace(type="thinking", thinking="")
    llm, _ = _client(_response(thinking, _text('{"ok": '), _text("true}")))
    assert await llm.complete_json(LLMRequest("hola")) == {"ok": True}


async def test_request_shape_for_current_models() -> None:
    llm, messages = _client(_response(_text("listo")))
    await llm.complete(LLMRequest("redacta", system="eres copywriter", temperature=0.9, max_tokens=500))
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["max_tokens"] >= 16_000  # el razonamiento consume del mismo presupuesto
    assert "temperature" not in call  # los modelos actuales la rechazan
    assert "thinking" not in call  # siempre activo en Opus 5.5; se controla con effort
    assert call["output_config"] == {"effort": "medium"}
    assert call["fallbacks"] == "default"
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["system"] == "eres copywriter"


async def test_refusal_becomes_domain_error() -> None:
    llm, _ = _client(_response(stop_reason="refusal", stop_details=SimpleNamespace(category="cyber")))
    with pytest.raises(ExternalServiceError):
        await llm.complete(LLMRequest("x"))


async def test_empty_answer_is_an_error() -> None:
    llm, _ = _client(_response(SimpleNamespace(type="thinking", thinking="")))
    with pytest.raises(ExternalServiceError):
        await llm.complete(LLMRequest("x"))


def test_settings_accept_standard_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-desde-entorno")
    s = Settings(_env_file=None, llm_provider="anthropic")  # type: ignore[call-arg]
    assert s.anthropic_api_key is not None
    assert s.anthropic_api_key.get_secret_value() == "sk-ant-desde-entorno"
    container = Container.from_settings(s, engine=object())
    assert isinstance(container.llm, AnthropicClaudeClient)
