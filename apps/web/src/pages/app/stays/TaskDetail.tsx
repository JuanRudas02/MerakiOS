import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, Camera, CheckCircle2, Loader2, MapPinCheck, Play, XCircle } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { ErrorState } from "@/components/common/States";
import { PageSkeleton } from "@/components/common/Loaders";
import { StatusBadge, TASK_TONE } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { RequirePermission } from "@/features/auth/permissions";
import {
  useCancelTask,
  useCompleteTask,
  useConfirmArrival,
  useReportIssue,
  useRequiredPhotos,
  useStartTask,
  useTask,
  useUpdateChecklist,
} from "@/features/stays/hooks";
import { fileUrl, TASK_STATUS_LABELS, type ChecklistItem, type IssueKind } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

const STEPS = ["pending", "arrived", "in_progress", "completed"] as const;
const ISSUE_LABELS: Record<IssueKind, string> = {
  problem: "Problema en la unidad",
  missing_supplies: "Faltan insumos",
  guests_not_out: "Huéspedes aún no salen",
};
const LUGGAGE = { none: "Sin indicación", leave: "Dejar equipaje", collect: "Recoger equipaje" } as const;

function PhotoUpload({ label, onSubmit, pending, hint }: { label: string; onSubmit: (files: File[]) => void; pending: boolean; hint?: string }) {
  const [files, setFiles] = useState<File[]>([]);
  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(files);
      }}
    >
      <div className="space-y-1.5">
        <Label htmlFor={`photos-${label}`}>Fotos (mínimo 1)</Label>
        <Input
          id={`photos-${label}`}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          multiple
          onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
        />
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      <Button type="submit" disabled={files.length === 0 || pending} className="w-full sm:w-auto">
        {pending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Camera className="mr-2 h-4 w-4" />} {label}
      </Button>
    </form>
  );
}

function Gallery({ title, photos }: { title: string; photos: string[] }) {
  if (!photos.length) return null;
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{title}</p>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {photos.map((p) => (
          <a key={p} href={fileUrl(p)} target="_blank" rel="noreferrer" className="block aspect-square overflow-hidden rounded-lg border">
            <img src={fileUrl(p)} alt={title} loading="lazy" className="h-full w-full object-cover" />
          </a>
        ))}
      </div>
    </div>
  );
}

export default function TaskDetail() {
  const { id = "" } = useParams();
  const { data: task, isLoading, error, refetch } = useTask(id);
  const required = useRequiredPhotos(id, "standard");
  const arrival = useConfirmArrival();
  const start = useStartTask();
  const checklist = useUpdateChecklist();
  const issue = useReportIssue();
  const complete = useCompleteTask();
  const cancel = useCancelTask();
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [issueKind, setIssueKind] = useState<IssueKind>("problem");
  const [issueText, setIssueText] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (task) setItems(task.checklist);
  }, [task]);

  if (isLoading) return <PageSkeleton />;
  if (error || !task) return <ErrorState error={error} onRetry={() => refetch()} />;

  const stepIndex = task.status === "cancelled" ? -1 : STEPS.indexOf(task.status as (typeof STEPS)[number]);
  const allDone = items.length > 0 && items.every((i) => i.done);
  const active = task.status !== "completed" && task.status !== "cancelled";

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={ROUTES.APP.STAYS_TASKS}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Tareas
        </Link>
      </Button>
      <PageHeader
        title={task.property_name}
        description={`${fmtDateTime(task.scheduled_at)} · ${task.staff_name ?? "Sin asignar"}`}
        icon={MapPinCheck}
        accent="mint"
        actions={<StatusBadge tone={TASK_TONE[task.status]}>{TASK_STATUS_LABELS[task.status]}</StatusBadge>}
      />

      {stepIndex >= 0 && (
        <ol className="grid grid-cols-4 gap-2" aria-label="Progreso de la tarea">
          {STEPS.map((s, i) => (
            <li key={s} className="space-y-1.5">
              <div className={cn("h-1.5 rounded-full", i <= stepIndex ? "bg-heavy-mint" : "bg-elevated")} />
              <p className={cn("text-xs", i <= stepIndex ? "text-foreground" : "text-muted-foreground")}>{TASK_STATUS_LABELS[s]}</p>
            </li>
          ))}
        </ol>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <RequirePermission permission={PERMISSIONS.TASKS_EXECUTE}>
            {task.status === "pending" && (
              <Section title="1. Confirmar llegada" description="Toma fotos del estado inicial de la unidad.">
                <PhotoUpload
                  label="Confirmar llegada"
                  pending={arrival.isPending}
                  hint={required.data ? `Fotos sugeridas: ${required.data.items.join(", ")}` : undefined}
                  onSubmit={(photos) => arrival.mutate({ id, photos })}
                />
              </Section>
            )}
            {task.status === "arrived" && (
              <Section title="2. Iniciar limpieza">
                <Button onClick={() => start.mutate(id)} disabled={start.isPending}>
                  {start.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />} Iniciar
                </Button>
              </Section>
            )}
            {task.status === "in_progress" && (
              <>
                <Section title="3. Checklist" description="Todos los ítems son obligatorios para finalizar.">
                  <ul className="space-y-2">
                    {items.map((it, idx) => (
                      <li key={it.item}>
                        <label className="flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm">
                          <Checkbox
                            checked={it.done}
                            onCheckedChange={(v) => {
                              const next = items.map((x, j) => (j === idx ? { ...x, done: v === true } : x));
                              setItems(next);
                              checklist.mutate({ id, items: next });
                            }}
                          />
                          <span className={cn(it.done && "text-muted-foreground line-through")}>{it.item}</span>
                        </label>
                      </li>
                    ))}
                  </ul>
                </Section>
                <Section title="4. Finalizar" description="Fotos del resultado final.">
                  {!allDone && items.length > 0 ? (
                    <p className="text-sm text-muted-foreground">Completa el checklist para habilitar la finalización.</p>
                  ) : (
                    <PhotoUpload label="Completar tarea" pending={complete.isPending} onSubmit={(photos) => complete.mutate({ id, photos })} />
                  )}
                </Section>
              </>
            )}
            {active && (
              <Section title="Reportar novedad" description="Se notifica al supervisor de inmediato.">
                <form
                  className="space-y-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    issue.mutate({ id, kind: issueKind, description: issueText }, { onSuccess: () => setIssueText("") });
                  }}
                >
                  <Select value={issueKind} onValueChange={(v) => setIssueKind(v as IssueKind)}>
                    <SelectTrigger aria-label="Tipo de novedad">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(Object.keys(ISSUE_LABELS) as IssueKind[]).map((k) => (
                        <SelectItem key={k} value={k}>
                          {ISSUE_LABELS[k]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Textarea required placeholder="Describe la novedad…" value={issueText} onChange={(e) => setIssueText(e.target.value)} />
                  <Button type="submit" variant="outline" disabled={!issueText || issue.isPending}>
                    <AlertTriangle className="mr-2 h-4 w-4 text-heavy-ember" /> Reportar
                  </Button>
                </form>
              </Section>
            )}
          </RequirePermission>

          {task.status === "completed" && (
            <Section>
              <p className="flex items-center gap-2 font-medium text-heavy-mint">
                <CheckCircle2 className="h-5 w-5" /> Completada {fmtDateTime(task.completed_at)}
              </p>
            </Section>
          )}

          {(task.initial_photos.length > 0 || task.final_photos.length > 0) && (
            <Section title="Evidencias">
              <div className="space-y-5">
                <Gallery title="Llegada" photos={task.initial_photos} />
                <Gallery title="Resultado final" photos={task.final_photos} />
              </div>
            </Section>
          )}
        </div>

        <div className="space-y-6">
          <Section title="Detalle">
            <dl className="space-y-3 text-sm">
              {[
                ["Equipaje", LUGGAGE[task.luggage]],
                ["Insumos", task.supplies_required ? "Requeridos" : "No"],
                ["Llegada", fmtDateTime(task.arrival_confirmed_at)],
                ["Inicio", fmtDateTime(task.started_at)],
                ["Fin", fmtDateTime(task.completed_at)],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="text-right font-medium">{v}</dd>
                </div>
              ))}
            </dl>
            {task.observations && <p className="mt-4 rounded-lg bg-elevated/60 p-3 text-sm">{task.observations}</p>}
          </Section>
          {task.issues.length > 0 && (
            <Section title="Novedades">
              <ul className="space-y-3 text-sm">
                {task.issues.map((i) => (
                  <li key={i.reported_at} className="rounded-lg border border-heavy-ember/30 bg-heavy-ember/5 p-3">
                    <p className="font-medium">{ISSUE_LABELS[i.kind]}</p>
                    <p className="text-muted-foreground">{i.description}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{fmtDateTime(i.reported_at)}</p>
                  </li>
                ))}
              </ul>
            </Section>
          )}
          {task.status === "pending" && (
            <RequirePermission permission={PERMISSIONS.TASKS_MANAGE}>
              <Section title="Cancelar tarea">
                <div className="space-y-3">
                  <Input placeholder="Motivo" value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Motivo de cancelación" />
                  <Button variant="destructive" disabled={!reason || cancel.isPending} onClick={() => cancel.mutate({ id, reason })}>
                    <XCircle className="mr-2 h-4 w-4" /> Cancelar
                  </Button>
                </div>
              </Section>
            </RequirePermission>
          )}
        </div>
      </div>
    </div>
  );
}
