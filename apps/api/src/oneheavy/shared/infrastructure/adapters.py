"""Adaptadores de búsqueda web y almacenamiento de archivos."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import httpx

from oneheavy.shared.application.ports import FileStorage, WebSearch
from oneheavy.shared.domain.errors import BusinessRuleViolation

log = logging.getLogger("oneheavy.adapters")


class NullWebSearch(WebSearch):
    """Sin proveedor configurado: el pipeline de investigación sigue sólo con el LLM."""

    async def search(self, query: str, max_results: int = 3) -> list[dict[str, Any]]:
        return []


class TavilyWebSearch(WebSearch):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 3) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": self._api_key, "query": query, "max_results": max_results},
                )
                resp.raise_for_status()
                return list(resp.json().get("results", []))
        except httpx.HTTPError:
            log.exception("tavily_search_failed", extra={"query": query})
            return []


# Firmas binarias (magic bytes) permitidas: sólo imágenes y PDF.
_MAGIC: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
    "application/pdf": (b"%PDF",),
}
_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "application/pdf": "pdf"}


def sniff_content_type(data: bytes) -> str | None:
    for content_type, signatures in _MAGIC.items():
        if any(data.startswith(sig) for sig in signatures):
            if content_type == "image/webp" and data[8:12] != b"WEBP":
                continue
            return content_type
    return None


class LocalFileStorage(FileStorage):
    """Guarda en disco y valida tipo real (magic bytes) y tamaño.

    Corrige el riesgo #8 de Stays (uploads sin validación). En producción se
    reemplaza por un adaptador S3/R2 con la misma interfaz.
    """

    def __init__(self, root: str, *, public_prefix: str = "/storage", max_mb: int = 10) -> None:
        self._root = Path(root)
        self._prefix = public_prefix
        self._max_bytes = max_mb * 1024 * 1024

    async def save(self, data: bytes, *, folder: str, filename: str, content_type: str) -> str:
        if len(data) > self._max_bytes:
            raise BusinessRuleViolation("El archivo supera el tamaño máximo permitido", code="file_too_large")
        real_type = sniff_content_type(data)
        if real_type is None:
            raise BusinessRuleViolation("Sólo se permiten imágenes JPG/PNG/WEBP o PDF", code="invalid_file")
        safe_folder = "/".join(p for p in Path(folder).parts if p not in ("..", "/"))
        target_dir = self._root / safe_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}.{_EXT[real_type]}"
        (target_dir / name).write_bytes(data)
        return f"{self._prefix}/{safe_folder}/{name}"
