import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { StatusPage } from "./StatusPage";

const statusPayload = {
  overall_status: "degraded",
  generated_at: "2026-06-15T09:00:00Z",
  components: [
    {
      id: "component-1",
      slug: "integrations",
      name: "集成与同步",
      description: "第三方连接和同步任务",
      status: "degraded",
    },
    {
      id: "component-2",
      slug: "workspace",
      name: "工作台",
      description: "登录和组织工作区",
      status: "operational",
    },
  ],
  incidents: [
    {
      id: "incident-1",
      component_id: "component-1",
      component_name: "集成与同步",
      title: "部分同步任务延迟",
      summary: "部分同步任务处理时间高于正常水平。",
      impact: "degraded",
      status: "investigating",
      started_at: "2026-06-15T08:00:00Z",
      resolved_at: null,
      postmortem_summary: null,
      updates: [
        {
          id: "update-1",
          status: "investigating",
          message: "我们正在调查部分同步任务延迟。",
          created_at: "2026-06-15T08:00:00Z",
        },
      ],
    },
  ],
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") {
        return new Response(JSON.stringify({ status: "confirmation_pending" }), {
          status: 202,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify(statusPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders public component health and incident timeline", async () => {
  render(<StatusPage />);

  expect(
    await screen.findByRole("heading", { level: 1, name: "系统运行状态" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("部分服务性能下降")).toBeInTheDocument();
  expect(screen.getAllByText("集成与同步")).toHaveLength(2);
  expect(screen.getByText("部分同步任务延迟")).toBeInTheDocument();
  expect(screen.getByText("我们正在调查部分同步任务延迟。")).toBeInTheDocument();
});

test("subscribes to incident updates with clear feedback", async () => {
  render(<StatusPage />);
  await screen.findByText("工作台");

  fireEvent.change(screen.getByLabelText("工作邮箱"), {
    target: { value: "ops@example.com" },
  });
  fireEvent.click(screen.getByRole("button", { name: "订阅状态更新" }));

  await waitFor(() => {
    expect(screen.getByText("确认邮件已发送，请检查收件箱。")).toBeInTheDocument();
  });
  expect(fetch).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/api/v1/status/subscriptions",
    expect.objectContaining({ method: "POST" }),
  );
});
