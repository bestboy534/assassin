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

beforeEach(() => {
  applicationItems = [];
  auditRuns = [];
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
