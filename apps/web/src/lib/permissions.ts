/** Debe coincidir con `oneheavy.shared.domain.access.Permission` del backend. */
export const PERMISSIONS = {
  WORKSPACE_MANAGE: "workspace.manage",
  MEMBERS_MANAGE: "members.manage",
  PROPERTIES_READ: "stays.properties.read",
  PROPERTIES_MANAGE: "stays.properties.manage",
  TASKS_READ: "stays.tasks.read",
  TASKS_MANAGE: "stays.tasks.manage",
  TASKS_EXECUTE: "stays.tasks.execute",
  RECEIPTS_UPLOAD: "stays.receipts.upload",
  RECEIPTS_VERIFY: "stays.receipts.verify",
  CONTACTS_READ: "crm.contacts.read",
  CONTACTS_MANAGE: "crm.contacts.manage",
  DEALS_MANAGE: "crm.deals.manage",
  MARKETING_MANAGE: "marketing.manage",
  META_MANAGE: "meta.manage",
  GROWTH_USE: "growth.use",
  ANALYTICS_READ: "analytics.read",
  GAMIFICATION_READ: "gamification.read",
  GAMIFICATION_MANAGE: "gamification.manage",
  BILLING_MANAGE: "billing.manage",
} as const;

export type PermissionKey = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];
