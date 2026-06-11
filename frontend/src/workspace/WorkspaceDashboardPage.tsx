import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { BarChart3, Bell, CheckCircle2, CreditCard, LogOut, Search } from "lucide-react";
import { getCurrentSession, logoutAccount, type AuthSession } from "../app/api";

const dashboardCards = [
  ["应用总数", "连接身份目录后自动统计", BarChart3],
  ["本月软件支出", "导入账单后展示趋势", CreditCard],
  ["待审批事项", "采购与续订任务会汇总到这里", Bell],
  ["已确认节省", "节省项目完成后自动归档", CheckCircle2],
] as const;

const workspaceNav = [
  ["总览", "dashboard"],
  ["应用目录", "applications"],
  ["采购审批", "procurement"],
  ["合同续订", "contracts"],
  ["预算交易", "spend"],
  ["报表", "reports"],
] as const;

export function WorkspaceDashboardPage() {
  const { organizationSlug } = useParams();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getCurrentSession()
      .then(value => {
        if (active) setSession(value);
      })
      .catch(caught => {
        if (active) setError(caught instanceof Error ? caught.message : "请先登录");
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <main className="workspace-auth-required">
        <h1>请先登录</h1>
        <p>{error}</p>
        <Link to="/login">返回登录</Link>
      </main>
    );
  }

  if (!session) {
    return (
      <main className="workspace-auth-required">
        <h1>正在进入工作区</h1>
        <p>正在确认账号、组织和权限。</p>
      </main>
    );
  }

  const currentOrganization =
    session.organizations.find(item => item.slug === organizationSlug) ?? session.organizations[0];
  const basePath = `/app/${currentOrganization?.slug ?? organizationSlug ?? "workspace"}`;

  return (
    <main className="workspace-shell">
      <aside className="workspace-sidebar">
        <Link aria-label="工作台首页" className="workspace-mark" to="/">
          <span />
          <strong>工作台</strong>
        </Link>
        <nav>
          {workspaceNav.map(([label, path]) => (
            <Link
              aria-current={path === "dashboard" ? "page" : undefined}
              key={path}
              to={`${basePath}/${path}`}
            >
              {label}
            </Link>
          ))}
        </nav>
      </aside>

      <section className="workspace-main">
        <header className="workspace-topbar">
          <div>
            <p>当前组织</p>
            <h1>{currentOrganization?.name ?? "工作区总览"}</h1>
          </div>
          <div className="workspace-actions">
            <button aria-label="全局搜索" type="button"><Search className="h-5 w-5" /></button>
            <button aria-label="通知中心" type="button"><Bell className="h-5 w-5" /></button>
            <button
              onClick={async () => {
                await logoutAccount();
                window.location.assign("/login");
              }}
              type="button"
            >
              <LogOut className="h-4 w-4" />
              退出
            </button>
          </div>
        </header>

        <div className="workspace-hero">
          <span>{session.user.display_name}</span>
          <h2>把软件发现、支出、审批和续订放进同一个工作流</h2>
          <p>这里已经接入账号、组织和会话。接下来应用目录、账单审计和采购任务会逐步填充这些工作台区域。</p>
        </div>

        <div className="workspace-grid">
          {dashboardCards.map(([title, body, Icon]) => (
            <article className="workspace-card" key={title}>
              <Icon className="h-6 w-6" />
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

export function WorkspaceSectionPage() {
  const { section } = useParams();
  const sectionTitle =
    workspaceNav.find(([, path]) => path === section)?.[0] ?? "工作区模块";

  return (
    <main className="workspace-auth-required">
      <h1>{sectionTitle}</h1>
      <p>这个模块的路由已经预留，后续实施计划会把真实列表、详情、审批和报表能力接入这里。</p>
      <Link relative="path" to="../dashboard">
        返回总览
      </Link>
    </main>
  );
}
