import {
  BarChart3,
  Brush,
  Building2,
  CalendarCheck2,
  CreditCard,
  Gamepad2,
  Home,
  KanbanSquare,
  LayoutDashboard,
  Megaphone,
  Plug,
  Rocket,
  Target,
  UserCircle2,
  Users,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import { PERMISSIONS, type PermissionKey } from "./permissions";
import { ROUTES } from "./routes";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  permission?: PermissionKey | PermissionKey[];
  end?: boolean;
}

export interface NavGroup {
  label: string;
  /** Clase de color del módulo para el indicador activo. */
  accent: string;
  items: NavItem[];
}

const P = PERMISSIONS;

export const NAVIGATION: NavGroup[] = [
  {
    label: "General",
    accent: "bg-heavy-blue",
    items: [{ label: "Inicio", to: ROUTES.APP.HOME, icon: Home, end: true }],
  },
  {
    label: "Operación · Stays",
    accent: "bg-heavy-mint",
    items: [
      { label: "Dashboard", to: ROUTES.APP.STAYS, icon: LayoutDashboard, permission: P.TASKS_READ, end: true },
      { label: "Propiedades", to: ROUTES.APP.STAYS_PROPERTIES, icon: Building2, permission: P.PROPERTIES_READ },
      { label: "Tareas", to: ROUTES.APP.STAYS_TASKS, icon: CalendarCheck2, permission: P.TASKS_READ },
      { label: "Personal", to: ROUTES.APP.STAYS_STAFF, icon: UsersRound, permission: P.TASKS_READ },
    ],
  },
  {
    label: "Comercial · CRM",
    accent: "bg-heavy-blue",
    items: [
      { label: "Contactos", to: ROUTES.APP.CRM_CONTACTS, icon: Users, permission: P.CONTACTS_READ },
      { label: "Pipeline", to: ROUTES.APP.CRM_PIPELINE, icon: KanbanSquare, permission: P.CONTACTS_READ },
    ],
  },
  {
    label: "Crecimiento",
    accent: "bg-heavy-violet",
    items: [
      { label: "Marketing · Mautic", to: ROUTES.APP.MARKETING, icon: Megaphone, permission: P.MARKETING_MANAGE },
      { label: "Meta Business", to: ROUTES.APP.META, icon: Target, permission: P.META_MANAGE },
      { label: "Growth IA", to: ROUTES.APP.GROWTH, icon: Rocket, permission: P.GROWTH_USE },
    ],
  },
  {
    label: "Rendimiento",
    accent: "bg-heavy-ember",
    items: [
      { label: "Gamificación", to: ROUTES.APP.GAMIFICATION, icon: Gamepad2, permission: P.GAMIFICATION_READ },
      { label: "Analítica", to: ROUTES.APP.ANALYTICS, icon: BarChart3, permission: P.ANALYTICS_READ },
    ],
  },
  {
    label: "Ajustes",
    accent: "bg-muted-foreground",
    items: [
      { label: "Perfil", to: ROUTES.APP.SETTINGS_PROFILE, icon: UserCircle2 },
      { label: "Equipo", to: ROUTES.APP.SETTINGS_TEAM, icon: UsersRound, permission: P.MEMBERS_MANAGE },
      { label: "Marca", to: ROUTES.APP.SETTINGS_BRAND, icon: Brush, permission: P.WORKSPACE_MANAGE },
      {
        label: "Integraciones",
        to: ROUTES.APP.SETTINGS_INTEGRATIONS,
        icon: Plug,
        permission: [P.MARKETING_MANAGE, P.META_MANAGE, P.WORKSPACE_MANAGE],
      },
      { label: "Facturación", to: ROUTES.APP.SETTINGS_BILLING, icon: CreditCard, permission: P.BILLING_MANAGE },
    ],
  },
];

export function visibleNavigation(can: (p: PermissionKey[]) => boolean): NavGroup[] {
  return NAVIGATION.map((g) => ({
    ...g,
    items: g.items.filter((i) => !i.permission || can(Array.isArray(i.permission) ? i.permission : [i.permission])),
  })).filter((g) => g.items.length > 0);
}
