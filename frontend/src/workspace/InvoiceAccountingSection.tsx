import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BookOpenCheck,
  CheckCircle2,
  FileSearch,
  Link2,
  RefreshCw,
  Send,
} from "lucide-react";
import {
  confirmInvoice,
  exportInvoice,
  extractInvoice,
  listAccountingMappings,
  listInvoices,
  matchInvoice,
  resolveInvoiceMapping,
  retryAccountingExport,
  updateInvoice,
  upsertAccountingMapping,
  type AccountingMappingItem,
  type InvoiceBundle,
  type ResolvedAccountingMapping,
} from "../app/api";

type ReviewDraft = {
  vendorName: string;
  invoiceNumber: string;
  invoiceDate: string;
  dueDate: string;
  subtotal: string;
  tax: string;
  total: string;
  purchaseOrderNumber: string;
  lineDescription: string;
  lineQuantity: string;
  lineUnitPrice: string;
  lineAmount: string;
  lineCategory: string;
};

const emptyReview: ReviewDraft = {
  vendorName: "",
  invoiceNumber: "",
  invoiceDate: "",
  dueDate: "",
  subtotal: "",
  tax: "",
  total: "",
  purchaseOrderNumber: "",
  lineDescription: "",
  lineQuantity: "1",
  lineUnitPrice: "",
  lineAmount: "",
  lineCategory: "software",
};

function reviewFromBundle(bundle: InvoiceBundle): ReviewDraft {
  const line = bundle.line_items[0];
  return {
    vendorName: bundle.invoice.vendor_name,
    invoiceNumber: bundle.invoice.invoice_number,
    invoiceDate: bundle.invoice.invoice_date,
    dueDate: bundle.invoice.due_date,
    subtotal: bundle.invoice.subtotal,
    tax: bundle.invoice.tax,
    total: bundle.invoice.total,
    purchaseOrderNumber: bundle.invoice.purchase_order_number,
    lineDescription: line?.description ?? "软件订阅",
    lineQuantity: line?.quantity ?? "1",
    lineUnitPrice: line?.unit_price ?? bundle.invoice.total,
    lineAmount: line?.amount ?? bundle.invoice.total,
    lineCategory: line?.category ?? "software",
  };
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    duplicate: "疑似重复",
    out_of_sync: "等待重新同步",
    ready: "字段已确认",
    review_required: "需要人工复核",
    synced: "已同步",
  };
  return labels[status] ?? status;
}

function scopeLabel(scope: string) {
  const labels: Record<string, string> = {
    application: "应用级映射",
    vendor: "供应商级映射",
    category: "类别级映射",
    default: "默认映射",
  };
  return labels[scope] ?? scope;
}

function exceptionLabel(code: string) {
  const labels: Record<string, string> = {
    amount_imbalance: "金额不平衡",
    missing_fields: "关键字段缺失",
  };
  return labels[code] ?? code;
}

function extractionEvidence(bundle: InvoiceBundle) {
  const field = bundle.extraction?.fields.total;
  if (!field || typeof field !== "object") return null;
  const record = field as {
    confidence?: string;
    evidence?: { page?: number; line?: number; text?: string };
  };
  return {
    confidence: record.confidence,
    page: record.evidence?.page,
    line: record.evidence?.line,
    text: record.evidence?.text,
  };
}

function randomKey(prefix: string) {
  return window.crypto.randomUUID?.() ?? `${prefix}-${Date.now()}`;
}

export function InvoiceAccountingSection({
  organizationId,
}: {
  organizationId: string;
}) {
  const [invoices, setInvoices] = useState<InvoiceBundle[]>([]);
  const [mappings, setMappings] = useState<AccountingMappingItem[]>([]);
  const [activeInvoiceId, setActiveInvoiceId] = useState<string | null>(null);
  const [resolvedMapping, setResolvedMapping] =
    useState<ResolvedAccountingMapping | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [filename, setFilename] = useState("invoice.txt");
  const [sourceText, setSourceText] = useState("");
  const [review, setReview] = useState<ReviewDraft>(emptyReview);
  const [accountCode, setAccountCode] = useState("");
  const [taxCode, setTaxCode] = useState("");
  const [costCenter, setCostCenter] = useState("");
  const [department, setDepartment] = useState("");
  const [project, setProject] = useState("");
  const [adjustedSubtotal, setAdjustedSubtotal] = useState("");
  const [adjustedTotal, setAdjustedTotal] = useState("");

  const activeBundle = useMemo(
    () => invoices.find(item => item.invoice.id === activeInvoiceId) ?? invoices[0] ?? null,
    [activeInvoiceId, invoices],
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([listInvoices(organizationId), listAccountingMappings(organizationId)])
      .then(([invoiceResponse, mappingResponse]) => {
        if (!active) return;
        setInvoices(invoiceResponse.items);
        setMappings(mappingResponse.items);
        setActiveInvoiceId(invoiceResponse.items[0]?.invoice.id ?? null);
        setError(null);
      })
      .catch(caught => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "发票与会计数据加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  useEffect(() => {
    if (!activeBundle) return;
    setReview(reviewFromBundle(activeBundle));
    setAdjustedSubtotal(activeBundle.invoice.subtotal);
    setAdjustedTotal(activeBundle.invoice.total);
    setResolvedMapping(null);
  }, [activeBundle?.invoice.id]);

  function replaceBundle(bundle: InvoiceBundle) {
    setInvoices(current => [
      bundle,
      ...current.filter(item => item.invoice.id !== bundle.invoice.id),
    ]);
    setActiveInvoiceId(bundle.invoice.id);
    setReview(reviewFromBundle(bundle));
    setAdjustedSubtotal(bundle.invoice.subtotal);
    setAdjustedTotal(bundle.invoice.total);
  }

  async function handleExtract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("extract");
    setError(null);
    setResolvedMapping(null);
    try {
      const key = randomKey("invoice");
      const bundle = await extractInvoice(
        organizationId,
        {
          source_type: "manual_text",
          external_id: key,
          filename,
          text: sourceText,
        },
        key,
      );
      replaceBundle(bundle);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发票提取失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeBundle) return;
    setBusyKey("confirm");
    setError(null);
    try {
      const bundle = await confirmInvoice(
        organizationId,
        activeBundle.invoice.id,
        {
          vendor_name: review.vendorName,
          invoice_number: review.invoiceNumber,
          invoice_date: review.invoiceDate,
          due_date: review.dueDate,
          currency: "USD",
          subtotal: review.subtotal,
          tax: review.tax,
          total: review.total,
          purchase_order_number: review.purchaseOrderNumber,
          line_items: [
            {
              description: review.lineDescription,
              quantity: review.lineQuantity,
              unit_price: review.lineUnitPrice,
              amount: review.lineAmount,
              category: review.lineCategory,
            },
          ],
        },
      );
      replaceBundle(bundle);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发票字段确认失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleMatch() {
    if (!activeBundle) return;
    setBusyKey("match");
    setError(null);
    try {
      replaceBundle(await matchInvoice(organizationId, activeBundle.invoice.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "业务记录匹配失败");
    } finally {
      setBusyKey(null);
    }
  }

  function mappingScope() {
    if (activeBundle?.match?.application_id) {
      return {
        scope_type: "application" as const,
        scope_value: activeBundle.match.application_id,
      };
    }
    if (activeBundle?.match?.vendor_id) {
      return {
        scope_type: "vendor" as const,
        scope_value: activeBundle.match.vendor_id,
      };
    }
    if (review.lineCategory) {
      return { scope_type: "category" as const, scope_value: review.lineCategory };
    }
    return { scope_type: "default" as const, scope_value: "*" };
  }

  async function handleSaveMapping(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeBundle) return;
    setBusyKey("mapping");
    setError(null);
    try {
      const mapping = await upsertAccountingMapping(organizationId, {
        ...mappingScope(),
        account_code: accountCode,
        tax_code: taxCode,
        cost_center: costCenter,
        department,
        project,
      });
      setMappings(current => [
        mapping,
        ...current.filter(item => item.id !== mapping.id),
      ]);
      setResolvedMapping(
        await resolveInvoiceMapping(organizationId, activeBundle.invoice.id),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "会计映射保存失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleExport() {
    if (!activeBundle) return;
    setBusyKey("export");
    setError(null);
    try {
      replaceBundle(
        await exportInvoice(
          organizationId,
          activeBundle.invoice.id,
          randomKey(`export-${activeBundle.invoice.id}`),
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发票导出失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleAdjustment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeBundle) return;
    setBusyKey("adjust");
    setError(null);
    try {
      replaceBundle(
        await updateInvoice(organizationId, activeBundle.invoice.id, {
          subtotal: adjustedSubtotal,
          tax: review.tax,
          total: adjustedTotal,
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发票调整保存失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRetry() {
    if (!activeBundle?.export) return;
    setBusyKey("retry");
    setError(null);
    try {
      const syncedExport = await retryAccountingExport(
        organizationId,
        activeBundle.export.id,
      );
      replaceBundle({
        ...activeBundle,
        invoice: { ...activeBundle.invoice, status: "synced" },
        export: syncedExport,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "重新同步失败");
    } finally {
      setBusyKey(null);
    }
  }

  const evidence = activeBundle ? extractionEvidence(activeBundle) : null;
  const matchPercent = activeBundle?.match
    ? Math.round(Number(activeBundle.match.confidence) * 100)
    : null;

  return (
    <section className="workspace-panel workspace-invoices">
      <div className="workspace-section-heading">
        <span>发票采集、复核与入账</span>
        <h2>发票与会计</h2>
        <p>
          从原始发票文本提取字段和证据，核对金额后关联供应商、合同、交易与应用，再按最具体的会计映射导出到 Sandbox 会计系统。
        </p>
      </div>

      <section className="workspace-invoice-band">
        <div className="workspace-spend-title">
          <FileSearch />
          <div>
            <h3>提取新发票</h3>
            <p>每次采集都会保留来源标识、文件名和字段证据，重复提交不会创建第二份记录。</p>
          </div>
        </div>
        <form className="workspace-invoice-source" onSubmit={handleExtract}>
          <label>
            <span>文件名</span>
            <input
              required
              value={filename}
              onChange={event => setFilename(event.target.value)}
            />
          </label>
          <label className="is-wide">
            <span>发票文本</span>
            <textarea
              required
              value={sourceText}
              onChange={event => setSourceText(event.target.value)}
              placeholder={"vendor: Notion Labs\ninvoice_number: INV-2026-001\nsubtotal: 100.00"}
            />
          </label>
          <button disabled={busyKey === "extract"} type="submit">
            <FileSearch />
            提取发票
          </button>
        </form>
      </section>

      {error ? <p className="workspace-inline-error">{error}</p> : null}
      {loading ? <p className="workspace-muted">正在加载发票与会计配置...</p> : null}

      {!loading && invoices.length === 0 ? (
        <div className="workspace-empty">
          <h3>还没有发票</h3>
          <p>在上方粘贴第一份发票文本，系统会创建待复核记录并保存提取证据。</p>
        </div>
      ) : null}

      {invoices.length > 0 ? (
        <div className="workspace-invoice-picker" aria-label="发票列表">
          {invoices.map(bundle => (
            <button
              aria-pressed={bundle.invoice.id === activeBundle?.invoice.id}
              key={bundle.invoice.id}
              onClick={() => setActiveInvoiceId(bundle.invoice.id)}
              type="button"
            >
              <strong>{bundle.invoice.vendor_name || "待识别供应商"}</strong>
              <span>
                {bundle.invoice.invoice_number || "待识别编号"} · {statusLabel(bundle.invoice.status)}
              </span>
            </button>
          ))}
        </div>
      ) : null}

      {activeBundle ? (
        <>
          <section className="workspace-invoice-band">
            <div className="workspace-invoice-state">
              <div>
                <span>当前发票</span>
                <strong>
                  {activeBundle.invoice.vendor_name} · {activeBundle.invoice.invoice_number}
                </strong>
              </div>
              <b className={`is-${activeBundle.invoice.status}`}>
                {statusLabel(activeBundle.invoice.status)}
              </b>
            </div>

            {activeBundle.invoice.exception_codes.length > 0 ? (
              <div className="workspace-invoice-exceptions">
                <AlertTriangle />
                <div>
                  <strong>需要处理的异常</strong>
                  <span>
                    {activeBundle.invoice.exception_codes.map(exceptionLabel).join("、")}
                  </span>
                </div>
              </div>
            ) : null}

            {evidence ? (
              <div className="workspace-invoice-evidence">
                <BookOpenCheck />
                <div>
                  <strong>提取证据</strong>
                  <span>
                    第 {evidence.page ?? 1} 页，第 {evidence.line ?? "-"} 行
                    {evidence.confidence ? ` · 置信度 ${Math.round(Number(evidence.confidence) * 100)}%` : ""}
                  </span>
                  {evidence.text ? <code>{evidence.text}</code> : null}
                </div>
              </div>
            ) : null}

            <form className="workspace-invoice-review" onSubmit={handleConfirm}>
              <label>
                <span>供应商名称</span>
                <input
                  required
                  value={review.vendorName}
                  onChange={event =>
                    setReview(current => ({ ...current, vendorName: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>发票编号</span>
                <input
                  required
                  value={review.invoiceNumber}
                  onChange={event =>
                    setReview(current => ({ ...current, invoiceNumber: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>开票日期</span>
                <input
                  required
                  type="date"
                  value={review.invoiceDate}
                  onChange={event =>
                    setReview(current => ({ ...current, invoiceDate: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>到期日期</span>
                <input
                  required
                  type="date"
                  value={review.dueDate}
                  onChange={event =>
                    setReview(current => ({ ...current, dueDate: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>小计</span>
                <input
                  required
                  step="0.01"
                  type="number"
                  value={review.subtotal}
                  onChange={event =>
                    setReview(current => ({ ...current, subtotal: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>税额</span>
                <input
                  required
                  step="0.01"
                  type="number"
                  value={review.tax}
                  onChange={event =>
                    setReview(current => ({ ...current, tax: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>总额</span>
                <input
                  required
                  step="0.01"
                  type="number"
                  value={review.total}
                  onChange={event =>
                    setReview(current => ({ ...current, total: event.target.value }))
                  }
                />
              </label>
              <label>
                <span>采购单号</span>
                <input
                  value={review.purchaseOrderNumber}
                  onChange={event =>
                    setReview(current => ({
                      ...current,
                      purchaseOrderNumber: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="is-wide">
                <span>行项目说明</span>
                <input
                  required
                  value={review.lineDescription}
                  onChange={event =>
                    setReview(current => ({
                      ...current,
                      lineDescription: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>数量</span>
                <input
                  required
                  step="0.01"
                  type="number"
                  value={review.lineQuantity}
                  onChange={event =>
                    setReview(current => ({
                      ...current,
                      lineQuantity: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>单价</span>
                <input
                  required
                  step="0.01"
                  type="number"
                  value={review.lineUnitPrice}
                  onChange={event =>
                    setReview(current => ({
                      ...current,
                      lineUnitPrice: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>行项目金额</span>
                <input
                  required
                  step="0.01"
                  type="number"
                  value={review.lineAmount}
                  onChange={event =>
                    setReview(current => ({
                      ...current,
                      lineAmount: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                <span>费用类别</span>
                <input
                  required
                  value={review.lineCategory}
                  onChange={event =>
                    setReview(current => ({
                      ...current,
                      lineCategory: event.target.value,
                    }))
                  }
                />
              </label>
              <button disabled={busyKey === "confirm"} type="submit">
                <CheckCircle2 />
                确认发票字段
              </button>
            </form>
          </section>

          <section className="workspace-invoice-band">
            <div className="workspace-spend-title">
              <Link2 />
              <div>
                <h3>业务关联</h3>
                <p>根据供应商、金额和已有业务记录关联合同、交易、应用与采购申请。</p>
              </div>
            </div>
            <div className="workspace-invoice-action">
              <button disabled={busyKey === "match"} onClick={handleMatch} type="button">
                自动匹配业务记录
              </button>
              {matchPercent !== null ? (
                <strong>匹配完成 · {matchPercent}%</strong>
              ) : (
                <span>尚未执行匹配</span>
              )}
            </div>
          </section>

          <section className="workspace-invoice-band">
            <div className="workspace-spend-title">
              <BookOpenCheck />
              <div>
                <h3>会计映射</h3>
                <p>优先使用应用映射，其次供应商、费用类别和组织默认值。</p>
              </div>
            </div>
            <form className="workspace-invoice-mapping" onSubmit={handleSaveMapping}>
              <label>
                <span>会计科目</span>
                <input
                  required
                  value={accountCode}
                  onChange={event => setAccountCode(event.target.value)}
                />
              </label>
              <label>
                <span>税码</span>
                <input
                  required
                  value={taxCode}
                  onChange={event => setTaxCode(event.target.value)}
                />
              </label>
              <label>
                <span>成本中心</span>
                <input
                  required
                  value={costCenter}
                  onChange={event => setCostCenter(event.target.value)}
                />
              </label>
              <label>
                <span>会计部门</span>
                <input
                  required
                  value={department}
                  onChange={event => setDepartment(event.target.value)}
                />
              </label>
              <label>
                <span>项目</span>
                <input value={project} onChange={event => setProject(event.target.value)} />
              </label>
              <button disabled={busyKey === "mapping"} type="submit">
                保存并应用映射
              </button>
            </form>
            {resolvedMapping ? (
              <p className="workspace-invoice-resolved">
                {scopeLabel(resolvedMapping.resolved_scope_type)} · 科目 {resolvedMapping.account_code}
              </p>
            ) : mappings.length > 0 ? (
              <p className="workspace-muted">当前组织已有 {mappings.length} 条会计映射。</p>
            ) : null}
          </section>

          <section className="workspace-invoice-band">
            <div className="workspace-spend-title">
              <Send />
              <div>
                <h3>会计系统同步</h3>
                <p>先在本地保存导出意图，再通过幂等请求写入外部会计系统。</p>
              </div>
            </div>
            <div className="workspace-invoice-sync">
              <button disabled={busyKey === "export"} onClick={handleExport} type="button">
                导出到会计系统
              </button>
              {activeBundle.export?.status === "synced" ? (
                <strong>已同步到 Sandbox 会计系统</strong>
              ) : null}
              {activeBundle.export?.status === "out_of_sync" ? (
                <strong className="is-warning">本地数据已变更，等待重新同步</strong>
              ) : null}
            </div>

            {activeBundle.export ? (
              <form className="workspace-invoice-adjustment" onSubmit={handleAdjustment}>
                <label>
                  <span>调整后小计</span>
                  <input
                    required
                    step="0.01"
                    type="number"
                    value={adjustedSubtotal}
                    onChange={event => setAdjustedSubtotal(event.target.value)}
                  />
                </label>
                <label>
                  <span>调整后总额</span>
                  <input
                    required
                    step="0.01"
                    type="number"
                    value={adjustedTotal}
                    onChange={event => setAdjustedTotal(event.target.value)}
                  />
                </label>
                <button disabled={busyKey === "adjust"} type="submit">
                  记录发票调整
                </button>
                {activeBundle.export.status === "out_of_sync" ? (
                  <button
                    className="is-secondary"
                    disabled={busyKey === "retry"}
                    onClick={handleRetry}
                    type="button"
                  >
                    <RefreshCw />
                    重新同步
                  </button>
                ) : null}
              </form>
            ) : null}
          </section>
        </>
      ) : null}
    </section>
  );
}
