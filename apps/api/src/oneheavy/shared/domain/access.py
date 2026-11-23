"""Control de acceso basado en roles (RBAC) — compartido por todos los módulos.

Une los roles de MerakiOS (usuario único) y de 1heavy Stays
(admin / operations / coordinator / staff / owner) en un solo modelo.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from oneheavy.shared.domain.errors import PermissionDenied


class Role(StrEnum):
    OWNER = "owner"  # dueño del workspace (cuenta que paga)
    ADMIN = "admin"  # administrador total
    MANAGER = "manager"  # gerente de operaciones (ex "operations" de Stays)
    COORDINATOR = "coordinator"  # coordina tareas y personal
    MARKETER = "marketer"  # growth, campañas, Mautic, Meta
    SALES = "sales"  # CRM: contactos y negocios
    STAFF = "staff"  # personal de limpieza / mantenimiento
    PROPERTY_OWNER = "property_owner"  # inversionista/propietario de unidades


class Permission(StrEnum):
    # identity
    WORKSPACE_MANAGE = "workspace.manage"
    MEMBERS_MANAGE = "members.manage"
    # stays
    PROPERTIES_READ = "stays.properties.read"
    PROPERTIES_MANAGE = "stays.properties.manage"
    TASKS_READ = "stays.tasks.read"
    TASKS_MANAGE = "stays.tasks.manage"
    TASKS_EXECUTE = "stays.tasks.execute"
    RECEIPTS_UPLOAD = "stays.receipts.upload"
    RECEIPTS_VERIFY = "stays.receipts.verify"
    # crm
    CONTACTS_READ = "crm.contacts.read"
    CONTACTS_MANAGE = "crm.contacts.manage"
    DEALS_MANAGE = "crm.deals.manage"
    # marketing / meta / growth
    MARKETING_MANAGE = "marketing.manage"
    META_MANAGE = "meta.manage"
    GROWTH_USE = "growth.use"
    # analytics / gamification / billing
    ANALYTICS_READ = "analytics.read"
    GAMIFICATION_READ = "gamification.read"
    GAMIFICATION_MANAGE = "gamification.manage"
    BILLING_MANAGE = "billing.manage"


_P = Permission

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset(Permission) - {_P.BILLING_MANAGE},
    Role.MANAGER: frozenset(
        {
            _P.PROPERTIES_READ,
            _P.PROPERTIES_MANAGE,
            _P.TASKS_READ,
            _P.TASKS_MANAGE,
            _P.RECEIPTS_VERIFY,
            _P.CONTACTS_READ,
            _P.ANALYTICS_READ,
            _P.GAMIFICATION_READ,
            _P.GAMIFICATION_MANAGE,
            _P.MEMBERS_MANAGE,
        }
    ),
    Role.COORDINATOR: frozenset(
        {_P.PROPERTIES_READ, _P.TASKS_READ, _P.TASKS_MANAGE, _P.ANALYTICS_READ, _P.GAMIFICATION_READ}
    ),
    Role.MARKETER: frozenset(
        {
            _P.CONTACTS_READ,
            _P.CONTACTS_MANAGE,
            _P.MARKETING_MANAGE,
            _P.META_MANAGE,
            _P.GROWTH_USE,
            _P.ANALYTICS_READ,
            _P.GAMIFICATION_READ,
        }
    ),
    Role.SALES: frozenset(
        {_P.CONTACTS_READ, _P.CONTACTS_MANAGE, _P.DEALS_MANAGE, _P.ANALYTICS_READ, _P.GAMIFICATION_READ}
    ),
    Role.STAFF: frozenset({_P.TASKS_READ, _P.TASKS_EXECUTE, _P.GAMIFICATION_READ}),
    Role.PROPERTY_OWNER: frozenset({_P.PROPERTIES_READ, _P.RECEIPTS_UPLOAD}),
}


@dataclass(frozen=True)
class Principal:
    """Actor autenticado que ejecuta un caso de uso."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: Role
    permissions: frozenset[Permission] = field(default_factory=frozenset)

    @classmethod
    def for_role(cls, user_id: uuid.UUID, tenant_id: uuid.UUID, role: Role) -> Principal:
        return cls(user_id, tenant_id, role, ROLE_PERMISSIONS[role])

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions

    def require(self, permission: Permission) -> None:
        if not self.can(permission):
            raise PermissionDenied(f"El rol '{self.role}' no tiene el permiso '{permission}'")
