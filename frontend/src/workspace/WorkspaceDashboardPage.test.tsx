import { render, screen } from "@testing-library/react";
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

beforeEach(() => {
  applicationItems = [];
  auditRuns = [];
  purchaseRequests = [];
  approvalTasks = [];
  contracts = [];
  renewals = [];
  vendors = [];
  riskFindings = [];
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
    initialEntries: ["/app/acme/spend"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { name: "账单审计" })).toBeVisible();
  expect(await screen.findByText("run-1")).toBeVisible();
  expect(screen.getByText("$64.52")).toBeVisible();
});

test("creates a billing audit run from pasted text", async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(routes, {
    initialEntries: ["/app/acme/spend"],
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
