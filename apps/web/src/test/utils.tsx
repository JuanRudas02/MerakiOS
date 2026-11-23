import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelmetProvider } from "react-helmet-async";
import { ThemeProvider } from "next-themes";
import { render } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthContext, type AuthContextValue } from "@/features/auth/AuthProvider";
import type { User, Workspace } from "@/lib/api";

export const workspace: Workspace = {
  id: "w1",
  name: "Acme",
  slug: "acme",
  plan: "trial",
  business_name: "Acme",
  logo_url: null,
  primary_color: "#3B5BFD",
  whatsapp_instance: null,
};

export function makeUser(permissions: string[], role: User["role"] = "staff"): User {
  return { id: "u1", name: "Luz Staff", username: "luz", email: null, phone: null, role, active: true, permissions, last_login_at: null };
}

export function authValue(user: User | null, overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    status: user ? "authenticated" : "anonymous",
    user,
    workspace: user ? workspace : null,
    login: async () => {},
    register: async () => {},
    logout: () => {},
    refresh: async () => {},
    setWorkspace: () => {},
    ...overrides,
  };
}

export function renderWith(ui: ReactNode, { user = null, route = "/" }: { user?: User | null; route?: string } = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <HelmetProvider>
      <ThemeProvider attribute="class" defaultTheme="dark">
        <QueryClientProvider client={qc}>
          <AuthContext.Provider value={authValue(user)}>
            <TooltipProvider>
              <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter>
            </TooltipProvider>
          </AuthContext.Provider>
        </QueryClientProvider>
      </ThemeProvider>
    </HelmetProvider>,
  );
}
