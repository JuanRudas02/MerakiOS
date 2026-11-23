import { useMemo, type ReactNode } from "react";
import { useAuth } from "./AuthProvider";
import type { PermissionKey } from "@/lib/permissions";

export function usePermissions() {
  const { user } = useAuth();
  return useMemo(() => {
    const set = new Set(user?.permissions ?? []);
    return {
      can: (permission: PermissionKey) => set.has(permission),
      canAny: (permissions: PermissionKey[]) => permissions.some((p) => set.has(p)),
    };
  }, [user]);
}

interface RequirePermissionProps {
  permission: PermissionKey | PermissionKey[];
  children: ReactNode;
  fallback?: ReactNode;
}

/** Renderiza `children` sólo si el usuario tiene (alguno de) los permisos. */
export function RequirePermission({ permission, children, fallback = null }: RequirePermissionProps) {
  const { canAny } = usePermissions();
  const list = Array.isArray(permission) ? permission : [permission];
  return <>{canAny(list) ? children : fallback}</>;
}
