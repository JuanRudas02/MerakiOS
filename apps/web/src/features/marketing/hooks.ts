import { useQuery } from "@tanstack/react-query";
import { marketingApi, type GenerateEmailInput, type SegmentFilters } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

export const mktKeys = {
  all: ["marketing"] as const,
  status: ["marketing", "status"] as const,
  segments: ["marketing", "segments"] as const,
  emails: ["marketing", "emails"] as const,
  campaigns: ["marketing", "campaigns"] as const,
};

export const useMarketingStatus = (enabled = true) =>
  useQuery({ queryKey: mktKeys.status, queryFn: marketingApi.status, enabled });
export const useSegments = () => useQuery({ queryKey: mktKeys.segments, queryFn: marketingApi.segments });
export const useEmails = () => useQuery({ queryKey: mktKeys.emails, queryFn: marketingApi.emails });
export const useCampaigns = () => useQuery({ queryKey: mktKeys.campaigns, queryFn: marketingApi.campaigns });

const inv = [mktKeys.all];
export const useCreateSegment = () =>
  useApiMutation((v: { name: string; description?: string; filters: SegmentFilters }) => marketingApi.createSegment(v), {
    invalidate: inv,
    success: "Segmento creado",
  });
export const useSyncSegment = () =>
  useApiMutation((id: string) => marketingApi.syncSegment(id), { invalidate: inv, success: "Segmento sincronizado con Mautic" });
export const useGenerateEmail = () =>
  useApiMutation((v: GenerateEmailInput) => marketingApi.generateEmail(v), { invalidate: inv, success: "Email generado con IA" });
export const usePushEmail = () =>
  useApiMutation((id: string) => marketingApi.pushEmail(id), { invalidate: inv, success: "Email enviado a Mautic" });
export const usePlanCampaign = () =>
  useApiMutation((v: { objective: string; segment_id?: string | null; duration_days: number }) => marketingApi.planCampaign(v), {
    invalidate: inv,
    success: "Campaña planificada con IA",
  });
export const useLaunchCampaign = () =>
  useApiMutation((id: string) => marketingApi.launchCampaign(id), { invalidate: inv, success: "Campaña lanzada" });
