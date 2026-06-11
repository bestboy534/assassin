import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { publicPages } from "../marketing/content/pages";
import { resolveLegacyHash, routes } from "./router";

const keyRoutes = [
  ["/", "建立战略性软件采购流程"],
  ["/solutions/application-directory", "完整掌握每一款软件工具"],
  ["/about", "我们的使命"],
  ["/legal/privacy", "隐私政策"],
  ["/careers", "和我们一起，建设更好的未来"],
  ["/security", "始终认真守护你的安全"],
] as const;

test.each(keyRoutes)("renders %s", async (path, heading) => {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(heading);
});

test.each(publicPages.map(page => [page.path, page.title] as const))(
  "%s renders a localized heading",
  async (path, heading) => {
    const router = createMemoryRouter(routes, { initialEntries: [path] });
    const view = render(<RouterProvider router={router} />);
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(heading);
    view.unmount();
  },
);

test("keeps live branded slugs compatible without visible brand text", async () => {
  const router = createMemoryRouter(routes, {
    initialEntries: ["/solutions/cledara-engage"],
  });
  render(<RouterProvider router={router} />);

  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(
    "让真正使用软件的员工参与治理",
  );
  expect(document.body).not.toHaveTextContent(/cledara/i);
});

test("maps legacy hashes to canonical paths", () => {
  expect(resolveLegacyHash("#/directory")).toBe(
    "/solutions/application-directory",
  );
  expect(resolveLegacyHash("#report")).toBe("/resources/ai-report");
  expect(resolveLegacyHash("#/unknown")).toBeNull();
});
