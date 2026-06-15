import { useEffect, useState } from "react";
import { ArrowRight, Check, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import {
  listBillingPlans,
  type BillingEntitlement,
  type BillingPlan,
} from "../../app/api";

export function PricingPage() {
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    listBillingPlans()
      .then(response => {
        if (active) setPlans(response.items);
      })
      .catch(caught => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "套餐加载失败");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="pricing-page">
      <section className="pricing-hero">
        <p>透明定价</p>
        <h1>按团队规模和使用场景选择合适方案</h1>
        <span>
          从软件资产与审批起步，随着团队规模和自动化需求平滑升级。
        </span>
      </section>

      <section aria-label="套餐列表" className="pricing-grid">
        {error ? <p className="pricing-error">{error}</p> : null}
        {!error && plans.length === 0 ? (
          <p className="pricing-loading">正在加载套餐...</p>
        ) : null}
        {plans.map(plan => (
          <article
            className={`pricing-plan${plan.key === "pro" ? " is-featured" : ""}`}
            key={plan.key}
          >
            <div className="pricing-plan-heading">
              <div>
                <p>{plan.key === "pro" ? "成长团队" : "基础管理"}</p>
                <h2>{plan.name}</h2>
              </div>
              {plan.key === "pro" ? <span>推荐</span> : null}
            </div>
            <div className="pricing-price">
              <strong>{formatMoney(plan.amount_minor, plan.currency)}</strong>
              <span>/ 月</span>
            </div>
            <p>{plan.description}</p>
            <Link className="pricing-cta" to={`/signup?plan=${plan.key}`}>
              {plan.amount_minor === 0 ? "免费开始" : "开始 14 天试用"}
              <ArrowRight aria-hidden="true" />
            </Link>
            <ul>
              {visibleEntitlements(plan.entitlements).map(entitlement => (
                <li key={entitlement.key}>
                  <Check aria-hidden="true" />
                  {formatEntitlement(entitlement)}
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      <section className="pricing-assurance">
        <ShieldCheck aria-hidden="true" />
        <div>
          <h2>额度和账单始终可追踪</h2>
          <p>
            管理员可随时查看用量、发票和套餐变更影响；降级与取消会提前展示生效时间。
          </p>
        </div>
      </section>
    </main>
  );
}

function visibleEntitlements(items: BillingEntitlement[]) {
  return items.filter(item =>
    [
      "applications",
      "members",
      "api_access",
      "integration_connections",
      "retention_days",
      "support_tier",
    ].includes(item.key),
  );
}

function formatEntitlement(item: BillingEntitlement): string {
  if (item.key === "applications") return `最多 ${item.value} 个应用`;
  if (item.key === "members") return `最多 ${item.value} 位成员`;
  if (item.key === "integration_connections") {
    return `最多 ${item.value} 个集成连接`;
  }
  if (item.key === "retention_days") return `${item.value} 天数据保留`;
  if (item.key === "api_access") {
    return item.value ? "包含 API 访问" : "暂不包含 API 访问";
  }
  if (item.key === "storage_bytes" && typeof item.value === "number") {
    return `${Math.round(item.value / 1_073_741_824)} GB 存储空间`;
  }
  if (item.key === "support_tier") {
    return item.value === "priority" ? "优先支持服务" : "标准支持服务";
  }
  const meteredNames: Record<string, string> = {
    ai_pages: "页 AI 分析",
    export_rows: "行数据导出",
    api_calls: "次 API 调用",
  };
  return `每月 ${item.value} ${meteredNames[item.key] ?? item.key}`;
}

function formatMoney(amountMinor: number, currency: string): string {
  if (amountMinor === 0) return "免费";
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amountMinor / 100);
}
