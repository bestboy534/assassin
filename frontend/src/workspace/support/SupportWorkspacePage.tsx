import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Clock3,
  Headphones,
  KeyRound,
  MessageSquare,
  Plus,
  Send,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  createCustomerSupportMessage,
  createSupportGrant,
  createSupportTicket,
  getSupportTicket,
  listSupportAgents,
  listSupportGrants,
  listSupportMessages,
  listSupportTickets,
  revokeSupportGrant,
  type SupportAgentItem,
  type SupportGrantItem,
  type SupportMessageItem,
  type SupportTicketItem,
} from "../../app/api";
import {
  WorkspaceError,
  WorkspaceLoading,
  WorkspaceShell,
  useWorkspaceState,
} from "../WorkspaceDashboardPage";
import "./support.css";

type SupportMode = "list" | "new" | "detail" | "access";

export function SupportWorkspacePage({ mode }: { mode: SupportMode }) {
  const workspace = useWorkspaceState();
  if (workspace.status === "loading") return <WorkspaceLoading />;
  if (workspace.status === "error") {
    return <WorkspaceError message={workspace.message} />;
  }

  const activeSection = mode === "access" ? "settings/support-access" : "support";
  return (
    <WorkspaceShell
      activeSection={activeSection}
      currentOrganization={workspace.currentOrganization}
    >
      <div className="support-page">
        {mode === "list" ? (
          <TicketList
            organizationId={workspace.currentOrganization.id}
            organizationSlug={workspace.currentOrganization.slug}
          />
        ) : null}
        {mode === "new" ? (
          <NewTicket
            organizationId={workspace.currentOrganization.id}
            organizationSlug={workspace.currentOrganization.slug}
          />
        ) : null}
        {mode === "detail" ? (
          <TicketDetail organizationSlug={workspace.currentOrganization.slug} />
        ) : null}
        {mode === "access" ? (
          <SupportAccess
            canManage={["owner", "admin"].includes(workspace.currentOrganization.role)}
            organizationId={workspace.currentOrganization.id}
          />
        ) : null}
      </div>
    </WorkspaceShell>
  );
}

function SupportHeading({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="support-heading">
      <div className="support-heading-icon">
        <Headphones />
      </div>
      <div>
        <span>客户支持</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}

function TicketList({
  organizationId,
  organizationSlug,
}: {
  organizationId: string;
  organizationSlug: string;
}) {
  const [tickets, setTickets] = useState<SupportTicketItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listSupportTickets(organizationId)
      .then(response => setTickets(response.items))
      .catch(caught => setError(messageFrom(caught)));
  }, [organizationId]);

  return (
    <>
      <SupportHeading
        title="支持工单"
        description="集中查看问题进度、支持回复和服务级别目标。"
        action={
          <Link className="support-primary-link" to={`/app/${organizationSlug}/support/new`}>
            <Plus />
            新建工单
          </Link>
        }
      />
      {error ? <p className="support-feedback is-error">{error}</p> : null}
      <section className="support-ticket-list">
        {tickets.length === 0 && !error ? (
          <div className="support-empty">
            <MessageSquare />
            <strong>暂时没有支持工单</strong>
            <span>遇到问题时，可以创建工单并持续补充上下文。</span>
          </div>
        ) : null}
        {tickets.map(item => (
          <Link
            className="support-ticket-row"
            key={item.id}
            to={`/app/${organizationSlug}/support/${item.id}`}
          >
            <div>
              <span className={`support-status is-${item.status}`}>
                {ticketStatus(item.status)}
              </span>
              <h3>{item.subject}</h3>
              <p>{item.description}</p>
            </div>
            <dl>
              <div>
                <dt>优先级</dt>
                <dd>{priorityLabel(item.priority)}</dd>
              </div>
              <div>
                <dt>响应目标</dt>
                <dd>{formatDate(item.first_response_due_at)}</dd>
              </div>
            </dl>
          </Link>
        ))}
      </section>
    </>
  );
}

function NewTicket({
  organizationId,
  organizationSlug,
}: {
  organizationId: string;
  organizationSlug: string;
}) {
  const navigate = useNavigate();
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("integration");
  const [priority, setPriority] = useState("normal");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const created = await createSupportTicket({
        organization_id: organizationId,
        subject,
        description,
        category,
        priority,
      });
      navigate(`/app/${organizationSlug}/support/${created.id}`);
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <SupportHeading
        title="新建支持工单"
        description="说明影响范围、出现时间和已尝试的处理方式，便于支持团队快速定位。"
      />
      <form className="support-form" onSubmit={submit}>
        <label>
          <span>问题标题</span>
          <input
            minLength={3}
            onChange={event => setSubject(event.target.value)}
            required
            value={subject}
          />
        </label>
        <label className="is-wide">
          <span>问题描述</span>
          <textarea
            minLength={3}
            onChange={event => setDescription(event.target.value)}
            required
            value={description}
          />
        </label>
        <div className="support-form-grid">
          <label>
            <span>问题类别</span>
            <select onChange={event => setCategory(event.target.value)} value={category}>
              <option value="integration">集成与同步</option>
              <option value="billing">账单与套餐</option>
              <option value="security">安全与权限</option>
              <option value="product">产品使用</option>
            </select>
          </label>
          <label>
            <span>优先级</span>
            <select onChange={event => setPriority(event.target.value)} value={priority}>
              <option value="low">低</option>
              <option value="normal">普通</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </label>
        </div>
        {error ? <p className="support-feedback is-error">{error}</p> : null}
        <div className="support-form-actions">
          <Link to={`/app/${organizationSlug}/support`}>取消</Link>
          <button disabled={saving} type="submit">
            <Send />
            {saving ? "正在提交" : "提交工单"}
          </button>
        </div>
      </form>
    </>
  );
}

function TicketDetail({ organizationSlug }: { organizationSlug: string }) {
  const { ticketId = "" } = useParams();
  const [ticket, setTicket] = useState<SupportTicketItem | null>(null);
  const [messages, setMessages] = useState<SupportMessageItem[]>([]);
  const [body, setBody] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getSupportTicket(ticketId), listSupportMessages(ticketId)])
      .then(([nextTicket, nextMessages]) => {
        setTicket(nextTicket);
        setMessages(nextMessages.items);
      })
      .catch(caught => setError(messageFrom(caught)));
  }, [ticketId]);

  async function send(event: FormEvent) {
    event.preventDefault();
    try {
      const created = await createCustomerSupportMessage(ticketId, body);
      setMessages(items => [...items, created]);
      setBody("");
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }

  if (!ticket && !error) return <p className="support-loading">正在加载工单...</p>;
  if (!ticket) return <p className="support-feedback is-error">{error}</p>;

  return (
    <>
      <SupportHeading
        title={ticket.subject}
        description={ticket.description}
        action={
          <Link className="support-secondary-link" to={`/app/${organizationSlug}/support`}>
            返回工单列表
          </Link>
        }
      />
      <section className="support-ticket-meta">
        <div>
          <span>当前状态</span>
          <strong>{ticketStatus(ticket.status)}</strong>
        </div>
        <div>
          <span>优先级</span>
          <strong>{priorityLabel(ticket.priority)}</strong>
        </div>
        <div>
          <span>首次响应目标</span>
          <strong>{formatDate(ticket.first_response_due_at)}</strong>
        </div>
        <div>
          <span>解决目标</span>
          <strong>{formatDate(ticket.resolution_due_at)}</strong>
        </div>
      </section>
      <section className="support-conversation">
        <h3>沟通记录</h3>
        {messages.map(message => (
          <article className={`support-message is-${message.author_type}`} key={message.id}>
            <div>
              <strong>{message.author_type === "support" ? "支持团队" : "你的团队"}</strong>
              <time>{formatDate(message.created_at)}</time>
            </div>
            <p>{message.body}</p>
          </article>
        ))}
        <form onSubmit={send}>
          <label>
            <span>补充消息</span>
            <textarea
              onChange={event => setBody(event.target.value)}
              required
              value={body}
            />
          </label>
          <button type="submit">
            <Send />
            发送消息
          </button>
        </form>
      </section>
    </>
  );
}

function SupportAccess({
  canManage,
  organizationId,
}: {
  canManage: boolean;
  organizationId: string;
}) {
  const [agents, setAgents] = useState<SupportAgentItem[]>([]);
  const [grants, setGrants] = useState<SupportGrantItem[]>([]);
  const [agentId, setAgentId] = useState("");
  const [reason, setReason] = useState("");
  const [durationHours, setDurationHours] = useState("2");
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([listSupportAgents(), listSupportGrants(organizationId)])
      .then(([agentResponse, grantResponse]) => {
        setAgents(agentResponse.items);
        setGrants(grantResponse.items);
      })
      .catch(caught => setError(messageFrom(caught)));
  }, [organizationId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    try {
      const expiresAt = new Date(
        Date.now() + Number(durationHours) * 60 * 60 * 1000,
      ).toISOString();
      const created = await createSupportGrant(organizationId, {
        support_user_id: agentId,
        scopes: ["configuration.read", "sync_diagnostics.read", "job_logs.read"],
        reason,
        expires_at: expiresAt,
      });
      setGrants(items => [created, ...items]);
      setReason("");
      setSuccess("授权已创建");
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }

  async function revoke(grantId: string) {
    try {
      const updated = await revokeSupportGrant(organizationId, grantId);
      setGrants(items => items.map(item => (item.id === updated.id ? updated : item)));
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }

  return (
    <>
      <SupportHeading
        title="支持访问授权"
        description="支持人员默认无法读取业务数据。仅在明确范围、原因和期限内开放诊断访问。"
      />
      {!canManage ? (
        <p className="support-feedback is-error">仅组织所有者和管理员可以管理授权。</p>
      ) : (
        <form className="support-form support-access-form" onSubmit={submit}>
          <div className="support-form-grid">
            <label>
              <span>支持专员</span>
              <select
                aria-label="支持专员"
                onChange={event => setAgentId(event.target.value)}
                required
                value={agentId}
              >
                <option value="">请选择</option>
                {agents.map(agent => (
                  <option key={agent.id} value={agent.id}>
                    {agent.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>授权时长</span>
              <select
                onChange={event => setDurationHours(event.target.value)}
                value={durationHours}
              >
                <option value="1">1 小时</option>
                <option value="2">2 小时</option>
                <option value="8">8 小时</option>
                <option value="24">24 小时</option>
                <option value="168">7 天</option>
              </select>
            </label>
          </div>
          <label>
            <span>授权原因</span>
            <textarea
              aria-label="授权原因"
              minLength={3}
              onChange={event => setReason(event.target.value)}
              required
              value={reason}
            />
          </label>
          <div className="support-scope-note">
            <ShieldCheck />
            <div>
              <strong>本次范围</strong>
              <span>配置只读、同步诊断只读、任务日志只读；不包含业务记录。</span>
            </div>
          </div>
          <button type="submit">
            <KeyRound />
            创建限时授权
          </button>
          {success ? <p className="support-feedback is-success">{success}</p> : null}
          {error ? <p className="support-feedback is-error">{error}</p> : null}
        </form>
      )}
      <section className="support-grants">
        <h3>授权记录</h3>
        {grants.length === 0 ? <p>暂无授权记录。</p> : null}
        {grants.map(grant => {
          const expired = new Date(grant.expires_at).getTime() <= Date.now();
          return (
            <article key={grant.id}>
              <div>
                {grant.revoked_at ? <XCircle /> : <Clock3 />}
                <div>
                  <strong>{grant.reason}</strong>
                  <span>
                    {grant.revoked_at
                      ? "已撤销"
                      : expired
                        ? "已过期"
                        : `有效至 ${formatDate(grant.expires_at)}`}
                  </span>
                </div>
              </div>
              {!grant.revoked_at && !expired ? (
                <button className="is-danger" onClick={() => revoke(grant.id)} type="button">
                  撤销授权
                </button>
              ) : null}
            </article>
          );
        })}
      </section>
    </>
  );
}

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "操作失败，请稍后重试。";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function ticketStatus(status: string) {
  return (
    {
      new: "新工单",
      open: "处理中",
      waiting_customer: "等待客户",
      waiting_support: "等待支持",
      resolved: "已解决",
      closed: "已关闭",
    }[status] ?? status
  );
}

function priorityLabel(priority: string) {
  return ({ low: "低", normal: "普通", high: "高", urgent: "紧急" }[priority] ?? priority);
}
