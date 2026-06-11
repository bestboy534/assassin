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

beforeEach(() => {
  applicationItems = [];
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
