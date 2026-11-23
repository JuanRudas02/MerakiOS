import { http } from "./client";
import type { LifecycleStage } from "./crm";

export interface MarketingStatus {
  mautic_enabled: boolean;
  connected: boolean;
  last_sync_at: string | null;
  synced_contacts: number;
}

export interface SegmentFilters {
  stages?: LifecycleStage[];
  tags?: string[];
  min_score?: number;
}

export interface Segment {
  id: string;
  name: string;
  description: string | null;
  filters: SegmentFilters;
  contacts_count: number;
  mautic_id: string | number | null;
  synced_at: string | null;
}

export interface EmailDraft {
  id: string;
  subject: string;
  preheader: string;
  body_html: string;
  body_text: string;
  goal: string;
  status: "draft" | "pushed" | "sent";
  segment_id: string | null;
  mautic_id: string | number | null;
  created_at: string;
}

export interface GenerateEmailInput {
  goal: string;
  audience: string;
  tone?: string;
  language?: string;
  segment_id?: string | null;
}

export interface CampaignStep {
  day: number;
  channel: "email" | "whatsapp" | "ads";
  subject: string;
  intent: string;
}

export interface Campaign {
  id: string;
  name: string;
  objective: string;
  status: "planned" | "active" | "paused" | "completed";
  segment_id: string | null;
  steps: CampaignStep[];
  mautic_id: string | number | null;
  created_at: string;
}

export const marketingApi = {
  status: () => http.get<MarketingStatus>("/marketing/status"),
  segments: () => http.get<Segment[]>("/marketing/segments"),
  createSegment: (input: { name: string; description?: string; filters: SegmentFilters }) =>
    http.post<Segment>("/marketing/segments", input),
  syncSegment: (id: string) => http.post<Segment>(`/marketing/segments/${id}/sync`),
  emails: () => http.get<EmailDraft[]>("/marketing/emails"),
  generateEmail: (input: GenerateEmailInput) => http.post<EmailDraft>("/marketing/emails/generate", input),
  pushEmail: (id: string) => http.post<EmailDraft>(`/marketing/emails/${id}/push`),
  campaigns: () => http.get<Campaign[]>("/marketing/campaigns"),
  planCampaign: (input: { objective: string; segment_id?: string | null; duration_days: number }) =>
    http.post<Campaign>("/marketing/campaigns/plan", input),
  launchCampaign: (id: string) => http.post<Campaign>(`/marketing/campaigns/${id}/launch`),
};
