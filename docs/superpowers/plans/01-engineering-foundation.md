# 工程基线实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理仓库运行时垃圾，建立前后端统一质量门禁、测试命令、环境模板和 CI，使后续 21 个计划可稳定迭代。

**Architecture:** 保留现有 `frontend` 与 `backend` 目录，新增根级开发命令和 GitHub Actions。测试分为快速单元测试、数据库集成测试与浏览器 E2E；本计划只建立框架和最小冒烟，不实现业务功能。

**Tech Stack:** React 18、TypeScript、Vite、Vitest、Testing Library、Playwright、FastAPI、Pytest、Ruff、Mypy、Docker Compose、GitHub Actions

---

## 文件结构

**Create**

- `.editorconfig`
- `.gitattributes`
- `.github/workflows/ci.yml`
- `frontend/eslint.config.js`
- `frontend/vitest.config.ts`
- `frontend/playwright.config.ts`
- `frontend/src/test/setup.ts`
- `frontend/src/App.smoke.test.tsx`
- `frontend/e2e/public-site.spec.ts`
- `backend/pyproject.toml`
- `backend/tests/conftest.py`
- `scripts/verify.ps1`

**Modify**

- `.gitignore`
- `frontend/package.json`
- `backend/requirements.txt`
- `README.md`

**Remove from Git index**

- `frontend/.edge-codex/**`
- `frontend/dist/**`
- `backend/data/*.db`

## Task 1: 清理仓库生成物

- [ ] **Step 1: 写入忽略规则**

在 `.gitignore` 中加入：

```gitignore
# Frontend
frontend/node_modules/
frontend/dist/
frontend/.edge-codex/
frontend/test-results/
frontend/playwright-report/
frontend/coverage/

# Backend
backend/.venv/
backend/.pytest_cache/
backend/.mypy_cache/
backend/.ruff_cache/
backend/data/*.db
backend/htmlcov/
**/__pycache__/
*.pyc

# Local environment
.env
*.log
```

- [ ] **Step 2: 从索引移除已暂存的浏览器目录**

Run:

```powershell
git rm -r --cached --ignore-unmatch frontend/.edge-codex frontend/dist
```

Expected: 路径从 Git 索引移除，本地文件可继续存在。

- [ ] **Step 3: 验证仓库状态**

Run:

```powershell
git status --short
git check-ignore frontend/.edge-codex/Default/Preferences
```

Expected: 浏览器目录不再显示为新增文件，第二条命令输出匹配路径。

- [ ] **Step 4: Commit**

```powershell
git add .gitignore
git commit -m "chore: ignore local runtime artifacts"
```

## Task 2: 建立前端测试与静态检查

- [ ] **Step 1: 安装开发依赖并添加脚本**

Run:

```powershell
cd frontend
npm install -D eslint @eslint/js typescript-eslint eslint-plugin-react-hooks eslint-plugin-react-refresh vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event @playwright/test
```

在 `package.json` 中加入：

```json
{
  "scripts": {
    "lint": "eslint .",
    "typecheck": "tsc -b --pretty false",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "verify": "npm run lint && npm run typecheck && npm run test && npm run build"
  }
}
```

- [ ] **Step 2: 写失败的冒烟测试**

`frontend/src/App.smoke.test.tsx`：

```tsx
import { render, screen } from "@testing-library/react";
import App from "./App";

test("renders the Chinese public homepage", () => {
  window.location.hash = "#/";
  render(<App />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("软件");
  expect(screen.getByRole("button", { name: "预约演示" })).toBeVisible();
});
```

- [ ] **Step 3: 配置 Vitest**

`frontend/vitest.config.ts`：

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: { reporter: ["text", "html"] },
  },
});
```

`frontend/src/test/setup.ts`：

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: 运行并修复测试环境**

Run:

```powershell
npm run lint
npm run typecheck
npm run test
```

Expected: 三条命令均通过；如果现有页面存在重复可访问名称，使用更精确的 role/name 修正测试，不降低断言。

- [ ] **Step 5: Commit**

```powershell
git add frontend/package.json frontend/package-lock.json frontend/eslint.config.js frontend/vitest.config.ts frontend/src/test
git commit -m "test: establish frontend quality checks"
```

## Task 3: 建立后端质量门禁

- [ ] **Step 1: 添加工具配置**

`backend/pyproject.toml`：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.11"
plugins = ["pydantic.mypy"]
strict = true
ignore_missing_imports = true
```

在 `backend/requirements.txt` 增加：

```text
ruff
mypy
```

- [ ] **Step 2: 建立隔离测试配置**

`backend/tests/conftest.py`：

```py
import os

os.environ.setdefault("USE_LLM", "false")
os.environ.setdefault("ENABLE_DATABASE", "false")
os.environ.setdefault("LOG_LEVEL", "warning")
```

- [ ] **Step 3: 运行现有测试并修复静态问题**

Run:

```powershell
cd backend
python -m pytest -q
python -m ruff check app tests
python -m mypy app
```

Expected: 测试通过；Ruff 与 Mypy 无错误。修复类型与格式问题时不得改变 API 响应语义。

- [ ] **Step 4: Commit**

```powershell
git add backend/pyproject.toml backend/requirements.txt backend/tests backend/app
git commit -m "test: establish backend quality checks"
```

## Task 4: 建立浏览器 E2E 冒烟

- [ ] **Step 1: 写公开站路由测试**

`frontend/e2e/public-site.spec.ts`：

```ts
import { expect, test } from "@playwright/test";

test("public navigation remains usable during delayed close", async ({ page }) => {
  await page.goto("/");
  const trigger = page.getByRole("button", { name: /为什么选择我们/ });
  await trigger.hover();
  await expect(page.getByText("财务团队", { exact: true })).toBeVisible();
  await page.mouse.move(0, 0);
  await page.waitForTimeout(1000);
  await expect(page.getByText("财务团队", { exact: true })).toBeVisible();
});

test("all public routes have a primary heading", async ({ page }) => {
  for (const route of ["/", "/solutions/application-directory", "/about", "/careers"]) {
    await page.goto(route);
    await expect(page.locator("h1").first()).toBeVisible();
  }
});
```

- [ ] **Step 2: 配置本地 Web Server**

`frontend/playwright.config.ts`：

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://127.0.0.1:4173", trace: "retain-on-failure" },
  webServer: {
    command: "npm run build && npm run preview -- --host 127.0.0.1",
    port: 4173,
    reuseExistingServer: true,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["iPhone 13"] } },
  ],
});
```

- [ ] **Step 3: 安装浏览器并运行**

Run:

```powershell
npx playwright install chromium
npm run test:e2e
```

Expected: Chromium 桌面与移动项目全部通过。

- [ ] **Step 4: Commit**

```powershell
git add frontend/playwright.config.ts frontend/e2e frontend/package.json frontend/package-lock.json
git commit -m "test: add public site browser smoke tests"
```

## Task 5: 建立 CI 与统一验证入口

- [ ] **Step 1: 创建 PowerShell 验证脚本**

`scripts/verify.ps1`：

```powershell
$ErrorActionPreference = "Stop"

Push-Location backend
python -m pytest -q
python -m ruff check app tests
python -m mypy app
Pop-Location

Push-Location frontend
npm ci
npm run verify
Pop-Location
```

- [ ] **Step 2: 创建 CI**

`.github/workflows/ci.yml` 必须包含：

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm", cache-dependency-path: frontend/package-lock.json }
      - run: pip install -r backend/requirements.txt
      - run: python -m pytest -q
        working-directory: backend
      - run: python -m ruff check app tests
        working-directory: backend
      - run: python -m mypy app
        working-directory: backend
      - run: npm ci
        working-directory: frontend
      - run: npm run verify
        working-directory: frontend
```

- [ ] **Step 3: 更新 README**

在 `README.md` 增加“开发验证”章节，列出：

```powershell
.\scripts\verify.ps1
```

并说明所有 PR 必须通过 CI。

- [ ] **Step 4: 完整验证**

Run:

```powershell
.\scripts\verify.ps1
git diff --check
```

Expected: 所有命令退出码为 `0`。

- [ ] **Step 5: Commit**

```powershell
git add .github .editorconfig .gitattributes scripts README.md
git commit -m "ci: add repository verification pipeline"
```

## 完成验收

- [ ] 本地运行时目录不再出现在 Git 状态中。
- [ ] 前后端均有 lint、类型检查和测试命令。
- [ ] 公开站至少有桌面与移动 E2E 冒烟。
- [ ] CI 在干净检出环境中可执行。
- [ ] README 给出唯一、准确的验证入口。

