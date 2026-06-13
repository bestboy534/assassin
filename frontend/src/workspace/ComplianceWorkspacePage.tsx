import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Database,
  Download,
  KeyRound,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldCheck,
  Webhook,
} from "lucide-react";
import {
  addComplianceEvidence,
  assignComplianceControlOwner,
  createApiKey,
  createComplianceControl,
  createComplianceFramework,
  createLegalHold,
  createPrivacyRequest,
  createRetentionPolicy,
  createSecurityIncident,
  createSecurityIncidentTask,
  createWebhookEndpoint,
  executeRetentionDeletion,
  exportAuditLogs,
  getComplianceControl,
  getCurrentSession,
  listApiKeys,
  listAuditLogs,
  listComplianceFrameworks,
  listPrivacyRequests,
  listSecurityIncidents,
  listWebhookDeliveries,
  listWebhookEndpoints,
  previewRetentionDeletion,
  processPrivacyRequest,
  retryWebhookDelivery,
  reviewComplianceControl,
  revokeApiKey,
  rotateWebhookSecret,
  testWebhookEndpoint,
  updateSecurityIncidentTask,
  verifyApiKey,
  type ApiKeyItem,
  type AuditLogExport,
  type AuditLogItem,
  type ComplianceControlItem,
  type ComplianceFrameworkItem,
  type DeletionJobItem,
  type DeletionPreview,
  type PrivacyRequestItem,
  type SecurityIncidentItem,
  type WebhookDeliveryItem,
  type WebhookEndpointItem,
} from "../app/api";
import {
  WorkspaceError,
  WorkspaceLoading,
  WorkspaceShell,
  useWorkspaceState,
} from "./WorkspaceDashboardPage";

type ComplianceSection =
  | "audit-log"
  | "compliance"
  | "incidents"
  | "data-retention"
  | "api-keys"
  | "webhooks";

const sectionPaths: Record<ComplianceSection, string> = {
  "audit-log": "security/audit-log",
  compliance: "security/compliance",
  incidents: "security/incidents",
  "data-retention": "settings/data-retention",
  "api-keys": "settings/api-keys",
  webhooks: "settings/webhooks",
};

function messageFrom(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function formatDate(value: string | null) {
  if (!value) return "无";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(parsed);
}

function splitValues(value: string) {
  return value
    .split(",")
    .map(item => item.trim())
    .filter(Boolean);
}

function replaceById<T extends { id: string }>(items: T[], updated: T) {
  return items.map(item => (item.id === updated.id ? updated : item));
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function PageHeading({
  eyebrow,
  title,
  description,
  icon,
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon: ReactNode;
}) {
  return (
    <header className="compliance-heading">
      <div className="compliance-heading-icon">{icon}</div>
      <div>
        <span>{eyebrow}</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </header>
  );
}

function Feedback({
  error,
  success,
}: {
  error?: string | null;
  success?: string | null;
}) {
  if (error) return <p className="compliance-feedback is-error">{error}</p>;
  if (success) return <p className="compliance-feedback is-success">{success}</p>;
  return null;
}

export function ComplianceWorkspacePage({
  section,
}: {
  section: ComplianceSection;
}) {
  const workspace = useWorkspaceState();

  if (workspace.status === "loading") return <WorkspaceLoading />;
  if (workspace.status === "error") {
    return <WorkspaceError message={workspace.message} />;
  }

  const organizationId = workspace.currentOrganization.id;
  let content: ReactNode;
  switch (section) {
    case "audit-log":
      content = <AuditLogSection organizationId={organizationId} />;
      break;
    case "compliance":
      content = <ComplianceControlSection organizationId={organizationId} />;
      break;
    case "incidents":
      content = <SecurityIncidentSection organizationId={organizationId} />;
      break;
    case "data-retention":
      content = <DataRetentionSection organizationId={organizationId} />;
      break;
    case "api-keys":
      content = <ApiKeySection organizationId={organizationId} />;
      break;
    case "webhooks":
      content = <WebhookSection organizationId={organizationId} />;
      break;
  }

  return (
    <WorkspaceShell
      activeSection={sectionPaths[section]}
      currentOrganization={workspace.currentOrganization}
    >
      <section className="workspace-panel compliance-page">{content}</section>
    </WorkspaceShell>
  );
}

function AuditLogSection({ organizationId }: { organizationId: string }) {
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exported, setExported] = useState<AuditLogExport | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const response = await listAuditLogs(organizationId);
      setItems(response.items);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "审计日志加载失败"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [organizationId]);

  const filtered = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase();
    if (!query) return items;
    return items.filter(item =>
      [
        item.action,
        item.resource_type,
        item.resource_id,
        item.actor_type,
        item.request_id,
      ]
        .filter(Boolean)
        .some(value => String(value).toLocaleLowerCase().includes(query)),
    );
  }, [filter, items]);

  async function handleExport() {
    try {
      const result = await exportAuditLogs(organizationId);
      setExported(result);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "审计日志导出失败"));
    }
  }

  return (
    <>
      <PageHeading
        description="按操作、资源和请求编号查询不可篡改的组织活动，并导出脱敏记录。"
        eyebrow="安全运营"
        icon={<ClipboardCheck />}
        title="审计日志"
      />
      <div className="compliance-toolbar">
        <label>
          <span>筛选操作</span>
          <input
            onChange={event => setFilter(event.target.value)}
            placeholder="例如 api_key、retention 或 request ID"
            value={filter}
          />
        </label>
        <button onClick={() => void refresh()} type="button">
          <RefreshCw />
          刷新
        </button>
        <button onClick={() => void handleExport()} type="button">
          <Download />
          导出 JSON
        </button>
      </div>
      <Feedback error={error} />
      {exported ? (
        <div className="compliance-result">
          <div>
            <strong>已生成 {exported.row_count} 条审计记录</strong>
            <span>导出时间：{formatDate(exported.exported_at)}</span>
          </div>
          <button
            onClick={() =>
              downloadJson(
                `audit-log-${new Date(exported.exported_at).toISOString()}.json`,
                exported,
              )
            }
            type="button"
          >
            下载审计文件
          </button>
        </div>
      ) : null}
      {loading ? <p className="compliance-empty">正在读取审计记录…</p> : null}
      {!loading && filtered.length === 0 ? (
        <p className="compliance-empty">没有符合条件的审计记录。</p>
      ) : null}
      <div className="compliance-list">
        {filtered.map(item => (
          <article aria-label={`审计记录 ${item.action}`} key={item.id}>
            <header>
              <div>
                <strong>{item.action}</strong>
                <span>
                  {item.resource_type}
                  {item.resource_id ? ` · ${item.resource_id}` : ""}
                </span>
              </div>
              <time>{formatDate(item.created_at)}</time>
            </header>
            <dl className="compliance-meta">
              <div>
                <dt>执行主体</dt>
                <dd>{item.actor_id ?? item.actor_type}</dd>
              </div>
              <div>
                <dt>请求 ID</dt>
                <dd>{item.request_id ?? "无"}</dd>
              </div>
              <div>
                <dt>来源 IP</dt>
                <dd>{item.ip_address ?? "无"}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </>
  );
}

function DataRetentionSection({ organizationId }: { organizationId: string }) {
  const [days, setDays] = useState("365");
  const [description, setDescription] = useState("");
  const [policyMessage, setPolicyMessage] = useState<string | null>(null);
  const [holdType, setHoldType] = useState<"stored_file" | "user">("stored_file");
  const [holdId, setHoldId] = useState("");
  const [holdReason, setHoldReason] = useState("");
  const [holdMessage, setHoldMessage] = useState<string | null>(null);
  const [preview, setPreview] = useState<DeletionPreview | null>(null);
  const [job, setJob] = useState<DeletionJobItem | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const policy = await createRetentionPolicy(organizationId, {
        retention_days: Number(days),
        description,
      });
      setPolicyMessage(`策略已生效：文件保留 ${policy.retention_days} 天`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "保留策略保存失败"));
    }
  }

  async function handleHold(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const hold = await createLegalHold(organizationId, {
        resource_type: holdType,
        resource_id: holdId.trim(),
        reason: holdReason.trim(),
      });
      setHoldMessage(`法务冻结已创建：${hold.resource_id}`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "法务冻结创建失败"));
    }
  }

  async function handlePreview() {
    try {
      setPreview(await previewRetentionDeletion(organizationId));
      setJob(null);
      setConfirmed(false);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "删除影响预览失败"));
    }
  }

  async function handleDelete() {
    try {
      setJob(await executeRetentionDeletion(organizationId, confirmed));
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "删除任务执行失败"));
    }
  }

  return (
    <>
      <PageHeading
        description="定义文件保留周期，先预览删除影响；有效法务冻结会阻止资源被删除。"
        eyebrow="数据治理"
        icon={<Database />}
        title="数据保留"
      />
      <Feedback error={error} />
      <div className="compliance-two-column">
        <form className="compliance-form" onSubmit={handlePolicy}>
          <header>
            <h3>保留策略</h3>
            <p>到期文件只会在执行删除任务后永久移除。</p>
          </header>
          <label>
            <span>保留天数</span>
            <input
              max="3650"
              min="1"
              onChange={event => setDays(event.target.value)}
              required
              type="number"
              value={days}
            />
          </label>
          <label>
            <span>策略说明</span>
            <textarea
              onChange={event => setDescription(event.target.value)}
              placeholder="说明业务或监管依据"
              value={description}
            />
          </label>
          <button type="submit">保存保留策略</button>
          <Feedback success={policyMessage} />
        </form>

        <form className="compliance-form" onSubmit={handleHold}>
          <header>
            <h3>法务冻结</h3>
            <p>被冻结的文件或用户数据不会被保留策略清除。</p>
          </header>
          <label>
            <span>资源类型</span>
            <select
              onChange={event =>
                setHoldType(event.target.value as "stored_file" | "user")
              }
              value={holdType}
            >
              <option value="stored_file">存储文件</option>
              <option value="user">用户</option>
            </select>
          </label>
          <label>
            <span>冻结资源 ID</span>
            <input
              onChange={event => setHoldId(event.target.value)}
              required
              value={holdId}
            />
          </label>
          <label>
            <span>冻结原因</span>
            <textarea
              onChange={event => setHoldReason(event.target.value)}
              required
              value={holdReason}
            />
          </label>
          <button type="submit">创建法务冻结</button>
          <Feedback success={holdMessage} />
        </form>
      </div>

      <section className="compliance-danger-zone">
        <header>
          <AlertTriangle />
          <div>
            <h3>永久删除到期文件</h3>
            <p>先预览候选项。执行后未受法务冻结保护的文件不可恢复。</p>
          </div>
        </header>
        <button onClick={() => void handlePreview()} type="button">
          预览删除影响
        </button>
        {preview ? (
          <>
            <div className="compliance-impact-grid">
              <div>
                <strong>将删除 {preview.delete_candidates.length} 项</strong>
                <span>截止时间：{formatDate(preview.cutoff_at)}</span>
                <code>{preview.delete_candidates.join("\n") || "无"}</code>
              </div>
              <div>
                <strong>
                  法务冻结保护 {preview.skipped_legal_hold.length} 项
                </strong>
                <span>这些资源不会进入删除任务。</span>
                <code>{preview.skipped_legal_hold.join("\n") || "无"}</code>
              </div>
            </div>
            <label className="compliance-confirm">
              <input
                checked={confirmed}
                onChange={event => setConfirmed(event.target.checked)}
                type="checkbox"
              />
              <span>我已重新认证，并理解删除后的文件无法恢复</span>
            </label>
            <button
              className="is-danger"
              disabled={!confirmed}
              onClick={() => void handleDelete()}
              type="button"
            >
              执行永久删除
            </button>
          </>
        ) : null}
        {job ? (
          <div className="compliance-result">
            <strong>
              删除完成：{job.deleted_resource_ids.length} 项；法务冻结跳过：
              {job.skipped_legal_hold.length} 项
            </strong>
          </div>
        ) : null}
      </section>
    </>
  );
}

function ApiKeySection({ organizationId }: { organizationId: string }) {
  const [items, setItems] = useState<ApiKeyItem[]>([]);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState("reports.read");
  const [secret, setSecret] = useState<string | null>(null);
  const [verification, setVerification] = useState<string | null>(null);
  const [confirmations, setConfirmations] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listApiKeys(organizationId)
      .then(response => setItems(response.items))
      .catch(caught => setError(messageFrom(caught, "API 密钥加载失败")));
  }, [organizationId]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const created = await createApiKey(organizationId, {
        name: name.trim(),
        scopes: splitValues(scopes),
      });
      const { secret: createdSecret, ...record } = created;
      setItems(current => [record, ...current]);
      setSecret(createdSecret);
      setVerification(null);
      setName("");
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "API 密钥创建失败"));
    }
  }

  async function handleVerify() {
    if (!secret) return;
    try {
      const principal = await verifyApiKey(secret, splitValues(scopes)[0]);
      setVerification(`验证成功：${principal.name}`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "API 密钥验证失败"));
    }
  }

  async function handleRevoke(item: ApiKeyItem) {
    try {
      const revoked = await revokeApiKey(organizationId, item.id);
      setItems(current => replaceById(current, revoked));
      setConfirmations(current => ({ ...current, [item.id]: false }));
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "API 密钥撤销失败"));
    }
  }

  return (
    <>
      <PageHeading
        description="为自动化创建最小权限凭证，验证实际权限，并在依赖迁移后立即撤销。"
        eyebrow="开发者设置"
        icon={<KeyRound />}
        title="API 密钥"
      />
      <Feedback error={error} />
      <form className="compliance-inline-form" onSubmit={handleCreate}>
        <label>
          <span>密钥名称</span>
          <input
            onChange={event => setName(event.target.value)}
            placeholder="例如 CI 自动化"
            required
            value={name}
          />
        </label>
        <label className="is-wide">
          <span>权限范围</span>
          <input
            aria-label="权限范围"
            aria-describedby="api-scope-help"
            onChange={event => setScopes(event.target.value)}
            required
            value={scopes}
          />
          <small id="api-scope-help">
            多个权限用英文逗号分隔，例如 reports.read, reports.export。
          </small>
        </label>
        <button type="submit">创建 API 密钥</button>
      </form>

      {secret ? (
        <section className="compliance-secret">
          <div>
            <strong>此密钥只显示一次</strong>
            <p>请立即保存到受控的密钥管理器，不要粘贴到代码或聊天中。</p>
          </div>
          <code>{secret}</code>
          <div className="compliance-actions-row">
            <button onClick={() => void handleVerify()} type="button">
              验证密钥
            </button>
            <button onClick={() => setSecret(null)} type="button">
              我已安全保存
            </button>
          </div>
          <Feedback success={verification} />
        </section>
      ) : null}

      <div className="compliance-list">
        {items.map(item => (
          <article aria-label={`API 密钥 ${item.name}`} key={item.id}>
            <header>
              <div>
                <strong>{item.name}</strong>
                <span>
                  {item.prefix}… · {item.scopes.join("、")}
                </span>
              </div>
              <span className={`compliance-status ${item.revoked_at ? "is-muted" : ""}`}>
                {item.revoked_at ? "已撤销" : "有效"}
              </span>
            </header>
            <dl className="compliance-meta">
              <div>
                <dt>创建时间</dt>
                <dd>{formatDate(item.created_at)}</dd>
              </div>
              <div>
                <dt>最后使用</dt>
                <dd>{formatDate(item.last_used_at)}</dd>
              </div>
              <div>
                <dt>到期时间</dt>
                <dd>{formatDate(item.expires_at)}</dd>
              </div>
            </dl>
            {!item.revoked_at ? (
              <div className="compliance-revoke">
                <p>撤销后，所有依赖此密钥的脚本和集成立即失去访问权限。</p>
                <label className="compliance-confirm">
                  <input
                    checked={Boolean(confirmations[item.id])}
                    onChange={event =>
                      setConfirmations(current => ({
                        ...current,
                        [item.id]: event.target.checked,
                      }))
                    }
                    type="checkbox"
                  />
                  <span>我确认依赖此密钥的自动化将立即停止</span>
                </label>
                <button
                  className="is-danger"
                  disabled={!confirmations[item.id]}
                  onClick={() => void handleRevoke(item)}
                  type="button"
                >
                  撤销密钥
                </button>
              </div>
            ) : null}
          </article>
        ))}
      </div>
      {items.length === 0 ? (
        <p className="compliance-empty">尚未创建 API 密钥。</p>
      ) : null}
    </>
  );
}

export function AccountPrivacyPage() {
  const [session, setSession] = useState<Awaited<
    ReturnType<typeof getCurrentSession>
  > | null>(null);
  const [items, setItems] = useState<PrivacyRequestItem[]>([]);
  const [requestType, setRequestType] =
    useState<PrivacyRequestItem["type"]>("access");
  const [confirmations, setConfirmations] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getCurrentSession(), listPrivacyRequests()])
      .then(([currentSession, response]) => {
        setSession(currentSession);
        setItems(response.items);
      })
      .catch(caught => setError(messageFrom(caught, "隐私请求加载失败")));
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const created = await createPrivacyRequest({
        type: requestType,
        scope: ["identity", "organization_memberships"],
      });
      setItems(current => [created, ...current]);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "隐私请求提交失败"));
    }
  }

  async function handleProcess(item: PrivacyRequestItem) {
    try {
      const processed = await processPrivacyRequest(
        item.id,
        Boolean(confirmations[item.id]),
      );
      setItems(current => replaceById(current, processed));
      setConfirmations(current => ({ ...current, [item.id]: false }));
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "隐私请求处理失败"));
    }
  }

  if (!session && !error) return <WorkspaceLoading />;
  if (!session) return <WorkspaceError message={error ?? "请先登录"} />;

  const organization = session.organizations[0];
  return (
    <main className="privacy-account-page">
      <header className="privacy-account-topbar">
        <Link to={organization ? `/app/${organization.slug}/dashboard` : "/"}>
          返回工作台
        </Link>
        <div>
          <span>{session.user.display_name}</span>
          <small>{session.user.email}</small>
        </div>
      </header>
      <section className="privacy-account-content">
        <PageHeading
          description="申请访问、更正、删除或导出个人数据。高风险请求需要重新认证确认。"
          eyebrow="个人账号"
          icon={<ShieldCheck />}
          title="隐私请求"
        />
        <Feedback error={error} />
        <form className="compliance-inline-form" onSubmit={handleCreate}>
          <label>
            <span>请求类型</span>
            <select
              onChange={event =>
                setRequestType(event.target.value as PrivacyRequestItem["type"])
              }
              value={requestType}
            >
              <option value="access">访问我的数据</option>
              <option value="correction">更正我的数据</option>
              <option value="portability">导出我的数据</option>
              <option value="deletion">删除我的数据</option>
            </select>
          </label>
          <div className="compliance-impact-note">
            {requestType === "deletion"
              ? "删除请求可能停用账号，但有效法务冻结会保留受保护数据。"
              : "请求会记录处理范围、完成时间和最终结果。"}
          </div>
          <button type="submit">提交隐私请求</button>
        </form>

        <div className="compliance-list">
          {items.map(item => {
            const completed = item.status === "completed";
            return (
              <article aria-label={`隐私请求 ${item.type}`} key={item.id}>
                <header>
                  <div>
                    <strong>{privacyTypeLabel(item.type)}</strong>
                    <span>截止时间：{formatDate(item.due_at)}</span>
                  </div>
                  <span className="compliance-status">
                    {completed ? "已完成" : "待处理"}
                  </span>
                </header>
                <p>处理范围：{item.scope.join("、")}</p>
                {!completed ? (
                  <div className="compliance-revoke">
                    <p>
                      处理会立即生成导出结果或应用更正/删除操作，请确认当前账号身份。
                    </p>
                    <label className="compliance-confirm">
                      <input
                        checked={Boolean(confirmations[item.id])}
                        onChange={event =>
                          setConfirmations(current => ({
                            ...current,
                            [item.id]: event.target.checked,
                          }))
                        }
                        type="checkbox"
                      />
                      <span>我已重新认证，并确认处理该隐私请求</span>
                    </label>
                    <button
                      disabled={!confirmations[item.id]}
                      onClick={() => void handleProcess(item)}
                      type="button"
                    >
                      确认并处理
                    </button>
                  </div>
                ) : (
                  <div className="compliance-actions-row">
                    <span>完成时间：{formatDate(item.completed_at)}</span>
                    {Object.keys(item.result).length > 0 ? (
                      <button
                        onClick={() =>
                          downloadJson(`privacy-${item.id}.json`, item.result)
                        }
                        type="button"
                      >
                        下载我的数据
                      </button>
                    ) : null}
                  </div>
                )}
              </article>
            );
          })}
        </div>
        {items.length === 0 ? (
          <p className="compliance-empty">还没有隐私请求。</p>
        ) : null}
      </section>
    </main>
  );
}

function privacyTypeLabel(type: PrivacyRequestItem["type"]) {
  return {
    access: "访问数据",
    correction: "更正数据",
    deletion: "删除数据",
    portability: "导出数据",
  }[type];
}

function ComplianceControlSection({
  organizationId,
}: {
  organizationId: string;
}) {
  const [frameworks, setFrameworks] = useState<ComplianceFrameworkItem[]>([]);
  const [frameworkCode, setFrameworkCode] = useState("");
  const [frameworkName, setFrameworkName] = useState("");
  const [frameworkVersion, setFrameworkVersion] = useState("1.0");
  const [selectedFramework, setSelectedFramework] = useState("");
  const [controlCode, setControlCode] = useState("");
  const [controlTitle, setControlTitle] = useState("");
  const [controlId, setControlId] = useState("");
  const [control, setControl] = useState<ComplianceControlItem | null>(null);
  const [ownerId, setOwnerId] = useState("");
  const [evidenceFileId, setEvidenceFileId] = useState("");
  const [evidenceTitle, setEvidenceTitle] = useState("");
  const [reviewOutcome, setReviewOutcome] =
    useState<"effective" | "ineffective" | "needs_attention">("effective");
  const [reviewNotes, setReviewNotes] = useState("");
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshFrameworks() {
    try {
      const response = await listComplianceFrameworks(organizationId);
      setFrameworks(response.items);
      setSelectedFramework(current => current || response.items[0]?.id || "");
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "合规框架加载失败"));
    }
  }

  useEffect(() => {
    void refreshFrameworks();
  }, [organizationId]);

  async function handleFramework(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const created = await createComplianceFramework(organizationId, {
        code: frameworkCode.trim(),
        name: frameworkName.trim(),
        version: frameworkVersion.trim(),
        description: "",
      });
      setFrameworks(current => [created, ...current]);
      setSelectedFramework(created.id);
      setFrameworkCode("");
      setFrameworkName("");
      setSuccess(`已创建框架：${created.name}`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "合规框架创建失败"));
    }
  }

  async function handleControl(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFramework) {
      setError("请先选择或创建合规框架");
      return;
    }
    try {
      const created = await createComplianceControl(
        organizationId,
        selectedFramework,
        {
          code: controlCode.trim(),
          title: controlTitle.trim(),
          description: "",
          frequency_days: 90,
        },
      );
      setControl(created);
      setControlId(created.id);
      setControlCode("");
      setControlTitle("");
      setSuccess(`已创建控制项：${created.title}`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "控制项创建失败"));
    }
  }

  async function loadControl() {
    try {
      const loaded = await getComplianceControl(organizationId, controlId.trim());
      setControl(loaded);
      setSuccess(`已载入控制项：${loaded.title}`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "控制项加载失败"));
    }
  }

  async function reloadControl(targetId: string) {
    setControl(await getComplianceControl(organizationId, targetId));
  }

  async function handleOwner(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!control) return;
    try {
      await assignComplianceControlOwner(organizationId, control.id, {
        user_id: ownerId.trim(),
        role: "owner",
      });
      await reloadControl(control.id);
      setOwnerId("");
      setSuccess("控制负责人已更新");
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "控制负责人分配失败"));
    }
  }

  async function handleEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!control) return;
    try {
      await addComplianceEvidence(organizationId, control.id, {
        stored_file_id: evidenceFileId.trim(),
        title: evidenceTitle.trim(),
        description: "",
      });
      await reloadControl(control.id);
      setEvidenceFileId("");
      setEvidenceTitle("");
      setSuccess("控制证据已关联");
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "控制证据关联失败"));
    }
  }

  async function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!control) return;
    try {
      await reviewComplianceControl(organizationId, control.id, {
        outcome: reviewOutcome,
        notes: reviewNotes,
      });
      await reloadControl(control.id);
      setReviewNotes("");
      setSuccess("控制评审已记录");
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "控制评审记录失败"));
    }
  }

  return (
    <>
      <PageHeading
        description="建立合规框架与控制项，指定负责人，关联证据并记录周期评审结果。"
        eyebrow="治理与保证"
        icon={<ShieldCheck />}
        title="合规控制"
      />
      <Feedback error={error} success={success} />
      <div className="compliance-two-column">
        <form className="compliance-form" onSubmit={handleFramework}>
          <header>
            <h3>新增合规框架</h3>
            <p>框架可对应 ISO 27001、SOC 2 或内部安全基线。</p>
          </header>
          <label>
            <span>框架代码</span>
            <input
              onChange={event => setFrameworkCode(event.target.value)}
              required
              value={frameworkCode}
            />
          </label>
          <label>
            <span>框架名称</span>
            <input
              onChange={event => setFrameworkName(event.target.value)}
              required
              value={frameworkName}
            />
          </label>
          <label>
            <span>版本</span>
            <input
              onChange={event => setFrameworkVersion(event.target.value)}
              required
              value={frameworkVersion}
            />
          </label>
          <button type="submit">创建框架</button>
        </form>

        <form className="compliance-form" onSubmit={handleControl}>
          <header>
            <h3>新增控制项</h3>
            <p>控制项默认每 90 天复审一次。</p>
          </header>
          <label>
            <span>所属框架</span>
            <select
              onChange={event => setSelectedFramework(event.target.value)}
              required
              value={selectedFramework}
            >
              <option value="">请选择框架</option>
              {frameworks.map(item => (
                <option key={item.id} value={item.id}>
                  {item.code} · {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>控制代码</span>
            <input
              onChange={event => setControlCode(event.target.value)}
              required
              value={controlCode}
            />
          </label>
          <label>
            <span>控制标题</span>
            <input
              onChange={event => setControlTitle(event.target.value)}
              required
              value={controlTitle}
            />
          </label>
          <button type="submit">创建控制项</button>
        </form>
      </div>

      <section className="compliance-control-inspector">
        <header>
          <div>
            <h3>控制项工作台</h3>
            <p>输入已有控制项 ID，或直接管理刚创建的控制项。</p>
          </div>
          <div className="compliance-id-loader">
            <label>
              <span>控制项 ID</span>
              <input
                onChange={event => setControlId(event.target.value)}
                value={controlId}
              />
            </label>
            <button
              disabled={!controlId.trim()}
              onClick={() => void loadControl()}
              type="button"
            >
              载入
            </button>
          </div>
        </header>
        {control ? (
          <>
            <div className="compliance-control-summary">
              <div>
                <strong>
                  {control.code} · {control.title}
                </strong>
                <span>状态：{control.status}</span>
              </div>
              <dl className="compliance-meta">
                <div>
                  <dt>负责人</dt>
                  <dd>{control.owners.length}</dd>
                </div>
                <div>
                  <dt>证据</dt>
                  <dd>{control.evidence.length}</dd>
                </div>
                <div>
                  <dt>评审</dt>
                  <dd>{control.reviews.length}</dd>
                </div>
              </dl>
            </div>
            <div className="compliance-three-column">
              <form className="compliance-form" onSubmit={handleOwner}>
                <h4>分配负责人</h4>
                <label>
                  <span>用户 ID</span>
                  <input
                    onChange={event => setOwnerId(event.target.value)}
                    required
                    value={ownerId}
                  />
                </label>
                <button type="submit">保存负责人</button>
              </form>
              <form className="compliance-form" onSubmit={handleEvidence}>
                <h4>关联证据</h4>
                <label>
                  <span>文件 ID</span>
                  <input
                    onChange={event => setEvidenceFileId(event.target.value)}
                    required
                    value={evidenceFileId}
                  />
                </label>
                <label>
                  <span>证据标题</span>
                  <input
                    onChange={event => setEvidenceTitle(event.target.value)}
                    required
                    value={evidenceTitle}
                  />
                </label>
                <button type="submit">关联证据</button>
              </form>
              <form className="compliance-form" onSubmit={handleReview}>
                <h4>记录评审</h4>
                <label>
                  <span>评审结果</span>
                  <select
                    onChange={event =>
                      setReviewOutcome(
                        event.target.value as typeof reviewOutcome,
                      )
                    }
                    value={reviewOutcome}
                  >
                    <option value="effective">有效</option>
                    <option value="needs_attention">需要关注</option>
                    <option value="ineffective">无效</option>
                  </select>
                </label>
                <label>
                  <span>评审说明</span>
                  <textarea
                    onChange={event => setReviewNotes(event.target.value)}
                    value={reviewNotes}
                  />
                </label>
                <button type="submit">记录评审</button>
              </form>
            </div>
          </>
        ) : (
          <p className="compliance-empty">尚未载入控制项。</p>
        )}
      </section>

      <div className="compliance-list">
        {frameworks.map(item => (
          <article aria-label={`合规框架 ${item.name}`} key={item.id}>
            <header>
              <div>
                <strong>
                  {item.code} · {item.name}
                </strong>
                <span>{item.description || "暂无说明"}</span>
              </div>
              <span className="compliance-status">{item.status}</span>
            </header>
            <p>版本 {item.version}</p>
          </article>
        ))}
      </div>
    </>
  );
}

function SecurityIncidentSection({
  organizationId,
}: {
  organizationId: string;
}) {
  const [items, setItems] = useState<SecurityIncidentItem[]>([]);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] =
    useState<"low" | "medium" | "high" | "critical">("medium");
  const [summary, setSummary] = useState("");
  const [taskTitles, setTaskTitles] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSecurityIncidents(organizationId)
      .then(response => setItems(response.items))
      .catch(caught => setError(messageFrom(caught, "安全事件加载失败")));
  }, [organizationId]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const created = await createSecurityIncident(organizationId, {
        title: title.trim(),
        severity,
        summary: summary.trim(),
        detected_at: new Date().toISOString(),
      });
      setItems(current => [created, ...current]);
      setTitle("");
      setSummary("");
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "安全事件创建失败"));
    }
  }

  async function addTask(incident: SecurityIncidentItem) {
    const taskTitle = taskTitles[incident.id]?.trim();
    if (!taskTitle) return;
    try {
      const task = await createSecurityIncidentTask(
        organizationId,
        incident.id,
        { title: taskTitle },
      );
      setItems(current =>
        current.map(item =>
          item.id === incident.id
            ? { ...item, tasks: [...item.tasks, task] }
            : item,
        ),
      );
      setTaskTitles(current => ({ ...current, [incident.id]: "" }));
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "响应任务创建失败"));
    }
  }

  async function completeTask(
    incident: SecurityIncidentItem,
    taskId: string,
  ) {
    try {
      const updated = await updateSecurityIncidentTask(
        organizationId,
        incident.id,
        taskId,
        "completed",
      );
      setItems(current =>
        current.map(item =>
          item.id === incident.id
            ? { ...item, tasks: replaceById(item.tasks, updated) }
            : item,
        ),
      );
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "响应任务更新失败"));
    }
  }

  return (
    <>
      <PageHeading
        description="集中记录事件严重级别、发现时间与响应任务，形成可审计的处置过程。"
        eyebrow="安全响应"
        icon={<AlertTriangle />}
        title="安全事件"
      />
      <Feedback error={error} />
      <form className="compliance-inline-form" onSubmit={handleCreate}>
        <label>
          <span>事件标题</span>
          <input
            onChange={event => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        <label>
          <span>严重级别</span>
          <select
            onChange={event =>
              setSeverity(event.target.value as typeof severity)
            }
            value={severity}
          >
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
            <option value="critical">严重</option>
          </select>
        </label>
        <label className="is-wide">
          <span>事件摘要</span>
          <input
            onChange={event => setSummary(event.target.value)}
            required
            value={summary}
          />
        </label>
        <button type="submit">创建安全事件</button>
      </form>
      <div className="compliance-list">
        {items.map(incident => (
          <article aria-label={`安全事件 ${incident.title}`} key={incident.id}>
            <header>
              <div>
                <strong>{incident.title}</strong>
                <span>{incident.summary}</span>
              </div>
              <span className={`compliance-severity is-${incident.severity}`}>
                {severityLabel(incident.severity)}
              </span>
            </header>
            <p>发现时间：{formatDate(incident.detected_at)}</p>
            <div className="compliance-task-list">
              {incident.tasks.map(task => (
                <div key={task.id}>
                  <span>{task.title}</span>
                  <span>{task.status === "completed" ? "已完成" : "待处理"}</span>
                  {task.status !== "completed" ? (
                    <button
                      onClick={() => void completeTask(incident, task.id)}
                      type="button"
                    >
                      标记完成
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
            <div className="compliance-actions-row">
              <label>
                <span>新增响应任务</span>
                <input
                  onChange={event =>
                    setTaskTitles(current => ({
                      ...current,
                      [incident.id]: event.target.value,
                    }))
                  }
                  value={taskTitles[incident.id] ?? ""}
                />
              </label>
              <button
                disabled={!taskTitles[incident.id]?.trim()}
                onClick={() => void addTask(incident)}
                type="button"
              >
                添加任务
              </button>
            </div>
          </article>
        ))}
      </div>
      {items.length === 0 ? (
        <p className="compliance-empty">当前没有安全事件。</p>
      ) : null}
    </>
  );
}

function severityLabel(severity: string) {
  return (
    {
      low: "低",
      medium: "中",
      high: "高",
      critical: "严重",
    }[severity] ?? severity
  );
}

function WebhookSection({ organizationId }: { organizationId: string }) {
  const [items, setItems] = useState<WebhookEndpointItem[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState("security.incident.created");
  const [secret, setSecret] = useState<string | null>(null);
  const [confirmations, setConfirmations] = useState<Record<string, boolean>>({});
  const [deliveries, setDeliveries] = useState<
    Record<string, WebhookDeliveryItem[]>
  >({});
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listWebhookEndpoints(organizationId)
      .then(response => setItems(response.items))
      .catch(caught => setError(messageFrom(caught, "Webhook 加载失败")));
  }, [organizationId]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const created = await createWebhookEndpoint(organizationId, {
        name: name.trim(),
        url: url.trim(),
        events: splitValues(events),
      });
      const { secret: createdSecret, ...record } = created;
      setItems(current => [record, ...current]);
      setSecret(createdSecret);
      setName("");
      setUrl("");
      setFeedback(`Webhook 已创建：${created.name}`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "Webhook 创建失败"));
    }
  }

  async function handleTest(endpoint: WebhookEndpointItem) {
    try {
      const delivery = await testWebhookEndpoint(
        organizationId,
        endpoint.id,
        endpoint.events[0] ?? "webhook.test",
      );
      setDeliveries(current => ({
        ...current,
        [endpoint.id]: [delivery, ...(current[endpoint.id] ?? [])],
      }));
      setFeedback(`测试投递结果：${delivery.status}`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "Webhook 测试失败"));
    }
  }

  async function handleRotate(endpoint: WebhookEndpointItem) {
    try {
      const rotated = await rotateWebhookSecret(
        organizationId,
        endpoint.id,
      );
      setItems(current =>
        current.map(item =>
          item.id === endpoint.id
            ? {
                ...item,
                secret_version: rotated.secret_version,
                previous_secret_expires_at:
                  rotated.previous_secret_expires_at,
              }
            : item,
        ),
      );
      setSecret(rotated.secret);
      setConfirmations(current => ({ ...current, [endpoint.id]: false }));
      setFeedback("签名密钥已轮换，旧密钥将在重叠窗口结束后失效。");
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "Webhook 密钥轮换失败"));
    }
  }

  async function loadDeliveries(endpoint: WebhookEndpointItem) {
    try {
      const response = await listWebhookDeliveries(
        organizationId,
        endpoint.id,
      );
      setDeliveries(current => ({
        ...current,
        [endpoint.id]: response.items,
      }));
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "投递记录加载失败"));
    }
  }

  async function handleRetry(
    endpoint: WebhookEndpointItem,
    delivery: WebhookDeliveryItem,
  ) {
    try {
      const updated = await retryWebhookDelivery(
        organizationId,
        endpoint.id,
        delivery.id,
      );
      setDeliveries(current => ({
        ...current,
        [endpoint.id]: replaceById(current[endpoint.id] ?? [], updated),
      }));
      setFeedback(`重试结果：${updated.status}`);
      setError(null);
    } catch (caught) {
      setError(messageFrom(caught, "Webhook 重试失败"));
    }
  }

  return (
    <>
      <PageHeading
        description="订阅组织事件，验证签名投递，查看失败原因并在受控重叠窗口内轮换密钥。"
        eyebrow="开发者设置"
        icon={<Webhook />}
        title="Webhook"
      />
      <Feedback error={error} success={feedback} />
      <form className="compliance-inline-form" onSubmit={handleCreate}>
        <label>
          <span>端点名称</span>
          <input
            onChange={event => setName(event.target.value)}
            required
            value={name}
          />
        </label>
        <label className="is-wide">
          <span>HTTPS 地址</span>
          <input
            onChange={event => setUrl(event.target.value)}
            placeholder="https://example.com/webhooks"
            required
            type="url"
            value={url}
          />
        </label>
        <label className="is-wide">
          <span>订阅事件</span>
          <input
            onChange={event => setEvents(event.target.value)}
            required
            value={events}
          />
        </label>
        <button type="submit">创建 Webhook</button>
      </form>

      {secret ? (
        <section className="compliance-secret">
          <div>
            <strong>签名密钥只显示一次</strong>
            <p>接收端应使用该密钥验证每次请求的 HMAC 签名。</p>
          </div>
          <code>{secret}</code>
          <button onClick={() => setSecret(null)} type="button">
            我已安全保存
          </button>
        </section>
      ) : null}

      <div className="compliance-list">
        {items.map(endpoint => (
          <article aria-label={`Webhook ${endpoint.name}`} key={endpoint.id}>
            <header>
              <div>
                <strong>{endpoint.name}</strong>
                <span>{endpoint.url}</span>
              </div>
              <span className="compliance-status">{endpoint.status}</span>
            </header>
            <p>事件：{endpoint.events.join("、")}</p>
            <p>签名密钥版本：v{endpoint.secret_version}</p>
            <div className="compliance-actions-row">
              <button onClick={() => void handleTest(endpoint)} type="button">
                <Send />
                发送测试
              </button>
              <button
                onClick={() => void loadDeliveries(endpoint)}
                type="button"
              >
                <RefreshCw />
                查看投递
              </button>
            </div>
            <div className="compliance-revoke">
              <p>
                轮换后新投递使用新密钥，旧密钥仅在一小时重叠窗口内继续有效。
              </p>
              <label className="compliance-confirm">
                <input
                  checked={Boolean(confirmations[endpoint.id])}
                  onChange={event =>
                    setConfirmations(current => ({
                      ...current,
                      [endpoint.id]: event.target.checked,
                    }))
                  }
                  type="checkbox"
                />
                <span>我确认接收端会在重叠窗口内更新签名密钥</span>
              </label>
              <button
                disabled={!confirmations[endpoint.id]}
                onClick={() => void handleRotate(endpoint)}
                type="button"
              >
                <RotateCcw />
                轮换密钥
              </button>
            </div>
            {(deliveries[endpoint.id] ?? []).length > 0 ? (
              <div className="compliance-deliveries">
                {(deliveries[endpoint.id] ?? []).map(delivery => (
                  <div key={delivery.id}>
                    <span>{delivery.event_type}</span>
                    <span>{delivery.status}</span>
                    <span>尝试 {delivery.attempts} 次</span>
                    {delivery.status !== "delivered" ? (
                      <button
                        onClick={() => void handleRetry(endpoint, delivery)}
                        type="button"
                      >
                        <RotateCcw />
                        重试
                      </button>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}
          </article>
        ))}
      </div>
      {items.length === 0 ? (
        <p className="compliance-empty">尚未配置 Webhook。</p>
      ) : null}
    </>
  );
}
