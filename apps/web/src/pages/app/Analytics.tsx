import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, BarChart3, Bot, CheckCircle2, Lightbulb, Loader2, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ChartBox, CHART_COLORS, SERIES, axisProps, tooltipProps } from "@/components/common/charts";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useInsights, useLifecycleFunnel, useOverview, useTimeseries } from "@/features/analytics/hooks";
import { METRIC_LABELS, STAGE_LABELS, type LifecycleStage, type MetricKey } from "@/lib/api";
import { fmtCompact, fmtDate, fmtMoney, fmtMoneyCompact, fmtNumber, fmtPercent } from "@/lib/format";

const MONEY_METRICS: MetricKey[] = ["revenue", "ad_spend"];

export default function Analytics() {
  const [days, setDays] = useState(30);
  const [metric, setMetric] = useState<MetricKey>("leads_captured");
  const overview = useOverview(days);
  const series = useTimeseries(metric, days);
  const funnel = useLifecycleFunnel();
  const insights = useInsights();
  const o = overview.data;
  const money = MONEY_METRICS.includes(metric);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analítica"
        description="Una sola verdad para operación, ventas, marketing y growth."
        icon={BarChart3}
        accent="cyan"
        actions={
          <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
            <SelectTrigger className="w-40" aria-label="Periodo">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[7, 30, 90, 180].map((d) => (
                <SelectItem key={d} value={String(d)}>
                  Últimos {d} días
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {overview.error ? (
        <ErrorState error={overview.error} onRetry={() => overview.refetch()} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Ingresos" value={fmtMoneyCompact(o?.sales.revenue)} hint={o ? `${o.sales.deals_won} negocios · cierre ${fmtPercent(o.sales.win_rate)}` : undefined} tone="mint" loading={overview.isLoading} />
          <StatCard label="Leads" value={fmtNumber(o?.marketing.leads_captured)} hint={o ? `CPL ${fmtMoney(o.marketing.cpl)} · inversión ${fmtMoney(o.marketing.ad_spend)}` : undefined} tone="meta" loading={overview.isLoading} />
          <StatCard label="Operación" value={fmtPercent(o?.operations.on_time_rate)} hint={o ? `${o.operations.tasks_completed} limpiezas · ${Math.round(o.operations.avg_cleaning_minutes)} min prom.` : undefined} tone="cyan" loading={overview.isLoading} />
          <StatCard label="Engagement" value={fmtNumber(o?.marketing.engagement_events)} hint={o ? `${o.marketing.campaigns_launched} campañas · ${fmtCompact(o.gamification.points_awarded)} pts` : undefined} tone="violet" loading={overview.isLoading} />
        </div>
      )}

      <Section
        title="Serie de tiempo"
        actions={
          <Select value={metric} onValueChange={(v) => setMetric(v as MetricKey)}>
            <SelectTrigger className="w-56" aria-label="Métrica">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(METRIC_LABELS) as MetricKey[]).map((m) => (
                <SelectItem key={m} value={m}>
                  {METRIC_LABELS[m]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      >
        {series.isLoading ? (
          <Skeleton className="h-72" />
        ) : series.error ? (
          <ErrorState error={series.error} onRetry={() => series.refetch()} />
        ) : !series.data?.length ? (
          <EmptyState title="Sin datos en el periodo" />
        ) : (
          <ChartBox label={`${METRIC_LABELS[metric]} por día`} height={300}>
            <AreaChart data={series.data} margin={{ left: -6, right: 8, top: 8 }}>
              <defs>
                <linearGradient id="ts-fill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0" stopColor={CHART_COLORS.cyan} stopOpacity={0.45} />
                  <stop offset="1" stopColor={CHART_COLORS.cyan} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" {...axisProps} tickFormatter={(v) => fmtDate(v, "d MMM")} minTickGap={24} />
              <YAxis {...axisProps} tickFormatter={fmtCompact} />
              <Tooltip {...tooltipProps} labelFormatter={(v) => fmtDate(v)} formatter={(v: number) => [money ? fmtMoney(v) : fmtNumber(v), METRIC_LABELS[metric]]} />
              <Area type="monotone" dataKey="value" stroke={CHART_COLORS.cyan} strokeWidth={2} fill="url(#ts-fill)" />
            </AreaChart>
          </ChartBox>
        )}
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Embudo de ciclo de vida" description="Contactos por etapa">
          {funnel.isLoading ? (
            <Skeleton className="h-64" />
          ) : funnel.error ? (
            <ErrorState error={funnel.error} />
          ) : !funnel.data?.length ? (
            <EmptyState title="Sin contactos aún" />
          ) : (
            <ChartBox label="Contactos por etapa del ciclo de vida" height={280}>
              <BarChart data={funnel.data.map((f) => ({ ...f, label: STAGE_LABELS[f.stage as LifecycleStage] ?? f.stage }))} layout="vertical" margin={{ left: 10, right: 16 }}>
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" {...axisProps} allowDecimals={false} />
                <YAxis type="category" dataKey="label" {...axisProps} width={96} />
                <Tooltip {...tooltipProps} />
                <Bar dataKey="count" name="Contactos" radius={[0, 6, 6, 0]}>
                  {funnel.data.map((f, i) => (
                    <Cell key={f.stage} fill={SERIES[i % SERIES.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ChartBox>
          )}
        </Section>

        <Section
          title="Insights con IA"
          description="Resumen ejecutivo, riesgos y recomendaciones"
          actions={
            <Button size="sm" onClick={() => insights.mutate(days)} disabled={insights.isPending} className="bg-gradient-volt text-white">
              {insights.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Sparkles className="mr-1 h-4 w-4" />} Generar
            </Button>
          }
        >
          {!insights.data ? (
            <EmptyState icon={Bot} title="Pídele al analista IA" description={`Interpreta los últimos ${days} días y sugiere qué hacer.`} />
          ) : (
            <div className="space-y-5 text-sm">
              <p className="leading-relaxed">{insights.data.summary}</p>
              {[
                { title: "Highlights", items: insights.data.highlights, icon: CheckCircle2, cls: "text-heavy-mint" },
                { title: "Riesgos", items: insights.data.risks, icon: AlertTriangle, cls: "text-heavy-rose" },
                { title: "Recomendaciones", items: insights.data.recommendations, icon: Lightbulb, cls: "text-heavy-ember" },
              ].map((g) =>
                g.items.length ? (
                  <div key={g.title}>
                    <p className="mb-2 font-semibold">{g.title}</p>
                    <ul className="space-y-1.5">
                      {g.items.map((i) => (
                        <li key={i} className="flex gap-2">
                          <g.icon className={`mt-0.5 h-4 w-4 shrink-0 ${g.cls}`} aria-hidden /> {i}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null,
              )}
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}
