import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import {
  ArrowRight,
  Banknote,
  CalendarCheck2,
  Flame,
  Megaphone,
  Sparkles,
  Target,
  Trophy,
  UserPlus,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ChartBox, CHART_COLORS, axisProps, tooltipProps } from "@/components/common/charts";
import { StatusBadge, TASK_TONE } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/AuthProvider";
import { usePermissions } from "@/features/auth/permissions";
import { useOverview, useTimeseries } from "@/features/analytics/hooks";
import { usePlayer, useLeaderboard } from "@/features/gamification/hooks";
import { useTasks } from "@/features/stays/hooks";
import { TASK_STATUS_LABELS } from "@/lib/api";
import { fmtCompact, fmtDate, fmtDateTime, fmtMoney, fmtMoneyCompact, fmtNumber, fmtPercent } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { ROUTES } from "@/lib/routes";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Buenos días" : h < 19 ? "Buenas tardes" : "Buenas noches";
}

function GamificationWidget() {
  const player = usePlayer();
  const board = useLeaderboard("week", "all");
  return (
    <Section
      title="Tu progreso"
      actions={
        <Button variant="ghost" size="sm" asChild>
          <Link to={ROUTES.APP.GAMIFICATION}>
            Ver todo <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </Link>
        </Button>
      }
    >
      {player.isLoading ? (
        <Skeleton className="h-24" />
      ) : player.error ? (
        <ErrorState error={player.error} onRetry={() => player.refetch()} />
      ) : player.data ? (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-gradient-ember font-display text-xl font-bold text-white">
              {player.data.level.number}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-muted-foreground">{player.data.level.name}</p>
              <p className="font-display text-2xl font-bold">{fmtNumber(player.data.points)} pts</p>
              <Progress value={player.data.level.progress * 100} className="mt-2 h-1.5" aria-label="Progreso de nivel" />
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Flame className="h-4 w-4 text-heavy-ember" /> {player.data.streak_days} días de racha
            </span>
            {player.data.rank && (
              <span className="flex items-center gap-1">
                <Trophy className="h-4 w-4 text-heavy-ember" /> #{player.data.rank}
              </span>
            )}
          </div>
          {board.data && board.data.length > 0 && (
            <ol className="space-y-1.5 border-t pt-3">
              {board.data.slice(0, 3).map((e) => (
                <li key={e.user_id} className="flex items-center justify-between text-sm">
                  <span>
                    <span className="mr-2 font-semibold text-heavy-ember">#{e.rank}</span>
                    {e.name}
                  </span>
                  <span className="text-muted-foreground">{fmtNumber(e.points)}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      ) : null}
    </Section>
  );
}

function MyTasks() {
  const today = new Date();
  const from = new Date(today.getFullYear(), today.getMonth(), today.getDate()).toISOString();
  const to = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 2).toISOString();
  const tasks = useTasks({ from, to });
  return (
    <Section title="Mis próximas tareas" description="Hoy y mañana">
      {tasks.isLoading ? (
        <Skeleton className="h-32" />
      ) : tasks.error ? (
        <ErrorState error={tasks.error} onRetry={() => tasks.refetch()} />
      ) : !tasks.data?.length ? (
        <EmptyState icon={CalendarCheck2} title="Sin tareas próximas" description="Te avisaremos por WhatsApp cuando tengas una." />
      ) : (
        <ul className="divide-y">
          {tasks.data.map((t) => (
            <li key={t.id}>
              <Link to={ROUTES.APP.STAYS_TASK(t.id)} className="flex items-center justify-between gap-3 py-3 hover:opacity-80">
                <div>
                  <p className="font-medium">{t.property_name}</p>
                  <p className="text-xs text-muted-foreground">{fmtDateTime(t.scheduled_at)}</p>
                </div>
                <StatusBadge tone={TASK_TONE[t.status]}>{TASK_STATUS_LABELS[t.status]}</StatusBadge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

export default function Home() {
  const { user } = useAuth();
  const { can } = usePermissions();
  const analytics = can(PERMISSIONS.ANALYTICS_READ);
  const overview = useOverview(30, analytics);
  const leads = useTimeseries("leads_captured", 30, analytics);
  const o = overview.data;
  const firstName = user?.name.split(" ")[0] ?? "";

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${greeting()}, ${firstName}`}
        description={o ? `Resumen de los últimos 30 días · ${fmtDate(o.period.from)} – ${fmtDate(o.period.to)}` : "Este es el pulso de tu negocio."}
        actions={
          analytics && (
            <Button variant="outline" asChild>
              <Link to={ROUTES.APP.ANALYTICS}>
                <Sparkles className="mr-2 h-4 w-4 text-heavy-cyan" /> Insights IA
              </Link>
            </Button>
          )
        }
      />

      {analytics && (
        <>
          {overview.error ? (
            <ErrorState error={overview.error} onRetry={() => overview.refetch()} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Leads capturados"
                value={fmtNumber(o?.marketing.leads_captured)}
                hint={o ? `CPL ${fmtMoney(o.marketing.cpl)}` : undefined}
                icon={Target}
                tone="meta"
                loading={overview.isLoading}
              />
              <StatCard
                label="Contactos nuevos"
                value={fmtNumber(o?.sales.new_contacts)}
                hint={o ? `Tasa de cierre ${fmtPercent(o.sales.win_rate)}` : undefined}
                icon={UserPlus}
                tone="primary"
                loading={overview.isLoading}
              />
              <StatCard
                label="Ingresos ganados"
                value={fmtMoneyCompact(o?.sales.revenue)}
                hint={o ? `${fmtNumber(o.sales.deals_won)} negocios` : undefined}
                icon={Banknote}
                tone="mint"
                loading={overview.isLoading}
              />
              <StatCard
                label="Limpiezas a tiempo"
                value={fmtPercent(o?.operations.on_time_rate)}
                hint={o ? `${fmtNumber(o.operations.tasks_completed)} completadas` : undefined}
                icon={CalendarCheck2}
                tone="cyan"
                loading={overview.isLoading}
              />
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-3">
            <Section title="Leads capturados" description="Últimos 30 días" className="lg:col-span-2">
              {leads.isLoading ? (
                <Skeleton className="h-64" />
              ) : leads.error ? (
                <ErrorState error={leads.error} />
              ) : (
                <ChartBox label="Leads capturados por día" height={260}>
                  <AreaChart
                    data={(leads.data ?? []).map((d) => ({ date: d.date, leads: d.value }))}
                    margin={{ left: -16, right: 8, top: 8 }}
                  >
                    <defs>
                      <linearGradient id="home-leads" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0" stopColor={CHART_COLORS.meta} stopOpacity={0.4} />
                        <stop offset="1" stopColor={CHART_COLORS.meta} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" {...axisProps} tickFormatter={(v) => fmtDate(v, "d MMM")} minTickGap={24} />
                    <YAxis {...axisProps} tickFormatter={fmtCompact} />
                    <Tooltip {...tooltipProps} labelFormatter={(v) => fmtDate(v)} />
                    <Area type="monotone" dataKey="leads" name="Leads" stroke={CHART_COLORS.meta} strokeWidth={2} fill="url(#home-leads)" />
                  </AreaChart>
                </ChartBox>
              )}
            </Section>
            <GamificationWidget />
          </div>

          {o && (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard label="Interacciones de marketing" value={fmtNumber(o.marketing.engagement_events)} icon={Megaphone} tone="violet" />
              <StatCard label="Inversión en Meta" value={fmtMoneyCompact(o.marketing.ad_spend)} icon={Target} tone="meta" />
              <StatCard label="Auditorías IA" value={fmtNumber(o.growth.audits_completed)} hint={`${o.growth.funnels_designed} embudos`} icon={Sparkles} tone="violet" />
              <StatCard label="Puntos otorgados" value={fmtCompact(o.gamification.points_awarded)} hint={`${o.gamification.active_players} jugadores activos`} icon={Trophy} tone="ember" />
            </div>
          )}
        </>
      )}

      {!analytics && (
        <div className="grid gap-6 lg:grid-cols-2">
          {can(PERMISSIONS.TASKS_READ) && <MyTasks />}
          {can(PERMISSIONS.GAMIFICATION_READ) && <GamificationWidget />}
          {can(PERMISSIONS.PROPERTIES_READ) && !can(PERMISSIONS.TASKS_READ) && (
            <Section title="Mis propiedades">
              <EmptyState
                title="Consulta tus unidades"
                description="Revisa el estado de tus propiedades y carga comprobantes de servicios."
                action={
                  <Button asChild>
                    <Link to={ROUTES.APP.STAYS_PROPERTIES}>Ver propiedades</Link>
                  </Button>
                }
              />
            </Section>
          )}
        </div>
      )}
    </div>
  );
}
