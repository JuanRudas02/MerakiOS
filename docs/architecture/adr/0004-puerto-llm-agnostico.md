# ADR-0004 · Puerto LLM agnóstico al proveedor

- **Estado:** Aceptado · 2026-11-22

## Contexto
MerakiOS dependía de LangChain/LangGraph + OpenAI directamente en sus agentes: difícil de probar y de cambiar de proveedor.

## Decisión
Puerto `LLMClient` (`complete`, `complete_json`) con adaptadores `OpenAIChatClient` (HTTP directo) y
`FakeLLMClient` (respuestas por `metadata["task"]`). Los agentes se reescriben como pipelines OOP
(`PipelineStep`) que dependen sólo del puerto. Igual para búsqueda (`WebSearch`: Tavily / Null).

## Consecuencias
- ✅ Tests deterministas sin red, cambio de proveedor por configuración (`ONEHEAVY_LLM_PROVIDER`), menos dependencias.
- ✅ Agregar un adaptador (p. ej. Anthropic, modelo local) = una clase nueva.
- ⚠️ Se pierde el tooling de LangGraph (visualización de grafos); se compensa con pipelines explícitos y logs.
