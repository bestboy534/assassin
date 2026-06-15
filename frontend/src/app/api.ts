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
    platform_role?: string | null;
  };
  organizations: OrganizationSummary[];
};

export type BillingEntitlement = {
  key: string;
  value_type: string;
  value: boolean | number | string;
  hard_limit: boolean;
};

export type BillingPlan = {
  key: string;
  name: string;
  description: string;
  currency: string;
  billing_interval: string;
  amount_minor: number;
  entitlements: BillingEntitlement[];
};

export type BillingSubscription = {
  status: string;
  read_only: boolean;
  trial_ends_at: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  pending_change_at: string | null;
  pending_change_type: string | null;
};

export type BillingSummary = {
  plan: BillingPlan;
  subscription: BillingSubscription;
  pending_plan: BillingPlan | null;
  payment_issue: boolean;
};

export type BillingUsageMetric = {
  metric: string;
  current_value: number;
  limit: number;
  hard_limit: boolean;
  status: string;
};

export type BillingInvoice = {
  external_invoice_id: string;
  status: string;
  currency: string;
  amount_due_minor: number;
  amount_paid_minor: number;
  hosted_invoice_url: string | null;
  due_at: string | null;
  paid_at: string | null;
  created_at: string;
};

export type BillingChangePreview = {
  current_plan: string;
  target_plan: string;
  direction: "upgrade" | "downgrade";
  effective_at: string;
  current_amount_minor: number;
  target_amount_minor: number;
  proration_minor: number;
  lost_features: string[];
  over_limit: Record<string, number>;
};

export type PublicStatusComponent = {
  id: string;
  slug: string;
  name: string;
  description: string;
  status: string;
};

export type PublicIncidentUpdate = {
  id: string;
  status: string;
  message: string;
  created_at: string;
};

export type PublicStatusIncident = {
  id: string;
  component_id: string;
  component_name: string;
  title: string;
  summary: string;
  impact: string;
  status: string;
  started_at: string;
  resolved_at: string | null;
  postmortem_summary: string | null;
  updates: PublicIncidentUpdate[];
};

export type PublicStatusOverview = {
  overall_status: string;
  generated_at: string;
  components: PublicStatusComponent[];
  incidents: PublicStatusIncident[];
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

export type BudgetItem = {
  id: string;
  organization_id: string;
  name: string;
  fiscal_year: number;
  department: string;
  amount: string;
  currency: string;
  status: string;
  created_at: string;
};

export type BudgetSummaryItem = {
  budget_id: string;
  currency: string;
  allocated: string;
  actual: string;
  committed: string;
  forecast: string;
  remaining: string;
};

export type TransactionSplitItem = {
  id: string;
  amount: string;
  department: string;
  category: string;
};

export type SpendTransactionItem = {
  id: string;
  organization_id: string;
  source_provider: string;
  source_account_id: string;
  external_id: string;
  transaction_date: string;
  merchant_name: string;
  description: string;
  amount: string;
  currency: string;
  department: string;
  category: string | null;
  application_id: string | null;
  match_confidence: string;
  splits: TransactionSplitItem[];
};

export type TransactionAnomalyItem = {
  id: string;
  transaction_id: string;
  budget_id: string | null;
  code: string;
  rule_version: string;
  baseline_amount: string;
  observed_amount: string;
  status: string;
  evidence: string;
};

export type AccountingPeriodItem = {
  id: string;
  organization_id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
  locked_at: string | null;
};

export type ImportTransactionsResponse = {
  created_count: number;
  existing_count: number;
  items: SpendTransactionItem[];
};

export type SavingsBaselineItem = {
  id: string;
  version: number;
  monthly_cost: string;
  calculation_months: number;
  amount: string;
  calculation_method: string;
  effective_date: string;
  contract_end: string | null;
};

export type SavingsOpportunityItem = {
  id: string;
  organization_id: string;
  source_type: string;
  source_id: string;
  rule_version: string;
  period_key: string;
  title: string;
  department: string;
  category: string;
  status: string;
  estimated_amount: string;
  currency: string;
  evidence: string;
  created_at: string;
  baseline: SavingsBaselineItem;
};

export type OptimizationTaskItem = {
  id: string;
  title: string;
  status: string;
};

export type SavingsResultItem = {
  id: string;
  project_id: string;
  status: string;
  action: string;
  effective_date: string;
  new_monthly_cost: string;
  realized_amount: string;
  verified_amount: string;
  realization_evidence: string;
  evidence_references: string[];
  verified_at: string | null;
};

export type OptimizationProjectBundle = {
  project: {
    id: string;
    opportunity_id: string;
    owner_name: string;
    due_date: string;
    status: string;
    target_amount: string;
    currency: string;
  };
  tasks: OptimizationTaskItem[];
  result: SavingsResultItem | null;
};

export type SavingsSummaryItem = {
  currency: string;
  estimated: string;
  realized: string;
  verified: string;
  cost_avoidance: string;
};

export type PaymentInstrumentBundle = {
  instrument: {
    id: string;
    purchase_request_id: string;
    provider: string;
    external_id: string;
    brand: string;
    last4: string;
    status: string;
    sandbox: boolean;
    owner_name: string;
    department: string;
    merchant_lock: string;
    currency: string;
  };
  limits: {
    single: string;
    daily: string;
    monthly: string;
    total: string;
  };
};

export type InvoiceLineItem = {
  id: string;
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
  category: string;
};

export type InvoiceBundle = {
  invoice: {
    id: string;
    organization_id: string;
    vendor_name: string;
    invoice_number: string;
    invoice_date: string;
    due_date: string;
    currency: string;
    subtotal: string;
    tax: string;
    total: string;
    purchase_order_number: string;
    status: string;
    exception_codes: string[];
    duplicate_of_id: string | null;
    current_version: number;
    filename: string;
    created_at: string;
  };
  line_items: InvoiceLineItem[];
  extraction: {
    provider: string;
    status: string;
    fields: Record<string, unknown>;
  } | null;
  match: {
    id: string;
    vendor_id: string | null;
    contract_id: string | null;
    transaction_id: string | null;
    application_id: string | null;
    purchase_request_id: string | null;
    confidence: string;
    status: string;
    explanation: Record<string, unknown>;
  } | null;
  export: {
    id: string;
    invoice_id: string;
    provider: string;
    status: string;
    external_id: string | null;
    external_version: number | null;
    exported_invoice_version: number | null;
    diff: Record<string, unknown>;
    attempts: number;
  } | null;
};

export type AccountingMappingItem = {
  id: string;
  scope_type: string;
  scope_value: string;
  account_code: string;
  tax_code: string;
  cost_center: string;
  department: string;
  project: string;
};

export type ResolvedAccountingMapping = {
  mapping_id: string;
  resolved_scope_type: string;
  account_code: string;
  tax_code: string;
  cost_center: string;
  department: string;
  project: string;
};

export type IntegrationDefinitionItem = {
  id: string;
  key: string;
  name: string;
  provider: string;
  category: string;
  auth_type: string;
  capabilities: string[];
  resource_types: string[];
  status: string;
};

export type IntegrationConnectionItem = {
  id: string;
  organization_id: string;
  definition_key: string;
  definition_name: string;
  display_name: string;
  status: string;
  auth_type: string;
  credential_label: string;
  credential_last4: string;
  capabilities: string[];
  resource_types: string[];
  last_health_status: string | null;
  last_sync_at: string | null;
  created_at: string;
};

export type IntegrationSyncRunItem = {
  id: string;
  connection_id: string;
  resource_type: string;
  status: string;
  cursor_before: string | null;
  cursor_after: string | null;
  read_count: number;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  failed_count: number;
  error_summary: string | null;
  started_at: string;
  finished_at: string | null;
  errors: Array<{
    code: string;
    message: string;
    external_id: string | null;
    retryable: boolean;
  }>;
};

export type ReportMetricDefinitionItem = {
  key: string;
  label: string;
  description: string;
  value_type: "money" | "number" | "percentage" | "duration" | string;
  required_permission: string;
  dimensions: string[];
};

export type ReportDimensionItem = {
  key: string;
  label: string;
};

export type ReportQueryPayload = {
  metrics: string[];
  date_range: {
    start: string;
    end: string;
  };
  group_by: string[];
  filters: Array<{
    dimension: string;
    operator: "equals" | "in";
    value: string | string[];
  }>;
  comparison?: "previous_period" | "previous_year" | null;
};

export type ReportRowItem = {
  dimensions: Record<string, string>;
  metrics: Record<string, string>;
};

export type ReportQueryResult = {
  metrics: string[];
  group_by: string[];
  rows: ReportRowItem[];
  generated_at: string;
};

export type SavedReportItem = {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  query: ReportQueryPayload;
  chart_type: string;
  visibility: string;
  created_at: string;
  updated_at: string;
};

export type ReportSnapshotItem = {
  id: string;
  saved_report_id: string;
  payload: ReportQueryResult;
  created_at: string;
};

export type ReportExportItem = {
  id: string;
  job_id: string;
  saved_report_id: string;
  format: string;
  status: string;
  row_count: number;
  filename: string;
  download_url: string;
  expires_at: string;
  created_at: string;
};

export type ReportSubscriptionItem = {
  id: string;
  saved_report_id: string;
  frequency: string;
  cron: string;
  timezone: string;
  recipients: string[];
  status: string;
  next_run_at: string;
  failure_count: number;
  created_at: string;
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
    let message = `请求失败（${response.status}）`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (body.detail?.code === "entitlement_exceeded") {
        message = `当前套餐额度已用尽（上限 ${body.detail.limit}）。请升级套餐后继续。`;
      }
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

export function listBudgets(organizationId: string) {
  return request<{ items: BudgetItem[] }>(
    `/api/v1/organizations/${organizationId}/budgets`,
  );
}

export function createBudget(
  organizationId: string,
  input: {
    name: string;
    fiscal_year: number;
    department: string;
    amount: string;
    currency: string;
  },
) {
  return request<BudgetItem>(`/api/v1/organizations/${organizationId}/budgets`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createBudgetCommitment(
  organizationId: string,
  budgetId: string,
  input: {
    commitment_type: "committed" | "forecast";
    amount: string;
    description: string;
  },
) {
  return request<{
    id: string;
    budget_id: string;
    commitment_type: string;
    amount: string;
    description: string;
  }>(`/api/v1/organizations/${organizationId}/budgets/${budgetId}/commitments`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getBudgetSummary(organizationId: string, budgetId: string) {
  return request<BudgetSummaryItem>(
    `/api/v1/organizations/${organizationId}/budgets/${budgetId}/summary`,
  );
}

export function listSpendTransactions(organizationId: string) {
  return request<{ items: SpendTransactionItem[] }>(
    `/api/v1/organizations/${organizationId}/transactions`,
  );
}

export function importSpendTransactions(
  organizationId: string,
  input: {
    source_provider: string;
    source_account_id: string;
    rows: Array<{
      external_id: string;
      transaction_date: string;
      merchant_name: string;
      description: string;
      amount: string;
      currency: string;
      department: string;
    }>;
  },
) {
  return request<ImportTransactionsResponse>(
    `/api/v1/organizations/${organizationId}/transactions/import`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function updateSpendTransaction(
  organizationId: string,
  transactionId: string,
  input: {
    category?: string;
    department?: string;
  },
) {
  return request<SpendTransactionItem>(
    `/api/v1/organizations/${organizationId}/transactions/${transactionId}`,
    {
      method: "PATCH",
      body: JSON.stringify(input),
    },
  );
}

export function setSpendTransactionSplits(
  organizationId: string,
  transactionId: string,
  splits: Array<{
    amount: string;
    department: string;
    category: string;
  }>,
) {
  return request<SpendTransactionItem>(
    `/api/v1/organizations/${organizationId}/transactions/${transactionId}/splits`,
    {
      method: "POST",
      body: JSON.stringify({ splits }),
    },
  );
}

export function listTransactionAnomalies(organizationId: string) {
  return request<{ items: TransactionAnomalyItem[] }>(
    `/api/v1/organizations/${organizationId}/transaction-anomalies`,
  );
}

export function createAccountingPeriod(
  organizationId: string,
  input: {
    name: string;
    start_date: string;
    end_date: string;
  },
) {
  return request<AccountingPeriodItem>(
    `/api/v1/organizations/${organizationId}/accounting-periods`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function listAccountingPeriods(organizationId: string) {
  return request<{ items: AccountingPeriodItem[] }>(
    `/api/v1/organizations/${organizationId}/accounting-periods`,
  );
}

export function lockAccountingPeriod(
  organizationId: string,
  accountingPeriodId: string,
) {
  return request<AccountingPeriodItem>(
    `/api/v1/organizations/${organizationId}/accounting-periods/${accountingPeriodId}/lock`,
    { method: "POST" },
  );
}

export function listSavingsOpportunities(organizationId: string) {
  return request<{ items: SavingsOpportunityItem[] }>(
    `/api/v1/organizations/${organizationId}/savings-opportunities`,
  );
}

export function createSavingsOpportunity(
  organizationId: string,
  input: {
    source_type: string;
    source_id: string;
    rule_version: string;
    period_key: string;
    title: string;
    department: string;
    category: "cancellation" | "downgrade" | "negotiation" | "seat_recovery" | "cost_avoidance";
    monthly_baseline: string;
    currency: string;
    effective_date: string;
    contract_end: string | null;
    evidence: string;
  },
) {
  return request<SavingsOpportunityItem>(
    `/api/v1/organizations/${organizationId}/savings-opportunities`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function confirmSavingsOpportunity(
  organizationId: string,
  opportunityId: string,
) {
  return request<SavingsOpportunityItem>(
    `/api/v1/organizations/${organizationId}/savings-opportunities/${opportunityId}/confirm`,
    { method: "POST" },
  );
}

export function listOptimizationProjects(organizationId: string) {
  return request<{ items: OptimizationProjectBundle[] }>(
    `/api/v1/organizations/${organizationId}/optimization-projects`,
  );
}

export function createOptimizationProject(
  organizationId: string,
  opportunityId: string,
  input: { owner_name: string; due_date: string },
) {
  return request<OptimizationProjectBundle>(
    `/api/v1/organizations/${organizationId}/savings-opportunities/${opportunityId}/projects`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function realizeSavings(
  organizationId: string,
  projectId: string,
  input: {
    action: "cancelled" | "downgraded" | "negotiated" | "seats_recovered";
    effective_date: string;
    new_monthly_cost: string;
    evidence: string;
  },
) {
  return request<OptimizationProjectBundle>(
    `/api/v1/organizations/${organizationId}/optimization-projects/${projectId}/realize`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function verifySavings(
  organizationId: string,
  projectId: string,
  evidenceReferences: string[],
) {
  return request<OptimizationProjectBundle>(
    `/api/v1/organizations/${organizationId}/optimization-projects/${projectId}/verify`,
    {
      method: "POST",
      body: JSON.stringify({ evidence_references: evidenceReferences }),
    },
  );
}

export function getSavingsSummary(organizationId: string) {
  return request<SavingsSummaryItem>(
    `/api/v1/organizations/${organizationId}/savings-summary`,
  );
}

export function listPaymentInstruments(organizationId: string) {
  return request<{ items: PaymentInstrumentBundle[] }>(
    `/api/v1/organizations/${organizationId}/payment-instruments`,
  );
}

export function createPaymentInstrument(
  organizationId: string,
  input: {
    purchase_request_id: string;
    owner_name: string;
    merchant_lock: string;
    currency: "USD";
    limits: {
      single: string;
      daily: string;
      monthly: string;
      total: string;
    };
  },
  idempotencyKey: string,
) {
  return request<PaymentInstrumentBundle>(
    `/api/v1/organizations/${organizationId}/payment-instruments`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    },
  );
}

export function updatePaymentInstrumentLimits(
  organizationId: string,
  instrumentId: string,
  limits: {
    single: string;
    daily: string;
    monthly: string;
    total: string;
  },
) {
  return request<PaymentInstrumentBundle>(
    `/api/v1/organizations/${organizationId}/payment-instruments/${instrumentId}/limits`,
    {
      method: "PUT",
      body: JSON.stringify(limits),
    },
  );
}

export function freezePaymentInstrument(
  organizationId: string,
  instrumentId: string,
) {
  return request<PaymentInstrumentBundle>(
    `/api/v1/organizations/${organizationId}/payment-instruments/${instrumentId}/freeze`,
    { method: "POST" },
  );
}

export function unfreezePaymentInstrument(
  organizationId: string,
  instrumentId: string,
) {
  return request<PaymentInstrumentBundle>(
    `/api/v1/organizations/${organizationId}/payment-instruments/${instrumentId}/unfreeze`,
    { method: "POST" },
  );
}

export function closePaymentInstrument(
  organizationId: string,
  instrumentId: string,
) {
  return request<PaymentInstrumentBundle>(
    `/api/v1/organizations/${organizationId}/payment-instruments/${instrumentId}/close`,
    { method: "POST" },
  );
}

export function listInvoices(organizationId: string) {
  return request<{ items: InvoiceBundle[] }>(
    `/api/v1/organizations/${organizationId}/invoices`,
  );
}

export function extractInvoice(
  organizationId: string,
  input: {
    source_type: "manual_text" | "email" | "api" | "integration";
    external_id: string;
    filename: string;
    text: string;
  },
  idempotencyKey: string,
) {
  return request<InvoiceBundle>(
    `/api/v1/organizations/${organizationId}/invoices/extract`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    },
  );
}

export function confirmInvoice(
  organizationId: string,
  invoiceId: string,
  input: {
    vendor_name: string;
    invoice_number: string;
    invoice_date: string;
    due_date: string;
    currency: "USD";
    subtotal: string;
    tax: string;
    total: string;
    purchase_order_number: string;
    line_items: Array<{
      description: string;
      quantity: string;
      unit_price: string;
      amount: string;
      category: string;
    }>;
  },
) {
  return request<InvoiceBundle>(
    `/api/v1/organizations/${organizationId}/invoices/${invoiceId}/confirm`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function matchInvoice(organizationId: string, invoiceId: string) {
  return request<InvoiceBundle>(
    `/api/v1/organizations/${organizationId}/invoices/${invoiceId}/match`,
    { method: "POST" },
  );
}

export function listAccountingMappings(organizationId: string) {
  return request<{ items: AccountingMappingItem[] }>(
    `/api/v1/organizations/${organizationId}/accounting-mappings`,
  );
}

export function upsertAccountingMapping(
  organizationId: string,
  input: {
    scope_type: "application" | "vendor" | "category" | "default";
    scope_value: string;
    account_code: string;
    tax_code: string;
    cost_center: string;
    department: string;
    project: string;
  },
) {
  return request<AccountingMappingItem>(
    `/api/v1/organizations/${organizationId}/accounting-mappings`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function resolveInvoiceMapping(
  organizationId: string,
  invoiceId: string,
) {
  return request<ResolvedAccountingMapping>(
    `/api/v1/organizations/${organizationId}/invoices/${invoiceId}/mapping`,
  );
}

export function exportInvoice(
  organizationId: string,
  invoiceId: string,
  idempotencyKey: string,
) {
  return request<InvoiceBundle>(
    `/api/v1/organizations/${organizationId}/invoices/${invoiceId}/export`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    },
  );
}

export function updateInvoice(
  organizationId: string,
  invoiceId: string,
  input: {
    subtotal?: string;
    tax?: string;
    total?: string;
  },
) {
  return request<InvoiceBundle>(
    `/api/v1/organizations/${organizationId}/invoices/${invoiceId}`,
    {
      method: "PATCH",
      body: JSON.stringify(input),
    },
  );
}

export function retryAccountingExport(
  organizationId: string,
  exportId: string,
) {
  return request<NonNullable<InvoiceBundle["export"]>>(
    `/api/v1/organizations/${organizationId}/accounting-exports/${exportId}/retry`,
    { method: "POST" },
  );
}

export function listIntegrationDefinitions(organizationId: string) {
  return request<{ items: IntegrationDefinitionItem[] }>(
    `/api/v1/organizations/${organizationId}/integrations/definitions`,
  );
}

export function listIntegrationConnections(organizationId: string) {
  return request<{ items: IntegrationConnectionItem[] }>(
    `/api/v1/organizations/${organizationId}/integrations/connections`,
  );
}

export function createIntegrationConnection(
  organizationId: string,
  input: {
    definition_key: string;
    display_name: string;
    api_token: string;
    sandbox_options: Record<string, unknown>;
  },
) {
  return request<IntegrationConnectionItem>(
    `/api/v1/organizations/${organizationId}/integrations/connections`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function testIntegrationConnection(
  organizationId: string,
  connectionId: string,
) {
  return request<{ healthy: boolean; message: string }>(
    `/api/v1/organizations/${organizationId}/integrations/connections/${connectionId}/test`,
    { method: "POST" },
  );
}

export function syncIntegrationConnection(
  organizationId: string,
  connectionId: string,
) {
  return request<IntegrationSyncRunItem>(
    `/api/v1/organizations/${organizationId}/integrations/connections/${connectionId}/sync`,
    { method: "POST" },
  );
}

export function listIntegrationSyncRuns(
  organizationId: string,
  connectionId: string,
) {
  return request<{ items: IntegrationSyncRunItem[] }>(
    `/api/v1/organizations/${organizationId}/integrations/connections/${connectionId}/sync-runs`,
  );
}

export function pauseIntegrationConnection(
  organizationId: string,
  connectionId: string,
) {
  return request<IntegrationConnectionItem>(
    `/api/v1/organizations/${organizationId}/integrations/connections/${connectionId}/pause`,
    { method: "POST" },
  );
}

export function resumeIntegrationConnection(
  organizationId: string,
  connectionId: string,
) {
  return request<IntegrationConnectionItem>(
    `/api/v1/organizations/${organizationId}/integrations/connections/${connectionId}/resume`,
    { method: "POST" },
  );
}

export function deleteIntegrationConnection(
  organizationId: string,
  connectionId: string,
) {
  return request<{ status: "deleted"; data_retention: "retain_synced_data" }>(
    `/api/v1/organizations/${organizationId}/integrations/connections/${connectionId}`,
    { method: "DELETE" },
  );
}

export function listReportMetrics(organizationId: string) {
  return request<{ items: ReportMetricDefinitionItem[] }>(
    `/api/v1/organizations/${organizationId}/reports/metrics`,
  );
}

export function listReportDimensions(organizationId: string) {
  return request<{ items: ReportDimensionItem[] }>(
    `/api/v1/organizations/${organizationId}/reports/dimensions`,
  );
}

export function queryReport(organizationId: string, input: ReportQueryPayload) {
  return request<ReportQueryResult>(
    `/api/v1/organizations/${organizationId}/reports/query`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function listSavedReports(organizationId: string) {
  return request<{ items: SavedReportItem[] }>(
    `/api/v1/organizations/${organizationId}/reports/saved-reports`,
  );
}

export function createSavedReport(
  organizationId: string,
  input: {
    name: string;
    description: string;
    query: ReportQueryPayload;
    chart_type: "table" | "bar" | "line" | "area" | "donut";
    visibility: "private" | "organization" | "role" | "member";
  },
) {
  return request<SavedReportItem>(
    `/api/v1/organizations/${organizationId}/reports/saved-reports`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function createReportSnapshot(organizationId: string, reportId: string) {
  return request<ReportSnapshotItem>(
    `/api/v1/organizations/${organizationId}/reports/saved-reports/${reportId}/snapshots`,
    { method: "POST" },
  );
}

export function createReportExport(
  organizationId: string,
  reportId: string,
  format: "csv" | "xlsx" | "pdf",
) {
  return request<ReportExportItem>(
    `/api/v1/organizations/${organizationId}/reports/saved-reports/${reportId}/exports`,
    {
      method: "POST",
      body: JSON.stringify({ format }),
    },
  );
}

export function createReportSubscription(
  organizationId: string,
  reportId: string,
  input: {
    frequency: "daily" | "weekly" | "monthly";
    cron: string;
    timezone: string;
    recipients: string[];
  },
) {
  return request<ReportSubscriptionItem>(
    `/api/v1/organizations/${organizationId}/reports/saved-reports/${reportId}/subscriptions`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export type AuditLogItem = {
  id: string;
  organization_id: string;
  actor_type: string;
  actor_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  ip_address: string | null;
  user_agent_hash: string | null;
  request_id: string | null;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AuditLogExport = {
  format: "json";
  row_count: number;
  rows: AuditLogItem[];
  exported_at: string;
};

export type RetentionPolicyItem = {
  id: string;
  organization_id: string;
  data_type: string;
  retention_days: number;
  action: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type LegalHoldItem = {
  id: string;
  organization_id: string;
  resource_type: string;
  resource_id: string;
  reason: string;
  status: string;
  expires_at: string | null;
  created_at: string;
};

export type DeletionPreview = {
  data_type: string;
  cutoff_at: string | null;
  delete_candidates: string[];
  skipped_legal_hold: string[];
};

export type DeletionJobItem = {
  id: string;
  data_type: string;
  status: string;
  deleted_resource_ids: string[];
  skipped_legal_hold: string[];
  created_at: string;
  completed_at: string | null;
};

export type PrivacyRequestItem = {
  id: string;
  subject_user_id: string;
  type: "access" | "correction" | "deletion" | "portability";
  status: string;
  identity_verified_at: string;
  due_at: string;
  scope: string[];
  requested_changes: Record<string, unknown>;
  result: Record<string, unknown>;
  processing_history: Array<{
    id: string;
    action: string;
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type ComplianceFrameworkItem = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  version: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ComplianceControlItem = {
  id: string;
  organization_id: string;
  framework_id: string;
  code: string;
  title: string;
  description: string;
  status: string;
  frequency_days: number;
  last_reviewed_at: string | null;
  next_review_at: string | null;
  owners: Array<{
    id: string;
    user_id: string;
    role: string;
    created_at: string;
  }>;
  evidence: Array<{
    id: string;
    stored_file_id: string;
    title: string;
    description: string;
    status: string;
    collected_at: string;
    expires_at: string | null;
    created_at: string;
  }>;
  reviews: Array<{
    id: string;
    reviewer_user_id: string;
    outcome: string;
    notes: string;
    reviewed_at: string;
    next_review_at: string | null;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
};

export type IncidentTaskItem = {
  id: string;
  title: string;
  status: string;
  assignee_user_id: string | null;
  due_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SecurityIncidentItem = {
  id: string;
  organization_id: string;
  title: string;
  severity: string;
  status: string;
  summary: string;
  detected_at: string;
  resolved_at: string | null;
  tasks: IncidentTaskItem[];
  created_at: string;
  updated_at: string;
};

export type ApiKeyItem = {
  id: string;
  organization_id: string;
  name: string;
  prefix: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
};

export type ApiKeyCreated = ApiKeyItem & { secret: string };

export type ApiKeyPrincipal = {
  api_key_id: string;
  organization_id: string;
  name: string;
  scopes: string[];
};

export type WebhookEndpointItem = {
  id: string;
  organization_id: string;
  name: string;
  url: string;
  events: string[];
  status: string;
  secret_version: number;
  previous_secret_expires_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WebhookEndpointCreated = WebhookEndpointItem & { secret: string };

export type WebhookDeliveryItem = {
  id: string;
  endpoint_id: string;
  event_id: string;
  event_type: string;
  status: string;
  attempts: number;
  next_attempt_at: string;
  response_status: number | null;
  last_error: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
};

export function listAuditLogs(organizationId: string) {
  return request<{ items: AuditLogItem[] }>(
    `/api/v1/organizations/${organizationId}/audit-logs`,
  );
}

export function exportAuditLogs(organizationId: string) {
  return request<AuditLogExport>(
    `/api/v1/organizations/${organizationId}/audit-logs/export`,
    { method: "POST", body: JSON.stringify({ format: "json" }) },
  );
}

export function createRetentionPolicy(
  organizationId: string,
  input: { retention_days: number; description: string },
) {
  return request<RetentionPolicyItem>(
    `/api/v1/organizations/${organizationId}/retention-policies`,
    {
      method: "POST",
      body: JSON.stringify({ data_type: "stored_file", ...input }),
    },
  );
}

export function createLegalHold(
  organizationId: string,
  input: {
    resource_type: "stored_file" | "user";
    resource_id: string;
    reason: string;
    expires_at?: string | null;
  },
) {
  return request<LegalHoldItem>(
    `/api/v1/organizations/${organizationId}/legal-holds`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function previewRetentionDeletion(organizationId: string) {
  return request<DeletionPreview>(
    `/api/v1/organizations/${organizationId}/retention/deletion-preview?data_type=stored_file`,
  );
}

export function executeRetentionDeletion(
  organizationId: string,
  reauthConfirmed: boolean,
) {
  return request<DeletionJobItem>(
    `/api/v1/organizations/${organizationId}/retention/deletion-jobs`,
    {
      method: "POST",
      body: JSON.stringify({
        data_type: "stored_file",
        reauth_confirmed: reauthConfirmed,
      }),
    },
  );
}

export function listPrivacyRequests() {
  return request<{ items: PrivacyRequestItem[] }>("/api/v1/privacy/requests");
}

export function createPrivacyRequest(input: {
  type: PrivacyRequestItem["type"];
  scope: string[];
  requested_changes?: Record<string, string>;
}) {
  return request<PrivacyRequestItem>("/api/v1/privacy/requests", {
    method: "POST",
    body: JSON.stringify({
      requested_changes: {},
      ...input,
    }),
  });
}

export function processPrivacyRequest(requestId: string, reauthConfirmed: boolean) {
  return request<PrivacyRequestItem>(
    `/api/v1/privacy/requests/${requestId}/process`,
    {
      method: "POST",
      body: JSON.stringify({ reauth_confirmed: reauthConfirmed }),
    },
  );
}

export function listComplianceFrameworks(organizationId: string) {
  return request<{ items: ComplianceFrameworkItem[] }>(
    `/api/v1/organizations/${organizationId}/compliance/frameworks`,
  );
}

export function createComplianceFramework(
  organizationId: string,
  input: { code: string; name: string; version: string; description: string },
) {
  return request<ComplianceFrameworkItem>(
    `/api/v1/organizations/${organizationId}/compliance/frameworks`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function createComplianceControl(
  organizationId: string,
  frameworkId: string,
  input: {
    code: string;
    title: string;
    description: string;
    frequency_days: number;
  },
) {
  return request<ComplianceControlItem>(
    `/api/v1/organizations/${organizationId}/compliance/frameworks/${frameworkId}/controls`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function getComplianceControl(organizationId: string, controlId: string) {
  return request<ComplianceControlItem>(
    `/api/v1/organizations/${organizationId}/compliance/controls/${controlId}`,
  );
}

export function assignComplianceControlOwner(
  organizationId: string,
  controlId: string,
  input: { user_id: string; role: "owner" | "reviewer" },
) {
  return request<ComplianceControlItem["owners"][number]>(
    `/api/v1/organizations/${organizationId}/compliance/controls/${controlId}/owners`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function addComplianceEvidence(
  organizationId: string,
  controlId: string,
  input: {
    stored_file_id: string;
    title: string;
    description: string;
    collected_at?: string | null;
    expires_at?: string | null;
  },
) {
  return request<ComplianceControlItem["evidence"][number]>(
    `/api/v1/organizations/${organizationId}/compliance/controls/${controlId}/evidence`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function reviewComplianceControl(
  organizationId: string,
  controlId: string,
  input: {
    outcome: "effective" | "ineffective" | "needs_attention";
    notes: string;
  },
) {
  return request<ComplianceControlItem["reviews"][number]>(
    `/api/v1/organizations/${organizationId}/compliance/controls/${controlId}/reviews`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function listSecurityIncidents(organizationId: string) {
  return request<{ items: SecurityIncidentItem[] }>(
    `/api/v1/organizations/${organizationId}/security/incidents`,
  );
}

export function createSecurityIncident(
  organizationId: string,
  input: {
    title: string;
    severity: "low" | "medium" | "high" | "critical";
    summary: string;
    detected_at: string;
  },
) {
  return request<SecurityIncidentItem>(
    `/api/v1/organizations/${organizationId}/security/incidents`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function createSecurityIncidentTask(
  organizationId: string,
  incidentId: string,
  input: { title: string; assignee_user_id?: string | null; due_at?: string | null },
) {
  return request<IncidentTaskItem>(
    `/api/v1/organizations/${organizationId}/security/incidents/${incidentId}/tasks`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function updateSecurityIncidentTask(
  organizationId: string,
  incidentId: string,
  taskId: string,
  status: "open" | "in_progress" | "completed" | "cancelled",
) {
  return request<IncidentTaskItem>(
    `/api/v1/organizations/${organizationId}/security/incidents/${incidentId}/tasks/${taskId}`,
    { method: "PATCH", body: JSON.stringify({ status }) },
  );
}

export function listApiKeys(organizationId: string) {
  return request<{ items: ApiKeyItem[] }>(
    `/api/v1/organizations/${organizationId}/api-keys`,
  );
}

export function createApiKey(
  organizationId: string,
  input: { name: string; scopes: string[]; expires_at?: string | null },
) {
  return request<ApiKeyCreated>(
    `/api/v1/organizations/${organizationId}/api-keys`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function verifyApiKey(secret: string, requiredScope?: string) {
  const query = requiredScope
    ? `?required_scope=${encodeURIComponent(requiredScope)}`
    : "";
  return request<ApiKeyPrincipal>(`/api/v1/api-keys/current${query}`, {
    headers: { Authorization: `Bearer ${secret}` },
  });
}

export function revokeApiKey(organizationId: string, apiKeyId: string) {
  return request<ApiKeyItem>(
    `/api/v1/organizations/${organizationId}/api-keys/${apiKeyId}/revoke`,
    { method: "POST" },
  );
}

export function listWebhookEndpoints(organizationId: string) {
  return request<{ items: WebhookEndpointItem[] }>(
    `/api/v1/organizations/${organizationId}/webhooks`,
  );
}

export function createWebhookEndpoint(
  organizationId: string,
  input: { name: string; url: string; events: string[] },
) {
  return request<WebhookEndpointCreated>(
    `/api/v1/organizations/${organizationId}/webhooks`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function rotateWebhookSecret(
  organizationId: string,
  endpointId: string,
  overlapSeconds = 3600,
) {
  return request<{
    id: string;
    secret: string;
    secret_version: number;
    previous_secret_expires_at: string;
  }>(
    `/api/v1/organizations/${organizationId}/webhooks/${endpointId}/rotate-secret`,
    {
      method: "POST",
      body: JSON.stringify({ overlap_seconds: overlapSeconds }),
    },
  );
}

export function testWebhookEndpoint(
  organizationId: string,
  endpointId: string,
  eventType: string,
) {
  return request<WebhookDeliveryItem>(
    `/api/v1/organizations/${organizationId}/webhooks/${endpointId}/test`,
    {
      method: "POST",
      body: JSON.stringify({
        event_type: eventType,
        payload: { source: "web-console", sent_at: new Date().toISOString() },
      }),
    },
  );
}

export function listWebhookDeliveries(organizationId: string, endpointId: string) {
  return request<{ items: WebhookDeliveryItem[] }>(
    `/api/v1/organizations/${organizationId}/webhooks/${endpointId}/deliveries`,
  );
}

export function retryWebhookDelivery(
  organizationId: string,
  endpointId: string,
  deliveryId: string,
) {
  return request<WebhookDeliveryItem>(
    `/api/v1/organizations/${organizationId}/webhooks/${endpointId}/deliveries/${deliveryId}/retry`,
    { method: "POST" },
  );
}

export function listBillingPlans() {
  return request<{ items: BillingPlan[] }>("/api/v1/billing/plans");
}

export function getBillingSummary(organizationId: string) {
  return request<BillingSummary>(
    `/api/v1/organizations/${organizationId}/billing`,
  );
}

export function getBillingUsage(organizationId: string) {
  return request<{ items: BillingUsageMetric[] }>(
    `/api/v1/organizations/${organizationId}/billing/usage`,
  );
}

export function listBillingInvoices(organizationId: string) {
  return request<{ items: BillingInvoice[] }>(
    `/api/v1/organizations/${organizationId}/billing/invoices`,
  );
}

export function previewBillingChange(
  organizationId: string,
  targetPlan: string,
) {
  return request<BillingChangePreview>(
    `/api/v1/organizations/${organizationId}/billing/change-preview`,
    {
      method: "POST",
      body: JSON.stringify({ target_plan: targetPlan }),
    },
  );
}

export function changeBillingPlan(
  organizationId: string,
  targetPlan: string,
) {
  return request<BillingSummary>(
    `/api/v1/organizations/${organizationId}/billing/change-plan`,
    {
      method: "POST",
      body: JSON.stringify({ target_plan: targetPlan }),
    },
  );
}

export function cancelBillingSubscription(organizationId: string) {
  return request<BillingSummary>(
    `/api/v1/organizations/${organizationId}/billing/cancel`,
    { method: "POST" },
  );
}

export function undoBillingCancellation(organizationId: string) {
  return request<BillingSummary>(
    `/api/v1/organizations/${organizationId}/billing/undo-cancellation`,
    { method: "POST" },
  );
}

export function createBillingPortalSession(
  organizationId: string,
  returnUrl: string,
) {
  return request<{ url: string }>(
    `/api/v1/organizations/${organizationId}/billing/portal-session`,
    {
      method: "POST",
      body: JSON.stringify({ return_url: returnUrl }),
    },
  );
}

export function getPublicStatus() {
  return request<PublicStatusOverview>("/api/v1/status");
}

export function subscribeToStatus(email: string) {
  return request<{ status: string }>("/api/v1/status/subscriptions", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export type SupportTicketItem = {
  id: string;
  organization_id: string;
  subject: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  support_tier: string;
  resolution_summary: string | null;
  first_response_due_at: string;
  resolution_due_at: string;
  first_responded_at: string | null;
  sla_paused_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SupportMessageItem = {
  id: string;
  support_ticket_id: string;
  author_type: string;
  body: string;
  internal: boolean;
  created_at: string;
};

export type SupportAgentItem = {
  id: string;
  display_name: string;
  platform_role: string;
};

export type SupportGrantItem = {
  id: string;
  organization_id: string;
  support_user_id: string;
  scopes: string[];
  reason: string;
  approved_by_user_id: string;
  expires_at: string;
  revoked_at: string | null;
  created_at: string;
};

export type SupportDiagnosticItem = {
  id: string;
  connection_id: string;
  resource_type: string;
  status: string;
  failed_count: number;
  attempts: number;
  error_summary: string | null;
  started_at: string;
  finished_at: string | null;
};

export function listSupportTickets(organizationId: string) {
  return request<{ items: SupportTicketItem[] }>(
    `/api/v1/support/tickets?organization_id=${encodeURIComponent(organizationId)}`,
  );
}

export function createSupportTicket(input: {
  organization_id: string;
  subject: string;
  description: string;
  category: string;
  priority: string;
}) {
  return request<SupportTicketItem>("/api/v1/support/tickets", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getSupportTicket(ticketId: string) {
  return request<SupportTicketItem>(`/api/v1/support/tickets/${ticketId}`);
}

export function listSupportMessages(ticketId: string) {
  return request<{ items: SupportMessageItem[] }>(
    `/api/v1/support/tickets/${ticketId}/messages`,
  );
}

export function createCustomerSupportMessage(ticketId: string, body: string) {
  return request<SupportMessageItem>(
    `/api/v1/support/tickets/${ticketId}/messages`,
    { method: "POST", body: JSON.stringify({ body }) },
  );
}

export function listSupportAgents() {
  return request<{ items: SupportAgentItem[] }>("/api/v1/support/agents");
}

export function listSupportGrants(organizationId: string) {
  return request<{ items: SupportGrantItem[] }>(
    `/api/v1/organizations/${organizationId}/support-grants`,
  );
}

export function createSupportGrant(
  organizationId: string,
  input: {
    support_user_id: string;
    scopes: string[];
    reason: string;
    expires_at: string;
  },
) {
  return request<SupportGrantItem>(
    `/api/v1/organizations/${organizationId}/support-grants`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function revokeSupportGrant(organizationId: string, grantId: string) {
  return request<SupportGrantItem>(
    `/api/v1/organizations/${organizationId}/support-grants/${grantId}/revoke`,
    { method: "POST" },
  );
}

export function listOperationalTickets() {
  return request<{ items: SupportTicketItem[] }>(
    "/api/v1/support/operations/tickets",
  );
}

export function listOperationalMessages(ticketId: string) {
  return request<{ items: SupportMessageItem[] }>(
    `/api/v1/support/operations/tickets/${ticketId}/messages`,
  );
}

export function createOperationalMessage(ticketId: string, body: string) {
  return request<SupportMessageItem>(
    `/api/v1/support/operations/tickets/${ticketId}/messages`,
    { method: "POST", body: JSON.stringify({ body }) },
  );
}

export function listOperationalGrants() {
  return request<{ items: SupportGrantItem[] }>(
    "/api/v1/support/operations/grants",
  );
}

export function readSupportDiagnostics(grantId: string, purpose: string) {
  return request<{
    grant_id: string;
    organization_id: string;
    items: SupportDiagnosticItem[];
  }>(`/api/v1/support/grants/${grantId}/diagnostics`, {
    method: "POST",
    body: JSON.stringify({ purpose }),
  });
}

export type AdminStatusComponent = PublicStatusComponent;

export type AdminStatusIncident = {
  id: string;
  component_id: string;
  title: string;
  public_summary: string;
  internal_summary: string;
  impact: string;
  status: string;
  started_at: string;
  resolved_at: string | null;
};

export function listAdminStatusComponents() {
  return request<AdminStatusComponent[]>("/api/v1/admin/status/components");
}

export function createAdminStatusComponent(input: {
  slug: string;
  name: string;
  description: string;
  display_order: number;
}) {
  return request<AdminStatusComponent>("/api/v1/admin/status/components", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createAdminStatusIncident(input: {
  component_id: string;
  title: string;
  public_summary: string;
  internal_summary: string;
  impact: string;
  public_message: string;
  internal_note: string;
}) {
  return request<AdminStatusIncident>("/api/v1/admin/status/incidents", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export type AdminOrganizationItem = {
  id: string;
  name: string;
  slug: string;
  status: string;
  member_count: number;
  plan_key: string | null;
  created_at: string;
};

export type AdminUserItem = {
  id: string;
  email: string;
  display_name: string;
  status: string;
  platform_role: string | null;
  created_at: string;
};

export function listAdminOrganizations() {
  return request<{ items: AdminOrganizationItem[] }>("/api/v1/admin/organizations");
}

export function listAdminUsers() {
  return request<{ items: AdminUserItem[] }>("/api/v1/admin/users");
}

export function runHighRiskAdminAction(
  path: string,
  reason: string,
  password: string,
) {
  return request<{ id: string; status: string }>(path, {
    method: "POST",
    body: JSON.stringify({
      reason,
      reauth_confirmed: true,
      reauth_password: password,
    }),
  });
}

export type KnowledgeBundle = {
  entry: {
    id: string;
    object_type: string;
    key: string;
    status: string;
    published_version_number: number | null;
    created_at: string;
  };
  version: {
    id: string;
    entry_id: string;
    version_number: number;
    status: string;
    data: Record<string, unknown>;
    change_summary: string;
    created_by_user_id: string;
    reviewed_by_user_id: string | null;
    published_by_user_id: string | null;
    created_at: string;
    reviewed_at: string | null;
    published_at: string | null;
  };
};

export function listAdminKnowledge(collection: string) {
  return request<{ items: KnowledgeBundle[] }>(`/api/v1/admin/${collection}`);
}

export function createAdminKnowledge(
  collection: string,
  input: {
    key: string;
    data: Record<string, unknown>;
    change_summary: string;
  },
) {
  return request<KnowledgeBundle>(`/api/v1/admin/${collection}`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createAdminKnowledgeDraft(
  entryId: string,
  input: { data: Record<string, unknown>; change_summary: string },
) {
  return request<KnowledgeBundle["version"]>(
    `/api/v1/admin/knowledge/${entryId}/drafts`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function submitAdminKnowledgeReview(versionId: string) {
  return request<KnowledgeBundle["version"]>(
    `/api/v1/admin/knowledge/versions/${versionId}/submit-review`,
    { method: "POST" },
  );
}

export function approveAdminKnowledgeVersion(versionId: string) {
  return request<KnowledgeBundle["version"]>(
    `/api/v1/admin/knowledge/versions/${versionId}/approve`,
    { method: "POST" },
  );
}

export function publishAdminKnowledgeVersion(
  versionId: string,
  reason: string,
  password: string,
) {
  return request<KnowledgeBundle>(
    `/api/v1/admin/knowledge/versions/${versionId}/publish`,
    {
      method: "POST",
      body: JSON.stringify({
        reason,
        reauth_confirmed: true,
        reauth_password: password,
      }),
    },
  );
}

export function rollbackAdminKnowledge(
  entryId: string,
  targetVersion: number,
  reason: string,
  password: string,
) {
  return request<KnowledgeBundle>(
    `/api/v1/admin/knowledge/${entryId}/rollback`,
    {
      method: "POST",
      body: JSON.stringify({
        target_version: targetVersion,
        reason,
        reauth_confirmed: true,
        reauth_password: password,
      }),
    },
  );
}
