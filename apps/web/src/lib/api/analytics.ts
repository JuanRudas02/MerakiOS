import { http } from "./client";

export interface Overview {
  period: { from: string; to: string };
  operations: { tasks_completed: number; on_time_rate: number; avg_cleaning_minutes: number; issues: number };
  sales: { new_contacts: number; deals_won: number; revenue: number; win_rate: number };
  marketing: {
    leads_captured: number;
    engagement_events: number;
    campaigns_launched: number;
    ad_spend: number;
    cpl: number;
  };
  growth: { audits_completed: number; funnels_designed: number };
  gamification: { points_awarded: number; active_players: number };
}

export type MetricKey =
  | "tasks_completed"
  | "contacts_created"
  | "leads_captured"
  | "deals_won"
  | "revenue"
  | "ad_spend"
  | "engagement_events"
  | "points_awarded";

export const METRIC_LABELS: Record<MetricKey, string> = {
  tasks_completed: "Limpiezas completadas",
  contacts_created: "Contactos nuevos",
  leads_captured: "Leads capturados",
  deals_won: "Negocios ganados",
  revenue: "Ingresos",
  ad_spend: "Inversión publicitaria",
  engagement_events: "Interacciones de marketing",
  points_awarded: "Puntos otorgados",
};

export interface Insights {
  summary: string;
  highlights: string[];
  risks: string[];
  recommendations: string[];
}

export const analyticsApi = {
  overview: (days = 30) => http.get<Overview>("/analytics/overview", { days }),
  timeseries: (metric: MetricKey, days = 30) =>
    http.get<{ date: string; value: number }[]>("/analytics/timeseries", { metric, days }),
  funnel: () => http.get<{ stage: string; count: number }[]>("/analytics/funnel"),
  insights: (days = 30) => http.post<Insights>("/analytics/insights", { days }),
};
