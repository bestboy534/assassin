import { type FormEvent, useEffect, useMemo, useState } from "react";
import { BarChart3, Camera, Download, Save, Send } from "lucide-react";
import {
  createReportExport,
  createReportSnapshot,
  createReportSubscription,
  createSavedReport,
  listReportDimensions,
  listReportMetrics,
  listSavedReports,
  queryReport,
  type ReportDimensionItem,
  type ReportExportItem,
  type ReportMetricDefinitionItem,
  type ReportQueryPayload,
  type ReportQueryResult,
  type ReportSnapshotItem,
  type ReportSubscriptionItem,
  type SavedReportItem,
} from "../app/api";

type ReportMessage =
  | { type: "success"; text: string }
  | { type: "error"; text: string }
  | null;

const DEFAULT_QUERY: ReportQueryPayload = {
  metrics: ["monthly_spend"],
  date_range: {
    start: "2026-06-01",
    end: "2026-06-30",
  },
  group_by: ["department"],
  filters: [],
  comparison: null,
};

export function ReportWorkspaceSection({
  organizationId,
}: {
  organizationId: string;
}) {
  const [metrics, setMetrics] = useState<ReportMetricDefinitionItem[]>([]);
  const [dimensions, setDimensions] = useState<ReportDimensionItem[]>([]);
  const [savedReports, setSavedReports] = useState<SavedReportItem[]>([]);
  const [query, setQuery] = useState<ReportQueryPayload>(DEFAULT_QUERY);
  const [result, setResult] = useState<ReportQueryResult | null>(null);
  const [reportName, setReportName] = useState("");
  const [activeReport, setActiveReport] = useState<SavedReportItem | null>(null);
  const [latestSnapshot, setLatestSnapshot] = useState<ReportSnapshotItem | null>(null);
  const [latestExport, setLatestExport] = useState<ReportExportItem | null>(null);
  const [latestSubscription, setLatestSubscription] =
    useState<ReportSubscriptionItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<ReportMessage>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      listReportMetrics(organizationId),
      listReportDimensions(organizationId),
      listSavedReports(organizationId),
    ])
      .then(([metricResponse, dimensionResponse, savedResponse]) => {
        if (!active) return;
        setMetrics(metricResponse.items);
        setDimensions(dimensionResponse.items);
        setSavedReports(savedResponse.items);
        setActiveReport(savedResponse.items[0] ?? null);
        setMessage(null);
      })
      .catch(caught => {
        if (active) {
          setMessage({
            type: "error",
            text: caught instanceof Error ? caught.message : "报表配置加载失败",
          });
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  const selectedMetric = useMemo(
    () => metrics.find(metric => metric.key === query.metrics[0]) ?? metrics[0],
    [metrics, query.metrics],
  );

  const availableDimensions = useMemo(() => {
    if (!selectedMetric) return dimensions;
    const supported = new Set(selectedMetric.dimensions);
    return dimensions.filter(dimension => supported.has(dimension.key));
  }, [dimensions, selectedMetric]);

  function updateMetric(metricKey: string) {
    const metric = metrics.find(item => item.key === metricKey);
    const nextDimension = metric?.dimensions.includes(query.group_by[0])
      ? query.group_by[0]
      : metric?.dimensions[0] ?? "";
    setQuery(current => ({
      ...current,
      metrics: [metricKey],
      group_by: nextDimension ? [nextDimension] : [],
    }));
  }

  function updateDimension(dimensionKey: string) {
    setQuery(current => ({
      ...current,
      group_by: dimensionKey ? [dimensionKey] : [],
    }));
  }

  async function handleRunQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("query");
    setMessage(null);
    try {
      const response = await queryReport(organizationId, query);
      setResult(response);
    } catch (caught) {
      setMessage({
        type: "error",
        text: caught instanceof Error ? caught.message : "报表查询失败",
      });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSaveReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!result) {
      setMessage({ type: "error", text: "请先运行查询，再保存报表" });
      return;
    }
    setBusyKey("save");
    setMessage(null);
    try {
      const saved = await createSavedReport(organizationId, {
        name: reportName.trim() || "未命名报表",
        description: "由自助报表构建器创建",
        query,
        chart_type: "bar",
        visibility: "organization",
      });
      setSavedReports(current => [saved, ...current.filter(item => item.id !== saved.id)]);
      setActiveReport(saved);
      setReportName("");
      setMessage({ type: "success", text: "已保存报表" });
    } catch (caught) {
      setMessage({
        type: "error",
        text: caught instanceof Error ? caught.message : "保存报表失败",
      });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSnapshot() {
    const report = activeReport;
    if (!report) {
      setMessage({ type: "error", text: "请先保存一个报表" });
      return;
    }
    setBusyKey("snapshot");
    setMessage(null);
    try {
      const snapshot = await createReportSnapshot(organizationId, report.id);
      setLatestSnapshot(snapshot);
      setMessage({ type: "success", text: "快照已创建" });
    } catch (caught) {
      setMessage({
        type: "error",
        text: caught instanceof Error ? caught.message : "创建快照失败",
      });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleExport() {
    const report = activeReport;
    if (!report) {
      setMessage({ type: "error", text: "请先保存一个报表" });
      return;
    }
    setBusyKey("export");
    setMessage(null);
    try {
      const reportExport = await createReportExport(organizationId, report.id, "xlsx");
      setLatestExport(reportExport);
      setMessage({ type: "success", text: "导出已生成" });
    } catch (caught) {
      setMessage({
        type: "error",
        text: caught instanceof Error ? caught.message : "导出失败",
      });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSubscription() {
    const report = activeReport;
    if (!report) {
      setMessage({ type: "error", text: "请先保存一个报表" });
      return;
    }
    setBusyKey("subscription");
    setMessage(null);
    try {
      const subscription = await createReportSubscription(organizationId, report.id, {
        frequency: "monthly",
        cron: "0 9 1 * *",
        timezone: "Asia/Hong_Kong",
        recipients: ["finance@example.com"],
      });
      setLatestSubscription(subscription);
      setMessage({
        type: "success",
        text: `下次发送 ${formatUtcMinute(subscription.next_run_at)}`,
      });
    } catch (caught) {
      setMessage({
        type: "error",
        text: caught instanceof Error ? caught.message : "创建订阅失败",
      });
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="workspace-panel workspace-reports">
      <div className="workspace-section-heading">
        <span>指标、快照、导出与订阅</span>
        <h2>报表</h2>
        <p>
          通过统一指标口径查询支出、预算、节省和风险数据，保存为组织报表后可以创建不可变快照、生成短期下载导出，并安排月度发送。
        </p>
      </div>

      {message ? (
        <p
          aria-live="polite"
          className={
            message.type === "success"
              ? "workspace-reports-success"
              : "workspace-inline-error"
          }
        >
          {message.text}
        </p>
      ) : null}

      <section className="workspace-report-band">
        <div className="workspace-spend-title">
          <BarChart3 />
          <div>
            <h3>查询构建器</h3>
            <p>指标、分组和过滤都来自白名单定义；客户端不会提交任意 SQL。</p>
          </div>
        </div>
        {loading ? <p className="workspace-muted">正在加载报表配置...</p> : null}
        <form className="workspace-report-builder" onSubmit={handleRunQuery}>
          <label>
            <span>指标</span>
            <select
              disabled={metrics.length === 0}
              onChange={event => updateMetric(event.target.value)}
              value={query.metrics[0]}
            >
              {metrics.map(metric => (
                <option key={metric.key} value={metric.key}>
                  {metric.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>分组维度</span>
            <select
              disabled={availableDimensions.length === 0}
              onChange={event => updateDimension(event.target.value)}
              value={query.group_by[0] ?? ""}
            >
              {availableDimensions.map(dimension => (
                <option key={dimension.key} value={dimension.key}>
                  {dimension.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>开始日期</span>
            <input
              onChange={event =>
                setQuery(current => ({
                  ...current,
                  date_range: { ...current.date_range, start: event.target.value },
                }))
              }
              type="date"
              value={query.date_range.start}
            />
          </label>
          <label>
            <span>结束日期</span>
            <input
              onChange={event =>
                setQuery(current => ({
                  ...current,
                  date_range: { ...current.date_range, end: event.target.value },
                }))
              }
              type="date"
              value={query.date_range.end}
            />
          </label>
          <button disabled={busyKey === "query" || metrics.length === 0} type="submit">
            运行查询
          </button>
        </form>
      </section>

      <ReportResultTable
        dimensions={dimensions}
        metrics={metrics}
        result={result}
      />

      <section className="workspace-report-band">
        <div className="workspace-spend-title">
          <Save />
          <div>
            <h3>保存与分发</h3>
            <p>保存后的报表会成为快照、导出和订阅的权限锚点。</p>
          </div>
        </div>
        <form className="workspace-report-save" onSubmit={handleSaveReport}>
          <label>
            <span>报表名称</span>
            <input
              onChange={event => setReportName(event.target.value)}
              placeholder="例如 部门支出报表"
              required
              value={reportName}
            />
          </label>
          <button disabled={busyKey === "save" || !result} type="submit">
            保存报表
          </button>
        </form>

        <div className="workspace-report-actions">
          <button
            disabled={busyKey === "snapshot" || !activeReport}
            onClick={handleSnapshot}
            type="button"
          >
            <Camera />
            创建快照
          </button>
          <button
            disabled={busyKey === "export" || !activeReport}
            onClick={handleExport}
            type="button"
          >
            <Download />
            导出 XLSX
          </button>
          <button
            disabled={busyKey === "subscription" || !activeReport}
            onClick={handleSubscription}
            type="button"
          >
            <Send />
            创建月度订阅
          </button>
        </div>

        <div className="workspace-report-artifacts">
          {latestSnapshot ? <span>快照 {latestSnapshot.id}</span> : null}
          {latestExport ? <span>{latestExport.filename}</span> : null}
          {latestSubscription ? (
            <span>订阅计划 {formatUtcMinute(latestSubscription.next_run_at)}</span>
          ) : null}
        </div>
      </section>

      <section className="workspace-report-band">
        <div className="workspace-spend-title">
          <Save />
          <div>
            <h3>保存的报表</h3>
            <p>选择一个报表后，后续快照、导出和订阅会基于该报表执行。</p>
          </div>
        </div>
        {savedReports.length === 0 ? (
          <div className="workspace-empty">
            <h3>还没有保存报表</h3>
            <p>运行查询并保存后，这里会展示可复用的报表定义。</p>
          </div>
        ) : (
          <div className="workspace-report-list">
            {savedReports.map(report => (
              <button
                aria-pressed={activeReport?.id === report.id}
                key={report.id}
                onClick={() => setActiveReport(report)}
                type="button"
              >
                <strong>{report.name}</strong>
                <span>{report.chart_type} · {report.visibility}</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

function ReportResultTable({
  dimensions,
  metrics,
  result,
}: {
  dimensions: ReportDimensionItem[];
  metrics: ReportMetricDefinitionItem[];
  result: ReportQueryResult | null;
}) {
  if (!result) {
    return (
      <div className="workspace-empty">
        <h3>等待查询结果</h3>
        <p>选择指标和分组维度后运行查询，结果会以可导出的表格展示。</p>
      </div>
    );
  }

  const metricLookup = new Map(metrics.map(metric => [metric.key, metric]));
  const dimensionLookup = new Map(dimensions.map(dimension => [dimension.key, dimension.label]));
  return (
    <div className="workspace-table-wrap workspace-report-table">
      <table className="workspace-table">
        <thead>
          <tr>
            {result.group_by.map(dimension => (
              <th key={dimension}>{dimensionLookup.get(dimension) ?? dimension}</th>
            ))}
            {result.metrics.map(metric => (
              <th key={metric}>{metricLookup.get(metric)?.label ?? metric}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map(row => {
            const rowKey = [
              ...result.group_by.map(dimension => row.dimensions[dimension]),
              ...result.metrics.map(metric => row.metrics[metric]),
            ].join("|");
            return (
              <tr key={rowKey}>
                {result.group_by.map(dimension => (
                  <td key={dimension}>{row.dimensions[dimension] ?? ""}</td>
                ))}
                {result.metrics.map(metric => (
                  <td key={metric}>
                    {formatMetricValue(row.metrics[metric], metricLookup.get(metric))}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function formatMetricValue(
  rawValue: string,
  metric: ReportMetricDefinitionItem | undefined,
) {
  const numericValue = Number(rawValue);
  if (Number.isNaN(numericValue)) return rawValue;
  if (metric?.value_type === "money") return `$${numericValue.toFixed(2)}`;
  if (metric?.value_type === "percentage") return `${numericValue.toFixed(2)}%`;
  if (metric?.value_type === "duration") return `${numericValue.toFixed(1)} 天`;
  return numericValue.toLocaleString("zh-CN");
}

function formatUtcMinute(value: string) {
  const date = new Date(value);
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hour = String(date.getUTCHours()).padStart(2, "0");
  const minute = String(date.getUTCMinutes()).padStart(2, "0");
  return `${year}-${month}-${day} ${hour}:${minute} UTC`;
}
