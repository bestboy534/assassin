import type { SourceHint, SubscriptionItem } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type OrganizationSummary = {
  id: string;
  name: string;
  slug: string;
  role: string;
};

export type AuthSession = {
  user: {
    id: string;
    email: string;
    display_name: string;
    status: string;
  };
  organizations: OrganizationSummary[];
};

export type ApplicationItem = {
  id: string;
  organization_id: string;
  name: string;
  category: string;
  status: string;
  business_owner: string | null;
  technical_owner: string | null;
  risk_level: string;
  approved: boolean;
};

export type AnalysisRunSummary = {
  id: string;
  organization_id: string | null;
  status: string;
  source_hint: SourceHint;
  items_count: number;
  total_monthly_cost_usd: number;
  created_at: string;
};

export type AnalysisRunDetail = {
  run: AnalysisRunSummary;
  items: SubscriptionItem[];
};

export type PurchaseRequestItem = {
  id: string;
  organization_id: string;
  software_name: string;
  business_reason: string;
  estimated_monthly_cost_usd: number;
  department: string;
  handles_sensitive_data: boolean;
  data_categories: string[];
  status: string;
  current_approval_task_id: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  created_at: string;
};

export type ApprovalTaskItem = {
  id: string;
  organization_id: string;
  purchase_request_id: string;
  assignee_role: string;
  status: string;
  created_at: string;
};

export type ContractItem = {
  id: string;
  organization_id: string;
  name: string;
  vendor_name: string;
  application_name: string | null;
  owner_name: string;
  status: string;
  current_version_id: string | null;
  created_at: string;
};

export type ContractVersionItem = {
  id: string;
  organization_id: string;
  contract_id: string;
  version_number: number;
  status: string;
  start_date: string;
  end_date: string;
  amount: number;
  currency: string;
  billing_frequency: string;
  auto_renew: boolean;
  notice_period_days: number;
  signed_at: string | null;
};

export type RenewalItem = {
  id: string;
  organization_id: string;
  contract_id: string;
  source_version_id: string;
  renewal_date: string;
  decision_deadline: string;
  owner_name: string;
  status: string;
  decision: string | null;
  current_amount: number;
  currency: string;
};

export type ContractBundle = {
  contract: ContractItem;
  version: ContractVersionItem;
  renewal: RenewalItem | null;
};

export type VendorItem = {
  id: string;
  organization_id: string;
  name: string;
  domain: string | null;
  country_code: string | null;
  category: string;
  status: string;
  business_owner: string | null;
  risk_owner: string | null;
  overall_risk_score: number | null;
  risk_level: string;
  created_at: string;
};

export type RiskDimensionItem = {
  score: number;
  reasons: string[];
};

export type VendorAssessmentItem = {
  id: string;
  vendor_id: string;
  questionnaire_version: number;
  rule_version: string;
  status: string;
  total_score: number;
  dimensions: Record<string, RiskDimensionItem>;
  submitted_at: string;
};

export type RiskFindingItem = {
  id: string;
  vendor_id: string;
  assessment_id: string;
  dimension: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  owner_name: string;
  due_date: string;
  mitigation_plan: string | null;
  accepted_reason: string | null;
  accepted_until: string | null;
};

export type VendorAssessmentBundle = {
  assessment: VendorAssessmentItem;
  findings: RiskFindingItem[];
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `请求失败：${response.status}`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      message = (await response.text()) || message;
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function registerAccount(input: {
  email: string;
  password: string;
  displayName: string;
  organizationName: string;
}) {
  return request<AuthSession>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      display_name: input.displayName,
      organization_name: input.organizationName,
    }),
  });
}

export function loginAccount(input: { email: string; password: string }) {
  return request<AuthSession>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getCurrentSession() {
  return request<AuthSession>("/api/v1/auth/me");
}

export function logoutAccount() {
  return request<{ status: string }>("/api/v1/auth/logout", { method: "POST" });
}

export function listApplications(organizationId: string) {
  return request<{ items: ApplicationItem[] }>(
    `/api/v1/organizations/${organizationId}/applications`,
  );
}

export function createApplication(
  organizationId: string,
  input: {
    name: string;
    category: string;
    business_owner: string | null;
    technical_owner: string | null;
    approved: boolean;
  },
) {
  return request<ApplicationItem>(`/api/v1/organizations/${organizationId}/applications`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listAnalysisRuns(organizationId: string) {
  return request<{ items: AnalysisRunSummary[] }>(
    `/api/v1/organizations/${organizationId}/analysis-runs`,
  );
}

export function createAnalysisRun(
  organizationId: string,
  input: {
    raw_text: string;
    source_hint: SourceHint;
  },
) {
  return request<AnalysisRunDetail>(`/api/v1/organizations/${organizationId}/analysis-runs`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listPurchaseRequests(organizationId: string) {
  return request<{ items: PurchaseRequestItem[] }>(
    `/api/v1/organizations/${organizationId}/purchase-requests`,
  );
}

export function createPurchaseRequest(
  organizationId: string,
  input: {
    software_name: string;
    business_reason: string;
    estimated_monthly_cost_usd: number;
    department: string;
    handles_sensitive_data: boolean;
    data_categories: string[];
  },
) {
  return request<PurchaseRequestItem>(
    `/api/v1/organizations/${organizationId}/purchase-requests`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function submitPurchaseRequest(organizationId: string, requestId: string) {
  return request<PurchaseRequestItem>(
    `/api/v1/organizations/${organizationId}/purchase-requests/${requestId}/submit`,
    { method: "POST" },
  );
}

export function listApprovalTasks(organizationId: string) {
  return request<{ items: ApprovalTaskItem[] }>(
    `/api/v1/organizations/${organizationId}/approval-tasks`,
  );
}

export function approveApprovalTask(
  organizationId: string,
  taskId: string,
  comment: string,
  idempotencyKey: string,
) {
  return request<ApprovalTaskItem>(
    `/api/v1/organizations/${organizationId}/approval-tasks/${taskId}/approve`,
    {
      method: "POST",
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify({ comment }),
    },
  );
}

export function listContracts(organizationId: string) {
  return request<{ items: ContractItem[] }>(
    `/api/v1/organizations/${organizationId}/contracts`,
  );
}

export function listRenewals(organizationId: string) {
  return request<{ items: RenewalItem[] }>(
    `/api/v1/organizations/${organizationId}/renewals`,
  );
}

export function createContract(
  organizationId: string,
  input: {
    name: string;
    vendor_name: string;
    application_name: string | null;
    owner_name: string;
    start_date: string;
    end_date: string;
    amount: number;
    currency: string;
    billing_frequency: string;
    auto_renew: boolean;
    notice_period_days: number;
  },
) {
  return request<ContractBundle>(`/api/v1/organizations/${organizationId}/contracts`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function markContractVersionSigned(
  organizationId: string,
  contractId: string,
  versionId: string,
) {
  return request<ContractBundle>(
    `/api/v1/organizations/${organizationId}/contracts/${contractId}/versions/${versionId}/mark-signed`,
    { method: "POST" },
  );
}

export function listVendors(organizationId: string) {
  return request<{ items: VendorItem[] }>(
    `/api/v1/organizations/${organizationId}/vendors`,
  );
}

export function listRiskFindings(organizationId: string) {
  return request<{ items: RiskFindingItem[] }>(
    `/api/v1/organizations/${organizationId}/risk-findings`,
  );
}

export function createVendor(
  organizationId: string,
  input: {
    name: string;
    domain: string | null;
    country_code: string | null;
    category: string;
    business_owner: string | null;
    risk_owner: string | null;
  },
) {
  return request<VendorItem>(`/api/v1/organizations/${organizationId}/vendors`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createVendorAssessment(
  organizationId: string,
  vendorId: string,
  input: {
    questionnaire_version: number;
    has_soc2: boolean;
    has_iso27001: boolean;
    has_dpa: boolean;
    supports_sso: boolean;
    has_incident_response: boolean;
    financial_stability: "strong" | "medium" | "weak";
    service_criticality: "low" | "medium" | "high";
    stores_sensitive_data: boolean;
  },
) {
  return request<VendorAssessmentBundle>(
    `/api/v1/organizations/${organizationId}/vendors/${vendorId}/assessments`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function getLatestVendorAssessment(
  organizationId: string,
  vendorId: string,
) {
  return request<{ item: VendorAssessmentBundle | null }>(
    `/api/v1/organizations/${organizationId}/vendors/${vendorId}/assessments/latest`,
  );
}

export function acceptRiskFinding(
  organizationId: string,
  findingId: string,
  input: {
    reason: string;
    expires_at: string;
    risk_owner: string;
  },
) {
  return request<RiskFindingItem>(
    `/api/v1/organizations/${organizationId}/risk-findings/${findingId}/accept`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}
