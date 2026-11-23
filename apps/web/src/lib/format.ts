import { format, formatDistanceToNow, parseISO } from "date-fns";
import { es } from "date-fns/locale";

const num = new Intl.NumberFormat("es-CO");
const compact = new Intl.NumberFormat("es-CO", { notation: "compact", maximumFractionDigits: 1 });

export const fmtNumber = (v: number | string | null | undefined) => num.format(Number(v ?? 0));
export const fmtCompact = (v: number | string | null | undefined) => compact.format(Number(v ?? 0));
export const fmtPercent = (ratio: number | null | undefined, digits = 0) =>
  `${(Number(ratio ?? 0) * 100).toFixed(digits)}%`;
export const fmtMoney = (v: number | string | null | undefined, currency = "COP") =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency, maximumFractionDigits: currency === "COP" ? 0 : 2 }).format(
    Number(v ?? 0),
  );

const toDate = (v: string | Date) => (typeof v === "string" ? parseISO(v) : v);
export const fmtDate = (v: string | Date | null | undefined, pattern = "d MMM yyyy") =>
  v ? format(toDate(v), pattern, { locale: es }) : "—";
export const fmtDateTime = (v: string | Date | null | undefined) => fmtDate(v, "d MMM yyyy · HH:mm");
export const fmtRelative = (v: string | Date | null | undefined) =>
  v ? formatDistanceToNow(toDate(v), { addSuffix: true, locale: es }) : "—";
export const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
/** Dinero compacto para tarjetas KPI ($ 48,2 M). */
export const fmtMoneyCompact = (v: number | string | null | undefined, currency = "COP") =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency, notation: "compact", maximumFractionDigits: 1 }).format(Number(v ?? 0));
