import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { routes } from "../app/router";

const session = {
  user: {
    id: "user-1",
    email: "owner@example.com",
    display_name: "负责人",
    status: "active",
  },
  organizations: [
    {
      id: "org-1",
      name: "Acme 中国",
      slug: "acme",
      role: "owner",
    },
  ],
};

let applicationItems: Array<{
  id: string;
  organization_id: string;
  name: string;
  category: string;
  status: string;
  business_owner: string | null;
  technical_owner: string | null;
  risk_level: string;
  approved: boolean;
}>;
let auditRuns: Array<{
  id: string;
  organization_id: string;
  status: string;
  source_hint: string;
  items_count: number;
  total_monthly_cost_usd: number;
  created_at: string;
}>;
let purchaseRequests: Array<{
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
}>;
let approvalTasks: Array<{
  id: string;
  organization_id: string;
  purchase_request_id: string;
  assignee_role: string;
  status: string;
  created_at: string;
}>;
let contracts: Array<{
  id: string;
  organization_id: string;
  name: string;
  vendor_name: string;
  application_name: string | null;
  owner_name: string;
  status: string;
  current_version_id: string | null;
  created_at: string;
}>;
let renewals: Array<{
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
}>;
let vendors: Array<{
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
}>;
let riskFindings: Array<{
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
}>;
let budgets: Array<{
  id: string;
  organization_id: string;
  name: string;
  fiscal_year: number;
  department: string;
  amount: string;
  currency: string;
  status: string;
  created_at: string;
}>;
let spendTransactions: Array<{
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
  splits: Array<{
    id: string;
    amount: string;
    department: string;
    category: string;
  }>;
}>;
let transactionAnomalies: Array<{
  id: string;
  transaction_id: string;
  budget_id: string | null;
  code: string;
  rule_version: string;
  baseline_amount: string;
  observed_amount: string;
  status: string;
  evidence: string;
}>;
let budgetSummary: {
  budget_id: string;
  currency: string;
  allocated: string;
  actual: string;
  committed: string;
  forecast: string;
  remaining: string;
} | null;
let accountingPeriod: {
  id: string;
  organization_id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
  locked_at: string | null;
} | null;
let savingsOpportunities: Array<{
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
  baseline: {
    id: string;
    version: number;
    monthly_cost: string;
    calculation_months: number;
    amount: string;
    calculation_method: string;
    effective_date: string;
    contract_end: string | null;
  };
}>;
let optimizationProjects: Array<{
  project: {
    id: string;
    opportunity_id: string;
    owner_name: string;
    due_date: string;
    status: string;
    target_amount: string;
    currency: string;
  };
  tasks: Array<{ id: string; title: string; status: string }>;
  result: {
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
  } | null;
}>;
let savingsSummary: {
  currency: string;
  estimated: string;
  realized: string;
  verified: string;
  cost_avoidance: string;
};
let paymentInstruments: Array<{
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
}>;
let invoiceBundles: Array<{
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
  line_items: Array<{
    id: string;
    description: string;
    quantity: string;
    unit_price: string;
    amount: string;
    category: string;
  }>;
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
    explanation: Record<string, boolean>;
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
}>;
let accountingMappings: Array<{
  id: string;
  scope_type: string;
  scope_value: string;
  account_code: string;
  tax_code: string;
  cost_center: string;
  department: string;
  project: string;
}>;
let integrationDefinitions: Array<{
  id: string;
  key: string;
  name: string;
  provider: string;
  category: string;
  auth_type: string;
  capabilities: string[];
  resource_types: string[];
  status: string;
}>;
let integrationConnections: Array<{
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
  fail_on_page?: number;
}>;
let syncRunsByConnection: Record<
  string,
  Array<{
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
  }>
>;

beforeEach(() => {
  applicationItems = [];
  auditRuns = [];
  purchaseRequests = [];
  approvalTasks = [];
  contracts = [];
  renewals = [];
  vendors = [];
  riskFindings = [];
  budgets = [];
  spendTransactions = [];
  transactionAnomalies = [];
  budgetSummary = null;
  accountingPeriod = null;
  savingsOpportunities = [];
  optimizationProjects = [];
  savingsSummary = {
    currency: "USD",
    estimated: "0.0000",
    realized: "0.0000",
    verified: "0.0000",
    cost_avoidance: "0.0000",
  };
  paymentInstruments = [];
  invoiceBundles = [];
  accountingMappings = [];
  integrationDefinitions = [
    {
      id: "definition-fake",
      key: "fake_identity",
      name: "Sandbox 身份目录",
      provider: "fake_identity",
      category: "identity",
      auth_type: "api_token",
      capabilities: ["applications.read", "users.read", "groups.read"],
      resource_types: ["applications"],
      status: "available",
    },
  ];
  integrationConnections = [];
  syncRunsByConnection = {};
  vi.spyOn(window, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/v1/auth/me")) {
      return Response.json(session);
    }
    if (url.endsWith("/api/v1/organizations/org-1/applications") && method === "GET") {
      return Response.json({
        items: applicationItems,
      });
    }
    if (url.endsWith("/api/v1/organizations/org-1/applications") && method === "POST") {
      const body = JSON.parse(String(init?.body));
      const created = {
        id: "app-created",
        organization_id: "org-1",
        name: body.name,
        category: body.category,
        status: "active",
        business_owner: body.business_owner,
        technical_owner: body.technical_owner,
        risk_level: "unknown",
        approved: body.approved,
      };
      applicationItems = [created, ...applicationItems];
      return Response.json(created, { status: 201 });
    }
    if (url.endsWith("/api/v1/organizations/org-1/analysis-runs") && method === "GET") {
      return Response.json({ items: auditRuns });
    }
    if (url.endsWith("/api/v1/organizations/org-1/analysis-runs") && method === "POST") {
      const created = {
        id: "run-created",
        organization_id: "org-1",
        status: "completed",
        source_hint: "csv",
        items_count: 1,
        total_monthly_cost_usd: 20,
        created_at: "2026-06-11T10:00:00Z",
      };
      auditRuns = [created, ...auditRuns];
      return Response.json(
        {
          run: created,
          items: [
            {
              id: "sub-1",
              software_name: "ChatGPT",
              merchant_name: "OPENAI",
              amount: 20,
              currency: "USD",
              billing_cycle: "monthly",
              transaction_date: "2026-05-01",
              normalized_amount_usd: 20,
              monthly_cost_usd: 20,
              status: "need_confirm",
              risk_type: "none",
              confidence: 0.9,
              evidence: "OPENAI row",
              needs_user_confirmation: true,
              cancel_url: null,
              fallback_search_url: null,
              support_email: null,
              guide_steps: [],
              risk_note: null,
            },
          ],
        },
        { status: 201 },
      );
    }
    if (url.endsWith("/api/v1/organizations/org-1/purchase-requests") && method === "GET") {
      return Response.json({ items: purchaseRequests });
    }
    if (url.endsWith("/api/v1/organizations/org-1/purchase-requests") && method === "POST") {
      const body = JSON.parse(String(init?.body));
      const created = {
        id: "request-created",
        organization_id: "org-1",
        software_name: body.software_name,
        business_reason: body.business_reason,
        estimated_monthly_cost_usd: body.estimated_monthly_cost_usd,
        department: body.department,
        handles_sensitive_data: body.handles_sensitive_data,
        data_categories: body.data_categories,
        status: "draft",
        current_approval_task_id: null,
      };
      purchaseRequests = [created, ...purchaseRequests];
      return Response.json(created, { status: 201 });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/purchase-requests/request-created/submit") &&
      method === "POST"
    ) {
      purchaseRequests = purchaseRequests.map(item =>
        item.id === "request-created"
          ? { ...item, status: "in_review", current_approval_task_id: "task-created" }
          : item,
      );
      approvalTasks = [
        {
          id: "task-created",
          organization_id: "org-1",
          purchase_request_id: "request-created",
          assignee_role: "finance",
          status: "pending",
          created_at: "2026-06-11T10:05:00Z",
        },
        ...approvalTasks,
      ];
      return Response.json(purchaseRequests.find(item => item.id === "request-created"));
    }
    if (url.endsWith("/api/v1/organizations/org-1/approval-tasks") && method === "GET") {
      return Response.json({ items: approvalTasks });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/approval-tasks/task-created/approve") &&
      method === "POST"
    ) {
      purchaseRequests = purchaseRequests.map(item =>
        item.id === "request-created" ? { ...item, status: "approved" } : item,
      );
      approvalTasks = approvalTasks.map(item =>
        item.id === "task-created" ? { ...item, status: "approved" } : item,
      );
      return Response.json(
        {
          id: "task-created",
          organization_id: "org-1",
          purchase_request_id: "request-created",
          assignee_role: "finance",
          status: "approved",
          created_at: "2026-06-11T10:05:00Z",
        },
        { status: 200 },
      );
    }
    if (url.endsWith("/api/v1/organizations/org-1/contracts") && method === "GET") {
      return Response.json({ items: contracts });
    }
    if (url.endsWith("/api/v1/organizations/org-1/renewals") && method === "GET") {
      return Response.json({ items: renewals });
    }
    if (url.endsWith("/api/v1/organizations/org-1/contracts") && method === "POST") {
      const body = JSON.parse(String(init?.body));
      const contract = {
        id: "contract-created",
        organization_id: "org-1",
        name: body.name,
        vendor_name: body.vendor_name,
        application_name: body.application_name,
        owner_name: body.owner_name,
        status: "draft",
        current_version_id: "version-created",
        created_at: "2026-06-11T10:10:00Z",
      };
      const version = {
        id: "version-created",
        organization_id: "org-1",
        contract_id: "contract-created",
        version_number: 1,
        status: "draft",
        start_date: body.start_date,
        end_date: body.end_date,
        amount: body.amount,
        currency: body.currency,
        billing_frequency: body.billing_frequency,
        auto_renew: body.auto_renew,
        notice_period_days: body.notice_period_days,
        signed_at: null,
      };
      contracts = [contract, ...contracts];
      return Response.json({ contract, version, renewal: null }, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/contracts/contract-created/versions/version-created/mark-signed",
      ) &&
      method === "POST"
    ) {
      const contract = {
        ...contracts.find(item => item.id === "contract-created")!,
        status: "active",
        current_version_id: "version-created",
      };
      contracts = [contract, ...contracts.filter(item => item.id !== contract.id)];
      const version = {
        id: "version-created",
        organization_id: "org-1",
        contract_id: "contract-created",
        version_number: 1,
        status: "signed",
        start_date: "2026-02-01",
        end_date: "2027-01-31",
        amount: 12000,
        currency: "USD",
        billing_frequency: "yearly",
        auto_renew: true,
        notice_period_days: 60,
        signed_at: "2026-06-11T10:11:00Z",
      };
      const renewal = {
        id: "renewal-created",
        organization_id: "org-1",
        contract_id: "contract-created",
        source_version_id: "version-created",
        renewal_date: "2027-01-31",
        decision_deadline: "2026-12-02",
        owner_name: "运营负责人",
        status: "upcoming",
        decision: null,
        current_amount: 12000,
        currency: "USD",
      };
      renewals = [renewal, ...renewals];
      return Response.json({ contract, version, renewal });
    }
    if (url.endsWith("/api/v1/organizations/org-1/vendors") && method === "GET") {
      return Response.json({ items: vendors });
    }
    if (url.endsWith("/api/v1/organizations/org-1/risk-findings") && method === "GET") {
      return Response.json({ items: riskFindings });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/vendors/vendor-created/assessments/latest",
      ) &&
      method === "GET"
    ) {
      return Response.json({ item: null });
    }
    if (url.endsWith("/api/v1/organizations/org-1/vendors") && method === "POST") {
      const body = JSON.parse(String(init?.body));
      const vendor = {
        id: "vendor-created",
        organization_id: "org-1",
        name: body.name,
        domain: body.domain,
        country_code: body.country_code,
        category: body.category,
        status: "active",
        business_owner: body.business_owner,
        risk_owner: body.risk_owner,
        overall_risk_score: null,
        risk_level: "not_assessed",
        created_at: "2026-06-11T10:20:00Z",
      };
      vendors = [vendor, ...vendors];
      return Response.json(vendor, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/vendors/vendor-created/assessments",
      ) &&
      method === "POST"
    ) {
      const dimensions = {
        security: { score: 80, reasons: ["未提供 SOC 2 报告"] },
        privacy: { score: 90, reasons: ["处理敏感数据", "未提供数据处理协议"] },
        financial: { score: 85, reasons: ["财务稳定性评估为 weak"] },
        operational: { score: 75, reasons: ["服务关键性为 high"] },
        compliance: { score: 80, reasons: ["合规证据缺失"] },
      };
      riskFindings = Object.entries(dimensions).map(([dimension, value], index) => ({
        id: `finding-${index + 1}`,
        vendor_id: "vendor-created",
        assessment_id: "assessment-created",
        dimension,
        title: `${dimension} 风险需要处理`,
        description: value.reasons.join("；"),
        severity: value.score >= 80 ? "high" : "medium",
        status: "open",
        owner_name: "安全负责人",
        due_date: "2026-07-11",
        mitigation_plan: null,
        accepted_reason: null,
        accepted_until: null,
      }));
      vendors = vendors.map(item =>
        item.id === "vendor-created"
          ? { ...item, overall_risk_score: 82, risk_level: "high" }
          : item,
      );
      return Response.json(
        {
          assessment: {
            id: "assessment-created",
            vendor_id: "vendor-created",
            questionnaire_version: 1,
            rule_version: "vendor-risk-v1",
            status: "completed",
            total_score: 82,
            dimensions,
            submitted_at: "2026-06-11T10:21:00Z",
          },
          findings: riskFindings,
        },
        { status: 201 },
      );
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/risk-findings/finding-1/accept",
      ) &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const accepted = {
        ...riskFindings[0],
        status: "accepted",
        accepted_reason: body.reason,
        accepted_until: body.expires_at,
      };
      riskFindings = [accepted, ...riskFindings.slice(1)];
      return Response.json(accepted);
    }
    if (url.endsWith("/api/v1/organizations/org-1/budgets") && method === "GET") {
      return Response.json({ items: budgets });
    }
    if (url.endsWith("/api/v1/organizations/org-1/transactions") && method === "GET") {
      return Response.json({ items: spendTransactions });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/transaction-anomalies") &&
      method === "GET"
    ) {
      return Response.json({ items: transactionAnomalies });
    }
    if (url.endsWith("/api/v1/organizations/org-1/budgets") && method === "POST") {
      const body = JSON.parse(String(init?.body));
      const budget = {
        id: "budget-created",
        organization_id: "org-1",
        name: body.name,
        fiscal_year: body.fiscal_year,
        department: body.department,
        amount: Number(body.amount).toFixed(4),
        currency: body.currency,
        status: "active",
        created_at: "2026-06-11T10:30:00Z",
      };
      budgets = [budget, ...budgets];
      budgetSummary = {
        budget_id: budget.id,
        currency: budget.currency,
        allocated: budget.amount,
        actual: "0.0000",
        committed: "0.0000",
        forecast: "0.0000",
        remaining: budget.amount,
      };
      return Response.json(budget, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/budgets/budget-created/commitments",
      ) &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      if (budgetSummary) {
        budgetSummary = {
          ...budgetSummary,
          [body.commitment_type]: Number(body.amount).toFixed(4),
        };
        budgetSummary.remaining = (
          Number(budgetSummary.allocated) -
          Number(budgetSummary.actual) -
          Number(budgetSummary.committed) -
          Number(budgetSummary.forecast)
        ).toFixed(4);
      }
      return Response.json(
        {
          id: `commitment-${body.commitment_type}`,
          budget_id: "budget-created",
          commitment_type: body.commitment_type,
          amount: Number(body.amount).toFixed(4),
          description: body.description,
        },
        { status: 201 },
      );
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/budgets/budget-created/summary") &&
      method === "GET"
    ) {
      return Response.json(budgetSummary);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/transactions/import") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const row = body.rows[0];
      const existing = spendTransactions.find(item => item.external_id === row.external_id);
      if (existing) {
        return Response.json(
          { created_count: 0, existing_count: 1, items: [existing] },
          { status: 201 },
        );
      }
      const transaction = {
        id: "transaction-created",
        organization_id: "org-1",
        source_provider: body.source_provider,
        source_account_id: body.source_account_id,
        external_id: row.external_id,
        transaction_date: row.transaction_date,
        merchant_name: row.merchant_name,
        description: row.description,
        amount: Number(row.amount).toFixed(4),
        currency: row.currency,
        department: row.department,
        category: null,
        application_id: null,
        match_confidence: "0.0000",
        splits: [],
      };
      spendTransactions = [transaction, ...spendTransactions];
      if (budgetSummary) {
        budgetSummary = {
          ...budgetSummary,
          actual: transaction.amount,
        };
        budgetSummary.remaining = (
          Number(budgetSummary.allocated) -
          Number(budgetSummary.actual) -
          Number(budgetSummary.committed) -
          Number(budgetSummary.forecast)
        ).toFixed(4);
        if (Number(budgetSummary.actual) > Number(budgetSummary.allocated)) {
          transactionAnomalies = [
            {
              id: "anomaly-created",
              transaction_id: transaction.id,
              budget_id: budgetSummary.budget_id,
              code: "budget_exceeded",
              rule_version: "spend-anomaly-v1",
              baseline_amount: budgetSummary.allocated,
              observed_amount: budgetSummary.actual,
              status: "open",
              evidence: "IT actual exceeds allocated budget",
            },
          ];
        }
      }
      return Response.json(
        { created_count: 1, existing_count: 0, items: [transaction] },
        { status: 201 },
      );
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/transactions/transaction-created",
      ) &&
      method === "PATCH"
    ) {
      const body = JSON.parse(String(init?.body));
      spendTransactions = spendTransactions.map(item =>
        item.id === "transaction-created" ? { ...item, ...body } : item,
      );
      return Response.json(spendTransactions[0]);
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/transactions/transaction-created/splits",
      ) &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      spendTransactions = spendTransactions.map(item =>
        item.id === "transaction-created"
          ? {
              ...item,
              splits: body.splits.map(
                (
                  split: { amount: string; department: string; category: string },
                  index: number,
                ) => ({
                  id: `split-${index + 1}`,
                  amount: Number(split.amount).toFixed(4),
                  department: split.department,
                  category: split.category,
                }),
              ),
            }
          : item,
      );
      transactionAnomalies = transactionAnomalies.map(item => ({
        ...item,
        status: "resolved",
      }));
      if (budgetSummary) {
        budgetSummary = {
          ...budgetSummary,
          actual: "5000.0000",
        };
        budgetSummary.remaining = (
          Number(budgetSummary.allocated) -
          Number(budgetSummary.actual) -
          Number(budgetSummary.committed) -
          Number(budgetSummary.forecast)
        ).toFixed(4);
      }
      return Response.json(spendTransactions[0]);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/accounting-periods") &&
      method === "GET"
    ) {
      return Response.json({ items: accountingPeriod ? [accountingPeriod] : [] });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/accounting-periods") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      accountingPeriod = {
        id: "period-created",
        organization_id: "org-1",
        name: body.name,
        start_date: body.start_date,
        end_date: body.end_date,
        status: "open",
        locked_at: null,
      };
      return Response.json(accountingPeriod, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/accounting-periods/period-created/lock",
      ) &&
      method === "POST"
    ) {
      accountingPeriod = {
        ...accountingPeriod!,
        status: "locked",
        locked_at: "2026-06-30T23:59:00Z",
      };
      return Response.json(accountingPeriod);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/savings-opportunities") &&
      method === "GET"
    ) {
      return Response.json({ items: savingsOpportunities });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/optimization-projects") &&
      method === "GET"
    ) {
      return Response.json({ items: optimizationProjects });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/savings-summary") &&
      method === "GET"
    ) {
      return Response.json(savingsSummary);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/savings-opportunities") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const months = body.contract_end ? 6 : 12;
      const estimated = (Number(body.monthly_baseline) * months).toFixed(4);
      const opportunity = {
        id: "opportunity-created",
        organization_id: "org-1",
        source_type: body.source_type,
        source_id: body.source_id,
        rule_version: body.rule_version,
        period_key: body.period_key,
        title: body.title,
        department: body.department,
        category: body.category,
        status: "new",
        estimated_amount: estimated,
        currency: body.currency,
        evidence: body.evidence,
        created_at: "2026-06-11T11:00:00Z",
        baseline: {
          id: "baseline-created",
          version: 1,
          monthly_cost: Number(body.monthly_baseline).toFixed(4),
          calculation_months: months,
          amount: estimated,
          calculation_method: body.contract_end ? "remaining_term" : "annualized",
          effective_date: body.effective_date,
          contract_end: body.contract_end,
        },
      };
      savingsOpportunities = [opportunity];
      savingsSummary = { ...savingsSummary, estimated };
      return Response.json(opportunity, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/savings-opportunities/opportunity-created/confirm",
      ) &&
      method === "POST"
    ) {
      savingsOpportunities = savingsOpportunities.map(item => ({
        ...item,
        status: "confirmed",
      }));
      return Response.json(savingsOpportunities[0]);
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/savings-opportunities/opportunity-created/projects",
      ) &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const bundle = {
        project: {
          id: "project-created",
          opportunity_id: "opportunity-created",
          owner_name: body.owner_name,
          due_date: body.due_date,
          status: "in_progress",
          target_amount: savingsOpportunities[0].estimated_amount,
          currency: "USD",
        },
        tasks: [
          {
            id: "task-created",
            title: "确认取消路径与负责人",
            status: "open",
          },
        ],
        result: null,
      };
      optimizationProjects = [bundle];
      savingsOpportunities = savingsOpportunities.map(item => ({
        ...item,
        status: "in_progress",
      }));
      return Response.json(bundle, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/optimization-projects/project-created/realize",
      ) &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const result = {
        id: "result-created",
        project_id: "project-created",
        status: "realized",
        action: body.action,
        effective_date: body.effective_date,
        new_monthly_cost: Number(body.new_monthly_cost).toFixed(4),
        realized_amount: "600.0000",
        verified_amount: "0.0000",
        realization_evidence: body.evidence,
        evidence_references: [],
        verified_at: null,
      };
      optimizationProjects = optimizationProjects.map(bundle => ({
        ...bundle,
        project: { ...bundle.project, status: "realized" },
        result,
      }));
      savingsSummary = { ...savingsSummary, realized: "600.0000" };
      return Response.json(optimizationProjects[0]);
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/optimization-projects/project-created/verify",
      ) &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      optimizationProjects = optimizationProjects.map(bundle => ({
        ...bundle,
        project: { ...bundle.project, status: "verified" },
        result: {
          ...bundle.result!,
          status: "verified",
          verified_amount: "600.0000",
          evidence_references: body.evidence_references,
          verified_at: "2026-08-01T09:00:00Z",
        },
      }));
      savingsSummary = { ...savingsSummary, verified: "600.0000" };
      return Response.json(optimizationProjects[0]);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/payment-instruments") &&
      method === "GET"
    ) {
      return Response.json({ items: paymentInstruments });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/payment-instruments") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const purchase = purchaseRequests.find(
        item => item.id === body.purchase_request_id,
      )!;
      const bundle = {
        instrument: {
          id: "instrument-created",
          purchase_request_id: body.purchase_request_id,
          provider: "fake",
          external_id: "sandbox_notion",
          brand: "Visa",
          last4: "4242",
          status: "active",
          sandbox: true,
          owner_name: body.owner_name,
          department: purchase.department,
          merchant_lock: body.merchant_lock,
          currency: body.currency,
        },
        limits: {
          single: Number(body.limits.single).toFixed(4),
          daily: Number(body.limits.daily).toFixed(4),
          monthly: Number(body.limits.monthly).toFixed(4),
          total: Number(body.limits.total).toFixed(4),
        },
      };
      paymentInstruments = [bundle];
      return Response.json(bundle, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/payment-instruments/instrument-created/limits",
      ) &&
      method === "PUT"
    ) {
      const body = JSON.parse(String(init?.body));
      paymentInstruments = paymentInstruments.map(bundle => ({
        ...bundle,
        limits: {
          single: Number(body.single).toFixed(4),
          daily: Number(body.daily).toFixed(4),
          monthly: Number(body.monthly).toFixed(4),
          total: Number(body.total).toFixed(4),
        },
      }));
      return Response.json(paymentInstruments[0]);
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/payment-instruments/instrument-created/freeze",
      ) &&
      method === "POST"
    ) {
      paymentInstruments = paymentInstruments.map(bundle => ({
        ...bundle,
        instrument: { ...bundle.instrument, status: "freeze_pending" },
      }));
      return Response.json(paymentInstruments[0]);
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/payment-instruments/instrument-created/unfreeze",
      ) &&
      method === "POST"
    ) {
      paymentInstruments = paymentInstruments.map(bundle => ({
        ...bundle,
        instrument: { ...bundle.instrument, status: "unfreeze_pending" },
      }));
      return Response.json(paymentInstruments[0]);
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/payment-instruments/instrument-created/close",
      ) &&
      method === "POST"
    ) {
      paymentInstruments = paymentInstruments.map(bundle => ({
        ...bundle,
        instrument: { ...bundle.instrument, status: "close_pending" },
      }));
      return Response.json(paymentInstruments[0]);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/invoices") &&
      method === "GET"
    ) {
      return Response.json({ items: invoiceBundles });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/accounting-mappings") &&
      method === "GET"
    ) {
      return Response.json({ items: accountingMappings });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/invoices/extract") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const bundle = {
        invoice: {
          id: "invoice-created",
          organization_id: "org-1",
          vendor_name: "Notion Labs",
          invoice_number: "INV-2026-001",
          invoice_date: "2026-07-10",
          due_date: "2026-08-09",
          currency: "USD",
          subtotal: "100.0000",
          tax: "15.0000",
          total: "118.0000",
          purchase_order_number: "",
          status: "review_required",
          exception_codes: ["amount_imbalance"],
          duplicate_of_id: null,
          current_version: 1,
          filename: body.filename,
          created_at: "2026-07-10T09:00:00Z",
        },
        line_items: [
          {
            id: "line-created",
            description: "Notion enterprise subscription",
            quantity: "1.0000",
            unit_price: "118.0000",
            amount: "118.0000",
            category: "software",
          },
        ],
        extraction: {
          provider: "fake_ocr",
          status: "completed",
          fields: {
            total: {
              value: "118.00",
              confidence: "0.9900",
              evidence: { page: 1, line: 8, text: "total: 118.00" },
            },
          },
        },
        match: null,
        export: null,
      };
      invoiceBundles = [bundle];
      return Response.json(bundle, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/invoices/invoice-created/confirm",
      ) &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      invoiceBundles = invoiceBundles.map(bundle => ({
        ...bundle,
        invoice: {
          ...bundle.invoice,
          ...body,
          subtotal: Number(body.subtotal).toFixed(4),
          tax: Number(body.tax).toFixed(4),
          total: Number(body.total).toFixed(4),
          status: "ready",
          exception_codes: [],
          current_version: 2,
        },
      }));
      return Response.json(invoiceBundles[0]);
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/invoices/invoice-created/match",
      ) &&
      method === "POST"
    ) {
      invoiceBundles = invoiceBundles.map(bundle => ({
        ...bundle,
        match: {
          id: "match-created",
          vendor_id: "vendor-1",
          contract_id: "contract-1",
          transaction_id: "transaction-1",
          application_id: "app-1",
          purchase_request_id: null,
          confidence: "1.0000",
          status: "matched",
          explanation: {
            vendor: true,
            contract: true,
            transaction: true,
            application: true,
          },
        },
      }));
      return Response.json(invoiceBundles[0]);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/accounting-mappings") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const mapping = { id: "mapping-created", ...body };
      accountingMappings = [mapping];
      return Response.json(mapping, { status: 201 });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/invoices/invoice-created/mapping",
      ) &&
      method === "GET"
    ) {
      const mapping = accountingMappings[0];
      return Response.json({
        mapping_id: mapping.id,
        resolved_scope_type: mapping.scope_type,
        account_code: mapping.account_code,
        tax_code: mapping.tax_code,
        cost_center: mapping.cost_center,
        department: mapping.department,
        project: mapping.project,
      });
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/invoices/invoice-created/export",
      ) &&
      method === "POST"
    ) {
      invoiceBundles = invoiceBundles.map(bundle => ({
        ...bundle,
        invoice: { ...bundle.invoice, status: "synced" },
        export: {
          id: "export-created",
          invoice_id: "invoice-created",
          provider: "fake",
          status: "synced",
          external_id: "sandbox_bill_notion",
          external_version: bundle.invoice.current_version,
          exported_invoice_version: bundle.invoice.current_version,
          diff: {},
          attempts: 1,
        },
      }));
      return Response.json(invoiceBundles[0]);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/invoices/invoice-created") &&
      method === "PATCH"
    ) {
      const body = JSON.parse(String(init?.body));
      invoiceBundles = invoiceBundles.map(bundle => ({
        ...bundle,
        invoice: {
          ...bundle.invoice,
          subtotal: Number(body.subtotal).toFixed(4),
          tax: Number(body.tax).toFixed(4),
          total: Number(body.total).toFixed(4),
          current_version: bundle.invoice.current_version + 1,
          status: "out_of_sync",
        },
        export: {
          ...bundle.export!,
          status: "out_of_sync",
          diff: {
            total: { external: "118.0000", local: "120.0000" },
          },
        },
      }));
      return Response.json(invoiceBundles[0]);
    }
    if (
      url.endsWith(
        "/api/v1/organizations/org-1/accounting-exports/export-created/retry",
      ) &&
      method === "POST"
    ) {
      invoiceBundles = invoiceBundles.map(bundle => ({
        ...bundle,
        invoice: { ...bundle.invoice, status: "synced" },
        export: {
          ...bundle.export!,
          status: "synced",
          diff: {},
          attempts: bundle.export!.attempts + 1,
        },
      }));
      return Response.json(invoiceBundles[0].export);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/integrations/definitions") &&
      method === "GET"
    ) {
      return Response.json({ items: integrationDefinitions });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/integrations/connections") &&
      method === "GET"
    ) {
      return Response.json({ items: integrationConnections });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/integrations/connections") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const connection = {
        id: `connection-${integrationConnections.length + 1}`,
        organization_id: "org-1",
        definition_key: body.definition_key,
        definition_name: "Sandbox 身份目录",
        display_name: body.display_name,
        status: "connected",
        auth_type: "api token",
        credential_label: "API token",
        credential_last4: String(body.api_token).slice(-4),
        capabilities: ["applications.read", "users.read", "groups.read"],
        resource_types: ["applications"],
        last_health_status: null,
        last_sync_at: null,
        created_at: "2026-07-10T09:00:00Z",
        fail_on_page: body.sandbox_options?.fail_on_page,
      };
      integrationConnections = [connection, ...integrationConnections];
      syncRunsByConnection[connection.id] = [];
      return Response.json(connection, { status: 201 });
    }
    const connectionId = url.match(/integrations\/connections\/([^/]+)/)?.[1];
    if (connectionId && url.endsWith(`/${connectionId}/test`) && method === "POST") {
      integrationConnections = integrationConnections.map(connection =>
        connection.id === connectionId
          ? { ...connection, last_health_status: "healthy" }
          : connection,
      );
      return Response.json({
        healthy: true,
        message: "Sandbox 身份目录连接正常",
      });
    }
    if (connectionId && url.endsWith(`/${connectionId}/sync`) && method === "POST") {
      const connection = integrationConnections.find(item => item.id === connectionId)!;
      const failed = connection.fail_on_page === 2;
      const run = failed
        ? {
            id: `run-${connectionId}-failed`,
            connection_id: connectionId,
            resource_type: "applications",
            status: "failed",
            cursor_before: null,
            cursor_after: null,
            read_count: 1,
            created_count: 0,
            updated_count: 0,
            skipped_count: 0,
            failed_count: 1,
            error_summary: "Sandbox provider failed on page 2",
            started_at: "2026-07-10T09:00:00Z",
            finished_at: "2026-07-10T09:00:01Z",
            errors: [
              {
                code: "provider_error",
                message: "Sandbox provider failed on page 2",
                external_id: null,
                retryable: false,
              },
            ],
          }
        : {
            id: `run-${connectionId}-ok`,
            connection_id: connectionId,
            resource_type: "applications",
            status: "succeeded",
            cursor_before: null,
            cursor_after: "page-2",
            read_count: 2,
            created_count: 2,
            updated_count: 0,
            skipped_count: 0,
            failed_count: 0,
            error_summary: null,
            started_at: "2026-07-10T09:00:00Z",
            finished_at: "2026-07-10T09:00:01Z",
            errors: [],
          };
      syncRunsByConnection[connectionId] = [run, ...(syncRunsByConnection[connectionId] ?? [])];
      integrationConnections = integrationConnections.map(item =>
        item.id === connectionId
          ? { ...item, last_sync_at: "2026-07-10T09:00:01Z" }
          : item,
      );
      return Response.json(run);
    }
    if (
      connectionId &&
      url.endsWith(`/${connectionId}/sync-runs`) &&
      method === "GET"
    ) {
      return Response.json({ items: syncRunsByConnection[connectionId] ?? [] });
    }
    if (connectionId && url.endsWith(`/${connectionId}/pause`) && method === "POST") {
      integrationConnections = integrationConnections.map(connection =>
        connection.id === connectionId ? { ...connection, status: "paused" } : connection,
      );
      return Response.json(integrationConnections.find(item => item.id === connectionId));
    }
    if (connectionId && url.endsWith(`/${connectionId}/resume`) && method === "POST") {
      integrationConnections = integrationConnections.map(connection =>
        connection.id === connectionId ? { ...connection, status: "connected" } : connection,
      );
      return Response.json(integrationConnections.find(item => item.id === connectionId));
    }
    if (connectionId && method === "DELETE") {
      integrationConnections = integrationConnections.map(connection =>
        connection.id === connectionId ? { ...connection, status: "deleted" } : connection,
      );
      return Response.json({
        status: "deleted",
        data_retention: "retain_synced_data",
      });
    }
    return Response.json({ detail: "Not found" }, { status: 404 });
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("renders the live application catalog for the current organization", async () => {
  applicationItems = [
    {
      id: "app-1",
      organization_id: "org-1",
      name: "Slack",
      category: "协作",
      status: "active",
      business_owner: "运营",
      technical_owner: "IT",
      risk_level: "low",
      approved: true,
    },
  ];
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/applications"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "应用目录" })).toBeVisible();
  expect(await screen.findByText("Slack")).toBeVisible();
  expect(screen.getByText("协作")).toBeVisible();
  expect(screen.getByRole("button", { name: "新增应用" })).toBeEnabled();
});

test("creates a manual application from the catalog form", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/applications"],
  });
  render(<RouterProvider router={router} />);

  await screen.findByRole("heading", { name: "应用目录" });
  await user.type(screen.getByLabelText("应用名称"), "Notion");
  await user.type(screen.getByLabelText("类别"), "协作");
  await user.type(screen.getByLabelText("业务负责人"), "运营");
  await user.click(screen.getByRole("button", { name: "新增应用" }));

  expect(await screen.findByText("Notion")).toBeVisible();
  expect(screen.getByText("待评估")).toBeVisible();
});

test("renders organization billing audit history", async () => {
  auditRuns = [
    {
      id: "run-1",
      organization_id: "org-1",
      status: "completed",
      source_hint: "csv",
      items_count: 3,
      total_monthly_cost_usd: 64.52,
      created_at: "2026-06-11T09:30:00Z",
    },
  ];
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/audit"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "账单审计" })).toBeVisible();
  expect(await screen.findByText("run-1")).toBeVisible();
  expect(screen.getByText("$64.52")).toBeVisible();
});

test("creates a billing audit run from pasted text", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/audit"],
  });
  render(<RouterProvider router={router} />);

  await screen.findByRole("heading", { name: "账单审计" });
  await user.type(
    screen.getByLabelText("账单文本"),
    "Transaction Date,Description,Amount,Currency\n2026-05-01,OPENAI,20,USD",
  );
  await user.click(screen.getByRole("button", { name: "开始审计" }));

  expect(await screen.findByText("ChatGPT")).toBeVisible();
  expect(screen.getByText("OPENAI row")).toBeVisible();
  expect(await screen.findByText("run-created")).toBeVisible();
});

test("renders procurement approvals and processes a request", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/procurement"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "采购审批" })).toBeVisible();
  await user.type(screen.getByLabelText("软件名称"), "Notion AI");
  await user.type(screen.getByLabelText("用途说明"), "团队知识库需要 AI 总结能力");
  await user.type(screen.getByLabelText("月度预算"), "120");
  await user.type(screen.getByLabelText("部门"), "运营");
  await user.click(screen.getByLabelText("涉及敏感数据"));
  await user.type(screen.getByLabelText("数据分类"), "客户资料, 内部文档");
  await user.click(screen.getByRole("button", { name: "保存申请" }));

  expect(await screen.findByText("Notion AI")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "提交审批" }));

  expect(await screen.findByText("财务审批")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "批准" }));

  expect((await screen.findAllByText("已批准")).length).toBeGreaterThanOrEqual(2);
});

test("creates and signs a contract with a renewal deadline", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/contracts"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "合同续订" })).toBeVisible();
  await user.type(screen.getByLabelText("合同名称"), "Notion 企业版 2026");
  await user.type(screen.getByLabelText("供应商"), "Notion Labs");
  await user.type(screen.getByLabelText("关联应用"), "Notion");
  await user.type(screen.getByLabelText("负责人"), "运营负责人");
  await user.type(screen.getByLabelText("开始日期"), "2026-02-01");
  await user.type(screen.getByLabelText("结束日期"), "2027-01-31");
  await user.type(screen.getByLabelText("合同金额"), "12000");
  await user.click(screen.getByLabelText("自动续订"));
  await user.clear(screen.getByLabelText("通知期（天）"));
  await user.type(screen.getByLabelText("通知期（天）"), "60");
  await user.click(screen.getByRole("button", { name: "保存合同" }));

  expect(await screen.findByText("Notion 企业版 2026")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "标记已签署" }));

  expect(await screen.findByText("2026-12-02")).toBeVisible();
  expect(screen.getByText("2027-01-31")).toBeVisible();
});

test("creates a vendor, explains risk, and accepts a finding", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/vendors"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "供应商风险" })).toBeVisible();
  await user.type(screen.getByLabelText("供应商名称"), "Adobe");
  await user.type(screen.getByLabelText("官网域名"), "adobe.com");
  await user.type(screen.getByLabelText("注册地"), "US");
  await user.type(screen.getByLabelText("类别"), "创意软件");
  await user.type(screen.getByLabelText("业务负责人"), "设计团队");
  await user.type(screen.getByLabelText("风险负责人"), "安全负责人");
  await user.click(screen.getByRole("button", { name: "保存供应商" }));

  expect(await screen.findByText("Adobe")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "发起风险评估" }));
  await user.click(screen.getByLabelText("处理敏感数据"));
  await user.click(screen.getByRole("button", { name: "提交评估" }));

  expect(await screen.findByText("风险总分 82")).toBeVisible();
  expect(screen.getByText("安全风险需要处理")).toBeVisible();

  await user.type(
    screen.getByLabelText("接受理由"),
    "合同期限内接受，已安排替代方案评估。",
  );
  await user.type(screen.getByLabelText("接受到期日"), "2027-01-31");
  await user.click(screen.getAllByRole("button", { name: "接受风险" })[0]);

  expect(await screen.findByText("已接受")).toBeVisible();
});

test("runs the budget, transaction, split, anomaly, and period close flow", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/spend"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "预算与交易" })).toBeVisible();
  await user.type(screen.getByLabelText("预算名称"), "2026 IT 软件预算");
  await user.clear(screen.getByLabelText("财年"));
  await user.type(screen.getByLabelText("财年"), "2026");
  await user.type(screen.getByLabelText("预算部门"), "IT");
  await user.type(screen.getByLabelText("预算金额"), "10000");
  await user.type(screen.getByLabelText("承诺金额"), "1800");
  await user.type(screen.getByLabelText("预测金额"), "900");
  await user.click(screen.getByRole("button", { name: "保存预算" }));

  expect(await screen.findByText("2026 IT 软件预算")).toBeVisible();
  await user.type(screen.getByLabelText("外部交易 ID"), "txn-001");
  await user.type(screen.getByLabelText("交易日期"), "2026-06-10");
  await user.type(screen.getByLabelText("商户"), "Notion Labs");
  await user.type(screen.getByLabelText("交易说明"), "NOTION TEAM");
  await user.type(screen.getByLabelText("交易金额"), "11000");
  await user.type(screen.getByLabelText("交易部门"), "IT");
  await user.click(screen.getByRole("button", { name: "导入交易" }));

  expect(await screen.findByText("预算已超支")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "归类为软件" }));
  await user.click(screen.getByRole("button", { name: "编辑拆分" }));
  await user.type(screen.getByLabelText("拆分金额 1"), "5000");
  await user.type(screen.getByLabelText("拆分部门 1"), "IT");
  await user.type(screen.getByLabelText("拆分金额 2"), "6000");
  await user.type(screen.getByLabelText("拆分部门 2"), "设计");
  await user.click(screen.getByRole("button", { name: "保存拆分" }));

  expect(await screen.findByText("2 条拆分")).toBeVisible();
  await waitFor(() => {
    expect(screen.queryByText("预算已超支")).not.toBeInTheDocument();
  });
  await user.type(screen.getByLabelText("期间名称"), "2026-06");
  await user.type(screen.getByLabelText("期间开始"), "2026-06-01");
  await user.type(screen.getByLabelText("期间结束"), "2026-06-30");
  await user.click(screen.getByRole("button", { name: "创建期间" }));
  await user.click(await screen.findByRole("button", { name: "锁定期间" }));

  expect(await screen.findByText("期间已锁定")).toBeVisible();
});

test("restores the latest accounting period after refresh", async () => {
  accountingPeriod = {
    id: "period-existing",
    organization_id: "org-1",
    name: "2026-05",
    start_date: "2026-05-01",
    end_date: "2026-05-31",
    status: "locked",
    locked_at: "2026-05-31T23:59:00Z",
  };
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/spend"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByText("2026-05")).toBeVisible();
  expect(screen.getByText("期间已锁定")).toBeVisible();
});

test("runs the savings opportunity through verified savings", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/savings"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "节省优化" })).toBeVisible();
  await user.type(screen.getByLabelText("机会标题"), "取消闲置 Notion 订阅");
  await user.type(screen.getByLabelText("负责部门"), "运营");
  await user.type(screen.getByLabelText("月度基线"), "100");
  await user.type(screen.getByLabelText("生效日期"), "2026-07-01");
  await user.type(screen.getByLabelText("合同结束"), "2026-12-31");
  await user.type(screen.getByLabelText("发现证据"), "连续 60 天无活跃使用记录");
  await user.click(screen.getByRole("button", { name: "创建节省机会" }));

  expect(await screen.findByText("$600.00")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "确认机会" }));
  await user.type(screen.getByLabelText("项目负责人"), "运营负责人");
  await user.type(screen.getByLabelText("完成期限"), "2026-07-31");
  await user.click(screen.getByRole("button", { name: "创建优化项目" }));

  expect(await screen.findByText("确认取消路径与负责人")).toBeVisible();
  await user.type(screen.getByLabelText("调整后月费"), "0");
  await user.type(screen.getByLabelText("执行日期"), "2026-07-01");
  await user.type(screen.getByLabelText("执行证据"), "供应商确认已取消");
  await user.click(screen.getByRole("button", { name: "记录实际节省" }));

  expect(await screen.findByText("已实现 $600.00")).toBeVisible();
  await user.type(
    screen.getByLabelText("验证证据"),
    "transaction:txn-2026-08-notion",
  );
  await user.click(screen.getByRole("button", { name: "验证正式节省" }));

  expect(await screen.findByText("正式节省 $600.00")).toBeVisible();
});

test("creates a savings opportunity from a billing audit result", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/audit"],
  });
  render(<RouterProvider router={router} />);

  await screen.findByRole("heading", { name: "账单审计" });
  await user.type(screen.getByLabelText("账单文本"), "OPENAI,20,USD");
  await user.click(screen.getByRole("button", { name: "开始审计" }));
  await user.click(await screen.findByRole("button", { name: "转为节省机会" }));

  expect(await screen.findByText("已创建节省机会")).toBeVisible();
});

test("creates and governs a sandbox virtual card from an approved purchase", async () => {
  purchaseRequests = [
    {
      id: "request-approved",
      organization_id: "org-1",
      software_name: "Notion 企业版",
      business_reason: "团队知识库与项目协作",
      estimated_monthly_cost_usd: 120,
      department: "运营",
      handles_sensitive_data: false,
      data_categories: [],
      status: "approved",
      current_approval_task_id: null,
    },
  ];
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/payments"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "支付与虚拟卡" })).toBeVisible();
  await user.selectOptions(screen.getByLabelText("已批准采购"), "request-approved");
  await user.type(screen.getByLabelText("持卡负责人"), "运营负责人");
  await user.type(screen.getByLabelText("限定商户"), "Notion Labs");
  await user.type(screen.getByLabelText("初始单笔限额"), "300");
  await user.type(screen.getByLabelText("初始日限额"), "500");
  await user.type(screen.getByLabelText("初始月度限额"), "1200");
  await user.type(screen.getByLabelText("初始总限额"), "12000");
  await user.click(screen.getByRole("button", { name: "创建虚拟卡" }));

  expect(await screen.findByText("Visa •••• 4242")).toBeVisible();
  expect(screen.getByText("Sandbox")).toBeVisible();
  await user.clear(screen.getByLabelText("月度限额"));
  await user.type(screen.getByLabelText("月度限额"), "1000");
  await user.click(screen.getByRole("button", { name: "更新限额" }));

  expect(await screen.findByText("$1,000.00/月")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "冻结卡片" }));
  await user.click(screen.getByRole("button", { name: "确认冻结" }));
  expect(await screen.findByText("等待冻结确认")).toBeVisible();
  expect(screen.queryByText("4242424242424242")).not.toBeInTheDocument();
});

test("unfreezes a frozen virtual card", async () => {
  paymentInstruments = [
    {
      instrument: {
        id: "instrument-created",
        purchase_request_id: "request-approved",
        provider: "fake",
        external_id: "sandbox_notion",
        brand: "Visa",
        last4: "4242",
        status: "frozen",
        sandbox: true,
        owner_name: "运营负责人",
        department: "运营",
        merchant_lock: "Notion Labs",
        currency: "USD",
      },
      limits: {
        single: "300.0000",
        daily: "500.0000",
        monthly: "1200.0000",
        total: "12000.0000",
      },
    },
  ];
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/payments"],
  });
  render(<RouterProvider router={router} />);

  await user.click(await screen.findByRole("button", { name: "解冻卡片" }));

  expect(await screen.findByText("等待解冻确认")).toBeVisible();
});

test("requires confirmation before closing a virtual card", async () => {
  paymentInstruments = [
    {
      instrument: {
        id: "instrument-created",
        purchase_request_id: "request-approved",
        provider: "fake",
        external_id: "sandbox_notion",
        brand: "Visa",
        last4: "4242",
        status: "active",
        sandbox: true,
        owner_name: "运营负责人",
        department: "运营",
        merchant_lock: "Notion Labs",
        currency: "USD",
      },
      limits: {
        single: "300.0000",
        daily: "500.0000",
        monthly: "1200.0000",
        total: "12000.0000",
      },
    },
  ];
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/payments"],
  });
  render(<RouterProvider router={router} />);

  await user.click(await screen.findByRole("button", { name: "关闭卡片" }));
  expect(screen.getByText("关闭后无法恢复，且后续交易将被拒绝。")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "确认关闭" }));

  expect(await screen.findByText("等待关闭确认")).toBeVisible();
});

test("does not offer limit changes for a closed virtual card", async () => {
  paymentInstruments = [
    {
      instrument: {
        id: "instrument-created",
        purchase_request_id: "request-approved",
        provider: "fake",
        external_id: "sandbox_notion",
        brand: "Visa",
        last4: "4242",
        status: "closed",
        sandbox: true,
        owner_name: "运营负责人",
        department: "运营",
        merchant_lock: "Notion Labs",
        currency: "USD",
      },
      limits: {
        single: "300.0000",
        daily: "500.0000",
        monthly: "1200.0000",
        total: "12000.0000",
      },
    },
  ];
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/payments"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByText("已关闭")).toBeVisible();
  expect(screen.queryByRole("button", { name: "更新限额" })).not.toBeInTheDocument();
});

test("reviews, matches, maps, exports, and resyncs an invoice", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/invoices"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "发票与会计" })).toBeVisible();
  await user.type(
    screen.getByLabelText("发票文本"),
    "vendor: Notion Labs\ninvoice_number: INV-2026-001",
  );
  await user.click(screen.getByRole("button", { name: "提取发票" }));

  expect(await screen.findByText("金额不平衡")).toBeVisible();
  await user.clear(screen.getByLabelText("税额"));
  await user.type(screen.getByLabelText("税额"), "18");
  await user.click(screen.getByRole("button", { name: "确认发票字段" }));
  expect(await screen.findByText("字段已确认")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "自动匹配业务记录" }));
  expect(await screen.findByText("匹配完成 · 100%")).toBeVisible();

  await user.type(screen.getByLabelText("会计科目"), "6200");
  await user.type(screen.getByLabelText("税码"), "VAT18");
  await user.type(screen.getByLabelText("成本中心"), "OPS-SAAS");
  await user.type(screen.getByLabelText("会计部门"), "运营");
  await user.type(screen.getByLabelText("项目"), "数字化");
  await user.click(screen.getByRole("button", { name: "保存并应用映射" }));
  expect(await screen.findByText("应用级映射 · 科目 6200")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "导出到会计系统" }));
  expect(await screen.findByText("已同步到 Sandbox 会计系统")).toBeVisible();

  await user.clear(screen.getByLabelText("调整后小计"));
  await user.type(screen.getByLabelText("调整后小计"), "102");
  await user.clear(screen.getByLabelText("调整后总额"));
  await user.type(screen.getByLabelText("调整后总额"), "120");
  await user.click(screen.getByRole("button", { name: "记录发票调整" }));
  expect(await screen.findByText("本地数据已变更，等待重新同步")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "重新同步" }));
  expect(await screen.findByText("已同步到 Sandbox 会计系统")).toBeVisible();
});

test("connects, syncs, diagnoses, pauses, resumes, and deletes an integration", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/integrations"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "集成中心" })).toBeVisible();
  expect(screen.getAllByText("Sandbox 身份目录")[0]).toBeVisible();

  await user.type(screen.getByLabelText("连接名称"), "企业身份目录");
  await user.type(screen.getByLabelText("API Token"), "sandbox-token-1234");
  await user.click(screen.getByRole("button", { name: "连接并保存" }));

  expect(
    await screen.findByText(
      (_, element) =>
        element?.tagName.toLowerCase() === "span" &&
        element.textContent?.includes("凭据尾号 1234") === true,
    ),
  ).toBeVisible();
  expect(screen.queryByText("sandbox-token-1234")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "测试连接" }));
  expect(await screen.findByText("Sandbox 身份目录连接正常")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "运行同步" }));
  expect(await screen.findByText("同步成功 · 读取 2 · 新增 2")).toBeVisible();
  expect(screen.getByText("游标 page-2")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "暂停" }));
  expect(await screen.findByText("已暂停")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "恢复" }));
  expect(await screen.findByText("已连接")).toBeVisible();

  await user.clear(screen.getByLabelText("连接名称"));
  await user.type(screen.getByLabelText("连接名称"), "失败诊断连接");
  await user.clear(screen.getByLabelText("API Token"));
  await user.type(screen.getByLabelText("API Token"), "sandbox-failure-9876");
  await user.click(screen.getByLabelText("模拟第二页失败"));
  await user.click(screen.getByRole("button", { name: "连接并保存" }));
  await user.click(screen.getAllByRole("button", { name: "运行同步" })[0]);
  expect(await screen.findByText("provider_error")).toBeVisible();
  expect(screen.getByText("Sandbox provider failed on page 2")).toBeVisible();

  await user.click(screen.getAllByRole("button", { name: "删除连接" })[1]);
  expect(await screen.findByText("已删除，已同步数据保留")).toBeVisible();
});
