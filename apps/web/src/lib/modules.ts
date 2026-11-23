import {
  BarChart3,
  Building2,
  Gamepad2,
  Megaphone,
  Rocket,
  Target,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { Tone } from "@/components/common/StatCard";

export interface ProductModule {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  icon: LucideIcon;
  tone: Tone;
  /** Clase de texto/fondo del color del módulo. */
  text: string;
  bg: string;
}

/** Fuente única del portafolio de 1heavy (landing, subpáginas, navegación). */
export const PRODUCT_MODULES: ProductModule[] = [
  {
    slug: "crm",
    name: "CRM & Contactos",
    tagline: "Cada contacto, una historia completa",
    description: "Contactos deduplicados, ciclo de vida, pipeline visual y lead scoring explicado por IA.",
    icon: Users,
    tone: "primary",
    text: "text-heavy-blue",
    bg: "bg-heavy-blue",
  },
  {
    slug: "meta-business",
    name: "Meta Business",
    tagline: "Pauta que se conecta con ventas",
    description: "Campañas, insights diarios, Lead Ads directo al CRM y alertas de rendimiento automáticas.",
    icon: Target,
    tone: "meta",
    text: "text-heavy-meta",
    bg: "bg-heavy-meta",
  },
  {
    slug: "mautic-ia",
    name: "Mautic + IA",
    tagline: "Marketing automation open source, potenciado con IA",
    description: "Segmentos sincronizados, emails y campañas generados por IA y medición de engagement.",
    icon: Megaphone,
    tone: "violet",
    text: "text-heavy-violet",
    bg: "bg-heavy-violet",
  },
  {
    slug: "gamificacion",
    name: "Gamificación",
    tagline: "Equipos que juegan para ganar",
    description: "Puntos, niveles, insignias, retos y rankings conectados a resultados reales del negocio.",
    icon: Gamepad2,
    tone: "ember",
    text: "text-heavy-ember",
    bg: "bg-heavy-ember",
  },
  {
    slug: "analitica",
    name: "Analítica",
    tagline: "Una sola verdad para todo el negocio",
    description: "KPIs de operación, ventas y marketing unificados, con insights y recomendaciones de IA.",
    icon: BarChart3,
    tone: "cyan",
    text: "text-heavy-cyan",
    bg: "bg-heavy-cyan",
  },
  {
    slug: "growth-ia",
    name: "Growth IA",
    tagline: "Estrategia de mercado en minutos",
    description: "Auditoría de mercado, avatar, nivel de conciencia y embudo diseñado por agentes de IA.",
    icon: Rocket,
    tone: "violet",
    text: "text-heavy-violet",
    bg: "bg-gradient-heavy",
  },
  {
    slug: "stays",
    name: "1heavy Stays",
    tagline: "Operación impecable de alquileres de corta estadía",
    description: "Limpiezas con evidencia fotográfica, WhatsApp con tu número, iCal y control de servicios.",
    icon: Building2,
    tone: "mint",
    text: "text-heavy-mint",
    bg: "bg-heavy-mint",
  },
];

export const moduleBySlug = (slug: string) => PRODUCT_MODULES.find((m) => m.slug === slug);
