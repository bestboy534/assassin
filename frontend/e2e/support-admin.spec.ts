import { expect, test, type Page, type Route } from "@playwright/test";

const now = "2026-06-15T08:00:00Z";

async function fulfill(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function mockSupportAndAdminApi(page: Page) {
  let platformRole: string | null = null;
  let subscribed = false;
  let subscriberNotifications = 0;
  let ticket: Record<string, unknown> | null = null;
  let messages: Array<Record<string, unknown>> = [];
  let grant: Record<string, unknown> | null = null;
  let incident: Record<string, unknown> | null = null;

  await page.route("**/api/v1/**", async route => {
    const request = route.request();
    const url = request.url();
    const method = request.method();

    if (url.endsWith("/api/v1/auth/me")) {
      await fulfill(route, {
        user: {
          id: platformRole ? "support-1" : "customer-1",
          email: platformRole ? "support@example.com" : "owner@example.com",
          display_name: platformRole ? "支持专员" : "负责人",
          status: "active",
          platform_role: platformRole,
        },
        organizations: [
          { id: "org-1", name: "示例科技", slug: "acme", role: "owner" },
        ],
      });
      return;
    }
    if (url.includes("/api/v1/support/tickets?") && method === "GET") {
      await fulfill(route, { items: ticket ? [ticket] : [] });
      return;
    }
    if (url.endsWith("/api/v1/support/tickets") && method === "POST") {
      const body = request.postDataJSON();
      ticket = {
        id: "ticket-1",
        organization_id: "org-1",
        subject: body.subject,
        description: body.description,
        category: body.category,
        priority: body.priority,
        status: "new",
        support_tier: "priority",
        resolution_summary: null,
        first_response_due_at: "2026-06-15T10:00:00Z",
        resolution_due_at: "2026-06-16T08:00:00Z",
        first_responded_at: null,
        sla_paused_at: null,
        resolved_at: null,
        closed_at: null,
        created_at: now,
        updated_at: now,
      };
      await fulfill(route, ticket, 201);
      return;
    }
    if (url.endsWith("/api/v1/support/tickets/ticket-1") && method === "GET") {
      await fulfill(route, ticket);
      return;
    }
    if (
      url.endsWith("/api/v1/support/tickets/ticket-1/messages") &&
      method === "GET"
    ) {
      await fulfill(route, { items: messages });
      return;
    }
    if (url.endsWith("/api/v1/support/agents")) {
      await fulfill(route, {
        items: [
          { id: "support-1", display_name: "支持专员", platform_role: "support_agent" },
        ],
      });
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/support-grants") &&
      method === "GET"
    ) {
      await fulfill(route, { items: grant ? [grant] : [] });
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/support-grants") &&
      method === "POST"
    ) {
      const body = request.postDataJSON();
      grant = {
        id: "grant-1",
        organization_id: "org-1",
        support_user_id: "support-1",
        scopes: body.scopes,
        reason: body.reason,
        approved_by_user_id: "customer-1",
        expires_at: body.expires_at,
        revoked_at: null,
        created_at: now,
      };
      await fulfill(route, grant, 201);
      return;
    }
    if (url.endsWith("/api/v1/support/operations/tickets")) {
      await fulfill(route, { items: ticket ? [ticket] : [] });
      return;
    }
    if (
      url.endsWith("/api/v1/support/operations/tickets/ticket-1/messages") &&
      method === "GET"
    ) {
      await fulfill(route, { items: messages });
      return;
    }
    if (
      url.endsWith("/api/v1/support/operations/tickets/ticket-1/messages") &&
      method === "POST"
    ) {
      const body = request.postDataJSON();
      const created = {
        id: `message-${messages.length + 1}`,
        support_ticket_id: "ticket-1",
        author_type: "support",
        body: body.body,
        internal: false,
        created_at: now,
      };
      messages.push(created);
      if (ticket) ticket = { ...ticket, status: "waiting_customer" };
      await fulfill(route, created, 201);
      return;
    }
    if (url.endsWith("/api/v1/support/operations/grants")) {
      await fulfill(route, { items: grant ? [grant] : [] });
      return;
    }
    if (url.endsWith("/api/v1/support/grants/grant-1/diagnostics")) {
      const expired =
        grant && new Date(String(grant.expires_at)).getTime() <= Date.now();
      if (expired) {
        await fulfill(route, { detail: "Support grant is not active" }, 403);
      } else {
        await fulfill(route, {
          grant_id: "grant-1",
          organization_id: "org-1",
          items: [
            {
              id: "sync-1",
              connection_id: "connection-1",
              resource_type: "users",
              status: "failed",
              failed_count: 12,
              attempts: 3,
              error_summary: "身份目录令牌已过期",
              started_at: now,
              finished_at: now,
            },
          ],
        });
      }
      return;
    }
    if (url.endsWith("/api/v1/status/subscriptions") && method === "POST") {
      subscribed = true;
      await fulfill(route, { status: "confirmation_pending" }, 202);
      return;
    }
    if (url.endsWith("/api/v1/admin/status/components") && method === "GET") {
      await fulfill(route, [
        {
          id: "component-1",
          slug: "integrations",
          name: "集成与同步",
          description: "第三方连接与同步任务",
          status: incident ? "degraded" : "operational",
        },
      ]);
      return;
    }
    if (url.endsWith("/api/v1/admin/status/incidents") && method === "POST") {
      const body = request.postDataJSON();
      incident = {
        id: "incident-1",
        component_id: "component-1",
        component_name: "集成与同步",
        title: body.title,
        summary: body.public_summary,
        public_summary: body.public_summary,
        internal_summary: body.internal_summary,
        impact: body.impact,
        status: "investigating",
        started_at: now,
        resolved_at: null,
        postmortem_summary: null,
        updates: [
          {
            id: "update-1",
            status: "investigating",
            message: body.public_message,
            created_at: now,
          },
        ],
      };
      if (subscribed) subscriberNotifications += 1;
      await fulfill(route, incident, 201);
      return;
    }
    if (url.endsWith("/api/v1/status") && method === "GET") {
      await fulfill(route, {
        overall_status: incident ? "degraded" : "operational",
        generated_at: now,
        components: [
          {
            id: "component-1",
            slug: "integrations",
            name: "集成与同步",
            description: "第三方连接与同步任务",
            status: incident ? "degraded" : "operational",
          },
        ],
        incidents: incident ? [incident] : [],
      });
      return;
    }
    await fulfill(route, { detail: `Unhandled ${method} ${url}` }, 404);
  });

  return {
    setRole(role: string | null) {
      platformRole = role;
    },
    expireGrant() {
      if (grant) grant = { ...grant, expires_at: "2020-01-01T00:00:00Z" };
    },
    notificationCount() {
      return subscriberNotifications;
    },
  };
}

test("客户建单、支持回复、限时诊断并在过期后阻断", async ({ page }) => {
  const state = await mockSupportAndAdminApi(page);

  await page.goto("/app/acme/support/new");
  await page.getByLabel("问题标题").fill("身份目录同步失败");
  await page.getByLabel("问题描述").fill("同步任务连续失败，请协助排查。");
  await page.getByRole("button", { name: "提交工单" }).click();
  await expect(page.getByRole("heading", { name: "身份目录同步失败" })).toBeVisible();

  state.setRole("support_agent");
  await page.goto("/admin/support");
  await page.getByRole("button", { name: "处理工单" }).click();
  await page.getByLabel("支持回复").fill("请重新授权身份目录连接。");
  await page.getByRole("button", { name: "回复客户" }).click();
  await expect(page.getByText("请重新授权身份目录连接。")).toBeVisible();

  state.setRole(null);
  await page.goto("/app/acme/settings/support-access");
  await page.getByLabel("支持专员").selectOption("support-1");
  await page.getByLabel("授权原因").fill("排查身份目录同步错误");
  await page.getByRole("button", { name: "创建限时授权" }).click();
  await expect(page.getByText("授权已创建")).toBeVisible();

  state.setRole("support_agent");
  await page.goto("/admin/support");
  await page.getByRole("button", { name: "查看同步诊断" }).click();
  await expect(page.getByText("身份目录令牌已过期")).toBeVisible();

  state.expireGrant();
  await page.reload();
  await expect(page.getByText("授权已过期")).toBeVisible();
  await expect(page.getByRole("button", { name: "查看同步诊断" })).toHaveCount(0);
  await page.screenshot({ path: "test-results/support-admin-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    )
    .toBe(true);
  await page.screenshot({ path: "test-results/support-admin-mobile.png", fullPage: true });
});

test("平台发布状态事件后订阅者收到更新", async ({ page }) => {
  const state = await mockSupportAndAdminApi(page);

  await page.goto("/status");
  await page.getByLabel("工作邮箱").fill("ops@example.com");
  await page.getByRole("button", { name: "订阅状态更新" }).click();
  await expect(page.getByText("确认邮件已发送，请检查收件箱。")).toBeVisible();

  state.setRole("platform_admin");
  await page.goto("/admin/status");
  await page.getByLabel("事件标题").fill("部分同步任务延迟");
  await page.getByLabel("公开摘要").fill("处理时间高于正常水平。");
  await page.getByLabel("首次公开更新").fill("我们正在调查该问题。");
  await page.getByRole("button", { name: "发布状态事件" }).click();
  await expect(page.getByText("状态事件已发布")).toBeVisible();
  await expect.poll(() => state.notificationCount()).toBe(1);
  await page.screenshot({ path: "test-results/status-admin-console.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    )
    .toBe(true);
  await page.screenshot({ path: "test-results/status-admin-mobile.png", fullPage: true });

  await page.goto("/status");
  await expect(page.getByRole("heading", { name: "部分同步任务延迟" })).toBeVisible();
  await page.screenshot({ path: "test-results/status-admin-desktop.png", fullPage: true });
});
