# 前端路由、设计系统与公开站重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 45 个公开页面从单体 `App.tsx` 和哈希路由迁移到路径路由、分域页面和共享设计系统，同时保持现有中文视觉与交互。

**Architecture:** React Router 负责公开站与未来工作台的路由边界；公开内容使用配置驱动页面模板，特殊页面保留独立组件。设计令牌和基础组件进入 `shared`，避免营销页与工作台复制样式。

**Tech Stack:** React、TypeScript、React Router、Tailwind/CSS Modules 或现有 CSS 渐进拆分、Vitest、Testing Library、Playwright

---

## 文件结构

**Create**

- `frontend/src/app/router.tsx`
- `frontend/src/app/providers.tsx`
- `frontend/src/marketing/layout/MarketingLayout.tsx`
- `frontend/src/marketing/navigation/navigation.ts`
- `frontend/src/marketing/pages/HomePage.tsx`
- `frontend/src/marketing/pages/GenericSolutionPage.tsx`
- `frontend/src/marketing/pages/ApplicationDirectoryPage.tsx`
- `frontend/src/marketing/pages/CompanyStoryPage.tsx`
- `frontend/src/marketing/pages/ContentIndexPage.tsx`
- `frontend/src/marketing/pages/ReportPage.tsx`
- `frontend/src/marketing/pages/LegalPage.tsx`
- `frontend/src/marketing/pages/NotFoundPage.tsx`
- `frontend/src/marketing/content/pages.ts`
- `frontend/src/shared/components/Button.tsx`
- `frontend/src/shared/components/BrandMark.tsx`
- `frontend/src/shared/styles/tokens.css`
- `frontend/src/shared/styles/base.css`
- `frontend/src/marketing/styles/marketing.css`

**Modify**

- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/package.json`
- `frontend/vite.config.ts`

## 路由映射

必须至少建立：

```text
/                                      首页
/why/finance                           财务团队
/why/procurement                       采购团队
/why/it                                IT 团队
/why/operations                        运营团队
/why/difference                        平台差异
/solutions/approvals                   审批采购
/solutions/optimization                支出优化
/solutions/payments                    软件支付
/solutions/spend                       企业支出
/solutions/application-directory       应用目录
/solutions/analytics                   分析报表
/solutions/accounting                  会计自动化
/solutions/integrations                集成
/solutions/engage                      员工参与
/solutions/onboarding                  入离职
/solutions/security                    软件安全
/solutions/compliance                  合规
/resources/*                           资源页面
/company/*                             公司页面
/legal/privacy                         隐私
/legal/terms                           条款
/pricing                               定价
/demo                                  预约演示
/login                                 登录入口
/signup                                开始使用
```

## Task 1: 建立路由契约

- [ ] **Step 1: 写失败的路径路由测试**

`frontend/src/app/router.test.tsx`：

```tsx
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { routes } from "./router";

test.each([
  ["/", "建立战略性软件采购流程"],
  ["/solutions/application-directory", "完整掌握每一款软件工具"],
  ["/about", "我们的使命"],
  ["/legal/privacy", "隐私政策"],
])("renders %s", async (path, heading) => {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(heading);
});
```

- [ ] **Step 2: 安装 React Router**

Run:

```powershell
cd frontend
npm install react-router-dom
npm run test -- router.test.tsx
```

Expected: 测试先因 `routes` 不存在而失败。

- [ ] **Step 3: 创建最小路由**

`frontend/src/app/router.tsx`：

```tsx
import type { RouteObject } from "react-router-dom";
import { MarketingLayout } from "../marketing/layout/MarketingLayout";
import { HomePage } from "../marketing/pages/HomePage";
import { NotFoundPage } from "../marketing/pages/NotFoundPage";

export const routes: RouteObject[] = [{
  element: <MarketingLayout />,
  children: [
    { index: true, element: <HomePage /> },
    { path: "*", element: <NotFoundPage /> },
  ],
}];
```

- [ ] **Step 4: 运行测试**

Run:

```powershell
npm run test -- router.test.tsx
```

Expected: 首页通过，其他路径继续失败，证明测试覆盖迁移目标。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/app frontend/package.json frontend/package-lock.json
git commit -m "feat: establish path based public routing"
```

## Task 2: 提取设计令牌与基础组件

- [ ] **Step 1: 写 Button 变体测试**

```tsx
import { render, screen } from "@testing-library/react";
import { Button } from "./Button";

test("renders link and button semantics explicitly", () => {
  const { rerender } = render(<Button>提交</Button>);
  expect(screen.getByRole("button", { name: "提交" })).toBeEnabled();
  rerender(<Button href="/demo">预约演示</Button>);
  expect(screen.getByRole("link", { name: "预约演示" })).toHaveAttribute("href", "/demo");
});
```

- [ ] **Step 2: 创建令牌**

`frontend/src/shared/styles/tokens.css`：

```css
:root {
  --color-ink: #171b46;
  --color-brand: #3f469e;
  --color-brand-dark: #20245f;
  --color-accent: #2ecad3;
  --color-accent-soft: #cafbff;
  --color-surface: #ffffff;
  --color-muted: #687488;
  --color-border: #dfe7ed;
  --radius-control: 6px;
  --radius-panel: 8px;
  --shadow-panel: 0 18px 55px rgb(15 23 42 / 8%);
  --content-wide: 1280px;
  --content-reading: 820px;
}
```

- [ ] **Step 3: 创建基础组件**

`Button.tsx` 必须使用判别联合，避免同时传 `href` 和 `onClick`：

```tsx
type Common = { children: React.ReactNode; variant?: "primary" | "secondary" | "ghost" | "dark" };
type Props = Common & (
  | { href: string; onClick?: never }
  | { href?: never; onClick?: React.MouseEventHandler<HTMLButtonElement>; type?: "button" | "submit" }
);
```

实现 `<a>` 与 `<button>` 两种语义，并保留当前视觉。

- [ ] **Step 4: 迁移品牌标记**

`BrandMark.tsx` 保留图形标记和空白品牌槽，禁止写入任何品牌名称；增加 `aria-label="未命名品牌"`。

- [ ] **Step 5: 验证**

Run:

```powershell
npm run test -- Button
npm run typecheck
```

Expected: 测试和类型检查通过。

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/shared
git commit -m "refactor: extract public design tokens and primitives"
```

## Task 3: 迁移导航与 2 秒菜单交互

- [ ] **Step 1: 写交互测试**

```tsx
test("keeps mega menu open for two seconds after pointer leaves", async () => {
  vi.useFakeTimers();
  render(<MarketingHeader />);
  await user.hover(screen.getByRole("button", { name: /为什么选择我们/ }));
  await user.unhover(screen.getByRole("button", { name: /为什么选择我们/ }));
  vi.advanceTimersByTime(1000);
  expect(screen.getByRole("link", { name: "财务团队" })).toBeVisible();
  vi.advanceTimersByTime(1100);
  expect(screen.queryByRole("link", { name: "财务团队" })).not.toBeVisible();
});
```

- [ ] **Step 2: 创建导航配置**

`navigation.ts` 导出强类型配置：

```ts
export type NavigationItem = {
  label: string;
  description?: string;
  to: string;
  icon?: LucideIcon;
};
```

将当前三组 mega menu 和普通链接完整迁移。

- [ ] **Step 3: 实现可访问菜单**

要求：

- 支持 hover、click、Escape 和焦点离开。
- `aria-expanded`、`aria-controls` 正确。
- 2 秒关闭计时器可取消。
- 路由跳转后立即关闭。
- 移动端使用展开列表，不依赖 hover。

- [ ] **Step 4: 运行测试**

Run:

```powershell
npm run test -- MarketingHeader
npm run test:e2e -- --grep "delayed close"
```

Expected: 单元测试与浏览器测试通过。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/marketing/navigation frontend/src/marketing/layout
git commit -m "refactor: migrate accessible public navigation"
```

## Task 4: 拆分页面模板与内容数据

- [ ] **Step 1: 定义内容模型**

`frontend/src/marketing/content/pages.ts`：

```ts
export type PublicPage = {
  path: string;
  category: string;
  title: string;
  description: string;
  badge: string;
  cta: { label: string; to: string };
  bullets: readonly string[];
  steps: readonly string[];
  stats: readonly [string, string, string];
};
```

将现有 `detailPages` 迁移为 `satisfies Record<string, PublicPage>`。

- [ ] **Step 2: 迁移通用解决方案页面**

`GenericSolutionPage.tsx` 从路由 loader 或配置读取页面数据，不再把全部数据和组件放在 `App.tsx`。

- [ ] **Step 3: 迁移特殊页面**

独立迁移：

- 应用目录
- 安全
- 关于/招聘
- 播客/媒体
- 软件支出报告/AI 报告
- 隐私/条款
- 支持指标

每个页面文件只负责一个页面族。

- [ ] **Step 4: 添加全路由测试**

```tsx
for (const page of publicPages) {
  test(`${page.path} renders localized heading`, async () => {
    const router = createMemoryRouter(routes, { initialEntries: [page.path] });
    render(<RouterProvider router={router} />);
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(page.title);
  });
}
```

- [ ] **Step 5: 运行**

Run:

```powershell
npm run test
npm run build
```

Expected: 所有公开路由测试通过，构建无循环依赖。

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/marketing frontend/src/app/router.tsx
git commit -m "refactor: split public pages by responsibility"
```

## Task 5: 替换入口并删除单体代码

- [ ] **Step 1: 切换 `main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./app/router";
import { AppProviders } from "./app/providers";
import "./shared/styles/tokens.css";
import "./shared/styles/base.css";
import "./marketing/styles/marketing.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </React.StrictMode>,
);
```

- [ ] **Step 2: 保留兼容重定向**

在应用启动时将旧 `#/directory` 等哈希映射到新路径一次，之后统一使用路径路由。映射表需要测试。

- [ ] **Step 3: 删除已迁移代码**

删除旧 `App.tsx` 中重复页面、路由状态和超大配置；`App.tsx` 最终仅保留兼容导出或彻底删除。拆分 `index.css` 后删除不再引用的选择器。

- [ ] **Step 4: 全面验证**

Run:

```powershell
npm run verify
npm run test:e2e
```

Expected: 45 个路由可直接访问；导航、移动菜单、搜索、折叠项和报告素材正常；无横向溢出。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src frontend/vite.config.ts
git commit -m "refactor: complete public site architecture migration"
```

## 完成验收

- [ ] URL 不再使用哈希。
- [ ] 刷新任意公开页面不会回到首页。
- [ ] 45 个页面均有中文 H1 和有效导航。
- [ ] 导航离开 1 秒仍显示，2.1 秒后关闭。
- [ ] 品牌文字槽仍为空。
- [ ] `App.tsx` 不再承担全部页面与内容。
- [ ] 桌面和 390px 移动视口无横向溢出。
