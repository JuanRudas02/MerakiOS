import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const TONES = {
  primary: "text-heavy-blue bg-heavy-blue/10",
  mint: "text-heavy-mint bg-heavy-mint/10",
  violet: "text-heavy-violet bg-heavy-violet/10",
  meta: "text-heavy-meta bg-heavy-meta/10",
  ember: "text-heavy-ember bg-heavy-ember/10",
  cyan: "text-heavy-cyan bg-heavy-cyan/10",
  rose: "text-heavy-rose bg-heavy-rose/10",
} as const;

export type Tone = keyof typeof TONES;

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "primary",
  loading,
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon?: LucideIcon;
  tone?: Tone;
  loading?: boolean;
}) {
  return (
    <Card className="relative overflow-hidden p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-2 h-8 w-24" />
          ) : (
            <p className="mt-1.5 truncate font-display text-2xl font-bold sm:text-3xl">{value}</p>
          )}
          {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        </div>
        {Icon && (
          <div className={cn("grid h-10 w-10 shrink-0 place-items-center rounded-lg", TONES[tone])}>
            <Icon className="h-5 w-5" aria-hidden />
          </div>
        )}
      </div>
    </Card>
  );
}
