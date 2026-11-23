import { http } from "./client";

export type ProjectStatus = "draft" | "analyzing" | "audited" | "designing" | "completed" | "failed";
export type AwarenessLevel = "unaware" | "problem_aware" | "solution_aware" | "product_aware" | "most_aware";
export type FunnelNodeType = "ad" | "landing" | "optin" | "vsl" | "email" | "checkout" | "upsell" | "thankyou";

export interface Audit {
  avatar: string;
  pain_points: string[];
  desires: string[];
  awareness_level: AwarenessLevel;
  jobs_to_be_done: string[];
  competitors: string[];
  market_opportunity: string;
}

export interface FunnelNode {
  id: string;
  type: FunnelNodeType;
  label: string;
  position: { x: number; y: number };
}

export interface Funnel {
  nodes: FunnelNode[];
  edges: { id: string; source: string; target: string }[];
}

export interface Project {
  id: string;
  name: string;
  niche: string;
  url: string | null;
  status: ProjectStatus;
  audit: Audit | null;
  funnel: Funnel | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratedAsset {
  kind: "ad" | "landing" | "email";
  title: string;
  body: string;
}

export const AWARENESS_LABELS: Record<AwarenessLevel, string> = {
  unaware: "Inconsciente",
  problem_aware: "Consciente del problema",
  solution_aware: "Consciente de la solución",
  product_aware: "Consciente del producto",
  most_aware: "Totalmente consciente",
};

export const growthApi = {
  projects: () => http.get<Project[]>("/growth/projects"),
  project: (id: string) => http.get<Project>(`/growth/projects/${id}`),
  create: (input: { name: string; niche: string; url?: string }) => http.post<Project>("/growth/projects", input),
  audit: (id: string) => http.post<{ status: string }>(`/growth/projects/${id}/audit`),
  funnel: (id: string) => http.post<{ status: string }>(`/growth/projects/${id}/funnel`),
  assets: (id: string, kind: GeneratedAsset["kind"], node_id?: string) =>
    http.post<{ assets: GeneratedAsset[] }>(`/growth/projects/${id}/assets`, { kind, node_id }),
};
