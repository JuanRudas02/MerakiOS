import { cn } from "@/lib/utils";

interface HeavyLogoProps {
  className?: string;
  showWordmark?: boolean;
  size?: number;
}

/** Isotipo original de 1heavy: monolito "1" + dos bloques apilados (peso + crecimiento). */
export function HeavyMark({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="heavy-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="hsl(var(--heavy-blue))" />
          <stop offset="1" stopColor="hsl(var(--heavy-violet))" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#heavy-mark)" />
      <path d="M20 18h9v28h-9zM33 18h11v12H33zM33 34h11v12H33z" fill="#fff" />
    </svg>
  );
}

export function HeavyLogo({ className, showWordmark = true, size = 32 }: HeavyLogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)} aria-label="1heavy">
      <HeavyMark size={size} />
      {showWordmark && (
        <span className="font-display text-xl font-bold leading-none tracking-tight">
          1<span className="text-gradient-heavy">heavy</span>
        </span>
      )}
    </span>
  );
}
