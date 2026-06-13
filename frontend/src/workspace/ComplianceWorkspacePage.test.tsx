import { render, screen, within } from "@testing-library/react";
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

const now = "2026-06-13T08:00:00Z";

let apiKeys: Array<Record<string, unknown>>;
let privacyRequests: Array<Record<string, unknown>>;

function renderRoute(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(<RouterProvider router={router} />);
}

beforeEach(() => {
  apiKeys = [];
  privacyRequests = [];

  vi.spyOn(window, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";

    if (url.endsWith("/api/v1/auth/me")) {
      return Response.json(session);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/audit-logs") &&
      method === "GET"
    ) {
      return Response.json({
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
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/audit-logs/export") &&
      method === "POST"
    ) {
      return Response.json(
        {
          format: "json",
          row_count: 1,
          rows: [
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
          exported_at: now,
        },
        { status: 201 },
      );
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/compliance/frameworks") &&
      method === "GET"
    ) {
      return Response.json({ items: [] });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/security/incidents") &&
      method === "GET"
    ) {
      return Response.json({ items: [] });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/api-keys") &&
      method === "GET"
    ) {
      return Response.json({ items: apiKeys });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/api-keys") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const created = {
        id: "key-1",
        organization_id: "org-1",
        name: body.name,
        prefix: "ssa_live",
        scopes: body.scopes,
        last_used_at: null,
        expires_at: null,
        revoked_at: null,
        created_at: now,
        secret: "ssa_live_secret",
      };
      apiKeys = [created];
      return Response.json(created, { status: 201 });
    }
    if (
      url.includes("/api/v1/api-keys/current") &&
      method === "GET"
    ) {
      return Response.json({
        api_key_id: "key-1",
        organization_id: "org-1",
        name: "CI 自动化",
        scopes: ["reports.read"],
      });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/api-keys/key-1/revoke") &&
      method === "POST"
    ) {
      apiKeys = apiKeys.map(item => ({ ...item, revoked_at: now }));
      return Response.json(apiKeys[0]);
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/webhooks") &&
      method === "GET"
    ) {
      return Response.json({ items: [] });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/retention-policies") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      return Response.json(
        {
          id: "policy-1",
          organization_id: "org-1",
          data_type: "stored_file",
          retention_days: body.retention_days,
          action: "delete",
          description: body.description,
          status: "active",
          created_at: now,
          updated_at: now,
        },
        { status: 201 },
      );
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/legal-holds") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      return Response.json(
        {
          id: "hold-1",
          organization_id: "org-1",
          resource_type: body.resource_type,
          resource_id: body.resource_id,
          reason: body.reason,
          status: "active",
          expires_at: null,
          created_at: now,
        },
        { status: 201 },
      );
    }
    if (
      url.includes("/api/v1/organizations/org-1/retention/deletion-preview") &&
      method === "GET"
    ) {
      return Response.json({
        data_type: "stored_file",
        cutoff_at: now,
        delete_candidates: ["file-delete"],
        skipped_legal_hold: ["file-held"],
      });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/retention/deletion-jobs") &&
      method === "POST"
    ) {
      return Response.json(
        {
          id: "job-1",
          data_type: "stored_file",
          status: "succeeded",
          deleted_resource_ids: ["file-delete"],
          skipped_legal_hold: ["file-held"],
          created_at: now,
          completed_at: now,
        },
        { status: 201 },
      );
    }
    if (
      url.endsWith("/api/v1/privacy/requests") &&
      method === "GET"
    ) {
      return Response.json({ items: privacyRequests });
    }
    if (
      url.endsWith("/api/v1/privacy/requests") &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      const created = {
        id: "privacy-1",
        subject_user_id: "user-1",
        type: body.type,
        status: "verified",
        identity_verified_at: now,
        due_at: now,
        scope: body.scope,
        requested_changes: {},
        result: {},
        processing_history: [],
        created_at: now,
        updated_at: now,
        completed_at: null,
      };
      privacyRequests = [created];
      return Response.json(created, { status: 201 });
    }
    if (
      url.endsWith("/api/v1/privacy/requests/privacy-1/process") &&
      method === "POST"
    ) {
      const completed = {
        ...privacyRequests[0],
        status: "completed",
        result: {
          export: {
            identity: { email: "owner@example.com" },
          },
        },
        completed_at: now,
        updated_at: now,
      };
      privacyRequests = [completed];
      return Response.json(completed);
    }

    throw new Error(`Unhandled request: ${method} ${url}`);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

test.each([
  ["/app/acme/security/audit-log", "审计日志"],
  ["/app/acme/security/compliance", "合规控制"],
  ["/app/acme/security/incidents", "安全事件"],
  ["/app/acme/settings/data-retention", "数据保留"],
  ["/app/acme/settings/api-keys", "API 密钥"],
  ["/app/acme/settings/webhooks", "Webhook"],
  ["/account/privacy", "隐私请求"],
] as const)("%s renders the Chinese administration page", async (path, heading) => {
  const view = renderRoute(path);
  expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
  view.unmount();
});

test("creates, verifies, and explicitly revokes an API key", async () => {
  const user = userEvent.setup();
  renderRoute("/app/acme/settings/api-keys");

  await user.type(await screen.findByLabelText("密钥名称"), "CI 自动化");
  await user.clear(screen.getByLabelText("权限范围"));
  await user.type(screen.getByLabelText("权限范围"), "reports.read");
  await user.click(screen.getByRole("button", { name: "创建 API 密钥" }));

  expect(await screen.findByText("ssa_live_secret")).toBeInTheDocument();
  expect(screen.getByText("此密钥只显示一次")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "验证密钥" }));
  expect(await screen.findByText("验证成功：CI 自动化")).toBeInTheDocument();

  const keyRow = screen.getByRole("article", { name: "API 密钥 CI 自动化" });
  await user.click(
    within(keyRow).getByRole("checkbox", {
      name: "我确认依赖此密钥的自动化将立即停止",
    }),
  );
  await user.click(within(keyRow).getByRole("button", { name: "撤销密钥" }));
  expect(await within(keyRow).findByText("已撤销")).toBeInTheDocument();
});

test("previews retention impact, preserves legal holds, and confirms deletion", async () => {
  const user = userEvent.setup();
  renderRoute("/app/acme/settings/data-retention");

  await user.clear(await screen.findByLabelText("保留天数"));
  await user.type(screen.getByLabelText("保留天数"), "30");
  await user.type(screen.getByLabelText("策略说明"), "原始文件保留 30 天");
  await user.click(screen.getByRole("button", { name: "保存保留策略" }));
  expect(await screen.findByText("策略已生效：文件保留 30 天")).toBeInTheDocument();

  await user.type(screen.getByLabelText("冻结资源 ID"), "file-held");
  await user.type(screen.getByLabelText("冻结原因"), "监管调查");
  await user.click(screen.getByRole("button", { name: "创建法务冻结" }));
  expect(await screen.findByText("法务冻结已创建：file-held")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "预览删除影响" }));
  expect(await screen.findByText("将删除 1 项")).toBeInTheDocument();
  expect(screen.getByText("法务冻结保护 1 项")).toBeInTheDocument();
  expect(screen.getByText("file-held")).toBeInTheDocument();

  const deleteButton = screen.getByRole("button", { name: "执行永久删除" });
  expect(deleteButton).toBeDisabled();
  await user.click(
    screen.getByRole("checkbox", {
      name: "我已重新认证，并理解删除后的文件无法恢复",
    }),
  );
  await user.click(deleteButton);
  expect(await screen.findByText("删除完成：1 项；法务冻结跳过：1 项")).toBeInTheDocument();
});

test("creates and processes a portable privacy export with explicit reauthentication", async () => {
  const user = userEvent.setup();
  renderRoute("/account/privacy");

  await user.selectOptions(await screen.findByLabelText("请求类型"), "portability");
  await user.click(screen.getByRole("button", { name: "提交隐私请求" }));
  expect(await screen.findByText("待处理")).toBeInTheDocument();

  const requestCard = screen.getByRole("article", { name: "隐私请求 portability" });
  const processButton = within(requestCard).getByRole("button", { name: "确认并处理" });
  expect(processButton).toBeDisabled();
  await user.click(
    within(requestCard).getByRole("checkbox", {
      name: "我已重新认证，并确认处理该隐私请求",
    }),
  );
  await user.click(processButton);

  expect(await within(requestCard).findByText("已完成")).toBeInTheDocument();
  expect(
    within(requestCard).getByRole("button", { name: "下载我的数据" }),
  ).toBeInTheDocument();
});

test("filters and exports the audit trail", async () => {
  const user = userEvent.setup();
  renderRoute("/app/acme/security/audit-log");

  await user.type(await screen.findByLabelText("筛选操作"), "api_key");
  expect(screen.getByText("api_key.created")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "导出 JSON" }));
  expect(await screen.findByText("已生成 1 条审计记录")).toBeInTheDocument();
});
