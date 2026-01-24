// MerakiOS - Centralized Route Constants
// All navigation must use these constants - no hardcoded URLs

export const ROUTES = {
  // 🌐 Public Routes (no authentication required)
  PUBLIC: {
    HOME: "/",
    LOGIN: "/login",
    PRICING: "/pricing",
    ABOUT: "/about",
  },

  // 🔐 Private Routes (authentication required)
  APP: {
    ROOT: "/app",
    HOME: "/app/home",
    SERVICES: "/app/services",
    SETTINGS: "/app/settings",
  },

  // 🧩 Services Routes (Strategic Modules)
  SERVICES: {
    ROOT: "/app/services",
    // The Brain - Market Audit
    MARKET_AUDIT: "/app/services/market-audit",
    // The Mapper - Funnel Architect
    FUNNEL_ARCHITECT: "/app/services/funnel-architect",
    // The Blueprints - Copy & Prompts
    BLUEPRINTS: "/app/services/blueprints",
    // The Director - Live Dashboard
    INTELLIGENCE: "/app/services/intelligence",
    // Metrics (sub-module of Intelligence)
    METRICS: "/app/services/metrics",
    METRICS_FB: "/app/services/metrics/facebook",
    METRICS_IG: "/app/services/metrics/instagram",
    // AI Reports
    AI_REPORTS: "/app/services/ai-reports",
  },

  // ⚙️ Settings Routes
  SETTINGS: {
    ROOT: "/app/settings",
    PROFILE: "/app/settings/profile",
    INTEGRATIONS: "/app/settings/integrations",
    META: "/app/settings/meta",
    BILLING: "/app/settings/billing",
  },
} as const;

export type RouteKey = typeof ROUTES;
