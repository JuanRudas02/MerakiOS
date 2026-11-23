import { cn } from "@/lib/utils";

type Tone = "neutral" | "info" | "success" | "warning" | "danger" | "violet";

const TONES: Record<Tone, string> = {
  neutral: "bg-elevated text-muted-foreground border-border",
  info: "bg-heavy-blue/10 text-heavy-blue border-heavy-blue/30",
  success: "bg-heavy-mint/10 text-heavy-mint border-heavy-mint/30",
  warning: "bg-heavy-ember/10 text-heavy-ember border-heavy-ember/30",
  danger: "bg-heavy-rose/10 text-heavy-rose border-heavy-rose/30",
  violet: "bg-heavy-violet/10 text-heavy-violet border-heavy-violet/30",
};

export function StatusBadge({ tone = "neutral", children, className }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", TONES[tone], className)}>
      {children}
    </span>
  );
}

export const TASK_TONE = {
  pending: "neutral",
  arrived: "info",
  in_progress: "warning",
  completed: "success",
  cancelled: "danger",
} as const;
