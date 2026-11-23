import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { crmApi, type ActivityKind, type ContactFilters, type ContactInput, type DealInput, type DealStage, type LifecycleStage } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

export const crmKeys = {
  all: ["crm"] as const,
  contacts: (f: ContactFilters) => ["crm", "contacts", f] as const,
  contact: (id: string) => ["crm", "contact", id] as const,
  timeline: (id: string) => ["crm", "timeline", id] as const,
  pipeline: ["crm", "pipeline"] as const,
};

export const useContacts = (f: ContactFilters) =>
  useQuery({ queryKey: crmKeys.contacts(f), queryFn: () => crmApi.contacts(f), placeholderData: keepPreviousData });
export const useContact = (id: string | null) =>
  useQuery({ queryKey: crmKeys.contact(id ?? ""), queryFn: () => crmApi.contact(id!), enabled: !!id });
export const useTimeline = (id: string | null) =>
  useQuery({ queryKey: crmKeys.timeline(id ?? ""), queryFn: () => crmApi.timeline(id!), enabled: !!id });
export const usePipeline = () => useQuery({ queryKey: crmKeys.pipeline, queryFn: crmApi.pipeline });

const inv = [crmKeys.all];
export const useCreateContact = () =>
  useApiMutation((input: ContactInput) => crmApi.createContact(input), { invalidate: inv, success: "Contacto creado" });
export const useChangeStage = () =>
  useApiMutation((v: { id: string; stage: LifecycleStage }) => crmApi.changeStage(v.id, v.stage), { invalidate: inv, success: "Etapa actualizada" });
export const useAddActivity = () =>
  useApiMutation((v: { id: string; kind: ActivityKind; summary: string }) => crmApi.addActivity(v.id, v.kind, v.summary), {
    invalidate: inv,
    success: "Actividad registrada",
  });
export const useContactInsight = () => useApiMutation((id: string) => crmApi.insight(id));
export const useCreateDeal = () =>
  useApiMutation((input: DealInput) => crmApi.createDeal(input), { invalidate: inv, success: "Negocio creado" });
export const useMoveDeal = () =>
  useApiMutation((v: { id: string; stage: DealStage }) => crmApi.moveDeal(v.id, v.stage), { invalidate: inv });
