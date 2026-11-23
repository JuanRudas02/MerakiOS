import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { addDays, format, startOfWeek } from "date-fns";
import { es } from "date-fns/locale";
import { CalendarCheck2, ChevronLeft, ChevronRight, LayoutList, Loader2, Plus, Rows3 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { StatusBadge, TASK_TONE } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { RequirePermission } from "@/features/auth/permissions";
import { useCreateTask, useProperties, useStaff, useTasks } from "@/features/stays/hooks";
import { TASK_STATUS_LABELS, type Luggage, type TaskInput, type TaskStatus } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

function NewTaskDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const properties = useProperties();
  const staff = useStaff();
  const create = useCreateTask();
  const [form, setForm] = useState<{ property_id: string; staff_id: string; when: string; observations: string; luggage: Luggage; supplies_required: boolean }>({
    property_id: "",
    staff_id: "",
    when: format(addDays(new Date(), 1), "yyyy-MM-dd'T'11:00"),
    observations: "",
    luggage: "none",
    supplies_required: false,
  });
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const input: TaskInput = {
      property_id: form.property_id,
      staff_id: form.staff_id || null,
      scheduled_at: new Date(form.when).toISOString(),
      observations: form.observations || null,
      luggage: form.luggage,
      supplies_required: form.supplies_required,
    };
    create.mutate(input, { onSuccess: () => onOpenChange(false) });
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Programar limpieza</DialogTitle>
        </DialogHeader>
        <form id="task-form" onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Propiedad</Label>
            <Select value={form.property_id} onValueChange={(v) => setForm({ ...form, property_id: v })} required>
              <SelectTrigger>
                <SelectValue placeholder="Selecciona la unidad" />
              </SelectTrigger>
              <SelectContent>
                {properties.data?.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.code} · {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Colaborador</Label>
            <Select value={form.staff_id || "default"} onValueChange={(v) => setForm({ ...form, staff_id: v === "default" ? "" : v })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default">Personal por defecto de la propiedad</SelectItem>
                {staff.data?.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="t-when">Fecha y hora</Label>
              <Input id="t-when" type="datetime-local" required value={form.when} onChange={(e) => setForm({ ...form, when: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Equipaje</Label>
              <Select value={form.luggage} onValueChange={(v) => setForm({ ...form, luggage: v as Luggage })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Sin indicación</SelectItem>
                  <SelectItem value="leave">Dejar equipaje</SelectItem>
                  <SelectItem value="collect">Recoger equipaje</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="t-obs">Observaciones</Label>
            <Textarea id="t-obs" rows={3} value={form.observations} onChange={(e) => setForm({ ...form, observations: e.target.value })} />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={form.supplies_required} onCheckedChange={(v) => setForm({ ...form, supplies_required: v === true })} />
            Requiere llevar insumos
          </label>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button type="submit" form="task-form" disabled={!form.property_id || create.isPending}>
            {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Programar y notificar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Tasks() {
  const [params, setParams] = useSearchParams();
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [view, setView] = useState<"week" | "list">("week");
  const [status, setStatus] = useState<TaskStatus | "all">("all");
  const filters = useMemo(
    () => ({
      from: weekStart.toISOString(),
      to: addDays(weekStart, 7).toISOString(),
      status: status === "all" ? undefined : status,
    }),
    [weekStart, status],
  );
  const { data, isLoading, error, refetch } = useTasks(filters);
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const creating = params.get("nueva") === "1";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tareas de limpieza"
        description="Programación semanal, estados y evidencias."
        icon={CalendarCheck2}
        accent="mint"
        actions={
          <RequirePermission permission={PERMISSIONS.TASKS_MANAGE}>
            <Button onClick={() => setParams({ nueva: "1" })}>
              <Plus className="mr-1 h-4 w-4" /> Programar
            </Button>
          </RequirePermission>
        }
      />
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon" onClick={() => setWeekStart(addDays(weekStart, -7))} aria-label="Semana anterior">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }))}>
            Hoy
          </Button>
          <Button variant="outline" size="icon" onClick={() => setWeekStart(addDays(weekStart, 7))} aria-label="Semana siguiente">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-sm font-medium">
          {format(weekStart, "d MMM", { locale: es })} – {format(addDays(weekStart, 6), "d MMM yyyy", { locale: es })}
        </p>
        <div className="ml-auto flex items-center gap-2">
          <Select value={status} onValueChange={(v) => setStatus(v as TaskStatus | "all")}>
            <SelectTrigger className="w-44" aria-label="Filtrar por estado">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los estados</SelectItem>
              {(Object.keys(TASK_STATUS_LABELS) as TaskStatus[]).map((s) => (
                <SelectItem key={s} value={s}>
                  {TASK_STATUS_LABELS[s]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <ToggleGroup type="single" value={view} onValueChange={(v) => v && setView(v as "week" | "list")} aria-label="Vista">
            <ToggleGroupItem value="week" aria-label="Vista semanal">
              <Rows3 className="h-4 w-4" />
            </ToggleGroupItem>
            <ToggleGroupItem value="list" aria-label="Vista de lista">
              <LayoutList className="h-4 w-4" />
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
      </div>

      {isLoading ? (
        <ListSkeleton rows={6} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <EmptyState icon={CalendarCheck2} title="Sin tareas esta semana" description="Programa una limpieza o sincroniza el calendario iCal de tus propiedades." />
      ) : view === "list" ? (
        <Card className="divide-y">
          {data.map((t) => (
            <Link key={t.id} to={ROUTES.APP.STAYS_TASK(t.id)} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 hover:bg-elevated/50">
              <div className="min-w-0">
                <p className="font-medium">{t.property_name}</p>
                <p className="text-xs text-muted-foreground">
                  {fmtDateTime(t.scheduled_at)} · {t.staff_name ?? "Sin asignar"}
                </p>
              </div>
              <StatusBadge tone={TASK_TONE[t.status]}>{TASK_STATUS_LABELS[t.status]}</StatusBadge>
            </Link>
          ))}
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-7">
          {days.map((d) => {
            const key = format(d, "yyyy-MM-dd");
            const dayTasks = data.filter((t) => format(new Date(t.scheduled_at), "yyyy-MM-dd") === key);
            const today = key === format(new Date(), "yyyy-MM-dd");
            return (
              <div key={key} className={cn("min-h-32 rounded-xl border bg-surface p-2", today && "border-heavy-mint/60")}>
                <p className={cn("mb-2 px-1 text-xs font-semibold capitalize", today ? "text-heavy-mint" : "text-muted-foreground")}>
                  {format(d, "EEE d", { locale: es })}
                </p>
                <div className="space-y-1.5">
                  {dayTasks.map((t) => (
                    <Link
                      key={t.id}
                      to={ROUTES.APP.STAYS_TASK(t.id)}
                      className="block rounded-lg border bg-elevated/60 p-2 text-xs transition-colors hover:border-heavy-mint/50"
                    >
                      <p className="truncate font-medium">{t.property_name}</p>
                      <p className="text-muted-foreground">{format(new Date(t.scheduled_at), "HH:mm")}</p>
                      <StatusBadge tone={TASK_TONE[t.status]} className="mt-1 text-[10px]">
                        {TASK_STATUS_LABELS[t.status]}
                      </StatusBadge>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {creating && <NewTaskDialog open onOpenChange={(v) => !v && setParams({})} />}
    </div>
  );
}
