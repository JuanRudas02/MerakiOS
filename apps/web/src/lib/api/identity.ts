import { http } from "./client";

export type Role =
  | "owner"
  | "admin"
  | "manager"
  | "coordinator"
  | "marketer"
  | "sales"
  | "staff"
  | "property_owner";

export type Plan = "trial" | "starter" | "growth" | "scale";

export interface User {
  id: string;
  name: string;
  username: string;
  email: string | null;
  phone: string | null;
  role: Role;
  active: boolean;
  permissions: string[];
  last_login_at: string | null;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  plan: Plan;
  business_name: string;
  logo_url: string | null;
  primary_color: string;
  whatsapp_instance: string | null;
}

export interface Session {
  access_token: string;
  token_type: "bearer";
  user: User;
  workspace: Workspace;
}

export interface RegisterInput {
  workspace_name: string;
  owner_name: string;
  email: string;
  password: string;
  phone?: string;
}

export interface InviteInput {
  name: string;
  role: Role;
  temporary_password: string;
  email?: string;
  phone?: string;
  username?: string;
}

export interface BrandingInput {
  business_name: string;
  logo_url?: string | null;
  primary_color?: string | null;
  whatsapp_instance?: string | null;
}

export const ROLE_LABELS: Record<Role, string> = {
  owner: "Dueño",
  admin: "Administrador",
  manager: "Gerente de operaciones",
  coordinator: "Coordinador",
  marketer: "Marketing",
  sales: "Ventas",
  staff: "Personal operativo",
  property_owner: "Propietario",
};

export const identityApi = {
  register: (input: RegisterInput) => http.public.post<Session>("/auth/register", input),
  login: (identifier: string, password: string) =>
    http.public.post<Session>("/auth/login", { identifier, password }),
  me: () => http.get<{ user: User; workspace: Workspace }>("/auth/me"),
  members: () => http.get<User[]>("/workspace/members"),
  invite: (input: InviteInput) => http.post<User>("/workspace/members", input),
  updateBranding: (input: BrandingInput) => http.put<Workspace>("/workspace/branding", input),
};
