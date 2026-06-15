import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { routes } from "../../app/router";

const now = "2026-06-15T08:00:00Z";
const ticket = {
  id: "ticket-1",
  organization_id: "org-1",
  subject: "身份目录同步失败",
  description: "同步任务连续失败，请协助排查。",
  category: "integration",
  priority: "high",
  status: "waiting_support",
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

let platformRole: string | null;
let messages: Array<Record<string, unknown>>;

function renderRoute(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(<RouterProvider router={router} />);
}

beforeEach(() => {
  platformRole = null;
  messages = [
    {
      id: "message-1",
      support_ticket_id: "ticket-1",
      author_type: "customer",
      body: "错误从今天凌晨开始出现。",
      internal: false,
      created_at: now,
    },
  ];
  vi.spyOn(window, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/v1/auth/me")) {
      return Response.json({
        user: {
          id: "user-1",
          email: "owner@example.com",
          display_name: "负责人",
          status: "active",
          platform_role: platformRole,
        },
        organizations: [
          { id: "org-1", name: "示例科技", slug: "acme", role: "owner" },
        ],
      });
    }
    if (url.includes("/api/v1/support/tickets?") && method === "GET") {
      return Response.json({ items: [ticket] });
    }
    if (url.endsWith("/api/v1/support/tickets") && method === "POST") {
      return Response.json(ticket, { status: 201 });
    }
    if (url.endsWith("/api/v1/support/tickets/ticket-1") && method === "GET") {
      return Response.json(ticket);
    }
    if (
      url.endsWith("/api/v1/support/tickets/ticket-1/messages") &&
      method === "GET"
    ) {
      return Response.json({ items: messages });
    }
    if (
      url.endsWith("/api/v1/support/tickets/ticket-1/messages") &&
      method === "POST"
    ) {
      const created = {
        id: "message-2",
        support_ticket_id: "ticket-1",
        author_type: "customer",
        body: JSON.parse(String(init?.body)).body,
        internal: false,
        created_at: now,
      };
      messages.push(created);
      return Response.json(created, { status: 201 });
    }
    if (url.endsWith("/api/v1/support/agents")) {
      return Response.json({
        items: [
          {
            id: "support-1",
            display_name: "支持专员",
            platform_role: "support_agent",
          },
        ],
      });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/support-grants") &&
      method === "GET"
    ) {
      return Response.json({ items: [] });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/support-grants") &&
      method === "POST"
    ) {
      return Response.json(
        {
          id: "grant-1",
          organization_id: "org-1",
          support_user_id: "support-1",
          scopes: ["sync_diagnostics.read"],
          reason: "排查身份目录同步错误",
          approved_by_user_id: "user-1",
          expires_at: "2026-06-15T10:00:00Z",
          revoked_at: null,
          created_at: now,
        },
        { status: 201 },
      );
    }
    if (url.endsWith("/api/v1/support/operations/tickets")) {
      return Response.json({ items: [ticket] });
    }
    if (
      url.endsWith("/api/v1/support/operations/tickets/ticket-1/messages") &&
      method === "GET"
    ) {
      return Response.json({ items: messages });
    }
    if (
      url.endsWith("/api/v1/support/operations/tickets/ticket-1/messages") &&
      method === "POST"
    ) {
      const created = {
        id: "message-support",
        support_ticket_id: "ticket-1",
        author_type: "support",
        body: JSON.parse(String(init?.body)).body,
        internal: false,
        created_at: now,
      };
      messages.push(created);
      return Response.json(created, { status: 201 });
    }
    if (url.endsWith("/api/v1/support/operations/grants")) {
      return Response.json({ items: [] });
    }
    if (url.endsWith("/api/v1/admin/status/components") && method === "GET") {
      return Response.json([
        {
          id: "component-1",
          slug: "integrations",
          name: "集成与同步",
          description: "第三方连接与同步任务",
          status: "operational",
        },
      ]);
    }
    if (url.endsWith("/api/v1/admin/status/incidents") && method === "POST") {
      return Response.json(
        {
          id: "incident-1",
          component_id: "component-1",
          title: "部分同步任务延迟",
          public_summary: "处理时间高于正常水平。",
          internal_summary: "内部队列积压。",
          impact: "degraded",
          status: "investigating",
          started_at: now,
          resolved_at: null,
        },
        { status: 201 },
      );
    }
    return Response.json({ detail: `Unhandled ${method} ${url}` }, { status: 404 });
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("客户可以浏览、新建并回复支持工单", async () => {
  const user = userEvent.setup();
  const listView = renderRoute("/app/acme/support");
  expect(await screen.findByRole("heading", { name: "支持工单" })).toBeVisible();
  expect(await screen.findByText("身份目录同步失败")).toBeVisible();
  listView.unmount();

  renderRoute("/app/acme/support/new");
  await user.type(await screen.findByLabelText("问题标题"), "新的同步问题");
  await user.type(screen.getByLabelText("问题描述"), "新的同步任务无法完成。");
  await user.click(screen.getByRole("button", { name: "提交工单" }));
  expect(await screen.findByRole("heading", { name: "身份目录同步失败" })).toBeVisible();

  await user.type(screen.getByLabelText("补充消息"), "我已经重新授权，但仍然失败。");
  await user.click(screen.getByRole("button", { name: "发送消息" }));
  expect(await screen.findByText("我已经重新授权，但仍然失败。")).toBeVisible();
});

test("客户可以创建限时诊断授权", async () => {
  const user = userEvent.setup();
  renderRoute("/app/acme/settings/support-access");
  expect(await screen.findByRole("heading", { name: "支持访问授权" })).toBeVisible();
  await screen.findByRole("option", { name: "支持专员" });
  await user.selectOptions(screen.getByLabelText("支持专员"), "support-1");
  await user.type(screen.getByLabelText("授权原因"), "排查身份目录同步错误");
  await user.click(screen.getByRole("button", { name: "创建限时授权" }));
  expect(await screen.findByText("授权已创建")).toBeVisible();
});

test("支持专员可以回复客户并查看诊断授权", async () => {
  platformRole = "support_agent";
  const user = userEvent.setup();
  renderRoute("/admin/support");
  expect(await screen.findByRole("heading", { name: "支持运营" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "处理工单" }));
  await user.type(screen.getByLabelText("支持回复"), "请重新授权身份目录连接。");
  await user.click(screen.getByRole("button", { name: "回复客户" }));
  expect(await screen.findByText("请重新授权身份目录连接。")).toBeVisible();
});

test("平台管理员可以发布公开状态事件", async () => {
  platformRole = "platform_admin";
  const user = userEvent.setup();
  renderRoute("/admin/status");
  expect(await screen.findByRole("heading", { name: "状态事件管理" })).toBeVisible();
  await user.type(screen.getByLabelText("事件标题"), "部分同步任务延迟");
  await user.type(screen.getByLabelText("公开摘要"), "处理时间高于正常水平。");
  await user.type(screen.getByLabelText("首次公开更新"), "我们正在调查该问题。");
  await user.click(screen.getByRole("button", { name: "发布状态事件" }));
  expect(await screen.findByText("状态事件已发布")).toBeVisible();
});
