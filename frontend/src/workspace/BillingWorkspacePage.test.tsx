import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { routes } from "../app/router";

const now = "2026-06-13T08:00:00Z";
const planItems = [
  {
    key: "starter",
    name: "Starter",
    description: "适合开始统一管理软件资产的团队。",
    currency: "USD",
    billing_interval: "month",
    amount_minor: 0,
    entitlements: [
      { key: "applications", value_type: "integer", value: 5, hard_limit: true },
    ],
  },
  {
    key: "pro",
    name: "Pro",
    description: "适合需要更高额度、API 与优先支持的团队。",
    currency: "USD",
    billing_interval: "month",
    amount_minor: 4900,
    entitlements: [
      { key: "applications", value_type: "integer", value: 50, hard_limit: true },
    ],
  },
];

function session(role = "owner") {
  return {
    user: {
      id: "user-1",
      email: "owner@example.com",
      display_name: "负责人",
      status: "active",
    },
    organizations: [
      { id: "org-1", name: "示例科技", slug: "acme", role },
    ],
  };
}

function summary(planKey = "starter") {
  return {
    plan: planItems.find(item => item.key === planKey),
    pending_plan: null,
    payment_issue: false,
    subscription: {
      status: planKey === "starter" ? "trialing" : "active",
      read_only: false,
      trial_ends_at: "2026-06-27T08:00:00Z",
      current_period_start: now,
      current_period_end: "2026-07-13T08:00:00Z",
      cancel_at_period_end: false,
      pending_change_at: null,
      pending_change_type: null,
    },
  };
}

function renderRoute(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(<RouterProvider router={router} />);
}

beforeEach(() => {
  vi.spyOn(window, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/v1/auth/me")) return Response.json(session());
    if (url.endsWith("/api/v1/billing/plans")) {
      return Response.json({ items: planItems });
    }
    if (
      url.endsWith("/api/v1/organizations/org-1/billing") &&
      method === "GET"
    ) {
      return Response.json(summary());
    }
    if (url.endsWith("/billing/change-preview") && method === "POST") {
      return Response.json({
        current_plan: "starter",
        target_plan: "pro",
        direction: "upgrade",
        effective_at: now,
        current_amount_minor: 0,
        target_amount_minor: 4900,
        proration_minor: 4900,
        lost_features: [],
        over_limit: {},
      });
    }
    if (url.endsWith("/billing/change-plan") && method === "POST") {
      return Response.json(summary("pro"));
    }
    return Response.json({ detail: "not mocked" }, { status: 404 });
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("公共定价页展示真实套餐与中文权益", async () => {
  renderRoute("/pricing");

  expect(
    await screen.findByRole("heading", {
      name: "按团队规模和使用场景选择合适方案",
    }),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Starter" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Pro" })).toBeInTheDocument();
  expect(screen.getByText("最多 50 个应用")).toBeInTheDocument();
});

test("组织所有者可以预览并确认升级", async () => {
  const user = userEvent.setup();
  renderRoute("/app/acme/settings/billing");

  expect(await screen.findByText("14 天免费试用")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Starter" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "升级到 Pro" }));
  expect(await screen.findByText("本次预计支付")).toBeInTheDocument();
  expect(screen.getByText("$49.00")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "确认升级" }));
  expect(await screen.findByRole("heading", { name: "Pro" })).toBeInTheDocument();
  expect(screen.getByText("计费同步正常")).toBeInTheDocument();
});

test("普通成员不能读取或看到组织账单", async () => {
  vi.mocked(window.fetch).mockImplementation(async input => {
    const url = String(input);
    if (url.endsWith("/api/v1/auth/me")) return Response.json(session("member"));
    return Response.json({ detail: "unexpected" }, { status: 500 });
  });

  renderRoute("/app/acme/settings/billing");

  expect(await screen.findByText("无权访问账单设置")).toBeInTheDocument();
  expect(
    vi.mocked(window.fetch).mock.calls.some(([input]) =>
      String(input).includes("/organizations/org-1/billing"),
    ),
  ).toBe(false);
});
