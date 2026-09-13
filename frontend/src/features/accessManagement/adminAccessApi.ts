import {
  accessPackageCodes,
  type AccessPackageCode,
  type EntitlementCode,
  type GrantSource,
} from "@fitician/core/entitlements";

import { request } from "../../shared/apiClient";

const adminAccessPath = "/api/v1/admin/access";
const adminAuditPath = "/api/v1/admin/audit/events";

export type AccessCampaignKind = "signup_trial" | "manual_promotion";
export type AccessTermWeeks = 4 | 6 | 8;
export type GrantStatus = "active" | "future" | "expired" | "revoked";

const campaignPackageCodes = accessPackageCodes.filter(
  (code) => code !== "free",
) as AccessPackageCode[];

export const adminAccessPackageCodes = campaignPackageCodes.filter(
  (code) => code !== "launch_trial",
);

export const signupTrialPackageCodes = campaignPackageCodes.filter(
  (code) => code === "launch_trial",
);

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
};

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
} = {}): Promise<AdminMemberSummary[]> {
  return request<AdminMemberSummary[]>(
    `${adminAccessPath}/users${queryString(params)}`,
  );
}

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
