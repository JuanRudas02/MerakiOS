import { useState } from "react";
import { Area, AreaChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { AlertOctagon, AlertTriangle, Info, Link2, Loader2, MousePointerClick, RefreshCcw, Send, Target, UserPlus, Wallet } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { ChartBox, CHART_COLORS, axisProps, tooltipProps } from "@/components/common/charts";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useConnectMeta, useMetaAlerts, useMetaCampaigns, useMetaConnection, useMetaDaily, useSyncMeta, useTestLead } from "@/features/meta/hooks";
import { fmtCompact, fmtDate, fmtMoney, fmtMoneyCompact, fmtNumber, fmtPercent, fmtRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

function ConnectionForm({ initial }: { initial?: { ad_account_id: string | null; page_id: string | null; pixel_id: string | null } }) {
  const connect = useConnectMeta();
  const [form, setForm] = useState({
    ad_account_id: initial?.ad_account_id ?? "",
    page_id: initial?.page_id ?? "",
    pixel_id: initial?.pixel_id ?? "",
    access_token: "",
  });
  return (
    <form
      className="grid gap-4 sm:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        connect.mutate(
          { ad_account_id: form.ad_account_id, page_id: form.page_id || undefined, pixel_id: form.pixel_id || undefined, access_token: form.access_token },
          { onSuccess: () => setForm((f) => ({ ...f, access_token: "" })) },
        );
      }}
    >
      <div className="space-y-1.5">
        <Label htmlFor="m-acc">ID de cuenta publicitaria</Label>
        <Input id="m-acc" required placeholder="act_1234567890" value={form.ad_account_id} onChange={(e) => setForm({ ...form, ad_account_id: e.target.value })} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="m-page">ID de página</Label>
        <Input id="m-page" value={form.page_id} onChange={(e) => setForm({ ...form, page_id: e.target.value })} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="m-pixel">ID de píxel / dataset</Label>
        <Input id="m-pixel" value={form.pixel_id} onChange={(e) => setForm({ ...form, pixel_id: e.target.value })} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="m-token">Token de acceso (usuario del sistema)</Label>
        <Input id="m-token" type="password" required autoComplete="off" value={form.access_token} onChange={(e) => setForm({ ...form, access_token: e.target.value })} />
        <p className="text-xs text-muted-foreground">Se guarda cifrado y nunca se vuelve a mostrar.</p>
      </div>
      <div className="sm:col-span-2">
        <Button type="submit" disabled={connect.isPending}>
          {connect.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Link2 className="mr-2 h-4 w-4" />} Guardar conexión
        </Button>
      </div>
    </form>
  );
}

function TestLead() {
  const test = useTestLead();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "" });
  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        test.mutate({ full_name: form.full_name, email: form.email || undefined, phone: form.phone || undefined }, { onSuccess: () => setForm({ full_name: "", email: "", phone: "" }) });
      }}
    >
      <Input aria-label="Nombre" required placeholder="Nombre completo" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
      <Input aria-label="Email" type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      <Input aria-label="Teléfono" type="tel" placeholder="Teléfono" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
      <Button type="submit" variant="outline" className="w-full" disabled={test.isPending || (!form.email && !form.phone)}>
        <Send className="mr-2 h-4 w-4" /> Enviar lead de prueba
      </Button>
    </form>
  );
}

const SEVERITY = {
  info: { icon: Info, cls: "border-heavy-cyan/30 bg-heavy-cyan/5 text-heavy-cyan" },
  warning: { icon: AlertTriangle, cls: "border-heavy-ember/30 bg-heavy-ember/5 text-heavy-ember" },
  critical: { icon: AlertOctagon, cls: "border-heavy-rose/30 bg-heavy-rose/5 text-heavy-rose" },
} as const;

export default function Meta() {
  const [days, setDays] = useState(30);
  const connection = useMetaConnection();
  const connected = !!connection.data?.connected;
  const campaigns = useMetaCampaigns(days, connected);
  const daily = useMetaDaily(days, connected);
  const alerts = useMetaAlerts(connected);
  const sync = useSyncMeta();
  const t = campaigns.data?.totals;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Meta Business"
        description={
          connected
            ? `Cuenta ${connection.data?.ad_account_id} · ${connection.data?.last_sync_at ? `sincronizada ${fmtRelative(connection.data.last_sync_at)}` : "sin sincronizar"}`
            : "Conecta tu cuenta publicitaria para ver campañas, leads y alertas."
        }
        icon={Target}
        accent="meta"
        actions={
          connected && (
            <>
              <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
                <SelectTrigger className="w-36" aria-label="Periodo">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[7, 14, 30, 90].map((d) => (
                    <SelectItem key={d} value={String(d)}>
                      Últimos {d} días
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={() => sync.mutate()} disabled={sync.isPending}>
                {sync.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCcw className="mr-2 h-4 w-4" />} Sincronizar
              </Button>
            </>
          )
        }
      />

      {connection.isLoading ? (
        <Skeleton className="h-40" />
      ) : connection.error ? (
        <ErrorState error={connection.error} onRetry={() => connection.refetch()} />
      ) : !connected ? (
        <Section title="Conectar cuenta publicitaria" description="Requiere un token de usuario del sistema con permisos ads_read y leads_retrieval.">
          <ConnectionForm />
        </Section>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Inversión" value={fmtMoneyCompact(t?.spend)} icon={Wallet} tone="meta" loading={campaigns.isLoading} />
            <StatCard label="Leads" value={fmtNumber(t?.leads)} hint={t ? `CPL ${fmtMoney(t.cpl)}` : undefined} icon={UserPlus} tone="primary" loading={campaigns.isLoading} />
            <StatCard label="CTR" value={fmtPercent((t?.ctr ?? 0) / 100, 2)} hint={t ? `CPC ${fmtMoney(t.cpc)}` : undefined} icon={MousePointerClick} tone="cyan" loading={campaigns.isLoading} />
            <StatCard label="ROAS" value={`${(t?.roas ?? 0).toFixed(2)}x`} hint={t ? `${fmtCompact(t.impressions)} impresiones` : undefined} icon={Target} tone="mint" loading={campaigns.isLoading} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Section title="Rendimiento diario" className="lg:col-span-2">
              {daily.isLoading ? (
                <Skeleton className="h-64" />
              ) : daily.error ? (
                <ErrorState error={daily.error} />
              ) : !daily.data?.length ? (
                <EmptyState title="Sin datos" description="Sincroniza para traer insights." />
              ) : (
                <ChartBox label="Inversión y leads por día">
                  <AreaChart data={daily.data} margin={{ left: -10, right: 8, top: 8 }}>
                    <defs>
                      <linearGradient id="meta-spend" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0" stopColor={CHART_COLORS.meta} stopOpacity={0.4} />
                        <stop offset="1" stopColor={CHART_COLORS.meta} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" {...axisProps} tickFormatter={(v) => fmtDate(v, "d MMM")} minTickGap={24} />
                    <YAxis yAxisId="spend" {...axisProps} tickFormatter={fmtCompact} />
                    <YAxis yAxisId="leads" orientation="right" {...axisProps} />
                    <Tooltip {...tooltipProps} labelFormatter={(v) => fmtDate(v)} />
                    <Area yAxisId="spend" type="monotone" dataKey="spend" name="Inversión" stroke={CHART_COLORS.meta} fill="url(#meta-spend)" strokeWidth={2} />
                    <Area yAxisId="leads" type="monotone" dataKey="leads" name="Leads" stroke={CHART_COLORS.cyan} fill="transparent" strokeWidth={2} />
                  </AreaChart>
                </ChartBox>
              )}
            </Section>
            <div className="space-y-6">
              <Section title="Alertas de rendimiento">
                {alerts.isLoading ? (
                  <ListSkeleton rows={2} />
                ) : !alerts.data?.length ? (
                  <p className="text-sm text-muted-foreground">Todo en orden. Sin anomalías detectadas.</p>
                ) : (
                  <ul className="space-y-2">
                    {alerts.data.slice(0, 6).map((a) => {
                      const sev = SEVERITY[a.severity];
                      return (
                        <li key={a.id} className={cn("flex gap-2 rounded-lg border p-3 text-sm", sev.cls)}>
                          <sev.icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                          <div className="text-foreground">
                            <p>{a.message}</p>
                            <p className="text-xs text-muted-foreground">
                              {a.campaign_ref} · {fmtRelative(a.created_at)}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </Section>
              <Section title="Probar Lead Ads → CRM">
                <TestLead />
              </Section>
            </div>
          </div>

          <Section title="Campañas" bodyClassName="p-0">
            {campaigns.isLoading ? (
              <div className="p-5">
                <ListSkeleton />
              </div>
            ) : campaigns.error ? (
              <ErrorState className="m-5" error={campaigns.error} />
            ) : !campaigns.data?.items.length ? (
              <EmptyState className="m-5" title="Sin campañas en el periodo" />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Campaña</TableHead>
                      <TableHead className="text-right">Inversión</TableHead>
                      <TableHead className="text-right">Impr.</TableHead>
                      <TableHead className="text-right">CTR</TableHead>
                      <TableHead className="text-right">CPC</TableHead>
                      <TableHead className="text-right">Leads</TableHead>
                      <TableHead className="text-right">CPL</TableHead>
                      <TableHead className="text-right">ROAS</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {campaigns.data.items.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell>
                          <p className="font-medium">{c.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {c.objective} · {c.status}
                          </p>
                        </TableCell>
                        <TableCell className="text-right">{fmtMoney(c.spend)}</TableCell>
                        <TableCell className="text-right">{fmtCompact(c.impressions)}</TableCell>
                        <TableCell className="text-right">{c.ctr.toFixed(2)}%</TableCell>
                        <TableCell className="text-right">{fmtMoney(c.cpc)}</TableCell>
                        <TableCell className="text-right">{fmtNumber(c.leads)}</TableCell>
                        <TableCell className="text-right">{fmtMoney(c.cpl)}</TableCell>
                        <TableCell className="text-right">{c.roas.toFixed(2)}x</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Section>

          <Card className="p-5">
            <details>
              <summary className="cursor-pointer text-sm font-medium">Actualizar credenciales</summary>
              <div className="mt-4">
                <ConnectionForm initial={connection.data} />
              </div>
            </details>
          </Card>
        </>
      )}
    </div>
  );
}
