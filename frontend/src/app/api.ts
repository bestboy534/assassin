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
