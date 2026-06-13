import { expect, test, type Page, type Route } from "@playwright/test";

const now = "2026-06-13T08:00:00Z";
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

type MockState = {
  apiKeys: Array<Record<string, unknown>>;
  privacyRequests: Array<Record<string, unknown>>;
};

async function fulfill(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function mockComplianceApi(page: Page) {
  const state: MockState = {
    apiKeys: [],
    privacyRequests: [],
  };

  await page.route("**/api/v1/**", async route => {
    const request = route.request();
    const url = request.url();
    const method = request.method();

    if (url.endsWith("/api/v1/auth/me")) {
      await fulfill(route, session);
      return;
    }
    if (url.endsWith("/api/v1/organizations/org-1/api-keys") && method === "GET") {
      await fulfill(route, { items: state.apiKeys });
      return;
    }
    if (url.endsWith("/api/v1/organizations/org-1/api-keys") && method === "POST") {
      const input = request.postDataJSON();
      const created = {
        id: "key-1",
        organization_id: "org-1",
        name: input.name,
        prefix: "ssa_live",
        scopes: input.scopes,
        last_used_at: null,
        expires_at: null,
        revoked_at: null,
        created_at: now,
        secret: "ssa_live_secret",
      };
      state.apiKeys = [created];
      await fulfill(route, created, 201);
      return;
    }
    if (url.includes("/api/v1/api-keys/current") && method === "GET") {
      await fulfill(route, {
        api_key_id: "key-1",
        organization_id: "org-1",
        name: "CI 自动化",
        scopes: ["reports.read"],
      });
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/api-keys/key-1/revoke") &&
      method === "POST"
    ) {
      state.apiKeys = state.apiKeys.map(item => ({ ...item, revoked_at: now }));
      await fulfill(route, state.apiKeys[0]);
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/retention-policies") &&
      method === "POST"
    ) {
      const input = request.postDataJSON();
      await fulfill(
        route,
        {
          id: "policy-1",
          organization_id: "org-1",
          data_type: "stored_file",
          retention_days: input.retention_days,
          action: "delete",
          description: input.description,
          status: "active",
          created_at: now,
          updated_at: now,
        },
        201,
      );
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/legal-holds") &&
      method === "POST"
    ) {
      const input = request.postDataJSON();
      await fulfill(
        route,
        {
          id: "hold-1",
          organization_id: "org-1",
          resource_type: input.resource_type,
          resource_id: input.resource_id,
          reason: input.reason,
          status: "active",
          expires_at: null,
          created_at: now,
        },
        201,
      );
      return;
    }
    if (
      url.includes("/api/v1/organizations/org-1/retention/deletion-preview") &&
      method === "GET"
    ) {
      await fulfill(route, {
        data_type: "stored_file",
        cutoff_at: now,
        delete_candidates: ["file-delete"],
        skipped_legal_hold: ["file-held"],
      });
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/retention/deletion-jobs") &&
      method === "POST"
    ) {
      await fulfill(
        route,
        {
          id: "job-1",
          data_type: "stored_file",
          status: "succeeded",
          deleted_resource_ids: ["file-delete"],
          skipped_legal_hold: ["file-held"],
          created_at: now,
          completed_at: now,
        },
        201,
      );
      return;
    }
    if (url.endsWith("/api/v1/privacy/requests") && method === "GET") {
      await fulfill(route, { items: state.privacyRequests });
      return;
    }
    if (url.endsWith("/api/v1/privacy/requests") && method === "POST") {
      const input = request.postDataJSON();
      const created = {
        id: "privacy-1",
        subject_user_id: "user-1",
        type: input.type,
        status: "verified",
        identity_verified_at: now,
        due_at: now,
        scope: input.scope,
        requested_changes: {},
        result: {},
        processing_history: [],
        created_at: now,
        updated_at: now,
        completed_at: null,
      };
      state.privacyRequests = [created];
      await fulfill(route, created, 201);
      return;
    }
    if (
      url.endsWith("/api/v1/privacy/requests/privacy-1/process") &&
      method === "POST"
    ) {
      const completed = {
        ...state.privacyRequests[0],
        status: "completed",
        result: { export: { identity: { email: "owner@example.com" } } },
        completed_at: now,
        updated_at: now,
      };
      state.privacyRequests = [completed];
      await fulfill(route, completed);
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/audit-logs") &&
      method === "GET"
    ) {
      await fulfill(route, {
        items: [
          {
            id: "audit-1",
            organization_id: "org-1",
            actor_type: "user",
            actor_id: "user-1",
            action: "api_key.created",
            resource_type: "api_key",
            resource_id: "key-1",
            ip_address: "127.0.0.1",
            user_agent_hash: "hash",
            request_id: "req-1",
            before: {},
            after: { name: "CI 自动化" },
            metadata: {},
            created_at: now,
          },
        ],
      });
      return;
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/audit-logs/export") &&
      method === "POST"
    ) {
      await fulfill(
        route,
        {
          format: "json",
          row_count: 1,
          rows: [],
          exported_at: now,
        },
        201,
      );
      return;
    }

    await fulfill(route, { items: [] });
  });
}

test.beforeEach(async ({ page }) => {
  await mockComplianceApi(page);
});

test("API key can be created, used, and revoked", async ({ page }) => {
  await page.goto("/app/acme/settings/api-keys");
  await page.getByLabel("密钥名称").fill("CI 自动化");
  await page.getByLabel("权限范围").fill("reports.read");
  await page.getByRole("button", { name: "创建 API 密钥" }).click();

  await expect(page.getByText("ssa_live_secret")).toBeVisible();
  await page.getByRole("button", { name: "验证密钥" }).click();
  await expect(page.getByText("验证成功：CI 自动化")).toBeVisible();

  const row = page.getByRole("article", { name: "API 密钥 CI 自动化" });
  await row.getByLabel("我确认依赖此密钥的自动化将立即停止").check();
  await row.getByRole("button", { name: "撤销密钥" }).click();
  await expect(row.getByText("已撤销")).toBeVisible();
});

test("privacy export can be requested, processed, and downloaded", async ({
  page,
}) => {
  await page.goto("/account/privacy");
  await page.getByLabel("请求类型").selectOption("portability");
  await page.getByRole("button", { name: "提交隐私请求" }).click();

  const request = page.getByRole("article", { name: "隐私请求 portability" });
  await request.getByLabel("我已重新认证，并确认处理该隐私请求").check();
  await request.getByRole("button", { name: "确认并处理" }).click();
  await expect(request.getByText("已完成")).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await request.getByRole("button", { name: "下载我的数据" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("privacy-privacy-1.json");
});

test("legal hold is shown as protected before permanent deletion", async ({
  page,
}) => {
  await page.goto("/app/acme/settings/data-retention");
  await page.getByLabel("保留天数").fill("30");
  await page.getByLabel("策略说明").fill("文件保留 30 天");
  await page.getByRole("button", { name: "保存保留策略" }).click();

  await page.getByLabel("冻结资源 ID").fill("file-held");
  await page.getByLabel("冻结原因").fill("监管调查");
  await page.getByRole("button", { name: "创建法务冻结" }).click();
  await page.getByRole("button", { name: "预览删除影响" }).click();
  await expect(page.getByText("法务冻结保护 1 项")).toBeVisible();
  await expect(page.getByText("file-held", { exact: true })).toBeVisible();

  await page.getByLabel("我已重新认证，并理解删除后的文件无法恢复").check();
  await page.getByRole("button", { name: "执行永久删除" }).click();
  await expect(
    page.getByText("删除完成：1 项；法务冻结跳过：1 项"),
  ).toBeVisible();
});

test("audit trail can be queried and exported", async ({ page }) => {
  await page.goto("/app/acme/security/audit-log");
  await page.getByLabel("筛选操作").fill("api_key");
  await expect(page.getByText("api_key.created")).toBeVisible();
  await page.getByRole("button", { name: "导出 JSON" }).click();
  await expect(page.getByText("已生成 1 条审计记录")).toBeVisible();
});
