"""Seguridad de webhooks de Meta (X-Hub-Signature-256)."""

from __future__ import annotations

import hashlib
import hmac

from oneheavy.shared.domain.errors import AuthenticationError

INSECURE_ENVS = frozenset({"local", "test"})


def compute_signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(secret: str | None, body: bytes, header: str | None, *, env: str) -> None:
    """Valida la firma HMAC-SHA256 en tiempo constante.

    Sin secreto configurado sólo se aceptan webhooks en entornos local/test.
    """
    if not secret:
        if env in INSECURE_ENVS:
            return
        raise AuthenticationError("Webhook de Meta sin secreto configurado", code="webhook_not_configured")
    if not header or not hmac.compare_digest(compute_signature(secret, body), header.strip()):
        raise AuthenticationError("Firma de webhook inválida", code="invalid_signature")


def verify_subscription(mode: str | None, token: str | None, expected: str | None) -> bool:
    return mode == "subscribe" and bool(expected) and hmac.compare_digest(token or "", expected or "")
