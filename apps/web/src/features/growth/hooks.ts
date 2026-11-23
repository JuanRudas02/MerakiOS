import { useQuery } from "@tanstack/react-query";
import { growthApi, type GeneratedAsset, type Project } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

export const growthKeys = {
  all: ["growth"] as const,
  projects: ["growth", "projects"] as const,
  project: (id: string) => ["growth", "project", id] as const,
};

const BUSY: Project["status"][] = ["analyzing", "designing"];

export const useProjects = () => useQuery({ queryKey: growthKeys.projects, queryFn: growthApi.projects });
/** Hace polling mientras un pipeline IA está corriendo. */
export const useProject = (id: string) =>
  useQuery({
    queryKey: growthKeys.project(id),
    queryFn: () => growthApi.project(id),
    refetchInterval: (q) => (q.state.data && BUSY.includes(q.state.data.status) ? 2500 : false),
  });

const inv = [growthKeys.all];
export const useCreateProject = () => useApiMutation(growthApi.create, { invalidate: inv, success: "Proyecto creado" });
export const useRunAudit = () =>
  useApiMutation((id: string) => growthApi.audit(id), { invalidate: inv, success: "Auditoría de mercado en curso" });
export const useRunFunnel = () =>
  useApiMutation((id: string) => growthApi.funnel(id), { invalidate: inv, success: "Diseñando el embudo" });
export const useGenerateAssets = () =>
  useApiMutation((v: { id: string; kind: GeneratedAsset["kind"]; node_id?: string }) => growthApi.assets(v.id, v.kind, v.node_id));
