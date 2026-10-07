import type { components } from "@fitician/core";
import {
  type AccessPackageCode,
  type EntitlementCode,
  type GrantSource,
} from "@fitician/core/entitlements";
import { type AccessCampaignKind } from "@fitician/core/campaigns";

import { request } from "../../shared/apiClient";

const adminAccessPath = "/api/v1/admin/access";
const adminAuditPath = "/api/v1/admin/audit/events";

export type AccessTermWeeks = 4 | 6 | 8;
export type GrantStatus = "active" | "future" | "expired" | "revoked";

export const campaignGrantPackageCodes = [
  "training",
  "training_coach",
  "nutrition",
  "nutrition_physician",
  "complete",
  "complete_care",
] as const satisfies readonly AccessPackageCode[];

export const signupBonusPackageCodes = campaignGrantPackageCodes;
export const adminAccessPackageCodes = campaignGrantPackageCodes;

export type { AccessCampaignKind } from "@fitician/core/campaigns";

export type AdminAccessCampaign = {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly description: string | null;
  readonly kind: AccessCampaignKind;
  readonly package_code: AccessPackageCode;
  readonly duration_days: number;
  readonly term_weeks: AccessTermWeeks | null;
  readonly available_from: string | null;
  readonly available_until: string | null;
  readonly is_active: boolean;
  readonly max_total_redemptions: number | null;
  readonly public_badge_fa: string | null;
  readonly public_badge_en: string | null;
  readonly public_title_fa: string | null;
  readonly public_title_en: string | null;
  readonly public_message_fa: string | null;
  readonly public_message_en: string | null;
  readonly public_cta_fa: string | null;
  readonly public_cta_en: string | null;
  readonly show_on_landing: boolean;
  readonly show_on_register: boolean;
  readonly redemption_count: number;
  readonly created_by_user_id: string | null;
  readonly created_at: string;
  readonly updated_at: string;
};

export type AdminAccessCampaignInput = {
  readonly code: string;
  readonly name: string;
  readonly description?: string | null;
  readonly kind: AccessCampaignKind;
  readonly package_code: AccessPackageCode;
  readonly duration_days: number;
  readonly term_weeks?: AccessTermWeeks | null;
  readonly available_from?: string | null;
  readonly available_until?: string | null;
  readonly is_active?: boolean;
  readonly max_total_redemptions?: number | null;
  readonly public_badge_fa?: string | null;
  readonly public_badge_en?: string | null;
  readonly public_title_fa?: string | null;
  readonly public_title_en?: string | null;
  readonly public_message_fa?: string | null;
  readonly public_message_en?: string | null;
  readonly public_cta_fa?: string | null;
  readonly public_cta_en?: string | null;
  readonly show_on_landing?: boolean;
  readonly show_on_register?: boolean;
};

export type AdminAccessCampaignUpdate = Partial<
  Omit<AdminAccessCampaignInput, "code" | "is_active">
>;

export type AdminMemberSummary = {
  readonly user_id: string;
  readonly display_name: string | null;
  readonly email: string | null;
  readonly phone_number: string | null;
  readonly created_at: string;
  readonly primary_package: AccessPackageCode;
  readonly active_packages: readonly AccessPackageCode[];
  readonly trial_active: boolean;
  readonly trial_ends_at: string | null;
  readonly paid_access_end: string | null;
  readonly last_activity_at?: string | null;
  readonly usage_status?: "no_recorded_activity" | "active" | "inactive";
};

export type Page<T> = { readonly items: readonly T[]; readonly total: number; readonly limit: number; readonly offset: number };
export type SignupPoint = components["schemas"]["SignupPoint"];
export type AccessOverview = components["schemas"]["AccessOverview"];
export type UserInsights = components["schemas"]["UserInsights"];
export type ActivityItem = components["schemas"]["ActivityItem"];
export type LoginItem = components["schemas"]["LoginItem"];
export type WorkoutHistoryItem = components["schemas"]["WorkoutHistoryItem"];
export type WorkoutDetail = components["schemas"]["WorkoutDetail"];
export type NutritionHistoryItem = components["schemas"]["NutritionHistoryItem"];
export type NutritionDetail = components["schemas"]["NutritionDetail"];
export type ProgressItem = components["schemas"]["ProgressItem"];
export type AnalysisItem = components["schemas"]["AnalysisItem"];

export type AdminEntitlementSnapshot = {
  readonly primary_package: AccessPackageCode;
  readonly active_packages: readonly AccessPackageCode[];
  readonly granted_entitlements: readonly EntitlementCode[];
  readonly trial_active: boolean;
  readonly trial_ends_at: string | null;
};

export type AdminGrant = {
  readonly id: string;
  readonly package_code: AccessPackageCode;
  readonly source: GrantSource;
  readonly term_weeks: AccessTermWeeks | null;
  readonly starts_at: string;
  readonly ends_at: string | null;
  readonly revoked_at: string | null;
  readonly created_at: string;
  readonly status: GrantStatus;
  readonly is_currently_active: boolean;
  readonly billing_order_id: string | null;
  readonly campaign_id: string | null;
  readonly campaign_name: string | null;
};

export type AdminUserAccess = {
  readonly member: AdminMemberSummary;
  readonly entitlement_snapshot: AdminEntitlementSnapshot;
  readonly grants: readonly AdminGrant[];
};

export type GrantUserAccessInput = {
  readonly package_code: AccessPackageCode;
  readonly term_weeks?: AccessTermWeeks | null;
  readonly starts_at?: string | null;
  readonly ends_at: string;
  readonly reason: string;
  readonly client_idempotency_key: string;
};

export type AdminAuditActor = {
  readonly user_id: string;
  readonly display_name: string | null;
  readonly email: string | null;
  readonly phone_number: string | null;
};

export type AdminAuditEvent = {
  readonly id: string;
  readonly action: string;
  readonly actor: AdminAuditActor | null;
  readonly target: AdminAuditActor | null;
  readonly resource_type: string;
  readonly resource_key: string;
  readonly reason: string | null;
  readonly before_state: Record<string, unknown> | null;
  readonly after_state: Record<string, unknown> | null;
  readonly created_at: string;
};

function queryString(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded === "" ? "" : `?${encoded}`;
}

export function getCampaigns(): Promise<AdminAccessCampaign[]> {
  return request<AdminAccessCampaign[]>(`${adminAccessPath}/campaigns`);
}

export function getCampaign(campaignId: string): Promise<AdminAccessCampaign> {
  return request<AdminAccessCampaign>(`${adminAccessPath}/campaigns/${campaignId}`);
}

export function createCampaign(
  input: AdminAccessCampaignInput,
): Promise<AdminAccessCampaign> {
  return request<AdminAccessCampaign>(`${adminAccessPath}/campaigns`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateCampaign(
  campaignId: string,
  input: AdminAccessCampaignUpdate,
): Promise<AdminAccessCampaign> {
  return request<AdminAccessCampaign>(`${adminAccessPath}/campaigns/${campaignId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function activateCampaign(campaignId: string): Promise<AdminAccessCampaign> {
  return request<AdminAccessCampaign>(`${adminAccessPath}/campaigns/${campaignId}/activate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function deactivateCampaign(campaignId: string): Promise<AdminAccessCampaign> {
  return request<AdminAccessCampaign>(`${adminAccessPath}/campaigns/${campaignId}/deactivate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function searchAccessUsers(params: {
  q?: string;
  limit?: number;
  offset?: number;
  signup_period?: "all" | "today" | "week" | "month" | "custom";
  from_date?: string;
  to_date?: string;
  sort?: "newest" | "oldest" | "last_activity";
} = {}): Promise<Page<AdminMemberSummary>> {
  return request<Page<AdminMemberSummary>>(
    `${adminAccessPath}/users${queryString(params)}`,
  );
}

export function getAccessOverview(): Promise<AccessOverview> { return request(`${adminAccessPath}/overview`); }
export function getUserInsights(userId: string): Promise<UserInsights> { return request(`${adminAccessPath}/users/${userId}/insights`); }
export function getUserActivity(userId: string, params: {limit?: number; offset?: number; event_type?: string} = {}): Promise<Page<ActivityItem>> { return request(`${adminAccessPath}/users/${userId}/activity${queryString(params)}`); }
export function getUserLogins(userId: string, params: {limit?: number; offset?: number} = {}): Promise<Page<LoginItem>> { return request(`${adminAccessPath}/users/${userId}/logins${queryString(params)}`); }
export function getWorkoutPlans(userId: string, params: {limit?: number; offset?: number} = {}): Promise<Page<WorkoutHistoryItem>> { return request(`${adminAccessPath}/users/${userId}/workout-plans${queryString(params)}`); }
export function getWorkoutPlan(userId: string, planId: string): Promise<WorkoutDetail> { return request(`${adminAccessPath}/users/${userId}/workout-plans/${planId}`); }
export function getNutritionPlans(userId: string, params: {limit?: number; offset?: number} = {}): Promise<Page<NutritionHistoryItem>> { return request(`${adminAccessPath}/users/${userId}/nutrition-plans${queryString(params)}`); }
export function getNutritionPlan(userId: string, planId: string): Promise<NutritionDetail> { return request(`${adminAccessPath}/users/${userId}/nutrition-plans/${planId}`); }
export function getUserProgress(userId: string, params: {limit?: number; offset?: number} = {}): Promise<Page<ProgressItem>> { return request(`${adminAccessPath}/users/${userId}/progress${queryString(params)}`); }
export function getUserBodyAnalyses(userId: string, params: {limit?: number; offset?: number} = {}): Promise<Page<AnalysisItem>> { return request(`${adminAccessPath}/users/${userId}/body-analyses${queryString(params)}`); }

export function getUserAccess(userId: string): Promise<AdminUserAccess> {
  return request<AdminUserAccess>(`${adminAccessPath}/users/${userId}`);
}

export function grantUserAccess(
  userId: string,
  input: GrantUserAccessInput,
): Promise<AdminGrant> {
  return request<AdminGrant>(`${adminAccessPath}/users/${userId}/grants`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function revokeUserAccess(
  grantId: string,
  reason: string,
): Promise<AdminGrant> {
  return request<AdminGrant>(`${adminAccessPath}/grants/${grantId}/revoke`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function redeemUserCampaign(
  userId: string,
  campaignId: string,
  reason: string,
): Promise<{ campaign: AdminAccessCampaign; grant: AdminGrant }> {
  return request<{ campaign: AdminAccessCampaign; grant: AdminGrant }>(
    `${adminAccessPath}/users/${userId}/campaigns/${campaignId}/redeem`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    },
  );
}

export function getAdminAuditEvents(params: {
  action?: string;
  actor_user_id?: string;
  target_user_id?: string;
  resource_type?: string;
  from_datetime?: string;
  to_datetime?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<AdminAuditEvent[]> {
  return request<AdminAuditEvent[]>(`${adminAuditPath}${queryString(params)}`);
}
