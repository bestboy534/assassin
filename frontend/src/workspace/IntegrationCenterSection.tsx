import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Cable,
  CheckCircle2,
  Pause,
  Play,
  RefreshCw,
  Trash2,
} from "lucide-react";
import {
  createIntegrationConnection,
  deleteIntegrationConnection,
  listIntegrationConnections,
  listIntegrationDefinitions,
  listIntegrationSyncRuns,
  pauseIntegrationConnection,
  resumeIntegrationConnection,
  syncIntegrationConnection,
  testIntegrationConnection,
  type IntegrationConnectionItem,
  type IntegrationDefinitionItem,
  type IntegrationSyncRunItem,
} from "../app/api";

function connectionStatusLabel(status: string) {
  const labels: Record<string, string> = {
    connected: "已连接",
    deleted: "已删除",
    paused: "已暂停",
  };
  return labels[status] ?? status;
}

function syncStatus(run: IntegrationSyncRunItem) {
  if (run.status === "succeeded") {
    return `同步成功 · 读取 ${run.read_count} · 新增 ${run.created_count}`;
  }
  if (run.status === "failed") {
    return `同步失败 · 读取 ${run.read_count} · 失败 ${run.failed_count}`;
  }
  return run.status;
}

export function IntegrationCenterSection({
  organizationId,
}: {
  organizationId: string;
}) {
  const [definitions, setDefinitions] = useState<IntegrationDefinitionItem[]>([]);
  const [connections, setConnections] = useState<IntegrationConnectionItem[]>([]);
  const [syncRuns, setSyncRuns] = useState<Record<string, IntegrationSyncRunItem[]>>({});
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [healthMessage, setHealthMessage] = useState<string | null>(null);
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null);

  const [definitionKey, setDefinitionKey] = useState("fake_identity");
  const [displayName, setDisplayName] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [failOnPage, setFailOnPage] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      listIntegrationDefinitions(organizationId),
      listIntegrationConnections(organizationId),
    ])
      .then(([definitionResponse, connectionResponse]) => {
        if (!active) return;
        setDefinitions(definitionResponse.items);
        setConnections(connectionResponse.items);
        setDefinitionKey(definitionResponse.items[0]?.key ?? "fake_identity");
        setError(null);
      })
      .catch(caught => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "集成数据加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  const selectedDefinition = useMemo(
    () => definitions.find(item => item.key === definitionKey) ?? definitions[0],
    [definitionKey, definitions],
  );

  function replaceConnection(connection: IntegrationConnectionItem) {
    setConnections(current => [
      connection,
      ...current.filter(item => item.id !== connection.id),
    ]);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("create");
    setError(null);
    setHealthMessage(null);
    setDeleteMessage(null);
    try {
      const created = await createIntegrationConnection(organizationId, {
        definition_key: definitionKey,
        display_name: displayName,
        api_token: apiToken,
        sandbox_options: failOnPage ? { fail_on_page: 2 } : {},
      });
      replaceConnection(created);
      setDisplayName("");
      setApiToken("");
      setFailOnPage(false);
      setSyncRuns(current => ({ ...current, [created.id]: [] }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "保存集成连接失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleTest(connection: IntegrationConnectionItem) {
    setBusyKey(`test-${connection.id}`);
    setError(null);
    try {
      const response = await testIntegrationConnection(organizationId, connection.id);
      setHealthMessage(response.message);
      replaceConnection({ ...connection, last_health_status: response.healthy ? "healthy" : "unhealthy" });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "测试连接失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function refreshRuns(connectionId: string) {
    const response = await listIntegrationSyncRuns(organizationId, connectionId);
    setSyncRuns(current => ({ ...current, [connectionId]: response.items }));
  }

  async function handleSync(connection: IntegrationConnectionItem) {
    setBusyKey(`sync-${connection.id}`);
    setError(null);
    try {
      const run = await syncIntegrationConnection(organizationId, connection.id);
      setSyncRuns(current => ({
        ...current,
        [connection.id]: [run, ...(current[connection.id] ?? [])],
      }));
      await refreshRuns(connection.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "同步运行失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handlePause(connection: IntegrationConnectionItem) {
    setBusyKey(`pause-${connection.id}`);
    try {
      replaceConnection(await pauseIntegrationConnection(organizationId, connection.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "暂停连接失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleResume(connection: IntegrationConnectionItem) {
    setBusyKey(`resume-${connection.id}`);
    try {
      replaceConnection(await resumeIntegrationConnection(organizationId, connection.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "恢复连接失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleDelete(connection: IntegrationConnectionItem) {
    setBusyKey(`delete-${connection.id}`);
    try {
      const response = await deleteIntegrationConnection(organizationId, connection.id);
      replaceConnection({ ...connection, status: response.status });
      setDeleteMessage("已删除，已同步数据保留");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "删除连接失败");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="workspace-panel workspace-integrations">
      <div className="workspace-section-heading">
        <span>OAuth、密钥与同步诊断</span>
        <h2>集成中心</h2>
        <p>
          统一管理身份目录、协作工具和会计系统连接。凭据只在后端加密保存，前端只显示权限范围、尾号、同步游标和错误诊断。
        </p>
      </div>

      {error ? <p className="workspace-inline-error">{error}</p> : null}
      {healthMessage ? <p className="workspace-integrations-success">{healthMessage}</p> : null}
      {deleteMessage ? <p className="workspace-integrations-success">{deleteMessage}</p> : null}

      <section className="workspace-integration-band">
        <div className="workspace-spend-title">
          <Cable />
          <div>
            <h3>可连接目录</h3>
            <p>先用 Sandbox 身份目录验证连接、增量同步和错误处理，再接入真实供应商适配器。</p>
          </div>
        </div>
        {loading ? <p className="workspace-muted">正在加载集成目录...</p> : null}
        <div className="workspace-integration-definitions">
          {definitions.map(definition => (
            <article key={definition.id}>
              <strong>{definition.name}</strong>
              <span>{definition.capabilities.join(" · ")}</span>
              <small>{definition.resource_types.join("、")}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="workspace-integration-band">
        <div className="workspace-spend-title">
          <CheckCircle2 />
          <div>
            <h3>创建连接</h3>
            <p>API Token 提交后立即加密，页面不会回显明文。</p>
          </div>
        </div>
        <form className="workspace-integration-form" onSubmit={handleCreate}>
          <label>
            <span>连接类型</span>
            <select value={definitionKey} onChange={event => setDefinitionKey(event.target.value)}>
              {definitions.map(definition => (
                <option key={definition.key} value={definition.key}>
                  {definition.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>连接名称</span>
            <input
              required
              value={displayName}
              onChange={event => setDisplayName(event.target.value)}
            />
          </label>
          <label>
            <span>API Token</span>
            <input
              required
              type="password"
              value={apiToken}
              onChange={event => setApiToken(event.target.value)}
            />
          </label>
          <label className="workspace-integration-toggle">
            <input
              checked={failOnPage}
              onChange={event => setFailOnPage(event.target.checked)}
              type="checkbox"
            />
            <span>模拟第二页失败</span>
          </label>
          <button disabled={busyKey === "create" || !selectedDefinition} type="submit">
            连接并保存
          </button>
        </form>
      </section>

      <section className="workspace-integration-band">
        <div className="workspace-spend-title">
          <Activity />
          <div>
            <h3>连接与同步</h3>
            <p>同步成功才推进游标；失败会保留错误详情，已同步数据按保留策略继续留存。</p>
          </div>
        </div>
        {connections.length === 0 ? (
          <div className="workspace-empty">
            <h3>还没有连接</h3>
            <p>创建第一个 Sandbox 连接后，这里会展示同步运行和诊断。</p>
          </div>
        ) : null}
        <div className="workspace-integration-list">
          {connections.map(connection => {
            const latestRun = syncRuns[connection.id]?.[0];
            return (
              <article key={connection.id}>
                <header>
                  <div>
                    <strong>{connection.display_name}</strong>
                    <span>{connection.definition_name} · 凭据尾号 {connection.credential_last4}</span>
                  </div>
                  <b className={`is-${connection.status}`}>
                    {connectionStatusLabel(connection.status)}
                  </b>
                </header>
                <div className="workspace-integration-capabilities">
                  {connection.capabilities.map(capability => (
                    <span key={capability}>{capability}</span>
                  ))}
                </div>
                <div className="workspace-integration-actions">
                  <button
                    disabled={busyKey === `test-${connection.id}`}
                    onClick={() => handleTest(connection)}
                    type="button"
                  >
                    测试连接
                  </button>
                  <button
                    disabled={busyKey === `sync-${connection.id}` || connection.status !== "connected"}
                    onClick={() => handleSync(connection)}
                    type="button"
                  >
                    <RefreshCw />
                    运行同步
                  </button>
                  {connection.status === "paused" ? (
                    <button
                      disabled={busyKey === `resume-${connection.id}`}
                      onClick={() => handleResume(connection)}
                      type="button"
                    >
                      <Play />
                      恢复
                    </button>
                  ) : (
                    <button
                      disabled={busyKey === `pause-${connection.id}` || connection.status !== "connected"}
                      onClick={() => handlePause(connection)}
                      type="button"
                    >
                      <Pause />
                      暂停
                    </button>
                  )}
                  <button
                    className="is-danger"
                    disabled={busyKey === `delete-${connection.id}` || connection.status === "deleted"}
                    onClick={() => handleDelete(connection)}
                    type="button"
                  >
                    <Trash2 />
                    删除连接
                  </button>
                </div>
                {latestRun ? (
                  <div className={`workspace-integration-run is-${latestRun.status}`}>
                    <strong>{syncStatus(latestRun)}</strong>
                    {latestRun.cursor_after ? <span>游标 {latestRun.cursor_after}</span> : null}
                    {latestRun.errors.map(error => (
                      <p key={`${latestRun.id}-${error.code}`}>
                        <b>{error.code}</b>
                        {error.message}
                      </p>
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      </section>
    </section>
  );
}
