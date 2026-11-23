import { useEffect, useState } from "react";
import { Bot, ChevronLeft, ChevronRight, Loader2, Mail, MessageSquare, Phone, Plus, Sparkles, Users } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { RequirePermission } from "@/features/auth/permissions";
import {
  useAddActivity,
  useChangeStage,
  useContact,
  useContactInsight,
  useContacts,
  useCreateContact,
  useTimeline,
} from "@/features/crm/hooks";
import { STAGE_LABELS, type ActivityKind, type ContactInput, type LifecycleStage } from "@/lib/api";
import { fmtDateTime, fmtNumber, fmtRelative } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { cn } from "@/lib/utils";

const STAGES = Object.keys(STAGE_LABELS) as LifecycleStage[];
const STAGE_TONE: Record<LifecycleStage, "neutral" | "info" | "success" | "warning" | "danger" | "violet"> = {
  subscriber: "neutral",
  lead: "info",
  mql: "violet",
  sql: "violet",
  opportunity: "warning",
  customer: "success",
  evangelist: "success",
  lost: "danger",
};
const ACTIVITY_LABELS: Record<ActivityKind, string> = {
  note: "Nota",
  call: "Llamada",
  email: "Email",
  whatsapp: "WhatsApp",
  meeting: "Reunión",
  marketing: "Marketing",
  ads: "Anuncios",
  system: "Sistema",
};

function scoreTone(score: number) {
  return score >= 70 ? "text-heavy-rose" : score >= 40 ? "text-heavy-ember" : "text-heavy-cyan";
}

function useDebounced<T>(value: T, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function CreateContactDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const create = useCreateContact();
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", phone: "", company: "", job_title: "", tags: "" });
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const input: ContactInput = {
      first_name: form.first_name,
      last_name: form.last_name || null,
      email: form.email || null,
      phone: form.phone || null,
      company: form.company || null,
      job_title: form.job_title || null,
      source: "manual",
      tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
    };
    create.mutate(input, { onSuccess: () => onOpenChange(false) });
  };
  const field = (k: keyof typeof form, label: string, type = "text") => (
    <div className="space-y-1.5">
      <Label htmlFor={`c-${k}`}>{label}</Label>
      <Input id={`c-${k}`} type={type} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} required={k === "first_name"} />
    </div>
  );
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Nuevo contacto</DialogTitle>
        </DialogHeader>
        <form id="contact-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          {field("first_name", "Nombre")}
          {field("last_name", "Apellido")}
          {field("email", "Email", "email")}
          {field("phone", "Teléfono / WhatsApp", "tel")}
          {field("company", "Empresa")}
          {field("job_title", "Cargo")}
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="c-tags">Etiquetas (separadas por coma)</Label>
            <Input id="c-tags" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="propietario, bogotá" />
          </div>
          {!form.email && !form.phone && <p className="text-xs text-muted-foreground sm:col-span-2">Se requiere email o teléfono.</p>}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button type="submit" form="contact-form" disabled={create.isPending || (!form.email && !form.phone)}>
            {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Crear
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ContactDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const contact = useContact(id);
  const timeline = useTimeline(id);
  const stage = useChangeStage();
  const activity = useAddActivity();
  const insight = useContactInsight();
  const [kind, setKind] = useState<ActivityKind>("note");
  const [summary, setSummary] = useState("");
  const c = contact.data;

  useEffect(() => insight.reset(), [id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Sheet open={!!id} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        {contact.isLoading || !c ? (
          contact.error ? <ErrorState error={contact.error} /> : <ListSkeleton />
        ) : (
          <div className="space-y-6">
            <SheetHeader>
              <SheetTitle className="text-xl">{c.full_name}</SheetTitle>
              <SheetDescription>{[c.job_title, c.company].filter(Boolean).join(" · ") || "Contacto"}</SheetDescription>
            </SheetHeader>
            <div className="space-y-2 text-sm">
              {c.email && (
                <p className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground" /> {c.email}
                </p>
              )}
              {c.phone && (
                <p className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-muted-foreground" /> {c.phone}
                </p>
              )}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {c.tags.map((t) => (
                  <Badge key={t} variant="secondary">
                    {t}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Card className="p-4">
                <p className="text-xs text-muted-foreground">Lead score</p>
                <p className={cn("font-display text-3xl font-bold", scoreTone(c.score))}>{c.score}</p>
                <Progress value={c.score} className="mt-2 h-1.5" aria-label="Lead score" />
              </Card>
              <Card className="space-y-2 p-4">
                <Label className="text-xs text-muted-foreground">Etapa</Label>
                <Select value={c.stage} onValueChange={(v) => stage.mutate({ id: c.id, stage: v as LifecycleStage })}>
                  <SelectTrigger aria-label="Etapa del ciclo de vida">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STAGES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {STAGE_LABELS[s]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Card>
            </div>

            <Card className="border-heavy-cyan/30 bg-heavy-cyan/5 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <Bot className="h-4 w-4 text-heavy-cyan" /> Insight IA
                </p>
                <Button size="sm" variant="outline" onClick={() => insight.mutate(c.id)} disabled={insight.isPending}>
                  {insight.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <Sparkles className="mr-1 h-3.5 w-3.5" />}
                  Analizar
                </Button>
              </div>
              {insight.data && (
                <div className="mt-3 space-y-2 text-sm">
                  <StatusBadge tone={insight.data.temperature === "hot" ? "danger" : insight.data.temperature === "warm" ? "warning" : "info"}>
                    {{ hot: "Caliente", warm: "Tibio", cold: "Frío" }[insight.data.temperature]}
                  </StatusBadge>
                  <p>{insight.data.explanation}</p>
                  <p className="rounded-md bg-background/60 p-2">
                    <span className="font-semibold">Siguiente acción: </span>
                    {insight.data.next_best_action}
                  </p>
                </div>
              )}
            </Card>

            <RequirePermission permission={PERMISSIONS.CONTACTS_MANAGE}>
              <form
                className="space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  activity.mutate({ id: c.id, kind, summary }, { onSuccess: () => setSummary("") });
                }}
              >
                <div className="flex gap-2">
                  <Select value={kind} onValueChange={(v) => setKind(v as ActivityKind)}>
                    <SelectTrigger className="w-36" aria-label="Tipo de actividad">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(["note", "call", "email", "whatsapp", "meeting"] as ActivityKind[]).map((k) => (
                        <SelectItem key={k} value={k}>
                          {ACTIVITY_LABELS[k]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button type="submit" size="sm" className="ml-auto" disabled={!summary || activity.isPending}>
                    Registrar
                  </Button>
                </div>
                <Textarea rows={2} placeholder="¿Qué pasó?" value={summary} onChange={(e) => setSummary(e.target.value)} aria-label="Resumen de actividad" />
              </form>
            </RequirePermission>

            <div>
              <h3 className="mb-3 text-sm font-semibold">Timeline</h3>
              {timeline.isLoading ? (
                <ListSkeleton rows={3} />
              ) : !timeline.data?.length ? (
                <p className="text-sm text-muted-foreground">Sin actividad aún.</p>
              ) : (
                <ol className="relative space-y-4 border-l pl-5">
                  {timeline.data.map((a) => (
                    <li key={a.id} className="relative">
                      <span className="absolute -left-[25px] top-1 h-2.5 w-2.5 rounded-full bg-heavy-blue ring-4 ring-background" />
                      <p className="text-xs text-muted-foreground">
                        {ACTIVITY_LABELS[a.kind]} · {fmtDateTime(a.occurred_at)}
                      </p>
                      <p className="text-sm">{a.summary}</p>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

export default function Contacts() {
  const [q, setQ] = useState("");
  const [stage, setStage] = useState<LifecycleStage | "all">("all");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const debounced = useDebounced(q);
  const size = 25;
  const { data, isLoading, error, refetch, isFetching } = useContacts({
    q: debounced || undefined,
    stage: stage === "all" ? undefined : stage,
    page,
    size,
  });
  const pages = data ? Math.max(1, Math.ceil(data.total / size)) : 1;

  useEffect(() => setPage(1), [debounced, stage]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Contactos"
        description="Todos tus leads y clientes, con su ciclo de vida, score y actividad."
        icon={Users}
        accent="primary"
        actions={
          <RequirePermission permission={PERMISSIONS.CONTACTS_MANAGE}>
            <Button onClick={() => setCreating(true)}>
              <Plus className="mr-1 h-4 w-4" /> Nuevo contacto
            </Button>
          </RequirePermission>
        }
      />
      <div className="flex flex-col gap-3 sm:flex-row">
        <Input placeholder="Buscar por nombre, email, teléfono o empresa…" value={q} onChange={(e) => setQ(e.target.value)} className="sm:max-w-sm" aria-label="Buscar contactos" />
        <Select value={stage} onValueChange={(v) => setStage(v as LifecycleStage | "all")}>
          <SelectTrigger className="sm:w-48" aria-label="Filtrar por etapa">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las etapas</SelectItem>
            {STAGES.map((s) => (
              <SelectItem key={s} value={s}>
                {STAGE_LABELS[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {data && <p className="self-center text-sm text-muted-foreground sm:ml-auto">{fmtNumber(data.total)} contactos</p>}
      </div>

      {isLoading ? (
        <ListSkeleton rows={8} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.items.length ? (
        <EmptyState icon={Users} title="Sin contactos" description="Crea contactos manualmente, conecta Meta Lead Ads o impórtalos." />
      ) : (
        <Card className={cn("overflow-hidden", isFetching && "opacity-70")}>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Contacto</TableHead>
                  <TableHead className="hidden md:table-cell">Empresa</TableHead>
                  <TableHead>Etapa</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead className="hidden text-right lg:table-cell">Última actividad</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((c) => (
                  <TableRow key={c.id} className="cursor-pointer" onClick={() => setSelected(c.id)}>
                    <TableCell>
                      <button className="text-left" onClick={() => setSelected(c.id)}>
                        <p className="font-medium">{c.full_name}</p>
                        <p className="flex items-center gap-1 text-xs text-muted-foreground">
                          {c.email ? <Mail className="h-3 w-3" /> : <MessageSquare className="h-3 w-3" />} {c.email ?? c.phone}
                        </p>
                      </button>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">{c.company ?? "—"}</TableCell>
                    <TableCell>
                      <StatusBadge tone={STAGE_TONE[c.stage]}>{STAGE_LABELS[c.stage]}</StatusBadge>
                    </TableCell>
                    <TableCell className={cn("text-right font-semibold", scoreTone(c.score))}>{c.score}</TableCell>
                    <TableCell className="hidden text-right text-sm text-muted-foreground lg:table-cell">{fmtRelative(c.last_activity_at ?? c.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
            <span className="text-muted-foreground">
              Página {page} de {pages}
            </span>
            <div className="flex gap-1">
              <Button variant="outline" size="icon" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Anterior">
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" disabled={page >= pages} onClick={() => setPage(page + 1)} aria-label="Siguiente">
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </Card>
      )}
      {creating && <CreateContactDialog open onOpenChange={setCreating} />}
      <ContactDrawer id={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
