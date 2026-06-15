import { expect, test, type Page, type Route } from "@playwright/test";

const now = "2026-06-15T08:00:00Z";
const periodEnd = "2026-07-15T08:00:00Z";
const plans = {
  starter: {
    key: "starter",
    name: "Starter",
    description: "适合开始统一管理软件资产的团队。",
    currency: "USD",
    billing_interval: "month",
    amount_minor: 0,
    entitlements: [
      { key: "applications", value_type: "integer", value: 5, hard_limit: true },
      { key: "members", value_type: "integer", value: 5, hard_limit: true },
    ],
  },
  pro: {
    key: "pro",
    name: "Pro",
    description: "适合需要更高额度、API 与优先支持的团队。",
    currency: "USD",
    billing_interval: "month",
    amount_minor: 4900,
    entitlements: [
      { key: "applications", value_type: "integer", value: 50, hard_limit: true },
      { key: "members", value_type: "integer", value: 25, hard_limit: true },
      { key: "api_access", value_type: "boolean", value: true, hard_limit: true },
    ],
  },
} as const;

type PlanKey = keyof typeof plans;

type BillingState = {
  plan: PlanKey;
  status: string;
  pendingPlan: PlanKey | null;
  pendingChangeAt: string | null;
  cancelAtPeriodEnd: boolean;
  applyScheduledOnNextRead: boolean;
};

async function fulfill(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function summary(state: BillingState) {
  return {
    plan: plans[state.plan],
    pending_plan: state.pendingPlan ? plans[state.pendingPlan] : null,
    payment_issue: false,
    subscription: {
      status: state.cancelAtPeriodEnd ? "cancel_at_period_end" : state.status,
      read_only: false,
      trial_ends_at: "2026-06-29T08:00:00Z",
      current_period_start: now,
      current_period_end: periodEnd,
      cancel_at_period_end: state.cancelAtPeriodEnd,
      pending_change_at: state.pendingChangeAt,
      pending_change_type: state.pendingPlan ? "downgrade" : null,
    },
  };
}

async function mockBillingApi(page: Page) {
  const state: BillingState = {
    plan: "starter",
    status: "trialing",
    pendingPlan: null,
    pendingChangeAt: null,
    cancelAtPeriodEnd: false,
    applyScheduledOnNextRead: false,
  };

  await page.route("**/api/v1/**", async route => {
    const request = route.request();
    const url = request.url();
    const method = request.method();

    if (url.endsWith("/api/v1/auth/me")) {
      await fulfill(route, {
        user: {
          id: "user-1",
          email: "owner@example.com",
          display_name: "负责人",
          status: "active",
        },
        organizations: [
          { id: "org-1", name: "示例科技", slug: "acme", role: "owner" },
        ],
      });
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/billing") &&
      method === "GET"
    ) {
      if (state.applyScheduledOnNextRead) {
        state.plan = "starter";
        state.status = "active";
        state.pendingPlan = null;
        state.pendingChangeAt = null;
        state.applyScheduledOnNextRead = false;
      }
      await fulfill(route, summary(state));
      return;
    }
    if (url.endsWith("/billing/change-preview") && method === "POST") {
      const targetPlan = request.postDataJSON().target_plan as PlanKey;
      const upgrade = targetPlan === "pro";
      await fulfill(route, {
        current_plan: state.plan,
        target_plan: targetPlan,
        direction: upgrade ? "upgrade" : "downgrade",
        effective_at: upgrade ? now : periodEnd,
        current_amount_minor: plans[state.plan].amount_minor,
        target_amount_minor: plans[targetPlan].amount_minor,
        proration_minor: upgrade ? 4900 : 0,
        lost_features: upgrade ? [] : ["api_access"],
        over_limit: upgrade ? {} : { applications: 43, members: 8 },
      });
      return;
    }
    if (url.endsWith("/billing/change-plan") && method === "POST") {
      const targetPlan = request.postDataJSON().target_plan as PlanKey;
      if (targetPlan === "pro") {
        // Sandbox checkout completed and its subscription Webhook has arrived.
        state.plan = "pro";
        state.status = "active";
        state.pendingPlan = null;
        state.pendingChangeAt = null;
      } else {
        state.pendingPlan = "starter";
        state.pendingChangeAt = periodEnd;
      }
      await fulfill(route, summary(state));
      return;
    }
    if (url.endsWith("/billing/usage") && method === "GET") {
      await fulfill(route, {
        items: [
          { metric: "applications", current_value: 40, limit: 50, hard_limit: true, status: "warning" },
          { metric: "members", current_value: 10, limit: 25, hard_limit: true, status: "ok" },
          { metric: "storage_bytes", current_value: 0, limit: 10737418240, hard_limit: true, status: "ok" },
          { metric: "ai_pages", current_value: 80, limit: 1000, hard_limit: false, status: "ok" },
          { metric: "integration_connections", current_value: 2, limit: 20, hard_limit: true, status: "ok" },
          { metric: "export_rows", current_value: 100, limit: 100000, hard_limit: false, status: "ok" },
          { metric: "api_calls", current_value: 400, limit: 50000, hard_limit: true, status: "ok" },
        ],
      });
      return;
    }
    if (url.endsWith("/billing/invoices") && method === "GET") {
      await fulfill(route, {
        items: [
          {
            external_invoice_id: "inv_sandbox_001",
            status: "paid",
            currency: "USD",
            amount_due_minor: 4900,
            amount_paid_minor: 4900,
            hosted_invoice_url: "https://billing.example.test/invoices/001",
            due_at: periodEnd,
            paid_at: now,
            created_at: now,
          },
        ],
      });
      return;
    }
    if (url.endsWith("/billing/cancel") && method === "POST") {
      state.cancelAtPeriodEnd = true;
      await fulfill(route, summary(state));
      return;
    }
    if (url.endsWith("/billing/undo-cancellation") && method === "POST") {
      state.cancelAtPeriodEnd = false;
      state.status = "active";
      await fulfill(route, summary(state));
      return;
    }
    await fulfill(route, { detail: `Unhandled ${method} ${url}` }, 404);
  });

  return {
    applyScheduledDowngrade() {
      state.applyScheduledOnNextRead = true;
    },
  };
}

test("试用、Webhook 激活、用量阈值、周期末降级和取消撤销", async ({
  page,
}) => {
  const billing = await mockBillingApi(page);
  await page.goto("/app/acme/settings/billing");

  await expect(page.getByText("14 天免费试用")).toBeVisible();
  await page.getByRole("button", { name: "升级到 Pro" }).click();
  await expect(page.getByText("本次预计支付")).toBeVisible();
  await page.getByRole("button", { name: "确认升级" }).click();
  await expect(page.getByRole("heading", { name: "Pro" })).toBeVisible();
  await expect(page.getByText("计费同步正常")).toBeVisible();

  await page.getByRole("link", { name: "产品用量" }).click();
  await expect(page.getByText("接近额度")).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "应用数量已使用 80%" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "发票", exact: true }).click();
  await expect(page.getByText("inv_sandbox_001")).toBeVisible();
  await expect(page.getByText("$49.00")).toBeVisible();

  await page.getByRole("link", { name: "套餐与付款" }).click();
  await page.getByRole("button", { name: "切换到 Starter" }).click();
  await expect(page.getByText("周期结束后降级")).toBeVisible();
  await expect(page.getByText("应用数量超出 43、团队成员超出 8")).toBeVisible();
  await page.getByRole("button", { name: "确认降级" }).click();
  await expect(page.getByText(/^将于 .*切换到 Starter$/)).toBeVisible();

  billing.applyScheduledDowngrade();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Starter" })).toBeVisible();

  await page.getByRole("button", { name: "取消订阅" }).click();
  await expect(page.getByText("订阅将在当前周期结束时取消")).toBeVisible();
  await page.getByRole("button", { name: "撤销取消" }).click();
  await expect(page.getByText("订阅将在当前周期结束时取消")).toHaveCount(0);
});
