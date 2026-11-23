import { useQuery } from "@tanstack/react-query";
import { staysApi, type ChecklistItem, type IssueKind, type PropertyInput, type StaysSettings, type TaskFilters, type TaskInput } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

export const staysKeys = {
  all: ["stays"] as const,
  properties: ["stays", "properties"] as const,
  property: (id: string) => ["stays", "properties", id] as const,
  receipts: (id: string) => ["stays", "receipts", id] as const,
  staff: ["stays", "staff"] as const,
  tasks: (f: TaskFilters) => ["stays", "tasks", f] as const,
  task: (id: string) => ["stays", "task", id] as const,
  dashboard: ["stays", "dashboard"] as const,
  settings: ["stays", "settings"] as const,
};

export const useStaysDashboard = (enabled = true) =>
  useQuery({ queryKey: staysKeys.dashboard, queryFn: staysApi.dashboard, enabled });
export const useProperties = () => useQuery({ queryKey: staysKeys.properties, queryFn: staysApi.properties });
export const useProperty = (id: string) => useQuery({ queryKey: staysKeys.property(id), queryFn: () => staysApi.property(id) });
export const useReceipts = (id: string) => useQuery({ queryKey: staysKeys.receipts(id), queryFn: () => staysApi.receipts(id) });
export const useStaff = () => useQuery({ queryKey: staysKeys.staff, queryFn: staysApi.staff });
export const useTasks = (filters: TaskFilters) =>
  useQuery({ queryKey: staysKeys.tasks(filters), queryFn: () => staysApi.tasks(filters) });
export const useTask = (id: string) => useQuery({ queryKey: staysKeys.task(id), queryFn: () => staysApi.task(id) });
export const useRequiredPhotos = (id: string, mode: "standard" | "random") =>
  useQuery({ queryKey: ["stays", "required-photos", id, mode], queryFn: () => staysApi.requiredPhotos(id, mode) });
export const useStaysSettings = () => useQuery({ queryKey: staysKeys.settings, queryFn: staysApi.settings });

const inv = [staysKeys.all];

export const useCreateProperty = () =>
  useApiMutation((input: PropertyInput) => staysApi.createProperty(input), { invalidate: inv, success: "Propiedad creada" });
export const useUpdateProperty = (id: string) =>
  useApiMutation((input: Partial<PropertyInput>) => staysApi.updateProperty(id, input), {
    invalidate: inv,
    success: "Propiedad actualizada",
  });
export const useSyncCalendar = (id: string) =>
  useApiMutation(() => staysApi.syncCalendar(id), {
    invalidate: inv,
    success: (d) => `Calendario sincronizado: ${d.created} tareas nuevas`,
  });
export const useUploadReceipt = (id: string) =>
  useApiMutation((v: { file: File; service: string; period: string }) => staysApi.uploadReceipt(id, v.file, v.service, v.period), {
    invalidate: inv,
    success: "Comprobante cargado",
  });
export const useReviewReceipt = () =>
  useApiMutation((v: { id: string; approved: boolean; note?: string }) => staysApi.reviewReceipt(v.id, v.approved, v.note), {
    invalidate: inv,
    success: "Comprobante revisado",
  });
export const useCreateStaff = () =>
  useApiMutation(staysApi.createStaff, { invalidate: inv, success: "Colaborador registrado" });
export const useCreateTask = () =>
  useApiMutation((input: TaskInput) => staysApi.createTask(input), { invalidate: inv, success: "Tarea programada y notificada" });
export const useCancelTask = () =>
  useApiMutation((v: { id: string; reason: string }) => staysApi.cancelTask(v.id, v.reason), { invalidate: inv, success: "Tarea cancelada" });
export const useConfirmArrival = () =>
  useApiMutation((v: { id: string; photos: File[] }) => staysApi.confirmArrival(v.id, v.photos), { invalidate: inv, success: "Llegada confirmada" });
export const useStartTask = () => useApiMutation((id: string) => staysApi.startTask(id), { invalidate: inv, success: "Limpieza iniciada" });
export const useUpdateChecklist = () =>
  useApiMutation((v: { id: string; items: ChecklistItem[] }) => staysApi.updateChecklist(v.id, v.items), { invalidate: inv });
export const useReportIssue = () =>
  useApiMutation((v: { id: string; kind: IssueKind; description: string }) => staysApi.reportIssue(v.id, v.kind, v.description), {
    invalidate: inv,
    success: "Novedad reportada al supervisor",
  });
export const useCompleteTask = () =>
  useApiMutation((v: { id: string; photos: File[] }) => staysApi.completeTask(v.id, v.photos), { invalidate: inv, success: "¡Tarea completada!" });
export const useUpdateStaysSettings = () =>
  useApiMutation((input: StaysSettings) => staysApi.updateSettings(input), { invalidate: inv, success: "Ajustes guardados" });
