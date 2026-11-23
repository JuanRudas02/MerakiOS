"""Firmas de Wompi (servicio de dominio puro, sin I/O).

- Integridad (checkout): SHA256(reference + amount_in_cents + currency + integrity_secret)
- Eventos (webhook):     SHA256(valores de `signature.properties` + timestamp + events_secret)

Corrige el bug de 1heavy Stays, donde `validate_webhook_signature` devolvía
siempre True.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any


def integrity_signature(reference: str, amount_in_cents: int, currency: str, secret: str) -> str:
    return hashlib.sha256(f"{reference}{amount_in_cents}{currency}{secret}".encode()).hexdigest()


def _resolve(data: dict[str, Any], path: str) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(path)
        node = node[part]
    return node


def event_checksum(event: dict[str, Any], secret: str) -> str:
    """Calcula el checksum esperado. Lanza KeyError/ValueError si el payload está incompleto."""
    signature = event["signature"]
    properties = signature["properties"]
    if not isinstance(properties, list) or not properties:
        raise ValueError("signature.properties vacío")
    data = event["data"]
    values = "".join(str(_resolve(data, p)) for p in properties)
    payload = f"{values}{event['timestamp']}{secret}"
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_event(event: dict[str, Any], secret: str, header_checksum: str | None = None) -> bool:
    try:
        expected = event_checksum(event, secret)
        provided = str(event["signature"]["checksum"])
    except (KeyError, ValueError, TypeError):
        return False
    if not hmac.compare_digest(expected.lower(), provided.lower()):
        return False
    return header_checksum is None or hmac.compare_digest(expected.lower(), header_checksum.lower())
