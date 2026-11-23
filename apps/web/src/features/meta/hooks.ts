import { useQuery } from "@tanstack/react-query";
import { metaApi } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

export const metaKeys = {
  all: ["meta"] as const,
  connection: ["meta", "connection"] as const,
  campaigns: (d: number) => ["meta", "campaigns", d] as const,
  daily: (d: number) => ["meta", "daily", d] as const,
  alerts: ["meta", "alerts"] as const,
};

export const useMetaConnection = (enabled = true) =>
  useQuery({ queryKey: metaKeys.connection, queryFn: metaApi.connection, enabled });
export const useMetaCampaigns = (days: number, enabled = true) =>
  useQuery({ queryKey: metaKeys.campaigns(days), queryFn: () => metaApi.campaigns(days), enabled });
export const useMetaDaily = (days: number, enabled = true) =>
  useQuery({ queryKey: metaKeys.daily(days), queryFn: () => metaApi.daily(days), enabled });
export const useMetaAlerts = (enabled = true) => useQuery({ queryKey: metaKeys.alerts, queryFn: metaApi.alerts, enabled });

const inv = [metaKeys.all];
export const useConnectMeta = () => useApiMutation(metaApi.connect, { invalidate: inv, success: "Cuenta publicitaria conectada" });
export const useSyncMeta = () =>
  useApiMutation(() => metaApi.sync(), { invalidate: inv, success: (d) => `Sincronizadas ${d.campaigns} campañas` });
export const useTestLead = () =>
  useApiMutation(metaApi.testLead, { invalidate: [...inv, ["crm"]], success: "Lead de prueba enviado al CRM" });
