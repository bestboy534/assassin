import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDir, "..");
const frontendPackage = path.join(repositoryRoot, "frontend", "package.json");
const requireFromFrontend = createRequire(frontendPackage);
const baseUrl = (process.argv[2] ?? "http://127.0.0.1:5173").replace(/\/$/, "");
const routeManifest = JSON.parse(
  await fs.readFile(path.join(scriptDir, "public_routes.json"), "utf8"),
);

let chromium;
try {
  ({ chromium } = requireFromFrontend("playwright"));
} catch {
  try {
    ({ chromium } = requireFromFrontend("@playwright/test"));
  } catch {
    console.error(
      "缺少 Playwright。请先在 frontend 目录安装 @playwright/test 并执行 npx playwright install chromium。",
    );
    process.exit(2);
  }
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const failures = [];

for (const route of routeManifest) {
  const url = `${baseUrl}${route.path}`;
  try {
    const response = await page.goto(url, {
      waitUntil: "networkidle",
      timeout: 20_000,
    });
    await page.locator("h1").first().waitFor({ state: "visible", timeout: 8_000 });

    const status = response?.status() ?? 0;
    const title = await page.title();
    const bodyText = await page.locator("body").innerText();
    const heading = (await page.locator("h1").first().innerText()).trim();
    const layout = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
    }));
    const deadLinks = await page.locator('a[href="#"], a[href=""]').count();

    if (status >= 400 || status === 0) {
      failures.push(`${route.path}: HTTP ${status}`);
    }
    if (!heading) {
      failures.push(`${route.path}: 缺少非空 H1`);
    }
    if (/没有找到这个页面/.test(bodyText)) {
      failures.push(`${route.path}: 命中了 404 页面`);
    }
    if (!/[\u3400-\u9fff]/u.test(heading)) {
      failures.push(`${route.path}: H1 不是中文（${heading}）`);
    }
    if (/cledara/i.test(`${title}\n${bodyText}`)) {
      failures.push(`${route.path}: 页面仍显示 Cledara 品牌文字`);
    }
    if (layout.scroll > layout.viewport + 1) {
      failures.push(
        `${route.path}: 页面存在横向溢出 ${layout.scroll - layout.viewport}px`,
      );
    }
    if (deadLinks > 0) {
      failures.push(`${route.path}: 存在 ${deadLinks} 个空链接`);
    }

    console.log(`PASS ${route.path} ${route.label} | ${heading}`);
  } catch (error) {
    failures.push(`${route.path}: ${error instanceof Error ? error.message : error}`);
  }
}

await browser.close();

if (failures.length > 0) {
  console.error("\n公开站验收失败：");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(`\n公开站 ${routeManifest.length} 个页面全部通过浏览器验收。`);
