import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { FullPageLoader, PageSkeleton } from "@/components/common/Loaders";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { AppLayout } from "@/components/layout/AppLayout";
import { ProtectedRoute } from "@/features/auth/ProtectedRoute";
import { RequirePermission } from "@/features/auth/permissions";
import { EmptyState } from "@/components/common/States";
import { PERMISSIONS, type PermissionKey } from "@/lib/permissions";
import { ShieldOff } from "lucide-react";

// Públicas
const Landing = lazy(() => import("@/pages/public/Landing"));
const ProductPage = lazy(() => import("@/pages/public/ProductPage"));
const Pricing = lazy(() => import("@/pages/public/Pricing"));
const About = lazy(() => import("@/pages/public/About"));
const Access = lazy(() => import("@/pages/public/Access"));
const NotFound = lazy(() => import("@/pages/public/NotFound"));
// App
const Home = lazy(() => import("@/pages/app/Home"));
const StaysDashboard = lazy(() => import("@/pages/app/stays/StaysDashboard"));
const Properties = lazy(() => import("@/pages/app/stays/Properties"));
const PropertyDetail = lazy(() => import("@/pages/app/stays/PropertyDetail"));
const Tasks = lazy(() => import("@/pages/app/stays/Tasks"));
const TaskDetail = lazy(() => import("@/pages/app/stays/TaskDetail"));
const Staff = lazy(() => import("@/pages/app/stays/Staff"));
const Contacts = lazy(() => import("@/pages/app/crm/Contacts"));
const Pipeline = lazy(() => import("@/pages/app/crm/Pipeline"));
const Marketing = lazy(() => import("@/pages/app/Marketing"));
const Meta = lazy(() => import("@/pages/app/Meta"));
const Projects = lazy(() => import("@/pages/app/growth/Projects"));
const ProjectDetail = lazy(() => import("@/pages/app/growth/ProjectDetail"));
const Gamification = lazy(() => import("@/pages/app/Gamification"));
const Analytics = lazy(() => import("@/pages/app/Analytics"));
const SettingsProfile = lazy(() => import("@/pages/app/settings/Profile"));
const SettingsTeam = lazy(() => import("@/pages/app/settings/Team"));
const SettingsBrand = lazy(() => import("@/pages/app/settings/Brand"));
const SettingsIntegrations = lazy(() => import("@/pages/app/settings/Integrations"));
const SettingsBilling = lazy(() => import("@/pages/app/settings/Billing"));

function Guard({ permission, children }: { permission: PermissionKey | PermissionKey[]; children: ReactNode }) {
  return (
    <RequirePermission
      permission={permission}
      fallback={<EmptyState icon={ShieldOff} title="Sin acceso" description="Tu rol no tiene permiso para ver este módulo. Pide acceso a un administrador." />}
    >
      {children}
    </RequirePermission>
  );
}

const P = PERMISSIONS;

export function AppRoutes() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<Landing />} />
          <Route path="producto/:slug" element={<ProductPage />} />
          <Route path="precios" element={<Pricing />} />
          <Route path="nosotros" element={<About />} />
          <Route path="404" element={<NotFound />} />
        </Route>
        <Route path="acceso" element={<Access />} />
        <Route path="login" element={<Navigate to="/acceso" replace />} />

        <Route
          path="app"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Home />} />
          <Route path="stays" element={<Guard permission={P.TASKS_READ}><StaysDashboard /></Guard>} />
          <Route path="stays/propiedades" element={<Guard permission={P.PROPERTIES_READ}><Properties /></Guard>} />
          <Route path="stays/propiedades/:id" element={<Guard permission={P.PROPERTIES_READ}><PropertyDetail /></Guard>} />
          <Route path="stays/tareas" element={<Guard permission={P.TASKS_READ}><Tasks /></Guard>} />
          <Route path="stays/tareas/:id" element={<Guard permission={P.TASKS_READ}><TaskDetail /></Guard>} />
          <Route path="stays/personal" element={<Guard permission={P.TASKS_READ}><Staff /></Guard>} />
          <Route path="crm/contactos" element={<Guard permission={P.CONTACTS_READ}><Contacts /></Guard>} />
          <Route path="crm/pipeline" element={<Guard permission={P.CONTACTS_READ}><Pipeline /></Guard>} />
          <Route path="marketing" element={<Guard permission={P.MARKETING_MANAGE}><Marketing /></Guard>} />
          <Route path="meta" element={<Guard permission={P.META_MANAGE}><Meta /></Guard>} />
          <Route path="growth" element={<Guard permission={P.GROWTH_USE}><Projects /></Guard>} />
          <Route path="growth/:id" element={<Guard permission={P.GROWTH_USE}><ProjectDetail /></Guard>} />
          <Route path="gamificacion" element={<Guard permission={P.GAMIFICATION_READ}><Gamification /></Guard>} />
          <Route path="analitica" element={<Guard permission={P.ANALYTICS_READ}><Analytics /></Guard>} />
          <Route path="ajustes" element={<Navigate to="perfil" replace />} />
          <Route path="ajustes/perfil" element={<SettingsProfile />} />
          <Route path="ajustes/equipo" element={<Guard permission={P.MEMBERS_MANAGE}><SettingsTeam /></Guard>} />
          <Route path="ajustes/marca" element={<Guard permission={P.WORKSPACE_MANAGE}><SettingsBrand /></Guard>} />
          <Route
            path="ajustes/integraciones"
            element={<Guard permission={[P.MARKETING_MANAGE, P.META_MANAGE, P.WORKSPACE_MANAGE]}><SettingsIntegrations /></Guard>}
          />
          <Route path="ajustes/facturacion" element={<Guard permission={P.BILLING_MANAGE}><SettingsBilling /></Guard>} />
          <Route path="*" element={<Suspense fallback={<PageSkeleton />}><NotFound /></Suspense>} />
        </Route>

        <Route path="*" element={<PublicLayout />}>
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
