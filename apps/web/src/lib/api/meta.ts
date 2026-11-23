import { http } from "./client";

export interface MetaConnection {
  connected: boolean;
  ad_account_id: string | null;
  page_id: string | null;
  pixel_id: string | null;
  last_sync_at: string | null;
}

export interface CampaignPerfTotals {
  name?: string;
  status?: string;
  objective?: string;
  spend: number;
  impressions: number;
  clicks: number;
  ctr: number;
  cpc: number;
  cpm: number;
  leads: number;
  cpl: number;
  conversions: number;
  roas: number;
}

export interface CampaignPerf extends CampaignPerfTotals {
  id: string;
  external_id: string;
  name: string;
  status: string;
  objective: string;
}

export interface DailyInsight {
  date: string;
  spend: number;
  impressions: number;
  clicks: number;
  leads: number;
}

export interface MetaAlert {
  id: string;
  campaign_ref: string;
  metric: string;
  value: number;
  benchmark: number;
  severity: "info" | "warning" | "critical";
  message: string;
  created_at: string;
}

export const metaApi = {
  connection: () => http.get<MetaConnection>("/meta/connection"),
  connect: (input: { ad_account_id: string; page_id?: string; pixel_id?: string; access_token: string }) =>
    http.put<MetaConnection>("/meta/connection", input),
  sync: () => http.post<{ campaigns: number; days: number }>("/meta/sync"),
  campaigns: (days = 30) => http.get<{ items: CampaignPerf[]; totals: CampaignPerfTotals }>("/meta/campaigns", { days }),
  daily: (days = 30) => http.get<DailyInsight[]>("/meta/insights/daily", { days }),
  alerts: () => http.get<MetaAlert[]>("/meta/alerts"),
  testLead: (input: { full_name: string; email?: string; phone?: string }) =>
    http.post<{ ok: boolean }>("/meta/leads/test", input),
};
