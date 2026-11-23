import { http } from "./client";

export interface PlanInfo {
  key: string;
  name: string;
  price_cop: number;
  period: "month";
  features: string[];
  limits: { properties: number; contacts: number; seats: number };
}

export interface Subscription {
  plan: string;
  status: "trialing" | "active" | "past_due" | "canceled";
  current_period_end: string | null;
}

export interface Checkout {
  reference: string;
  amount_in_cents: number;
  currency: string;
  public_key: string;
  signature: string;
  redirect_url: string;
}

/** Catálogo de respaldo si el API no está disponible (landing pública). */
export const FALLBACK_PLANS: PlanInfo[] = [
  {
    key: "starter",
    name: "Starter",
    price_cop: 89000,
    period: "month",
    features: ["CRM y pipeline", "Operación Stays hasta 10 unidades", "WhatsApp con tu número", "Gamificación básica"],
    limits: { properties: 10, contacts: 1000, seats: 3 },
  },
  {
    key: "growth",
    name: "Growth",
    price_cop: 249000,
    period: "month",
    features: [
      "Todo Starter",
      "Mautic + IA: emails y campañas",
      "Meta Business: Ads y Lead Ads",
      "Growth IA: auditoría y embudos",
      "Analítica con insights IA",
    ],
    limits: { properties: 50, contacts: 10000, seats: 10 },
  },
  {
    key: "scale",
    name: "Scale",
    price_cop: 590000,
    period: "month",
    features: ["Todo Growth", "Marca blanca completa", "Retos y reglas de gamificación a medida", "Soporte prioritario"],
    limits: { properties: 100000, contacts: 1000000, seats: 50 },
  },
];

export const billingApi = {
  plans: () => http.public.get<PlanInfo[]>("/billing/plans"),
  subscription: () => http.get<Subscription>("/billing/subscription"),
  checkout: (plan: string) => http.post<Checkout>("/billing/checkout", { plan }),
};
