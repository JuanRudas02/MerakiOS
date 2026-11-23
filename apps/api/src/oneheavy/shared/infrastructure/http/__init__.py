"""Adaptador HTTP compartido: dependencias FastAPI y mapeo de errores."""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from oneheavy.shared.application.ports import UnitOfWork
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import (
    AuthenticationError,
    BusinessRuleViolation,
    ConflictError,
    DomainError,
    ExternalServiceError,
    NotFoundError,
    PermissionDenied,
)
from oneheavy.shared.infrastructure.container import Container

log = logging.getLogger("oneheavy.http")
_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_uow(container: Container = Depends(get_container)) -> UnitOfWork:
    return container.uow()


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    container: Container = Depends(get_container),
) -> Principal:
    if credentials is None:
        raise AuthenticationError("Se requiere autenticación")
    return container.tokens.decode(credentials.credentials)


def require(permission: Permission) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """Dependencia: `principal = Depends(require(Permission.TASKS_MANAGE))`."""

    async def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        principal.require(permission)
        return principal

    return _dep


_STATUS: list[tuple[type[DomainError], int]] = [
    (NotFoundError, 404),
    (AuthenticationError, 401),
    (PermissionDenied, 403),
    (ConflictError, 409),
    (BusinessRuleViolation, 422),
    (ExternalServiceError, 502),
]


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        status = next((code for cls, code in _STATUS if isinstance(exc, cls)), 400)
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(
            status_code=status, content={"error": {"code": exc.code, "message": exc.message}}, headers=headers
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Nunca filtrar el detalle interno al cliente (Stays devolvía str(exc)).
        log.exception("unhandled_error", extra={"path": request.url.path, "method": request.method})
        return JSONResponse(
            status_code=500, content={"error": {"code": "internal_error", "message": "Error interno"}}
        )
