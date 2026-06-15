import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  BarChart3,
  Bell,
  CheckCircle2,
  CreditCard,
  FileText,
  LogOut,
  Plus,
  Search,
} from "lucide-react";
import {
  createAnalysisRun,
  createApplication,
  createSavingsOpportunity,
  approveApprovalTask,
  getCurrentSession,
  createPurchaseRequest,
  listApprovalTasks,
  listAnalysisRuns,
  listApplications,
  listPurchaseRequests,
  logoutAccount,
  type AnalysisRunSummary,
  type ApprovalTaskItem,
  type ApplicationItem,
  type AuthSession,
  type OrganizationSummary,
  type PurchaseRequestItem,
  submitPurchaseRequest,
} from "../app/api";
import type { SourceHint, SubscriptionItem } from "../types";
import { BudgetTransactionSection } from "./BudgetTransactionSection";
import { ContractRenewalSection } from "./ContractRenewalSection";
import { IntegrationCenterSection } from "./IntegrationCenterSection";
import { InvoiceAccountingSection } from "./InvoiceAccountingSection";
import { PaymentInstrumentSection } from "./PaymentInstrumentSection";
import { ReportWorkspaceSection } from "./ReportWorkspaceSection";
import { SavingsOptimizationSection } from "./SavingsOptimizationSection";
import { VendorRiskSection } from "./VendorRiskSection";

const dashboardCards = [
  ["应用总数", "连接身份目录后自动统计", BarChart3],
  ["本月软件支出", "导入账单后展示趋势", CreditCard],
  ["待审批事项", "采购与续订任务会汇总到这里", Bell],
  ["已确认节省", "节省项目完成后自动归档", CheckCircle2],
] as const;

export const workspaceNav = [
  ["总览", "dashboard"],
  ["应用目录", "applications"],
  ["采购审批", "procurement"],
  ["供应商风险", "vendors"],
  ["合同续订", "contracts"],
  ["预算交易", "spend"],
  ["账单审计", "audit"],
  ["节省优化", "savings"],
  ["支付卡片", "payments"],
  ["发票会计", "invoices"],
  ["集成中心", "integrations"],
  ["报表", "reports"],
  ["审计日志", "security/audit-log"],
  ["合规控制", "security/compliance"],
  ["安全事件", "security/incidents"],
  ["数据保留", "settings/data-retention"],
  ["API 密钥", "settings/api-keys"],
  ["Webhook", "settings/webhooks"],
  ["账单与套餐", "settings/billing"],
] as const;

export type WorkspaceState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      session: AuthSession;
      currentOrganization: OrganizationSummary;
    };

export function useWorkspaceState(): WorkspaceState {
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

  if (error) return { status: "error", message: error };
  if (!session) return { status: "loading" };

  const currentOrganization =
    session.organizations.find(item => item.slug === organizationSlug) ?? session.organizations[0];

  if (!currentOrganization) {
    return { status: "error", message: "没有可用组织，请先创建工作区。" };
  }

  return { status: "ready", session, currentOrganization };
}

export function WorkspaceLoading() {
  return (
    <main className="workspace-auth-required">
      <h1>正在进入工作区</h1>
      <p>正在确认账号、组织和权限。</p>
    </main>
  );
}

export function WorkspaceError({ message }: { message: string }) {
  return (
    <main className="workspace-auth-required">
      <h1>请先登录</h1>
      <p>{message}</p>
      <Link to="/login">返回登录</Link>
    </main>
  );
}

export function WorkspaceShell({
  activeSection,
  children,
  currentOrganization,
}: {
  activeSection: string;
  children: ReactNode;
  currentOrganization: OrganizationSummary;
}) {
  const basePath = `/app/${currentOrganization.slug}`;
  const canManageBilling = ["owner", "admin", "finance", "finance_admin"].includes(
    currentOrganization.role,
  );
  const visibleNav = workspaceNav.filter(
    ([, path]) => path !== "settings/billing" || canManageBilling,
  );

  return (
    <main className="workspace-shell">
      <aside className="workspace-sidebar">
        <Link aria-label="工作台首页" className="workspace-mark" to="/">
          <span />
          <strong>工作台</strong>
        </Link>
        <nav>
          {visibleNav.map(([label, path]) => (
            <Link
              aria-current={path === activeSection ? "page" : undefined}
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
            <h1>{currentOrganization.name}</h1>
          </div>
          <div className="workspace-actions">
            <button aria-label="全局搜索" type="button">
              <Search className="h-5 w-5" />
            </button>
            <button aria-label="通知中心" type="button">
              <Bell className="h-5 w-5" />
            </button>
            <button
              onClick={async () => {
                await logoutAccount();
                window.location.assign("/login");
              }}
              type="button"
            >
              <LogOut className="h-4 w-4" />
              <span>退出</span>
            </button>
          </div>
        </header>
        {children}
      </section>
    </main>
  );
}

export function WorkspaceDashboardPage() {
  const workspace = useWorkspaceState();

  if (workspace.status === "loading") return <WorkspaceLoading />;
  if (workspace.status === "error") return <WorkspaceError message={workspace.message} />;

  return (
    <WorkspaceShell activeSection="dashboard" currentOrganization={workspace.currentOrganization}>
      <div className="workspace-hero">
        <span>{workspace.session.user.display_name}</span>
        <h2>把软件发现、支出、审批和续订放进同一个工作流</h2>
        <p>这里已经接入账号、组织和会话。应用目录会把手动登记、供应商导入和账单发现汇总为可治理资产。</p>
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
    </WorkspaceShell>
  );
}

export function WorkspaceSectionPage() {
  const { section = "dashboard" } = useParams();
  const workspace = useWorkspaceState();

  if (workspace.status === "loading") return <WorkspaceLoading />;
  if (workspace.status === "error") return <WorkspaceError message={workspace.message} />;

  if (section === "applications") {
    return (
      <WorkspaceShell
        activeSection="applications"
        currentOrganization={workspace.currentOrganization}
      >
        <ApplicationCatalogSection
          organizationId={workspace.currentOrganization.id}
          organizationSlug={workspace.currentOrganization.slug}
        />
      </WorkspaceShell>
    );
  }

  if (section === "procurement") {
    return (
      <WorkspaceShell
        activeSection="procurement"
        currentOrganization={workspace.currentOrganization}
      >
        <ProcurementSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "contracts") {
    return (
      <WorkspaceShell activeSection="contracts" currentOrganization={workspace.currentOrganization}>
        <ContractRenewalSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "vendors") {
    return (
      <WorkspaceShell activeSection="vendors" currentOrganization={workspace.currentOrganization}>
        <VendorRiskSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "spend") {
    return (
      <WorkspaceShell activeSection="spend" currentOrganization={workspace.currentOrganization}>
        <BudgetTransactionSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "audit") {
    return (
      <WorkspaceShell activeSection="audit" currentOrganization={workspace.currentOrganization}>
        <BillingAuditSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "savings") {
    return (
      <WorkspaceShell activeSection="savings" currentOrganization={workspace.currentOrganization}>
        <SavingsOptimizationSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "payments") {
    return (
      <WorkspaceShell activeSection="payments" currentOrganization={workspace.currentOrganization}>
        <PaymentInstrumentSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "invoices") {
    return (
      <WorkspaceShell activeSection="invoices" currentOrganization={workspace.currentOrganization}>
        <InvoiceAccountingSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "integrations") {
    return (
      <WorkspaceShell
        activeSection="integrations"
        currentOrganization={workspace.currentOrganization}
      >
        <IntegrationCenterSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  if (section === "reports") {
    return (
      <WorkspaceShell activeSection="reports" currentOrganization={workspace.currentOrganization}>
        <ReportWorkspaceSection organizationId={workspace.currentOrganization.id} />
      </WorkspaceShell>
    );
  }

  const sectionTitle =
    workspaceNav.find(([, path]) => path === section)?.[0] ?? "工作区模块";

  return (
    <WorkspaceShell activeSection={section} currentOrganization={workspace.currentOrganization}>
      <section className="workspace-panel">
        <div className="workspace-section-heading">
          <span>即将上线</span>
          <h2>{sectionTitle}</h2>
          <p>这个模块的路由已经预留，后续会把真实列表、详情、审批和报表能力接入这里。</p>
        </div>
        <Link className="workspace-secondary-link" relative="path" to="../dashboard">
          返回总览
        </Link>
      </section>
    </WorkspaceShell>
  );
}

function ApplicationCatalogSection({
  organizationId,
  organizationSlug,
}: {
  organizationId: string;
  organizationSlug: string;
}) {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [businessOwner, setBusinessOwner] = useState("");
  const [technicalOwner, setTechnicalOwner] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    listApplications(organizationId)
      .then(response => {
        if (active) {
          setApplications(response.items);
          setError(null);
        }
      })
      .catch(caught => {
        if (active) setError(caught instanceof Error ? caught.message : "应用目录加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) return;

    setSaving(true);
    setError(null);
    try {
      const created = await createApplication(organizationId, {
        name: trimmedName,
        category: category.trim() || "未分类",
        business_owner: businessOwner.trim() || null,
        technical_owner: technicalOwner.trim() || null,
        approved: false,
      });
      setApplications(current => [created, ...current.filter(item => item.id !== created.id)]);
      setName("");
      setBusinessOwner("");
      setTechnicalOwner("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "新增应用失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-section-heading">
        <span>软件资产</span>
        <h2>应用目录</h2>
        <p>统一登记组织正在使用的软件，先把名称、类别和负责人落到可追踪清单，再逐步接入账单、身份和审批数据。</p>
      </div>

      <form className="workspace-app-form" onSubmit={handleSubmit}>
        <label>
          <span>应用名称</span>
          <input
            onChange={event => setName(event.target.value)}
            placeholder="例如 Notion"
            required
            value={name}
          />
        </label>
        <label>
          <span>类别</span>
          <input
            onChange={event => setCategory(event.target.value)}
            placeholder="协作、营销、财务"
            value={category}
          />
        </label>
        <label>
          <span>业务负责人</span>
          <input
            onChange={event => setBusinessOwner(event.target.value)}
            placeholder="业务团队"
            value={businessOwner}
          />
        </label>
        <label>
          <span>技术负责人</span>
          <input
            onChange={event => setTechnicalOwner(event.target.value)}
            placeholder="IT 或安全负责人"
            value={technicalOwner}
          />
        </label>
        <button disabled={saving} type="submit">
          <Plus className="h-4 w-4" />
          新增应用
        </button>
      </form>

      {error ? (
        <div className="workspace-inline-error">
          <p>{error}</p>
          {error.includes("套餐额度") ? (
            <Link to={`/app/${organizationSlug}/settings/billing`}>
              查看套餐与升级
            </Link>
          ) : null}
        </div>
      ) : null}

      <ApplicationCatalogTable applications={applications} loading={loading} />
    </section>
  );
}

function ApplicationCatalogTable({
  applications,
  loading,
}: {
  applications: ApplicationItem[];
  loading: boolean;
}) {
  if (loading) {
    return <p className="workspace-muted">正在加载应用目录...</p>;
  }

  if (applications.length === 0) {
    return (
      <div className="workspace-empty">
        <h3>还没有应用</h3>
        <p>先手动新增核心软件，后续导入账单和身份目录时会自动合并重复项。</p>
      </div>
    );
  }

  return (
    <div className="workspace-table-wrap">
      <table className="workspace-table">
        <thead>
          <tr>
            <th>应用</th>
            <th>类别</th>
            <th>业务负责人</th>
            <th>安全状态</th>
            <th>审批</th>
          </tr>
        </thead>
        <tbody>
          {applications.map(application => (
            <tr key={application.id}>
              <td>
                <strong>{application.name}</strong>
                <span>{application.status === "active" ? "使用中" : "已归档"}</span>
              </td>
              <td>{application.category}</td>
              <td>{application.business_owner ?? "未分配"}</td>
              <td>{riskLabel(application.risk_level)}</td>
              <td>{application.approved ? "已批准" : "待确认"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProcurementSection({ organizationId }: { organizationId: string }) {
  const [requests, setRequests] = useState<PurchaseRequestItem[]>([]);
  const [tasks, setTasks] = useState<ApprovalTaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [softwareName, setSoftwareName] = useState("");
  const [businessReason, setBusinessReason] = useState("");
  const [monthlyBudget, setMonthlyBudget] = useState("");
  const [department, setDepartment] = useState("");
  const [handlesSensitiveData, setHandlesSensitiveData] = useState(false);
  const [dataCategories, setDataCategories] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      listPurchaseRequests(organizationId),
      listApprovalTasks(organizationId),
    ])
      .then(([requestResponse, taskResponse]) => {
        if (active) {
          setRequests(requestResponse.items);
          setTasks(taskResponse.items);
          setError(null);
        }
      })
      .catch(caught => {
        if (active) setError(caught instanceof Error ? caught.message : "采购审批加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  async function refreshTasks() {
    const response = await listApprovalTasks(organizationId);
    setTasks(response.items);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const budget = Number(monthlyBudget);
    if (!softwareName.trim() || !businessReason.trim() || Number.isNaN(budget)) return;

    setSaving(true);
    setError(null);
    try {
      const created = await createPurchaseRequest(organizationId, {
        software_name: softwareName.trim(),
        business_reason: businessReason.trim(),
        estimated_monthly_cost_usd: budget,
        department: department.trim() || "未分配",
        handles_sensitive_data: handlesSensitiveData,
        data_categories: dataCategories
          .split(/[,，\n]/)
          .map(item => item.trim())
          .filter(Boolean),
      });
      setRequests(current => [created, ...current.filter(item => item.id !== created.id)]);
      setSoftwareName("");
      setBusinessReason("");
      setMonthlyBudget("");
      setDepartment("");
      setHandlesSensitiveData(false);
      setDataCategories("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "采购申请保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmitRequest(requestId: string) {
    setSaving(true);
    setError(null);
    try {
      const updated = await submitPurchaseRequest(organizationId, requestId);
      setRequests(current => current.map(item => (item.id === updated.id ? updated : item)));
      await refreshTasks();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "提交审批失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleApprove(task: ApprovalTaskItem) {
    setSaving(true);
    setError(null);
    try {
      const idempotencyKey = window.crypto.randomUUID?.() ?? `${task.id}-${Date.now()}`;
      const updated = await approveApprovalTask(
        organizationId,
        task.id,
        "同意采购。",
        idempotencyKey,
      );
      setTasks(current => current.map(item => (item.id === updated.id ? updated : item)));
      setRequests(current =>
        current.map(item =>
          item.id === task.purchase_request_id ? { ...item, status: "approved" } : item,
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "审批失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-section-heading">
        <span>采购与审批</span>
        <h2>采购审批</h2>
        <p>先登记采购意图，再交给财务审批。这里保留草稿、提交和批准三个动作，后续会继续接入版本化流程和多角色审批。</p>
      </div>

      <form className="workspace-procurement-form" onSubmit={handleCreate}>
        <label>
          <span>软件名称</span>
          <input
            onChange={event => setSoftwareName(event.target.value)}
            placeholder="例如 Notion AI"
            required
            value={softwareName}
          />
        </label>
        <label>
          <span>用途说明</span>
          <textarea
            onChange={event => setBusinessReason(event.target.value)}
            placeholder="为什么需要采购这款软件"
            required
            value={businessReason}
          />
        </label>
        <label>
          <span>月度预算</span>
          <input
            onChange={event => setMonthlyBudget(event.target.value)}
            placeholder="120"
            required
            step="0.01"
            type="number"
            value={monthlyBudget}
          />
        </label>
        <label>
          <span>部门</span>
          <input
            onChange={event => setDepartment(event.target.value)}
            placeholder="运营 / 财务 / IT"
            required
            value={department}
          />
        </label>
        <label className="workspace-toggle">
          <input
            checked={handlesSensitiveData}
            onChange={event => setHandlesSensitiveData(event.target.checked)}
            type="checkbox"
          />
          <span>涉及敏感数据</span>
        </label>
        <label className="workspace-procurement-wide">
          <span>数据分类</span>
          <textarea
            onChange={event => setDataCategories(event.target.value)}
            placeholder="客户资料, 内部文档"
            value={dataCategories}
          />
        </label>
        <button disabled={saving} type="submit">
          保存申请
        </button>
      </form>

      {error && <p className="workspace-inline-error">{error}</p>}

      <div className="workspace-audit-layout">
        <div className="workspace-run-list">
          <h3>采购申请</h3>
          {loading ? <p className="workspace-muted">正在加载采购申请...</p> : null}
          {!loading && requests.length === 0 ? (
            <div className="workspace-empty">
              <h3>还没有采购申请</h3>
              <p>先保存一个草稿，再提交给财务审批。</p>
            </div>
          ) : null}
          {requests.map(request => (
            <article key={request.id} className="workspace-procurement-card">
              <div>
                <strong>{request.software_name}</strong>
                <span>
                  {request.department} · {formatUsd(request.estimated_monthly_cost_usd)}/月
                </span>
                <small>{procurementStatusLabel(request.status)}</small>
              </div>
              {request.status === "draft" ? (
                <button
                  disabled={saving}
                  onClick={() => handleSubmitRequest(request.id)}
                  type="button"
                >
                  提交审批
                </button>
              ) : null}
            </article>
          ))}
        </div>

        <div className="workspace-audit-results">
          <h3>审批任务</h3>
          {loading ? <p className="workspace-muted">正在加载审批任务...</p> : null}
          {!loading && tasks.length === 0 ? (
            <div className="workspace-empty">
              <h3>还没有审批任务</h3>
              <p>提交采购申请后，这里会出现财务审批任务。</p>
            </div>
          ) : null}
          {tasks.map(task => (
            <article key={task.id} className="workspace-procurement-card">
              <div>
                <strong>{approvalRoleLabel(task.assignee_role)}</strong>
                <span>{task.purchase_request_id}</span>
                <small>{procurementStatusLabel(task.status)}</small>
              </div>
              {task.status === "pending" ? (
                <button disabled={saving} onClick={() => handleApprove(task)} type="button">
                  批准
                </button>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

const sourceOptions: Array<[SourceHint, string]> = [
  ["csv", "信用卡 CSV"],
  ["apple_mail", "Apple 收据"],
  ["stripe_mail", "Stripe 邮件"],
  ["paypal_mail", "PayPal 文本"],
  ["google_play", "Google Play"],
  ["unknown", "未知来源"],
];

function BillingAuditSection({ organizationId }: { organizationId: string }) {
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [items, setItems] = useState<SubscriptionItem[]>([]);
  const [rawText, setRawText] = useState("");
  const [sourceHint, setSourceHint] = useState<SourceHint>("csv");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdOpportunityIds, setCreatedOpportunityIds] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    listAnalysisRuns(organizationId)
      .then(response => {
        if (active) {
          setRuns(response.items);
          setError(null);
        }
      })
      .catch(caught => {
        if (active) setError(caught instanceof Error ? caught.message : "账单审计加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!rawText.trim()) return;

    setSaving(true);
    setError(null);
    try {
      const detail = await createAnalysisRun(organizationId, {
        raw_text: rawText,
        source_hint: sourceHint,
      });
      setRuns(current => [detail.run, ...current.filter(run => run.id !== detail.run.id)]);
      setItems(detail.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "账单审计失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateSavingsOpportunity(item: SubscriptionItem) {
    setError(null);
    try {
      const effectiveDate = new Date().toISOString().slice(0, 10);
      await createSavingsOpportunity(organizationId, {
        source_type: "analysis_item",
        source_id: item.id,
        rule_version: "billing-audit-v1",
        period_key: effectiveDate.slice(0, 7),
        title: `优化 ${item.software_name} 订阅`,
        department: "待分配",
        category: "cancellation",
        monthly_baseline: String(item.monthly_cost_usd),
        currency: "USD",
        effective_date: effectiveDate,
        contract_end: null,
        evidence: item.evidence,
      });
      setCreatedOpportunityIds(current => new Set(current).add(item.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建节省机会失败");
    }
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-section-heading">
        <span>AI 账单审计</span>
        <h2>账单审计</h2>
        <p>粘贴信用卡 CSV、收据或邮件正文，系统会提取软件订阅、月化成本、风险类型和退订线索，并把结果保存到当前组织。</p>
      </div>

      <form className="workspace-audit-form" onSubmit={handleSubmit}>
        <div className="workspace-audit-controls">
          <label>
            <span>来源类型</span>
            <select
              onChange={event => setSourceHint(event.target.value as SourceHint)}
              value={sourceHint}
            >
              {sourceOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button disabled={saving} type="submit">
            <FileText className="h-4 w-4" />
            开始审计
          </button>
        </div>
        <label className="workspace-audit-textarea">
          <span>账单文本</span>
          <textarea
            onChange={event => setRawText(event.target.value)}
            placeholder="粘贴 CSV、Apple 收据、Stripe 邮件或 PayPal 文本..."
            required
            value={rawText}
          />
        </label>
      </form>

      {error && <p className="workspace-inline-error">{error}</p>}

      <div className="workspace-audit-layout">
        <BillingRunList loading={loading} runs={runs} />
        <BillingAuditResults
          createdOpportunityIds={createdOpportunityIds}
          items={items}
          onCreateSavingsOpportunity={handleCreateSavingsOpportunity}
        />
      </div>
    </section>
  );
}

function BillingRunList({
  loading,
  runs,
}: {
  loading: boolean;
  runs: AnalysisRunSummary[];
}) {
  if (loading) {
    return <p className="workspace-muted">正在加载审计历史...</p>;
  }

  if (runs.length === 0) {
    return (
      <div className="workspace-empty">
        <h3>还没有审计记录</h3>
        <p>粘贴第一份账单后，这里会显示运行编号、来源、条目数和月化支出。</p>
      </div>
    );
  }

  return (
    <div className="workspace-run-list">
      <h3>最近审计</h3>
      {runs.map(run => (
        <article key={run.id}>
          <div>
            <strong>{run.id}</strong>
            <span>{sourceLabel(run.source_hint)} · {run.items_count} 项</span>
          </div>
          <p>{formatUsd(run.total_monthly_cost_usd)}</p>
        </article>
      ))}
    </div>
  );
}

function BillingAuditResults({
  createdOpportunityIds,
  items,
  onCreateSavingsOpportunity,
}: {
  createdOpportunityIds: Set<string>;
  items: SubscriptionItem[];
  onCreateSavingsOpportunity: (item: SubscriptionItem) => Promise<void>;
}) {
  if (items.length === 0) {
    return (
      <div className="workspace-empty">
        <h3>等待审计结果</h3>
        <p>提交后会在这里显示识别出的软件、证据、风险类型和月化成本。</p>
      </div>
    );
  }

  return (
    <div className="workspace-audit-results">
      <h3>本次识别结果</h3>
      {items.map(item => (
        <article key={item.id}>
          <div>
            <strong>{item.software_name}</strong>
            <span>{item.merchant_name ?? "未知商户"} · {formatUsd(item.monthly_cost_usd)}/月</span>
          </div>
          <p>{item.evidence}</p>
          <small>{statusLabel(item.status)} · {riskText(item.risk_type)}</small>
          {createdOpportunityIds.has(item.id) ? (
            <span className="workspace-status-success">已创建节省机会</span>
          ) : (
            <button
              className="workspace-audit-opportunity"
              onClick={() => onCreateSavingsOpportunity(item)}
              type="button"
            >
              转为节省机会
            </button>
          )}
        </article>
      ))}
    </div>
  );
}

function riskLabel(riskLevel: string): string {
  const labels: Record<string, string> = {
    critical: "高风险",
    high: "高风险",
    low: "低风险",
    medium: "中风险",
    unknown: "待评估",
  };
  return labels[riskLevel] ?? "待评估";
}

function formatUsd(value: number): string {
  return `$${value.toFixed(2)}`;
}

function sourceLabel(sourceHint: SourceHint): string {
  return sourceOptions.find(([value]) => value === sourceHint)?.[1] ?? "未知来源";
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: "仍在使用",
    apple_unresolved: "需要确认 Apple 收据",
    cancel_in_progress: "取消中",
    cancelled: "已取消",
    flagged: "已标记",
    ignored: "已忽略",
    need_confirm: "待确认",
    verified_saved: "已验证节省",
  };
  return labels[status] ?? "待确认";
}

function procurementStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    approved: "已批准",
    cancelled: "已撤回",
    draft: "草稿",
    in_review: "审批中",
    rejected: "已拒绝",
    withdrawn: "已撤回",
  };
  return labels[status] ?? "待处理";
}

function approvalRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    finance: "财务审批",
    it: "IT 审批",
    security: "安全审批",
    procurement: "采购审批",
  };
  return labels[role] ?? `${role} 审批`;
}

function riskText(riskType: string): string {
  const labels: Record<string, string> = {
    api_usage: "API 用量需复核",
    apple_unresolved: "Apple 收据需人工确认",
    hidden_fee: "可能存在隐藏费用",
    none: "未发现风险",
    possible_duplicate: "可能重复订阅",
    possible_idle: "可能低使用率",
  };
  return labels[riskType] ?? "风险待评估";
}
