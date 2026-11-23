import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { ROUTES } from "@/lib/routes";
import { FullPageLoader } from "@/components/common/Loaders";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageLoader />;
  if (status === "anonymous") return <Navigate to={ROUTES.PUBLIC.ACCESS} replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}
