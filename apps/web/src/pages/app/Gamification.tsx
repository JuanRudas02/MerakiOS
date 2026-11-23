import { useState } from "react";
import { Award, Crown, Flame, Gamepad2, Loader2, Medal, Plus, Sparkles, Target, Trophy, Zap } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { RequirePermission } from "@/features/auth/permissions";
import { useAuth } from "@/features/auth/AuthProvider";
import { useBadges, useChallenges, useCreateChallenge, useFeed, useLeaderboard, usePlayer, useRules, useUpdateRule } from "@/features/gamification/hooks";
import type { Period, Team } from "@/lib/api";
import { fmtDate, fmtNumber, fmtRelative, initials } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { cn } from "@/lib/utils";

const TEAMS: Record<Team, string> = { all: "Todos", operations: "Operaciones", sales: "Ventas", marketing: "Marketing" };
const PERIODS: Record<Period, string> = { week: "Semana", month: "Mes", all: "Histórico" };

function LevelRing({ progress, level }: { progress: number; level: number }) {
  const reduce = useReducedMotion();
  const r = 52;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative h-36 w-36" role="img" aria-label={`Nivel ${level}, ${Math.round(progress * 100)}% hacia el siguiente`}>
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="hsl(var(--elevated))" strokeWidth="10" />
        <motion.circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke="url(#ember-ring)"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: reduce ? c * (1 - progress) : c }}
          animate={{ strokeDashoffset: c * (1 - progress) }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
        <defs>
          <linearGradient id="ember-ring" x1="0" x2="1">
            <stop offset="0" stopColor="hsl(var(--heavy-ember))" />
            <stop offset="1" stopColor="hsl(var(--heavy-rose))" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <p className="text-xs text-muted-foreground">Nivel</p>
          <p className="font-display text-4xl font-bold">{level}</p>
        </div>
      </div>
    </div>
  );
}

function Profile() {
  const { data, isLoading, error, refetch } = usePlayer();
  if (isLoading) return <Skeleton className="h-56 rounded-xl" />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  return (
    <Card className="overflow-hidden shadow-card">
      <div className="grid gap-6 p-6 md:grid-cols-[auto_1fr]">
        <LevelRing progress={data.level.progress} level={data.level.number} />
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-heavy-ember">{data.level.name}</p>
            <p className="font-display text-4xl font-bold">{fmtNumber(data.points)} pts</p>
            <p className="text-sm text-muted-foreground">
              {data.level.next_level_points != null
                ? `${fmtNumber(data.level.next_level_points - data.points)} pts para el siguiente nivel`
                : "Nivel máximo alcanzado"}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <span className="flex items-center gap-1.5 rounded-full bg-heavy-ember/10 px-3 py-1 text-sm text-heavy-ember">
              <Flame className="h-4 w-4" /> {data.streak_days} días de racha
            </span>
            {data.rank && (
              <span className="flex items-center gap-1.5 rounded-full bg-elevated px-3 py-1 text-sm">
                <Trophy className="h-4 w-4 text-heavy-ember" /> Puesto #{data.rank}
              </span>
            )}
          </div>
          <div>
            <p className="mb-2 text-sm font-semibold">Insignias ({data.badges.length})</p>
            {data.badges.length === 0 ? (
              <p className="text-sm text-muted-foreground">Aún no tienes insignias. ¡Completa tu primera tarea o negocio!</p>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {data.badges.map((b) => (
                  <li key={b.key} title={b.description} className="flex items-center gap-2 rounded-lg border border-heavy-ember/30 bg-heavy-ember/5 px-3 py-1.5 text-sm">
                    <Award className="h-4 w-4 text-heavy-ember" aria-hidden /> {b.name}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

function Leaderboard() {
  const [period, setPeriod] = useState<Period>("week");
  const [team, setTeam] = useState<Team>("all");
  const { user } = useAuth();
  const { data, isLoading, error, refetch } = useLeaderboard(period, team);
  const podium = [Crown, Medal, Medal];
  return (
    <Section
      title="Leaderboard"
      actions={
        <>
          <Select value={period} onValueChange={(v) => setPeriod(v as Period)}>
            <SelectTrigger className="h-8 w-32" aria-label="Periodo">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(PERIODS) as Period[]).map((p) => (
                <SelectItem key={p} value={p}>
                  {PERIODS[p]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={team} onValueChange={(v) => setTeam(v as Team)}>
            <SelectTrigger className="h-8 w-36" aria-label="Equipo">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(TEAMS) as Team[]).map((t) => (
                <SelectItem key={t} value={t}>
                  {TEAMS[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </>
      }
    >
      {isLoading ? (
        <ListSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <EmptyState icon={Trophy} title="Sin puntos en este periodo" />
      ) : (
        <ol className="space-y-1.5">
          {data.map((e) => {
            const Icon = podium[e.rank - 1];
            return (
              <li
                key={e.user_id}
                className={cn("flex items-center gap-3 rounded-lg px-3 py-2.5", e.user_id === user?.id ? "bg-heavy-ember/10 ring-1 ring-heavy-ember/30" : "hover:bg-elevated/60")}
              >
                <span className="w-7 text-center font-display font-bold text-muted-foreground">
                  {Icon ? <Icon className={cn("mx-auto h-5 w-5", e.rank === 1 ? "text-heavy-ember" : e.rank === 2 ? "text-muted-foreground" : "text-heavy-ember/60")} aria-label={`Puesto ${e.rank}`} /> : e.rank}
                </span>
                <span className="grid h-8 w-8 place-items-center rounded-full bg-elevated text-xs font-semibold">{initials(e.name)}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{e.name}</span>
                  <span className="text-xs text-muted-foreground">Nivel {e.level}</span>
                </span>
                <span className="font-semibold">{fmtNumber(e.points)}</span>
              </li>
            );
          })}
        </ol>
      )}
    </Section>
  );
}

function Feed() {
  const { data, isLoading } = useFeed();
  return (
    <Section title="Actividad reciente">
      {isLoading ? (
        <ListSkeleton rows={4} />
      ) : !data?.length ? (
        <p className="text-sm text-muted-foreground">Aún no hay logros.</p>
      ) : (
        <ul className="space-y-3">
          {data.slice(0, 15).map((f) => (
            <li key={f.id} className="flex items-start gap-3 text-sm">
              <Zap className="mt-0.5 h-4 w-4 shrink-0 text-heavy-ember" aria-hidden />
              <div className="min-w-0 flex-1">
                <p>
                  <span className="font-medium">{f.user_name}</span> <span className="text-muted-foreground">· {f.reason}</span>
                </p>
                <p className="text-xs text-muted-foreground">{fmtRelative(f.occurred_at)}</p>
              </div>
              <span className="font-semibold text-heavy-ember">+{f.points}</span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function Challenges() {
  const { data, isLoading, error, refetch } = useChallenges();
  const create = useCreateChallenge();
  const [open, setOpen] = useState(false);
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ title: "", description: "", metric: "tasks_completed", target: 20, reward_points: 200, team: "operations" as Team, starts_at: today, ends_at: today });
  return (
    <Section
      title="Retos"
      actions={
        <RequirePermission permission={PERMISSIONS.GAMIFICATION_MANAGE}>
          <Button size="sm" onClick={() => setOpen(true)}>
            <Plus className="mr-1 h-4 w-4" /> Reto
          </Button>
        </RequirePermission>
      }
    >
      {isLoading ? (
        <ListSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <EmptyState icon={Target} title="Sin retos" description="Crea retos con metas y recompensas para tus equipos." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((c) => (
            <Card key={c.id} className="p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold">{c.title}</h3>
                <StatusBadge tone={c.status === "active" ? "warning" : c.status === "upcoming" ? "info" : "neutral"}>
                  {{ upcoming: "Próximo", active: "Activo", finished: "Finalizado" }[c.status]}
                </StatusBadge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{c.description}</p>
              <div className="mt-3 flex justify-between text-xs text-muted-foreground">
                <span>
                  {fmtNumber(c.progress)} / {fmtNumber(c.target)}
                </span>
                <span className="font-semibold text-heavy-ember">+{c.reward_points} pts</span>
              </div>
              <Progress value={Math.min(100, (c.progress / Math.max(1, c.target)) * 100)} className="mt-1.5 h-2" aria-label={`Progreso del reto ${c.title}`} />
              <p className="mt-2 text-xs text-muted-foreground">
                {TEAMS[c.team]} · {fmtDate(c.starts_at, "d MMM")} – {fmtDate(c.ends_at, "d MMM")}
              </p>
            </Card>
          ))}
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuevo reto</DialogTitle>
          </DialogHeader>
          <form
            id="challenge-form"
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate(
                { ...form, starts_at: new Date(form.starts_at).toISOString(), ends_at: new Date(`${form.ends_at}T23:59:59`).toISOString() },
                { onSuccess: () => setOpen(false) },
              );
            }}
          >
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="ch-title">Título</Label>
              <Input id="ch-title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="ch-desc">Descripción</Label>
              <Textarea id="ch-desc" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Métrica</Label>
              <Select value={form.metric} onValueChange={(v) => setForm({ ...form, metric: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tasks_completed">Limpiezas completadas</SelectItem>
                  <SelectItem value="deals_won">Negocios ganados</SelectItem>
                  <SelectItem value="contacts_created">Contactos creados</SelectItem>
                  <SelectItem value="campaigns_launched">Campañas lanzadas</SelectItem>
                  <SelectItem value="points">Puntos</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Equipo</Label>
              <Select value={form.team} onValueChange={(v) => setForm({ ...form, team: v as Team })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(TEAMS) as Team[]).map((t) => (
                    <SelectItem key={t} value={t}>
                      {TEAMS[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ch-target">Meta</Label>
              <Input id="ch-target" type="number" min={1} value={form.target} onChange={(e) => setForm({ ...form, target: Number(e.target.value) })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ch-reward">Recompensa (pts)</Label>
              <Input id="ch-reward" type="number" min={0} value={form.reward_points} onChange={(e) => setForm({ ...form, reward_points: Number(e.target.value) })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ch-start">Inicio</Label>
              <Input id="ch-start" type="date" value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ch-end">Fin</Label>
              <Input id="ch-end" type="date" value={form.ends_at} onChange={(e) => setForm({ ...form, ends_at: e.target.value })} />
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="challenge-form" disabled={create.isPending}>
              {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Crear
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Section>
  );
}

function RulesAndBadges() {
  const rules = useRules();
  const badges = useBadges();
  const update = useUpdateRule();
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Section title="Reglas de puntos" description="Cada regla escucha un evento real del negocio.">
        {rules.isLoading ? (
          <ListSkeleton />
        ) : !rules.data?.length ? (
          <p className="text-sm text-muted-foreground">Sin reglas.</p>
        ) : (
          <ul className="divide-y">
            {rules.data.map((r) => (
              <li key={r.key} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{r.description}</p>
                  <p className="text-xs text-muted-foreground">{r.event}</p>
                </div>
                <RequirePermission permission={PERMISSIONS.GAMIFICATION_MANAGE} fallback={<span className="text-sm font-semibold text-heavy-ember">+{r.points}</span>}>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      className="h-8 w-20"
                      defaultValue={r.points}
                      aria-label={`Puntos de ${r.description}`}
                      onBlur={(e) => Number(e.target.value) !== r.points && update.mutate({ key: r.key, points: Number(e.target.value), active: r.active })}
                    />
                    <Switch checked={r.active} onCheckedChange={(v) => update.mutate({ key: r.key, points: r.points, active: v })} aria-label={`Activar ${r.description}`} />
                  </div>
                </RequirePermission>
              </li>
            ))}
          </ul>
        )}
      </Section>
      <Section title="Catálogo de insignias">
        {badges.isLoading ? (
          <ListSkeleton />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {badges.data?.map((b) => (
              <li key={b.key} className="rounded-lg border p-3">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <Sparkles className="h-4 w-4 text-heavy-ember" aria-hidden /> {b.name}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{b.criteria ?? b.description}</p>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}

export default function Gamification() {
  return (
    <div className="space-y-6">
      <PageHeader title="Gamificación" description="Puntos, niveles, insignias y retos conectados a resultados reales." icon={Gamepad2} accent="ember" />
      <Profile />
      <Tabs defaultValue="ranking">
        <TabsList>
          <TabsTrigger value="ranking">Ranking</TabsTrigger>
          <TabsTrigger value="retos">Retos</TabsTrigger>
          <TabsTrigger value="reglas">Reglas e insignias</TabsTrigger>
        </TabsList>
        <TabsContent value="ranking" className="mt-6">
          <div className="grid gap-6 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <Leaderboard />
            </div>
            <div className="lg:col-span-2">
              <Feed />
            </div>
          </div>
        </TabsContent>
        <TabsContent value="retos" className="mt-6">
          <Challenges />
        </TabsContent>
        <TabsContent value="reglas" className="mt-6">
          <RulesAndBadges />
        </TabsContent>
      </Tabs>
    </div>
  );
}
