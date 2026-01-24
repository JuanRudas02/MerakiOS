import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider } from "@/hooks/useAuth";
import { ROUTES } from "@/lib/routes";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/layouts/AppLayout";

// Public Pages
import HomePublic from "@/pages/public/HomePublic";
import Login from "@/pages/public/Login";
import Pricing from "@/pages/public/Pricing";
import About from "@/pages/public/About";

// App Pages
import AppHome from "@/pages/app/AppHome";
import Services from "@/pages/app/Services";
import Metrics from "@/pages/app/services/Metrics";
import MetricsFacebook from "@/pages/app/services/MetricsFacebook";
import MetricsInstagram from "@/pages/app/services/MetricsInstagram";
import AIReports from "@/pages/app/services/AIReports";
import Settings from "@/pages/app/Settings";
import Profile from "@/pages/app/settings/Profile";
import Integrations from "@/pages/app/settings/Integrations";
import Meta from "@/pages/app/settings/Meta";
import Billing from "@/pages/app/settings/Billing";
import NotFound from "@/pages/NotFound";

// New Strategic Modules
import MarketAudit from "@/pages/app/services/MarketAudit";
import FunnelArchitect from "@/pages/app/services/FunnelArchitect";
import Blueprints from "@/pages/app/services/Blueprints";
import IntelligenceDashboard from "@/pages/app/services/IntelligenceDashboard";

const queryClient = new QueryClient();

const App = () => (
  <HelmetProvider>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <Routes>
              {/* Public Routes */}
              <Route path={ROUTES.PUBLIC.HOME} element={<HomePublic />} />
              <Route path={ROUTES.PUBLIC.LOGIN} element={<Login />} />
              <Route path={ROUTES.PUBLIC.PRICING} element={<Pricing />} />
              <Route path={ROUTES.PUBLIC.ABOUT} element={<About />} />

              {/* Protected App Routes */}
              <Route path={ROUTES.APP.ROOT} element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
                <Route index element={<Navigate to={ROUTES.APP.HOME} replace />} />
                <Route path="home" element={<AppHome />} />
                
                {/* Strategic Modules (The 4 Pillars) */}
                <Route path="services" element={<Services />}>
                  {/* The Brain - Market Audit */}
                  <Route path="market-audit" element={<MarketAudit />} />
                  {/* The Mapper - Funnel Architect */}
                  <Route path="funnel-architect" element={<FunnelArchitect />} />
                  {/* The Blueprints */}
                  <Route path="blueprints" element={<Blueprints />} />
                  {/* The Director - Intelligence Dashboard */}
                  <Route path="intelligence" element={<IntelligenceDashboard />} />
                  {/* Metrics */}
                  <Route path="metrics" element={<Metrics />} />
                  <Route path="metrics/facebook" element={<MetricsFacebook />} />
                  <Route path="metrics/instagram" element={<MetricsInstagram />} />
                  {/* AI Reports */}
                  <Route path="ai-reports" element={<AIReports />} />
                </Route>

                {/* Settings */}
                <Route path="settings" element={<Settings />}>
                  <Route path="profile" element={<Profile />} />
                  <Route path="integrations" element={<Integrations />} />
                  <Route path="meta" element={<Meta />} />
                  <Route path="billing" element={<Billing />} />
                </Route>
              </Route>

              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  </HelmetProvider>
);

export default App;
