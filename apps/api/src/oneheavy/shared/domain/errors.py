"""Jerarquía de errores de dominio.

El adaptador HTTP traduce cada tipo a un código de estado (ver
`shared/infrastructure/http/errors.py`). El dominio nunca conoce HTTP.
"""

from __future__ import annotations


class DomainError(Exception):
    code: str = "domain_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFoundError(DomainError):
    code = "not_found"


class BusinessRuleViolation(DomainError):
    """Una invariante o regla de negocio (REG-xx) fue violada."""

    code = "business_rule_violation"


class ConflictError(DomainError):
    code = "conflict"


class AuthenticationError(DomainError):
    code = "authentication_failed"


class PermissionDenied(DomainError):
    code = "permission_denied"


class ExternalServiceError(DomainError):
    """Falla en un adaptador externo (Mautic, Meta, Evolution, LLM...)."""

    code = "external_service_error"
