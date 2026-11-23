import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, CalendarCheck2, Clock, LayoutDashboard, Plus, Timer } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState, ErrorState } from "@/components/common/States";
import { PageSkeleton } from "@/components/common/Loaders";
import { ChartBox, CHART_COLORS, axisProps, tooltipProps } from "@/components/common/charts";
import { StatusBadge, TASK_TONE } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { RequirePermission } from "@/features/auth/permissions";
import { useStaysDashboard } from "@/features/stays/hooks";
import { TASK_STATUS_LABELS } from "@/lib/api";
import { fmtDateTime, fmtNumber, fmtPercent } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { ROUTES } from "@/lib/routes";

export default function StaysDashboard() {
  const { data, isLoading, error, refetch } = useStaysDashboard();
  if (isLoading) return <PageSkeleton />;

  const chart = data
    ? [
        { name: "Pendientes", value: data.today.pending, color: CHART_COLORS.axis },
        { name: "En progreso", value: data.today.in_progress, color: CHART_COLORS.ember },
        { name: "Completadas", value: data.today.completed, color: CHART_COLORS.mint },
        { name: "Canceladas", value: data.today.cancelled, color: CHART_COLORS.rose },
      ]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operación · Stays"
        description="Limpiezas, puntualidad y desempeño del personal en tiempo real."
        icon={LayoutDashboard}
        accent="mint"
        actions={
          <RequirePermission permission={PERMISSIONS.TASKS_MANAGE}>
            <Button asChild>
              <Link to={`${ROUTES.APP.STAYS_TASKS}?nueva=1`}>
                <Plus className="mr-1 h-4 w-4" /> Programar limpieza
              </Link>
            </Button>
          </RequirePermission>
        }
      />
      {error || !data ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Tareas de hoy" value={fmtNumber(data.today.total)} hint={`${data.today.completed} completadas`} icon={CalendarCheck2} tone="mint" />
            <StatCard label="A tiempo (7 días)" value={fmtPercent(data.week.on_time_rate)} icon={Clock} tone="cyan" />
            <StatCard label="Duración promedio" value={`${Math.round(data.week.avg_cleaning_minutes)} min`} icon={Timer} tone="primary" />
            <StatCard label="Novedades (7 días)" value={fmtNumber(data.week.issues)} icon={AlertTriangle} tone={data.week.issues ? "rose" : "mint"} />
          </div>

          <div className="grid gap-6 lg:grid-cols-5">
            <Section title="Estado de hoy" className="lg:col-span-2">
              <ChartBox label="Tareas de hoy por estado" height={240}>
                <BarChart data={chart} margin={{ left: -20, right: 8 }}>
                  <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" {...axisProps} />
                  <YAxis allowDecimals={false} {...axisProps} />
                  <Tooltip {...tooltipProps} />
                  <Bar dataKey="value" name="Tareas" radius={[6, 6, 0, 0]}>
                    {chart.map((c) => (
                      <Cell key={c.name} fill={c.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ChartBox>
            </Section>

            <Section title="Próximas limpiezas" className="lg:col-span-3" bodyClassName="p-0">
              {data.upcoming.length === 0 ? (
                <EmptyState className="m-5" icon={CalendarCheck2} title="Sin limpiezas próximas" />
              ) : (
                <ul className="divide-y">
                  {data.upcoming.map((t) => (
                    <li key={t.id}>
                      <Link to={ROUTES.APP.STAYS_TASK(t.id)} className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-elevated/50">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{t.property_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {fmtDateTime(t.scheduled_at)} · {t.staff_name ?? "Sin asignar"}
                          </p>
                        </div>
                        <StatusBadge tone={TASK_TONE[t.status]}>{TASK_STATUS_LABELS[t.status]}</StatusBadge>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          </div>

          <Section title="Ranking del personal" description="Últimos 7 días" bodyClassName="p-0">
            {data.staff_ranking.length === 0 ? (
              <EmptyState className="m-5" title="Aún no hay tareas completadas" />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">#</TableHead>
                      <TableHead>Colaborador</TableHead>
                      <TableHead className="text-right">Completadas</TableHead>
                      <TableHead className="text-right">A tiempo</TableHead>
                      <TableHead className="text-right">Promedio</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.staff_ranking.map((s, i) => (
                      <TableRow key={s.staff_id}>
                        <TableCell className="font-semibold text-heavy-ember">{i + 1}</TableCell>
                        <TableCell className="font-medium">{s.name}</TableCell>
                        <TableCell className="text-right">{s.completed}</TableCell>
                        <TableCell className="text-right">{fmtPercent(s.on_time_rate)}</TableCell>
                        <TableCell className="text-right">{Math.round(s.avg_minutes)} min</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Section>
        </>
      )}
    </div>
  );
}
