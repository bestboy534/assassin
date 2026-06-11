import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthPage } from "./AuthPage";

test("renders login form controls", () => {
  render(
    <MemoryRouter>
      <AuthPage mode="login" />
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: "登录你的软件管理工作区" })).toBeVisible();
  expect(screen.getByLabelText("工作邮箱")).toHaveAttribute("type", "email");
  expect(screen.getByLabelText("密码")).toHaveAttribute("type", "password");
  expect(screen.getByRole("button", { name: /登录/ })).toBeEnabled();
});

test("renders signup form controls", () => {
  render(
    <MemoryRouter>
      <AuthPage mode="signup" />
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: "从导入第一批软件支出开始" })).toBeVisible();
  expect(screen.getByLabelText("姓名")).toBeRequired();
  expect(screen.getByLabelText("组织名称")).toBeRequired();
  expect(screen.getByRole("button", { name: /创建工作区/ })).toBeEnabled();
});
