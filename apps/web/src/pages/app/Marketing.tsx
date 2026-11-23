import { useState } from "react";
import sanitizeHtml from "@/lib/sanitize";
import { Bot, CalendarRange, CheckCircle2, CircleDashed, Loader2, Mail, Megaphone, Plus, RefreshCcw, Rocket, Send, Users } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  useCampaigns,
  useCreateSegment,
  useEmails,
  useGenerateEmail,
  useLaunchCampaign,
  useMarketingStatus,
  usePlanCampaign,
  usePushEmail,
  useSegments,
  useSyncSegment,
} from "@/features/marketing/hooks";
import { STAGE_LABELS, type EmailDraft, type LifecycleStage } from "@/lib/api";
import { fmtDate, fmtNumber, fmtRelative } from "@/lib/format";

const NONE = "none";

function SegmentsTab() {
  const segments = useSegments();
  const create = useCreateSegment();
  const sync = useSyncSegment();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", stage: NONE, tags: "", min_score: "" });
  return (
    <Section
      title="Segmentos"
      description="Audiencias construidas con datos del CRM y sincronizadas con Mautic."
      actions={
        <Button size="sm" onClick={() => setOpen(true)}>
          <Plus className="mr-1 h-4 w-4" /> Segmento
        </Button>
      }
    >
      {segments.isLoading ? (
        <ListSkeleton />
      ) : segments.error ? (
        <ErrorState error={segments.error} onRetry={() => segments.refetch()} />
      ) : !segments.data?.length ? (
        <EmptyState icon={Users} title="Sin segmentos" description="Crea tu primera audiencia por etapa, etiquetas o score." />
      ) : (
        <ul className="divide-y">
          {segments.data.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div>
                <p className="font-medium">{s.name}</p>
                <p className="text-xs text-muted-foreground">
                  {fmtNumber(s.contacts_count)} contactos · {s.synced_at ? `Sincronizado ${fmtRelative(s.synced_at)}` : "No sincronizado"}
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={() => sync.mutate(s.id)} disabled={sync.isPending && sync.variables === s.id}>
                <RefreshCcw className="mr-1 h-3.5 w-3.5" /> Sincronizar
              </Button>
            </li>
          ))}
        </ul>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuevo segmento</DialogTitle>
          </DialogHeader>
          <form
            id="segment-form"
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate(
                {
                  name: form.name,
                  description: form.description || undefined,
                  filters: {
                    stages: form.stage === NONE ? undefined : [form.stage as LifecycleStage],
                    tags: form.tags ? form.tags.split(",").map((t) => t.trim()).filter(Boolean) : undefined,
                    min_score: form.min_score ? Number(form.min_score) : undefined,
                  },
                },
                { onSuccess: () => setOpen(false) },
              );
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="sg-name">Nombre</Label>
              <Input id="sg-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sg-desc">Descripción</Label>
              <Input id="sg-desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Etapa</Label>
                <Select value={form.stage} onValueChange={(v) => setForm({ ...form, stage: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>Cualquiera</SelectItem>
                    {(Object.keys(STAGE_LABELS) as LifecycleStage[]).map((s) => (
                      <SelectItem key={s} value={s}>
                        {STAGE_LABELS[s]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sg-score">Score mínimo</Label>
                <Input id="sg-score" type="number" min={0} max={100} value={form.min_score} onChange={(e) => setForm({ ...form, min_score: e.target.value })} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sg-tags">Etiquetas (coma)</Label>
              <Input id="sg-tags" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="segment-form" disabled={create.isPending}>
              {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Crear
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Section>
  );
}

function EmailPreview({ email }: { email: EmailDraft }) {
  return (
    <Card className="overflow-hidden">
      <div className="space-y-1 border-b bg-elevated/50 p-4">
        <p className="text-xs text-muted-foreground">Asunto</p>
        <p className="font-semibold">{email.subject}</p>
        <p className="text-xs text-muted-foreground">{email.preheader}</p>
      </div>
      <iframe
        title={`Vista previa: ${email.subject}`}
        sandbox=""
        srcDoc={sanitizeHtml(email.body_html)}
        className="h-80 w-full bg-white"
      />
    </Card>
  );
}

function EmailsTab() {
  const segments = useSegments();
  const emails = useEmails();
  const generate = useGenerateEmail();
  const push = usePushEmail();
  const [form, setForm] = useState({ goal: "", audience: "", tone: "cercano y profesional", segment_id: NONE });
  const [preview, setPreview] = useState<EmailDraft | null>(null);
  const shown = preview ?? generate.data ?? null;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Section title="Generador de emails con IA" description="Describe el objetivo y la audiencia; la IA redacta asunto, preheader y cuerpo.">
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            generate.mutate(
              { goal: form.goal, audience: form.audience, tone: form.tone, language: "es", segment_id: form.segment_id === NONE ? null : form.segment_id },
              { onSuccess: (d) => setPreview(d) },
            );
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="e-goal">Objetivo</Label>
            <Textarea id="e-goal" required rows={2} placeholder="Ej.: invitar a propietarios a una demo del reporte mensual" value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="e-aud">Audiencia</Label>
            <Input id="e-aud" required placeholder="Propietarios de apartamentos en Medellín" value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="e-tone">Tono</Label>
              <Input id="e-tone" value={form.tone} onChange={(e) => setForm({ ...form, tone: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Segmento</Label>
              <Select value={form.segment_id} onValueChange={(v) => setForm({ ...form, segment_id: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>Ninguno</SelectItem>
                  {segments.data?.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button type="submit" disabled={generate.isPending} className="bg-heavy-violet text-white hover:bg-heavy-violet/90">
            {generate.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Bot className="mr-2 h-4 w-4" />} Generar con IA
          </Button>
        </form>
        {shown && (
          <div className="mt-6 space-y-3">
            <EmailPreview email={shown} />
            {shown.status === "draft" && (
              <Button variant="outline" onClick={() => push.mutate(shown.id, { onSuccess: (d) => setPreview(d) })} disabled={push.isPending}>
                {push.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />} Enviar a Mautic
              </Button>
            )}
          </div>
        )}
      </Section>
      <Section title="Borradores" description="Nada se envía sin tu aprobación.">
        {emails.isLoading ? (
          <ListSkeleton />
        ) : emails.error ? (
          <ErrorState error={emails.error} onRetry={() => emails.refetch()} />
        ) : !emails.data?.length ? (
          <EmptyState icon={Mail} title="Sin emails" description="Genera tu primer email con IA." />
        ) : (
          <ul className="divide-y">
            {emails.data.map((m) => (
              <li key={m.id}>
                <button className="flex w-full items-center justify-between gap-3 py-3 text-left hover:opacity-80" onClick={() => setPreview(m)}>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{m.subject}</p>
                    <p className="text-xs text-muted-foreground">{fmtDate(m.created_at)}</p>
                  </div>
                  <StatusBadge tone={m.status === "draft" ? "neutral" : m.status === "pushed" ? "violet" : "success"}>
                    {{ draft: "Borrador", pushed: "En Mautic", sent: "Enviado" }[m.status]}
                  </StatusBadge>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}

function CampaignsTab() {
  const segments = useSegments();
  const campaigns = useCampaigns();
  const plan = usePlanCampaign();
  const launch = useLaunchCampaign();
  const [form, setForm] = useState({ objective: "", segment_id: NONE, duration_days: 14 });
  return (
    <div className="space-y-6">
      <Section title="Planificador de campañas con IA" description="La IA propone una secuencia multicanal día a día.">
        <form
          className="grid gap-4 sm:grid-cols-[1fr_200px_140px_auto] sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            plan.mutate({ objective: form.objective, segment_id: form.segment_id === NONE ? null : form.segment_id, duration_days: form.duration_days });
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="cp-obj">Objetivo</Label>
            <Input id="cp-obj" required value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} placeholder="Convertir leads de Meta en demos agendadas" />
          </div>
          <div className="space-y-1.5">
            <Label>Segmento</Label>
            <Select value={form.segment_id} onValueChange={(v) => setForm({ ...form, segment_id: v })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>Todos</SelectItem>
                {segments.data?.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cp-days">Duración (días)</Label>
            <Input id="cp-days" type="number" min={1} max={90} value={form.duration_days} onChange={(e) => setForm({ ...form, duration_days: Number(e.target.value) })} />
          </div>
          <Button type="submit" disabled={plan.isPending} className="bg-heavy-violet text-white hover:bg-heavy-violet/90">
            {plan.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Bot className="mr-2 h-4 w-4" />} Planificar
          </Button>
        </form>
      </Section>
      {campaigns.isLoading ? (
        <ListSkeleton />
      ) : campaigns.error ? (
        <ErrorState error={campaigns.error} onRetry={() => campaigns.refetch()} />
      ) : !campaigns.data?.length ? (
        <EmptyState icon={CalendarRange} title="Sin campañas" description="Planifica tu primera campaña con IA." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {campaigns.data.map((c) => (
            <Card key={c.id} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">{c.name}</h3>
                  <p className="text-sm text-muted-foreground">{c.objective}</p>
                </div>
                <StatusBadge tone={c.status === "active" ? "success" : c.status === "planned" ? "violet" : "neutral"}>
                  {{ planned: "Planificada", active: "Activa", paused: "Pausada", completed: "Finalizada" }[c.status]}
                </StatusBadge>
              </div>
              <ol className="mt-4 space-y-2">
                {c.steps.map((s, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span className="w-14 shrink-0 text-xs font-semibold text-heavy-violet">Día {s.day}</span>
                    <span className="min-w-0">
                      <span className="font-medium">{s.subject}</span>
                      <span className="block text-xs text-muted-foreground">
                        {s.channel.toUpperCase()} · {s.intent}
                      </span>
                    </span>
                  </li>
                ))}
              </ol>
              {c.status === "planned" && (
                <Button className="mt-4" size="sm" onClick={() => launch.mutate(c.id)} disabled={launch.isPending}>
                  <Rocket className="mr-1 h-4 w-4" /> Lanzar
                </Button>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Marketing() {
  const status = useMarketingStatus();
  const s = status.data;
  return (
    <div className="space-y-6">
      <PageHeader title="Marketing · Mautic + IA" description="Segmentos, emails y campañas con un copiloto de IA sobre Mautic open source." icon={Megaphone} accent="violet" />
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Mautic"
          value={s ? (s.connected ? "Conectado" : s.mautic_enabled ? "Sin conexión" : "Desactivado") : "—"}
          icon={s?.connected ? CheckCircle2 : CircleDashed}
          tone={s?.connected ? "mint" : "ember"}
          loading={status.isLoading}
        />
        <StatCard label="Contactos sincronizados" value={fmtNumber(s?.synced_contacts)} icon={Users} tone="violet" loading={status.isLoading} />
        <StatCard label="Última sincronización" value={s?.last_sync_at ? fmtRelative(s.last_sync_at) : "Nunca"} icon={RefreshCcw} tone="cyan" loading={status.isLoading} />
      </div>
      <Tabs defaultValue="emails">
        <TabsList>
          <TabsTrigger value="emails">Emails IA</TabsTrigger>
          <TabsTrigger value="campaigns">Campañas</TabsTrigger>
          <TabsTrigger value="segments">Segmentos</TabsTrigger>
        </TabsList>
        <TabsContent value="emails" className="mt-6">
          <EmailsTab />
        </TabsContent>
        <TabsContent value="campaigns" className="mt-6">
          <CampaignsTab />
        </TabsContent>
        <TabsContent value="segments" className="mt-6">
          <SegmentsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
