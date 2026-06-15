import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  BookOpen,
  Building2,
  Headphones,
  LogOut,
  Radio,
  Send,
  ServerCog,
  ShieldAlert,
  UserRound,
} from "lucide-react";
import {
  createAdminKnowledge,
  createAdminKnowledgeDraft,
  createAdminStatusComponent,
  createAdminStatusIncident,
  createOperationalMessage,
  getCurrentSession,
  listAdminKnowledge,
  listAdminOrganizations,
  listAdminStatusComponents,
  listAdminUsers,
  listOperationalGrants,
  listOperationalMessages,
  listOperationalTickets,
  logoutAccount,
  readSupportDiagnostics,
  rollbackAdminKnowledge,
  runHighRiskAdminAction,
  submitAdminKnowledgeReview,
  approveAdminKnowledgeVersion,
  publishAdminKnowledgeVersion,
  type AdminOrganizationItem,
  type AdminStatusComponent,
  type AdminUserItem,
  type KnowledgeBundle,
  type SupportDiagnosticItem,
  type SupportGrantItem,
  type SupportMessageItem,
  type SupportTicketItem,
} from "../app/api";
import "./admin.css";

type AdminSection = "operations" | "support" | "status" | "catalog";

export function AdminConsolePage({ section }: { section: AdminSection }) {
  const [role, setRole] = useState<string | null | undefined>(undefined);
  const [error, setError] = useState("");

  useEffect(() => {
    getCurrentSession()
      .then(session => setRole(session.user.platform_role ?? null))
      .catch(caught => setError(messageFrom(caught)));
  }, []);

  if (error) {
    return (
      <main className="admin-auth-state">
        <ShieldAlert />
        <h1>无法进入平台后台</h1>
        <p>{error}</p>
        <Link to="/login">返回登录</Link>
      </main>
    );
  }
  if (role === undefined) {
    return <main className="admin-auth-state"><p>正在验证平台权限...</p></main>;
  }
  if (!role || (role === "support_agent" && section !== "support")) {
    return (
      <main className="admin-auth-state">
        <ShieldAlert />
        <h1>没有平台权限</h1>
        <p>此区域与客户工作区隔离，仅限获授权的平台人员。</p>
        <Link to="/">返回首页</Link>
      </main>
    );
  }

  return (
    <AdminLayout role={role} section={section}>
      {section === "operations" ? <OperationsSection /> : null}
      {section === "support" ? <SupportOperationsSection /> : null}
      {section === "status" ? <StatusOperationsSection /> : null}
      {section === "catalog" ? <CatalogOperationsSection /> : null}
    </AdminLayout>
  );
}

function AdminLayout({
  role,
  section,
  children,
}: {
  role: string;
  section: AdminSection;
  children: ReactNode;
}) {
  const links: Array<[AdminSection, string, ReactNode]> = [
    ["operations", "平台运营", <ServerCog key="operations" />],
    ["support", "支持运营", <Headphones key="support" />],
    ["status", "状态管理", <Radio key="status" />],
    ["catalog", "全局目录", <BookOpen key="catalog" />],
  ];
  const visible = role === "support_agent" ? links.filter(([key]) => key === "support") : links;
  const environment = import.meta.env.MODE === "production" ? "生产环境" : "开发环境";

  return (
    <main className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-product">
          <span />
          <div>
            <strong>平台控制台</strong>
            <small>{role === "platform_admin" ? "平台管理员" : "支持专员"}</small>
          </div>
        </div>
        <nav>
          {visible.map(([key, label, icon]) => (
            <Link
              aria-current={section === key ? "page" : undefined}
              key={key}
              to={key === "operations" ? "/admin" : `/admin/${key}`}
            >
              {icon}
              {label}
            </Link>
          ))}
        </nav>
        <button
          className="admin-logout"
          onClick={async () => {
            await logoutAccount();
            window.location.assign("/login");
          }}
          type="button"
        >
          <LogOut />
          退出
        </button>
      </aside>
      <section className="admin-main">
        <header className="admin-topbar">
          <div>
            <span>独立平台权限域</span>
            <strong>{environment}</strong>
          </div>
          {environment === "生产环境" ? (
            <p><AlertTriangle />所有高风险操作都会写入不可变审计。</p>
          ) : null}
        </header>
        <div className="admin-content">{children}</div>
      </section>
    </main>
  );
}

function AdminHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <header className="admin-heading">
      <span>{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}

function OperationsSection() {
  const [organizations, setOrganizations] = useState<AdminOrganizationItem[]>([]);
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [action, setAction] = useState<{ type: "organization" | "user"; id: string } | null>(
    null,
  );
  const [reason, setReason] = useState("");
  const [password, setPassword] = useState("");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    Promise.all([listAdminOrganizations(), listAdminUsers()]).then(
      ([organizationResponse, userResponse]) => {
        setOrganizations(organizationResponse.items);
        setUsers(userResponse.items);
      },
    );
  }, []);

  async function confirmAction(event: FormEvent) {
    event.preventDefault();
    if (!action) return;
    const path =
      action.type === "organization"
        ? `/api/v1/admin/organizations/${action.id}/suspend`
        : `/api/v1/admin/users/${action.id}/ban`;
    try {
      await runHighRiskAdminAction(path, reason, password);
      setFeedback(action.type === "organization" ? "组织已暂停" : "用户已封禁");
      setAction(null);
      setReason("");
      setPassword("");
    } catch (caught) {
      setFeedback(messageFrom(caught));
    }
  }

  return (
    <>
      <AdminHeading
        eyebrow="平台运营"
        title="组织与用户控制"
        description="跨租户视图只提供显式操作。暂停、封禁等动作必须说明原因并重新认证。"
      />
      <div className="admin-split">
        <section className="admin-panel">
          <h2><Building2 />组织</h2>
          {organizations.map(item => (
            <article className="admin-row" key={item.id}>
              <div>
                <strong>{item.name}</strong>
                <span>{item.plan_key ?? "未配置套餐"} · {item.member_count} 名成员</span>
              </div>
              <button
                className="is-danger"
                onClick={() => setAction({ type: "organization", id: item.id })}
                type="button"
              >
                暂停
              </button>
            </article>
          ))}
        </section>
        <section className="admin-panel">
          <h2><UserRound />用户</h2>
          {users.map(item => (
            <article className="admin-row" key={item.id}>
              <div>
                <strong>{item.display_name}</strong>
                <span>{item.email} · {item.platform_role ?? "客户用户"}</span>
              </div>
              <button
                className="is-danger"
                onClick={() => setAction({ type: "user", id: item.id })}
                type="button"
              >
                封禁
              </button>
            </article>
          ))}
        </section>
      </div>
      {action ? (
        <form className="admin-danger-confirm" onSubmit={confirmAction}>
          <AlertTriangle />
          <div>
            <h2>确认高风险操作</h2>
            <p>此操作会立即影响客户访问，并记录操作者、原因和前后状态。</p>
          </div>
          <label>
            <span>操作原因</span>
            <input minLength={5} onChange={event => setReason(event.target.value)} required />
          </label>
          <label>
            <span>当前密码</span>
            <input
              minLength={8}
              onChange={event => setPassword(event.target.value)}
              required
              type="password"
            />
          </label>
          <div>
            <button onClick={() => setAction(null)} type="button">取消</button>
            <button className="is-danger" type="submit">确认执行</button>
          </div>
        </form>
      ) : null}
      {feedback ? <p className="admin-feedback">{feedback}</p> : null}
    </>
  );
}

function SupportOperationsSection() {
  const [tickets, setTickets] = useState<SupportTicketItem[]>([]);
  const [selected, setSelected] = useState<SupportTicketItem | null>(null);
  const [messages, setMessages] = useState<SupportMessageItem[]>([]);
  const [grants, setGrants] = useState<SupportGrantItem[]>([]);
  const [reply, setReply] = useState("");
  const [diagnostics, setDiagnostics] = useState<SupportDiagnosticItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([listOperationalTickets(), listOperationalGrants()])
      .then(([ticketResponse, grantResponse]) => {
        setTickets(ticketResponse.items);
        setGrants(grantResponse.items);
      })
      .catch(caught => setError(messageFrom(caught)));
  }, []);

  async function openTicket(ticket: SupportTicketItem) {
    setSelected(ticket);
    try {
      const response = await listOperationalMessages(ticket.id);
      setMessages(response.items);
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }

  async function sendReply(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    try {
      const created = await createOperationalMessage(selected.id, reply);
      setMessages(items => [...items, created]);
      setReply("");
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }

  async function inspectGrant(grant: SupportGrantItem) {
    try {
      const response = await readSupportDiagnostics(
        grant.id,
        "从支持控制台排查客户同步错误",
      );
      setDiagnostics(response.items);
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }

  return (
    <>
      <AdminHeading
        eyebrow="支持运营"
        title="支持运营"
        description="处理客户工单；只有客户主动授权后，才可读取限定范围的同步诊断。"
      />
      {error ? <p className="admin-feedback is-error">{error}</p> : null}
      <div className="admin-support-grid">
        <section className="admin-panel">
          <h2>待处理工单</h2>
          {tickets.map(ticket => (
            <article className="admin-row" key={ticket.id}>
              <div>
                <strong>{ticket.subject}</strong>
                <span>{ticket.status} · {ticket.priority}</span>
              </div>
              <button onClick={() => openTicket(ticket)} type="button">处理工单</button>
            </article>
          ))}
        </section>
        <section className="admin-panel admin-conversation">
          <h2>{selected?.subject ?? "选择一张工单"}</h2>
          {messages.map(message => (
            <article className={`admin-message is-${message.author_type}`} key={message.id}>
              <strong>{message.author_type === "support" ? "支持团队" : "客户"}</strong>
              <p>{message.body}</p>
            </article>
          ))}
          {selected ? (
            <form onSubmit={sendReply}>
              <label>
                <span>支持回复</span>
                <textarea
                  aria-label="支持回复"
                  onChange={event => setReply(event.target.value)}
                  required
                  value={reply}
                />
              </label>
              <button type="submit"><Send />回复客户</button>
            </form>
          ) : null}
        </section>
      </div>
      <section className="admin-panel">
        <h2>客户诊断授权</h2>
        {grants.length === 0 ? <p>当前没有分配给你的有效授权。</p> : null}
        {grants.map(grant => (
          <article className="admin-row" key={grant.id}>
            <div>
              <strong>{grant.reason}</strong>
              <span>
                {grant.revoked_at
                  ? "授权已撤销"
                  : new Date(grant.expires_at).getTime() <= Date.now()
                    ? "授权已过期"
                    : `有效至 ${formatDate(grant.expires_at)}`}
              </span>
            </div>
            {!grant.revoked_at && new Date(grant.expires_at).getTime() > Date.now() ? (
              <button onClick={() => inspectGrant(grant)} type="button">
                查看同步诊断
              </button>
            ) : null}
          </article>
        ))}
        {diagnostics.map(item => (
          <div className="admin-diagnostic" key={item.id}>
            <strong>{item.resource_type} · {item.status}</strong>
            <span>{item.error_summary ?? "无错误摘要"}</span>
          </div>
        ))}
      </section>
    </>
  );
}

function StatusOperationsSection() {
  const [components, setComponents] = useState<AdminStatusComponent[]>([]);
  const [componentId, setComponentId] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [message, setMessage] = useState("");
  const [internalSummary, setInternalSummary] = useState("");
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    listAdminStatusComponents()
      .then(items => {
        setComponents(items);
        setComponentId(items[0]?.id ?? "");
      })
      .catch(caught => setError(messageFrom(caught)));
  }, []);

  async function publish(event: FormEvent) {
    event.preventDefault();
    try {
      await createAdminStatusIncident({
        component_id: componentId,
        title,
        public_summary: summary,
        internal_summary: internalSummary,
        impact: "degraded",
        public_message: message,
        internal_note: internalSummary,
      });
      setSuccess("状态事件已发布");
      setTitle("");
      setSummary("");
      setMessage("");
      setInternalSummary("");
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }

  async function addComponent() {
    try {
      const created = await createAdminStatusComponent({
        slug: `component-${components.length + 1}`,
        name: `新服务组件 ${components.length + 1}`,
        description: "请在发布前完善组件说明。",
        display_order: components.length * 10,
      });
      setComponents(items => [...items, created]);
      setComponentId(created.id);
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }

  return (
    <>
      <AdminHeading
        eyebrow="公开状态"
        title="状态事件管理"
        description="公开文字与内部备注分离；发布后将同步到状态页并进入订阅通知队列。"
      />
      <div className="admin-status-toolbar">
        <strong>服务组件：{components.length}</strong>
        <button onClick={addComponent} type="button">新增组件</button>
      </div>
      <form className="admin-form" onSubmit={publish}>
        <label>
          <span>影响组件</span>
          <select
            onChange={event => setComponentId(event.target.value)}
            required
            value={componentId}
          >
            {components.map(component => (
              <option key={component.id} value={component.id}>{component.name}</option>
            ))}
          </select>
        </label>
        <label>
          <span>事件标题</span>
          <input
            aria-label="事件标题"
            minLength={3}
            onChange={event => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        <label>
          <span>公开摘要</span>
          <textarea
            aria-label="公开摘要"
            minLength={3}
            onChange={event => setSummary(event.target.value)}
            required
            value={summary}
          />
        </label>
        <label>
          <span>首次公开更新</span>
          <textarea
            aria-label="首次公开更新"
            minLength={3}
            onChange={event => setMessage(event.target.value)}
            required
            value={message}
          />
        </label>
        <label>
          <span>内部备注</span>
          <textarea
            onChange={event => setInternalSummary(event.target.value)}
            value={internalSummary}
          />
        </label>
        <button disabled={!componentId} type="submit"><Radio />发布状态事件</button>
      </form>
      {success ? <p className="admin-feedback is-success">{success}</p> : null}
      {error ? <p className="admin-feedback is-error">{error}</p> : null}
    </>
  );
}

const catalogCollections = [
  ["software-directory", "软件目录"],
  ["vendor-directory", "供应商目录"],
  ["merchant-aliases", "商户别名"],
  ["cancellation-routes", "取消路径"],
  ["risk-rules", "风险规则"],
  ["ai-prompts", "AI 提示"],
] as const;

function CatalogOperationsSection() {
  const [collection, setCollection] = useState<(typeof catalogCollections)[number][0]>(
    catalogCollections[0][0],
  );
  const [items, setItems] = useState<KnowledgeBundle[]>([]);
  const [key, setKey] = useState("");
  const [data, setData] = useState('{"name": ""}');
  const [summary, setSummary] = useState("");
  const [feedback, setFeedback] = useState("");
  const [reason, setReason] = useState("");
  const [password, setPassword] = useState("");
  const [targetVersion, setTargetVersion] = useState("1");

  useEffect(() => {
    listAdminKnowledge(collection)
      .then(response => setItems(response.items))
      .catch(caught => setFeedback(messageFrom(caught)));
  }, [collection]);

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      const created = await createAdminKnowledge(collection, {
        key,
        data: JSON.parse(data) as Record<string, unknown>,
        change_summary: summary,
      });
      setItems(current => [created, ...current]);
      setFeedback("草稿已创建，提交审核后才能发布。");
    } catch (caught) {
      setFeedback(messageFrom(caught));
    }
  }

  function replaceBundle(entryId: string, next: KnowledgeBundle) {
    setItems(current =>
      current.map(item => (item.entry.id === entryId ? next : item)),
    );
  }

  function replaceVersion(
    entryId: string,
    version: KnowledgeBundle["version"],
  ) {
    setItems(current =>
      current.map(item =>
        item.entry.id === entryId ? { ...item, version } : item,
      ),
    );
  }

  async function advance(item: KnowledgeBundle) {
    try {
      if (item.version.status === "draft") {
        const version = await submitAdminKnowledgeReview(item.version.id);
        replaceVersion(item.entry.id, version);
        setFeedback("已提交审核，需由另一位平台管理员批准。");
        return;
      }
      if (item.version.status === "in_review") {
        const version = await approveAdminKnowledgeVersion(item.version.id);
        replaceVersion(item.entry.id, version);
        setFeedback("版本已批准，重新认证后可发布。");
        return;
      }
      if (item.version.status === "approved") {
        const next = await publishAdminKnowledgeVersion(
          item.version.id,
          reason,
          password,
        );
        replaceBundle(item.entry.id, next);
        setFeedback("版本已发布，公开目录已切换。");
        return;
      }
      const version = await createAdminKnowledgeDraft(item.entry.id, {
        data: item.version.data,
        change_summary: reason,
      });
      replaceVersion(item.entry.id, version);
      setFeedback("已从当前发布版本创建下一版草稿。");
    } catch (caught) {
      setFeedback(messageFrom(caught));
    }
  }

  async function rollback(item: KnowledgeBundle) {
    try {
      const next = await rollbackAdminKnowledge(
        item.entry.id,
        Number(targetVersion),
        reason,
        password,
      );
      replaceBundle(item.entry.id, next);
      setFeedback(`已回滚并发布为 v${next.version.version_number}。`);
    } catch (caught) {
      setFeedback(messageFrom(caught));
    }
  }

  return (
    <>
      <AdminHeading
        eyebrow="全局知识"
        title="目录与规则版本"
        description="六类全局对象共享草稿、审核、发布和回滚模型，客户只能读取已发布版本。"
      />
      <div className="admin-catalog-tabs">
        {catalogCollections.map(([value, label]) => (
          <button
            aria-pressed={collection === value}
            key={value}
            onClick={() => setCollection(value)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>
      <form className="admin-form" onSubmit={create}>
        <label>
          <span>稳定键</span>
          <input onChange={event => setKey(event.target.value)} required value={key} />
        </label>
        <label>
          <span>JSON 数据</span>
          <textarea onChange={event => setData(event.target.value)} required value={data} />
        </label>
        <label>
          <span>变更摘要</span>
          <input
            minLength={3}
            onChange={event => setSummary(event.target.value)}
            required
            value={summary}
          />
        </label>
        <button type="submit"><BookOpen />创建草稿</button>
      </form>
      {feedback ? <p className="admin-feedback">{feedback}</p> : null}
      <section className="admin-panel">
        <h2>当前版本</h2>
        {items.map(item => (
          <article className="admin-row" key={item.entry.id}>
            <div>
              <strong>{item.entry.key}</strong>
              <span>v{item.version.version_number} · {item.version.status}</span>
            </div>
            <code>{JSON.stringify(item.version.data)}</code>
            <div className="admin-row-actions">
              <button onClick={() => advance(item)} type="button">
                {knowledgeActionLabel(item.version.status)}
              </button>
              {item.version.status === "published" &&
              item.version.version_number > 1 ? (
                <button
                  className="is-danger"
                  onClick={() => rollback(item)}
                  type="button"
                >
                  回滚
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </section>
      <section className="admin-form admin-knowledge-auth">
        <h2>版本操作确认</h2>
        <label>
          <span>变更或操作原因</span>
          <input
            minLength={3}
            onChange={event => setReason(event.target.value)}
            value={reason}
          />
        </label>
        <label>
          <span>当前密码（发布/回滚必填）</span>
          <input
            onChange={event => setPassword(event.target.value)}
            type="password"
            value={password}
          />
        </label>
        <label>
          <span>回滚目标版本</span>
          <input
            min={1}
            onChange={event => setTargetVersion(event.target.value)}
            type="number"
            value={targetVersion}
          />
        </label>
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

function knowledgeActionLabel(status: string) {
  if (status === "draft") return "提交审核";
  if (status === "in_review") return "批准版本";
  if (status === "approved") return "发布版本";
  return "创建下一版";
}
