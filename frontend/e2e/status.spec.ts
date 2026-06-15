import { expect, test, type Page, type Route } from "@playwright/test";

const statusPayload = {
  overall_status: "degraded",
  generated_at: "2026-06-15T09:00:00Z",
  components: [
    {
      id: "component-integrations",
      slug: "integrations",
      name: "集成与同步",
      description: "第三方连接和同步任务",
      status: "degraded",
    },
    {
      id: "component-workspace",
      slug: "workspace",
      name: "工作台",
      description: "登录和组织工作区",
      status: "operational",
    },
    {
      id: "component-api",
      slug: "api",
      name: "开放 API",
      description: "公开接口和 Webhook 投递",
      status: "operational",
    },
  ],
  incidents: [
    {
      id: "incident-sync-delay",
      component_id: "component-integrations",
      component_name: "集成与同步",
      title: "部分同步任务延迟",
      summary: "部分同步任务处理时间高于正常水平。",
      impact: "degraded",
      status: "monitoring",
      started_at: "2026-06-15T08:00:00Z",
      resolved_at: null,
      postmortem_summary: null,
      updates: [
        {
          id: "update-monitoring",
          status: "monitoring",
          message: "同步速度已经恢复，正在持续观察。",
          created_at: "2026-06-15T08:45:00Z",
        },
        {
          id: "update-identified",
          status: "identified",
          message: "已经定位到同步队列拥堵，正在扩容处理。",
          created_at: "2026-06-15T08:15:00Z",
        },
        {
          id: "update-investigating",
          status: "investigating",
          message: "我们正在调查部分同步任务延迟。",
          created_at: "2026-06-15T08:00:00Z",
        },
      ],
    },
  ],
};

async function fulfill(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function mockStatusApi(page: Page) {
  await page.route("**/api/v1/status**", async route => {
    if (
      route.request().url().endsWith("/subscriptions") &&
      route.request().method() === "POST"
    ) {
      await fulfill(route, { status: "confirmation_pending" }, 202);
      return;
    }
    await fulfill(route, statusPayload);
  });
}

test("公开状态页展示组件、事件时间线并完成订阅", async ({ page }) => {
  await mockStatusApi(page);
  await page.goto("/status");

  await expect(
    page.getByRole("heading", { level: 1, name: "系统运行状态" }),
  ).toBeVisible();
  await expect(page.getByText("部分服务性能下降")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "部分同步任务延迟" }),
  ).toBeVisible();
  await expect(page.getByText("同步速度已经恢复，正在持续观察。")).toBeVisible();

  await page.getByLabel("工作邮箱").fill("ops@example.com");
  await page.getByRole("button", { name: "订阅状态更新" }).click();
  await expect(page.getByText("确认邮件已发送，请检查收件箱。")).toBeVisible();

  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/status-desktop.png",
    fullPage: true,
  });
});

test("移动端状态页没有横向溢出", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockStatusApi(page);
  await page.goto("/status");

  await expect(page.getByText("部分服务性能下降")).toBeVisible();
  await expect(page.getByRole("button", { name: "订阅状态更新" })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/status-mobile.png",
    fullPage: true,
  });
});
