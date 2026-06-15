import { useEffect, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  CreditCard,
  ExternalLink,
  FileText,
  Gauge,
  RotateCcw,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  cancelBillingSubscription,
  changeBillingPlan,
  createBillingPortalSession,
  getBillingSummary,
  getBillingUsage,
  listBillingInvoices,
  previewBillingChange,
  undoBillingCancellation,
  type BillingChangePreview,
  type BillingInvoice,
  type BillingSummary,
  type BillingUsageMetric,
} from "../../app/api";
import {
  WorkspaceError,
  WorkspaceLoading,
  WorkspaceShell,
  useWorkspaceState,
} from "../WorkspaceDashboardPage";

export type BillingSection = "overview" | "usage" | "invoices";

const billingRoles = new Set(["owner", "admin", "finance", "finance_admin"]);

export function BillingWorkspacePage({
  section = "overview",
}: {
  section?: BillingSection;
}) {
  const workspace = useWorkspaceState();

  if (workspace.status === "loading") return <WorkspaceLoading />;
  if (workspace.status === "error") {
    return <WorkspaceError message={workspace.message} />;
  }

  if (!billingRoles.has(workspace.currentOrganization.role)) {
    return (
      <WorkspaceShell
        activeSection="settings/billing"
        currentOrganization={workspace.currentOrganization}
      >
        <section className="workspace-panel billing-forbidden">
          <CreditCard aria-hidden="true" />
          <h2>无权访问账单设置</h2>
          <p>只有组织所有者、管理员和财务角色可以查看套餐、用量与发票。</p>
          <Link to={`/app/${workspace.currentOrganization.slug}/dashboard`}>
            返回总览
          </Link>
        </section>
      </WorkspaceShell>
    );
  }

  return (
    <WorkspaceShell
      activeSection="settings/billing"
      currentOrganization={workspace.currentOrganization}
    >
      <BillingExperience
        organizationId={workspace.currentOrganization.id}
        organizationSlug={workspace.currentOrganization.slug}
        section={section}
      />
    </WorkspaceShell>
  );
}

function BillingExperience({
  organizationId,
  organizationSlug,
  section,
}: {
  organizationId: string;
  organizationSlug: string;
  section: BillingSection;
}) {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getBillingSummary(organizationId)
      .then(value => {
        if (active) {
          setSummary(value);
          setError(null);
        }
      })
      .catch(caught => {
        if (active) setError(messageFrom(caught, "账单信息加载失败"));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  return (
    <section className="workspace-panel billing-page">
      <header className="billing-heading">
        <div>
          <span>组织设置</span>
          <h2>账单与套餐</h2>
          <p>查看订阅状态、产品用量和付款记录，并在变更前确认影响。</p>
        </div>
        {summary?.subscription.status === "active" ? (
          <div className="billing-sync">
            <CheckCircle2 aria-hidden="true" />
            <span>计费同步正常</span>
          </div>
        ) : null}
      </header>

      <BillingTabs active={section} slug={organizationSlug} />
      {error ? <p className="billing-feedback is-error">{error}</p> : null}
      {loading ? <p className="billing-loading">正在加载账单信息...</p> : null}
      {!loading && summary && section === "overview" ? (
        <BillingOverview
          onSummaryChange={setSummary}
          organizationId={organizationId}
          summary={summary}
        />
      ) : null}
      {!loading && summary && section === "usage" ? (
        <BillingUsage organizationId={organizationId} />
      ) : null}
      {!loading && summary && section === "invoices" ? (
        <BillingInvoices organizationId={organizationId} />
      ) : null}
    </section>
  );
}

function BillingTabs({
  active,
  slug,
}: {
  active: BillingSection;
  slug: string;
}) {
  const base = `/app/${slug}/settings/billing`;
  const items: Array<[BillingSection, string, string]> = [
    ["overview", "套餐与付款", base],
    ["usage", "产品用量", `${base}/usage`],
    ["invoices", "发票", `${base}/invoices`],
  ];
  return (
    <nav aria-label="账单页面" className="billing-tabs">
      {items.map(([key, label, path]) => (
        <Link aria-current={active === key ? "page" : undefined} key={key} to={path}>
          {label}
        </Link>
      ))}
    </nav>
  );
}

function BillingOverview({
  organizationId,
  summary,
  onSummaryChange,
}: {
  organizationId: string;
  summary: BillingSummary;
  onSummaryChange: (summary: BillingSummary) => void;
}) {
  const [preview, setPreview] = useState<BillingChangePreview | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function previewPlan(targetPlan: string) {
    setSaving(true);
    setError(null);
    try {
      setPreview(await previewBillingChange(organizationId, targetPlan));
    } catch (caught) {
      setError(messageFrom(caught, "无法预览套餐变更"));
    } finally {
      setSaving(false);
    }
  }

  async function confirmPlanChange() {
    if (!preview) return;
    setSaving(true);
    setError(null);
    try {
      onSummaryChange(
        await changeBillingPlan(organizationId, preview.target_plan),
      );
      setPreview(null);
    } catch (caught) {
      setError(messageFrom(caught, "套餐变更失败"));
    } finally {
      setSaving(false);
    }
  }

  async function updateCancellation(undo: boolean) {
    setSaving(true);
    setError(null);
    try {
      const next = undo
        ? await undoBillingCancellation(organizationId)
        : await cancelBillingSubscription(organizationId);
      onSummaryChange(next);
    } catch (caught) {
      setError(messageFrom(caught, "订阅状态更新失败"));
    } finally {
      setSaving(false);
    }
  }

  async function openPortal() {
    setSaving(true);
    setError(null);
    try {
      const response = await createBillingPortalSession(
        organizationId,
        window.location.href,
      );
      window.location.assign(response.url);
    } catch (caught) {
      setError(messageFrom(caught, "付款门户打开失败"));
      setSaving(false);
    }
  }

  return (
    <div className="billing-overview">
      {summary.payment_issue ? (
        <Notice icon={<AlertTriangle />} tone="warning">
          <strong>付款需要处理</strong>
          <span>请更新付款方式，避免组织进入只读状态。</span>
        </Notice>
      ) : null}
      {summary.pending_plan ? (
        <Notice icon={<RotateCcw />} tone="info">
          <strong>
            将于 {formatDate(summary.subscription.pending_change_at)} 切换到{" "}
            {summary.pending_plan.name}
          </strong>
          <span>现有资源不会删除，超出新套餐额度的操作将受到限制。</span>
        </Notice>
      ) : null}
      {summary.subscription.cancel_at_period_end ? (
        <Notice icon={<AlertTriangle />} tone="warning">
          <strong>订阅将在当前周期结束时取消</strong>
          <button disabled={saving} onClick={() => updateCancellation(true)} type="button">
            撤销取消
          </button>
        </Notice>
      ) : null}

      <div className="billing-plan-layout">
        <article className="billing-current-plan">
          <div className="billing-plan-title">
            <div>
              <span>{subscriptionLabel(summary.subscription.status)}</span>
              <h3>{summary.plan.name}</h3>
            </div>
            <strong>
              {formatMoney(summary.plan.amount_minor, summary.plan.currency)}
              <small>/月</small>
            </strong>
          </div>
          <p>{summary.plan.description}</p>
          <dl>
            <div>
              <dt>订阅状态</dt>
              <dd>{statusLabel(summary.subscription.status)}</dd>
            </div>
            <div>
              <dt>下次续费 / 生效日期</dt>
              <dd>
                {formatDate(
                  summary.subscription.current_period_end ??
                    summary.subscription.trial_ends_at,
                )}
              </dd>
            </div>
            <div>
              <dt>付款周期</dt>
              <dd>按月结算</dd>
            </div>
          </dl>
          <div className="billing-actions">
            {summary.plan.key === "starter" ? (
              <button
                className="is-primary"
                disabled={saving}
                onClick={() => previewPlan("pro")}
                type="button"
              >
                <ArrowUpRight aria-hidden="true" />
                升级到 Pro
              </button>
            ) : (
              <button
                disabled={saving}
                onClick={() => previewPlan("starter")}
                type="button"
              >
                切换到 Starter
              </button>
            )}
            <button disabled={saving} onClick={openPortal} type="button">
              <CreditCard aria-hidden="true" />
              管理付款方式
            </button>
            {!summary.subscription.cancel_at_period_end ? (
              <button
                className="is-danger"
                disabled={saving}
                onClick={() => updateCancellation(false)}
                type="button"
              >
                取消订阅
              </button>
            ) : null}
          </div>
        </article>

        <aside className="billing-entitlements">
          <h3>当前套餐包含</h3>
          <ul>
            {summary.plan.entitlements.slice(0, 8).map(item => (
              <li key={item.key}>
                <CheckCircle2 aria-hidden="true" />
                <span>{entitlementText(item.key, item.value)}</span>
              </li>
            ))}
          </ul>
        </aside>
      </div>

      {error ? <p className="billing-feedback is-error">{error}</p> : null}
      {preview ? (
        <section aria-label="套餐变更预览" className="billing-preview">
          <div>
            <span>
              {preview.direction === "upgrade" ? "立即升级" : "周期结束后降级"}
            </span>
            <h3>
              {preview.direction === "upgrade" ? "升级到 Pro" : "切换到 Starter"}
            </h3>
            <p>
              生效时间：{formatDate(preview.effective_at)}
              {preview.lost_features.length > 0
                ? `；将失去 ${preview.lost_features.join("、")}`
                : "；现有数据会完整保留"}
            </p>
          </div>
          <div className="billing-preview-price">
            <span>本次预计支付</span>
            <strong>{formatMoney(preview.proration_minor, "USD")}</strong>
          </div>
          {Object.keys(preview.over_limit).length > 0 ? (
            <p className="billing-preview-warning">
              降级后存在超额资源：{formatOverLimit(preview.over_limit)}
            </p>
          ) : null}
          <div className="billing-preview-actions">
            <button disabled={saving} onClick={() => setPreview(null)} type="button">
              返回
            </button>
            <button
              className="is-primary"
              disabled={saving}
              onClick={confirmPlanChange}
              type="button"
            >
              {preview.direction === "upgrade" ? "确认升级" : "确认降级"}
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function BillingUsage({ organizationId }: { organizationId: string }) {
  const [items, setItems] = useState<BillingUsageMetric[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getBillingUsage(organizationId)
      .then(response => {
        if (active) setItems(response.items);
      })
      .catch(caught => {
        if (active) setError(messageFrom(caught, "产品用量加载失败"));
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  if (error) return <p className="billing-feedback is-error">{error}</p>;
  if (items.length === 0) return <p className="billing-loading">正在加载产品用量...</p>;

  return (
    <div className="billing-usage">
      <header>
        <Gauge aria-hidden="true" />
        <div>
          <h3>本月产品用量</h3>
          <p>达到 80% 时会发送提醒；硬额度达到 100% 后将阻止新增操作。</p>
        </div>
      </header>
      <div className="billing-usage-list">
        {items.map(item => {
          const percent =
            item.limit > 0 ? Math.min((item.current_value / item.limit) * 100, 100) : 0;
          return (
            <article key={item.metric}>
              <div>
                <strong>{metricLabel(item.metric)}</strong>
                <span>
                  {formatUsageValue(item.metric, item.current_value)} /{" "}
                  {formatUsageValue(item.metric, item.limit)}
                </span>
              </div>
              <div
                aria-label={`${metricLabel(item.metric)}已使用 ${Math.round(percent)}%`}
                className={`billing-meter is-${item.status}`}
                role="progressbar"
              >
                <span style={{ width: `${percent}%` }} />
              </div>
              <small>
                {item.hard_limit ? "硬额度" : "可超额计费"} · {usageStatusLabel(item.status)}
              </small>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function BillingInvoices({ organizationId }: { organizationId: string }) {
  const [items, setItems] = useState<BillingInvoice[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    listBillingInvoices(organizationId)
      .then(response => {
        if (active) setItems(response.items);
      })
      .catch(caught => {
        if (active) setError(messageFrom(caught, "发票加载失败"));
      })
      .finally(() => {
        if (active) setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  if (error) return <p className="billing-feedback is-error">{error}</p>;
  if (!loaded) return <p className="billing-loading">正在加载发票...</p>;

  return (
    <div className="billing-invoices">
      <header>
        <FileText aria-hidden="true" />
        <div>
          <h3>发票与付款记录</h3>
          <p>查看应付、已付金额和托管发票页面。</p>
        </div>
      </header>
      {items.length === 0 ? (
        <div className="billing-empty">
          <h3>暂无发票</h3>
          <p>产生首笔付费账单后，发票会出现在这里。</p>
        </div>
      ) : (
        <div className="billing-table-wrap">
          <table>
            <thead>
              <tr>
                <th>发票</th>
                <th>状态</th>
                <th>金额</th>
                <th>到期 / 付款日期</th>
                <th aria-label="操作" />
              </tr>
            </thead>
            <tbody>
              {items.map(invoice => (
                <tr key={invoice.external_invoice_id}>
                  <td>{invoice.external_invoice_id}</td>
                  <td>{invoiceStatusLabel(invoice.status)}</td>
                  <td>{formatMoney(invoice.amount_due_minor, invoice.currency)}</td>
                  <td>{formatDate(invoice.paid_at ?? invoice.due_at)}</td>
                  <td>
                    {invoice.hosted_invoice_url ? (
                      <a
                        href={invoice.hosted_invoice_url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        查看
                        <ExternalLink aria-hidden="true" />
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Notice({
  children,
  icon,
  tone,
}: {
  children: ReactNode;
  icon: ReactNode;
  tone: "warning" | "info";
}) {
  return (
    <div className={`billing-notice is-${tone}`}>
      {icon}
      <div>{children}</div>
    </div>
  );
}

function messageFrom(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function subscriptionLabel(status: string) {
  return status === "trialing" ? "14 天免费试用" : "当前套餐";
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    active: "生效中",
    trialing: "试用中",
    trial_expired: "试用已结束",
    past_due: "付款逾期",
    grace_period: "付款宽限期",
    suspended: "已暂停",
    cancel_at_period_end: "将在周期末取消",
    cancelled: "已取消",
    enterprise_contract: "企业合同",
  };
  return labels[status] ?? status;
}

function metricLabel(metric: string) {
  const labels: Record<string, string> = {
    members: "团队成员",
    applications: "应用数量",
    storage_bytes: "文件存储",
    ai_pages: "AI 分析页数",
    integration_connections: "集成连接",
    export_rows: "导出行数",
    api_calls: "API 调用",
  };
  return labels[metric] ?? metric;
}

function usageStatusLabel(status: string) {
  const labels: Record<string, string> = {
    ok: "用量正常",
    warning: "接近额度",
    limit_reached: "已达额度",
    overage: "已产生超额",
  };
  return labels[status] ?? status;
}

function invoiceStatusLabel(status: string) {
  const labels: Record<string, string> = {
    draft: "草稿",
    open: "待付款",
    paid: "已付款",
    void: "已作废",
    uncollectible: "无法收款",
  };
  return labels[status] ?? status;
}

function entitlementText(key: string, value: boolean | number | string) {
  const labels: Record<string, string> = {
    applications: `${value} 个应用`,
    members: `${value} 位成员`,
    api_access: value ? "API 访问" : "不含 API 访问",
    ai_pages: `每月 ${value} 页 AI 分析`,
    integration_connections: `${value} 个集成连接`,
    export_rows: `每月导出 ${value} 行`,
    api_calls: `每月 ${value} 次 API 调用`,
    retention_days: `${value} 天数据保留`,
    support_tier: value === "priority" ? "优先支持" : "标准支持",
  };
  if (key === "storage_bytes" && typeof value === "number") {
    return `${Math.round(value / 1_073_741_824)} GB 文件存储`;
  }
  return labels[key] ?? `${key}: ${value}`;
}

function formatMoney(amountMinor: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amountMinor / 100);
}

function formatDate(value: string | null) {
  if (!value) return "待确认";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(date);
}

function formatUsageValue(metric: string, value: number) {
  if (metric === "storage_bytes") {
    return `${(value / 1_073_741_824).toFixed(value === 0 ? 0 : 1)} GB`;
  }
  return new Intl.NumberFormat("zh-CN").format(value);
}

function formatOverLimit(values: Record<string, number>) {
  return Object.entries(values)
    .map(([key, value]) => `${metricLabel(key)}超出 ${value}`)
    .join("、");
}
