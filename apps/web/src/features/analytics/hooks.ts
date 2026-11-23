import { useQuery } from "@tanstack/react-query";
import { analyticsApi, type MetricKey } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

export const useOverview = (days: number, enabled = true) =>
  useQuery({ queryKey: ["analytics", "overview", days], queryFn: () => analyticsApi.overview(days), enabled });
export const useTimeseries = (metric: MetricKey, days: number, enabled = true) =>
  useQuery({ queryKey: ["analytics", "ts", metric, days], queryFn: () => analyticsApi.timeseries(metric, days), enabled });
export const useLifecycleFunnel = () => useQuery({ queryKey: ["analytics", "funnel"], queryFn: analyticsApi.funnel });
export const useInsights = () => useApiMutation((days: number) => analyticsApi.insights(days));
