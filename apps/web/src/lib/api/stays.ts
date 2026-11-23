import { http } from "./client";

export type BillingService = "administration" | "electricity" | "water" | "gas" | "internet" | "insurance";
export type BillingCutoffs = Partial<Record<BillingService, number | null>>;

export const BILLING_SERVICE_LABELS: Record<BillingService, string> = {
  administration: "Administración",
  electricity: "Energía",
  water: "Agua",
  gas: "Gas",
  internet: "Internet",
  insurance: "Seguro",
};

export interface PropertyInput {
  code: string;
  name: string;
  address?: string | null;
  capacity: number;
  owner_name?: string | null;
  owner_phone?: string | null;
  default_staff_id?: string | null;
  billing_cutoffs: BillingCutoffs;
  checklist_template: string[];
  visual_inventory: string[];
  ical_url?: string | null;
}

export interface Property extends PropertyInput {
  id: string;
  automation_paused: boolean;
  created_at: string;
}

export type ReceiptStatus = "pending" | "verified" | "rejected";
export interface Receipt {
  id: string;
  property_id: string;
  service: string;
  period: string;
  url: string;
  status: ReceiptStatus;
  note: string | null;
  uploaded_at: string;
  reviewed_at: string | null;
}

export type StaffCategory = "cleaning" | "maintenance";
export interface StaffMember {
  id: string;
  name: string;
  phone: string;
  category: StaffCategory;
  active: boolean;
  has_login: boolean;
}

export type TaskStatus = "pending" | "arrived" | "in_progress" | "completed" | "cancelled";
export type Luggage = "none" | "leave" | "collect";
export type IssueKind = "problem" | "missing_supplies" | "guests_not_out";

export interface ChecklistItem {
  item: string;
  done: boolean;
}

export interface Task {
  id: string;
  property_id: string;
  property_name: string;
  staff_id: string | null;
  staff_name: string | null;
  scheduled_at: string;
  status: TaskStatus;
  observations: string | null;
  luggage: Luggage;
  supplies_required: boolean;
  arrival_confirmed_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  checklist: ChecklistItem[];
  initial_photos: string[];
  final_photos: string[];
  issues: { kind: IssueKind; description: string; reported_at: string }[];
}

export interface TaskInput {
  property_id: string;
  staff_id?: string | null;
  scheduled_at: string;
  observations?: string | null;
  luggage: Luggage;
  supplies_required: boolean;
}

export interface TaskFilters {
  from?: string;
  to?: string;
  property_id?: string;
  staff_id?: string;
  status?: TaskStatus;
}

export interface StaysDashboard {
  today: { total: number; pending: number; in_progress: number; completed: number; cancelled: number };
  week: { completed: number; on_time_rate: number; avg_cleaning_minutes: number; issues: number };
  staff_ranking: { staff_id: string; name: string; completed: number; on_time_rate: number; avg_minutes: number }[];
  upcoming: Task[];
}

export interface StaysSettings {
  supervisor_phone: string | null;
  daily_reminder_hour: number;
  escalation_minutes: number;
  photo_mode: "standard" | "random";
}

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "Pendiente",
  arrived: "Llegada confirmada",
  in_progress: "En progreso",
  completed: "Completada",
  cancelled: "Cancelada",
};

const photosForm = (files: File[]) => {
  const form = new FormData();
  files.forEach((f) => form.append("photos", f));
  return form;
};

export const staysApi = {
  properties: () => http.get<Property[]>("/stays/properties"),
  property: (id: string) => http.get<Property>(`/stays/properties/${id}`),
  createProperty: (input: PropertyInput) => http.post<Property>("/stays/properties", input),
  updateProperty: (id: string, input: Partial<PropertyInput>) => http.patch<Property>(`/stays/properties/${id}`, input),
  syncCalendar: (id: string) => http.post<{ created: number }>(`/stays/properties/${id}/calendar-sync`),
  receipts: (propertyId: string) => http.get<Receipt[]>(`/stays/properties/${propertyId}/receipts`),
  uploadReceipt: (propertyId: string, file: File, service: string, period: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("service", service);
    form.append("period", period);
    return http.upload<Receipt>(`/stays/properties/${propertyId}/receipts`, form);
  },
  reviewReceipt: (id: string, approved: boolean, note?: string) =>
    http.post<Receipt>(`/stays/receipts/${id}/review`, { approved, note }),
  staff: () => http.get<StaffMember[]>("/stays/staff"),
  createStaff: (input: { name: string; phone: string; category: StaffCategory }) =>
    http.post<StaffMember>("/stays/staff", input),
  tasks: (filters: TaskFilters = {}) => http.get<Task[]>("/stays/tasks", { ...filters }),
  task: (id: string) => http.get<Task>(`/stays/tasks/${id}`),
  createTask: (input: TaskInput) => http.post<Task>("/stays/tasks", input),
  updateTask: (id: string, input: Partial<TaskInput>) => http.patch<Task>(`/stays/tasks/${id}`, input),
  cancelTask: (id: string, reason: string) => http.post<Task>(`/stays/tasks/${id}/cancel`, { reason }),
  requiredPhotos: (id: string, mode: "standard" | "random" = "standard") =>
    http.get<{ items: string[] }>(`/stays/tasks/${id}/required-photos`, { mode }),
  confirmArrival: (id: string, photos: File[]) => http.upload<Task>(`/stays/tasks/${id}/arrival`, photosForm(photos)),
  startTask: (id: string) => http.post<Task>(`/stays/tasks/${id}/start`),
  updateChecklist: (id: string, items: ChecklistItem[]) => http.put<Task>(`/stays/tasks/${id}/checklist`, { items }),
  reportIssue: (id: string, kind: IssueKind, description: string) =>
    http.post<Task>(`/stays/tasks/${id}/issues`, { kind, description }),
  completeTask: (id: string, photos: File[]) => http.upload<Task>(`/stays/tasks/${id}/complete`, photosForm(photos)),
  dashboard: () => http.get<StaysDashboard>("/stays/dashboard"),
  settings: () => http.get<StaysSettings>("/stays/settings"),
  updateSettings: (input: StaysSettings) => http.put<StaysSettings>("/stays/settings", input),
};
