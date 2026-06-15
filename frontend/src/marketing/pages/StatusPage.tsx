import { FormEvent, useEffect, useState } from "react";
import {
  Bell,
  CheckCircle2,
  CircleAlert,
  RefreshCw,
} from "lucide-react";
import {
  getPublicStatus,
  subscribeToStatus,
  type PublicStatusOverview,
} from "../../app/api";

export function StatusPage() {
  const [overview, setOverview] = useState<PublicStatusOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [subscriptionState, setSubscriptionState] = useState<
    "idle" | "submitting" | "success" | "error"
  >("idle");

  useEffect(() => {
    let active = true;
    getPublicStatus()
      .then(result => {
        if (active) setOverview(result);
      })
      .catch(caught => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "状态数据加载失败");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function submitSubscription(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubscriptionState("submitting");
    try {
      await subscribeToStatus(email);
      setSubscriptionState("success");
      setEmail("");
    } catch {
      setSubscriptionState("error");
    }
  }

  const overallStatus = overview?.overall_status ?? "operational";
  const healthy = overallStatus === "operational";

  return (
    <main className="public-status-page">
      <section className="public-status-hero">
        <div className="public-status-hero-inner">
          <p className="eyebrow">服务可用性</p>
          <h1>系统运行状态</h1>
          <div className={`public-status-overall is-${overallStatus}`}>
            {healthy ? (
              <CheckCircle2 aria-hidden="true" />
            ) : (
              <CircleAlert aria-hidden="true" />
            )}
            <div>
              <strong>{overallStatusLabel(overallStatus)}</strong>
              <span>
                {healthy
                  ? "所有公开服务均正常运行。"
                  : "团队正在处理当前事件，进展会持续更新。"}
              </span>
            </div>
          </div>
          <p className="public-status-updated">
            <RefreshCw aria-hidden="true" />
            {overview
              ? `最近更新：${formatDateTime(overview.generated_at)}`
              : "正在获取最新状态..."}
          </p>
        </div>
      </section>

      <section className="public-status-content">
        {error ? (
          <div className="public-status-error" role="alert">
            {error}
          </div>
        ) : null}

        <div className="public-status-section-heading">
          <div>
            <p className="eyebrow">组件状态</p>
            <h2>平台服务</h2>
          </div>
          <span>{overview?.components.length ?? 0} 个公开组件</span>
        </div>

        <div className="public-status-components">
          {overview?.components.map(component => (
            <article key={component.id}>
              <div>
                <h3>{component.name}</h3>
                <p>{component.description}</p>
              </div>
              <span className={`public-status-badge is-${component.status}`}>
                <i aria-hidden="true" />
                {componentStatusLabel(component.status)}
              </span>
            </article>
          ))}
        </div>

        <div className="public-status-section-heading public-status-incidents-heading">
          <div>
            <p className="eyebrow">事件时间线</p>
            <h2>当前事件</h2>
          </div>
        </div>

        {overview && overview.incidents.length === 0 ? (
          <div className="public-status-empty">
            <CheckCircle2 aria-hidden="true" />
            <div>
              <strong>目前没有进行中的事件</strong>
              <span>所有组件都在预期范围内运行。</span>
            </div>
          </div>
        ) : null}

        <div className="public-status-incidents">
          {overview?.incidents.map(incident => (
            <article key={incident.id}>
              <header>
                <div>
                  <span>{incident.component_name}</span>
                  <h3>{incident.title}</h3>
                  <p>{incident.summary}</p>
                </div>
                <strong>{incidentStatusLabel(incident.status)}</strong>
              </header>
              <ol>
                {incident.updates.map(update => (
                  <li key={update.id}>
                    <span aria-hidden="true" />
                    <div>
                      <div>
                        <strong>{incidentStatusLabel(update.status)}</strong>
                        <time dateTime={update.created_at}>
                          {formatDateTime(update.created_at)}
                        </time>
                      </div>
                      <p>{update.message}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </article>
          ))}
        </div>
      </section>

      <section className="public-status-subscribe">
        <div>
          <Bell aria-hidden="true" />
          <div>
            <h2>订阅状态更新</h2>
            <p>服务事件发布或状态变化时，我们会发送公开更新。</p>
          </div>
        </div>
        <form onSubmit={submitSubscription}>
          <label htmlFor="status-email">工作邮箱</label>
          <div>
            <input
              autoComplete="email"
              id="status-email"
              onChange={event => setEmail(event.target.value)}
              placeholder="name@company.com"
              required
              type="email"
              value={email}
            />
            <button disabled={subscriptionState === "submitting"} type="submit">
              {subscriptionState === "submitting" ? "正在提交..." : "订阅状态更新"}
            </button>
          </div>
          {subscriptionState === "success" ? (
            <p className="public-status-subscription-success">
              确认邮件已发送，请检查收件箱。
            </p>
          ) : null}
          {subscriptionState === "error" ? (
            <p className="public-status-subscription-error">
              暂时无法订阅，请稍后重试。
            </p>
          ) : null}
        </form>
      </section>
    </main>
  );
}

function overallStatusLabel(status: string) {
  if (status === "major_outage") return "部分服务重大中断";
  if (status === "partial_outage") return "部分服务不可用";
  if (status === "degraded") return "部分服务性能下降";
  if (status === "maintenance") return "正在进行计划维护";
  return "所有系统运行正常";
}

function componentStatusLabel(status: string) {
  if (status === "major_outage") return "重大中断";
  if (status === "partial_outage") return "部分中断";
  if (status === "degraded") return "性能下降";
  if (status === "maintenance") return "维护中";
  return "运行正常";
}

function incidentStatusLabel(status: string) {
  if (status === "identified") return "已定位";
  if (status === "monitoring") return "观察中";
  if (status === "resolved") return "已解决";
  return "调查中";
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}
