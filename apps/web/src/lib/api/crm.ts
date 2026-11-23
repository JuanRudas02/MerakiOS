import { http, type Page } from "./client";

export type LifecycleStage =
  | "subscriber"
  | "lead"
  | "mql"
  | "sql"
  | "opportunity"
  | "customer"
  | "evangelist"
  | "lost";

export const STAGE_LABELS: Record<LifecycleStage, string> = {
  subscriber: "Suscriptor",
  lead: "Lead",
  mql: "MQL",
  sql: "SQL",
  opportunity: "Oportunidad",
  customer: "Cliente",
  evangelist: "Evangelizador",
  lost: "Perdido",
};

export type ContactSource = "manual" | "meta_lead_ads" | "whatsapp" | "instagram" | "web_form" | "import" | "mautic";

export interface ContactInput {
  first_name: string;
  last_name?: string | null;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  job_title?: string | null;
  source?: ContactSource;
  tags: string[];
  owner_id?: string | null;
}

export interface Contact extends ContactInput {
  id: string;
  full_name: string;
  stage: LifecycleStage;
  score: number;
  mautic_id: string | number | null;
  last_activity_at: string | null;
  created_at: string;
}

export type ActivityKind = "note" | "call" | "email" | "whatsapp" | "meeting" | "marketing" | "ads" | "system";
export interface Activity {
  id: string;
  contact_id: string;
  kind: ActivityKind;
  summary: string;
  actor_id: string | null;
  occurred_at: string;
}

export interface ContactInsight {
  score: number;
  temperature: "cold" | "warm" | "hot";
  explanation: string;
  next_best_action: string;
}

export type DealStage = "new" | "qualified" | "proposal" | "negotiation" | "won" | "lost";
export interface Deal {
  id: string;
  title: string;
  contact_id: string | null;
  contact_name: string | null;
  amount: number | string;
  currency: string;
  stage: DealStage;
  owner_id: string | null;
  expected_close: string | null;
  created_at: string;
  closed_at: string | null;
}

export interface DealInput {
  title: string;
  contact_id?: string | null;
  amount: number;
  currency: string;
  stage?: DealStage;
  owner_id?: string | null;
  expected_close?: string | null;
}

export interface Pipeline {
  stages: { key: DealStage; name: string; order: number; probability: number }[];
  deals: Deal[];
}

export interface ContactFilters {
  q?: string;
  stage?: LifecycleStage;
  tag?: string;
  owner_id?: string;
  page?: number;
  size?: number;
}

export const crmApi = {
  contacts: (filters: ContactFilters = {}) => http.get<Page<Contact>>("/crm/contacts", { ...filters }),
  contact: (id: string) => http.get<Contact>(`/crm/contacts/${id}`),
  createContact: (input: ContactInput) => http.post<Contact>("/crm/contacts", input),
  updateContact: (id: string, input: Partial<ContactInput>) => http.patch<Contact>(`/crm/contacts/${id}`, input),
  changeStage: (id: string, stage: LifecycleStage) => http.post<Contact>(`/crm/contacts/${id}/stage`, { stage }),
  timeline: (id: string) => http.get<Activity[]>(`/crm/contacts/${id}/timeline`),
  addActivity: (id: string, kind: ActivityKind, summary: string) =>
    http.post<Activity>(`/crm/contacts/${id}/activities`, { kind, summary }),
  insight: (id: string) => http.post<ContactInsight>(`/crm/contacts/${id}/insight`),
  importContacts: (contacts: ContactInput[]) =>
    http.post<{ created: number; merged: number; skipped: number }>("/crm/contacts/import", { contacts }),
  pipeline: () => http.get<Pipeline>("/crm/pipeline"),
  createDeal: (input: DealInput) => http.post<Deal>("/crm/deals", input),
  updateDeal: (id: string, input: Partial<DealInput>) => http.patch<Deal>(`/crm/deals/${id}`, input),
  moveDeal: (id: string, stage: DealStage) => http.post<Deal>(`/crm/deals/${id}/move`, { stage }),
};
