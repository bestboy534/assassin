import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BadgeDollarSign,
  CalendarCheck,
  GitBranch,
  Landmark,
  Tags,
  Upload,
} from "lucide-react";
import {
  createAccountingPeriod,
  createBudget,
  createBudgetCommitment,
  getBudgetSummary,
  importSpendTransactions,
  listAccountingPeriods,
  listBudgets,
  listSpendTransactions,
  listTransactionAnomalies,
  lockAccountingPeriod,
  setSpendTransactionSplits,
  updateSpendTransaction,
  type AccountingPeriodItem,
  type BudgetItem,
  type BudgetSummaryItem,
  type SpendTransactionItem,
  type TransactionAnomalyItem,
} from "../app/api";

type SplitDraft = {
  amount: string;
  department: string;
};

const emptySplit = (): SplitDraft => ({ amount: "", department: "" });

export function BudgetTransactionSection({
  organizationId,
}: {
  organizationId: string;
}) {
  const [budgets, setBudgets] = useState<BudgetItem[]>([]);
  const [summary, setSummary] = useState<BudgetSummaryItem | null>(null);
  const [transactions, setTransactions] = useState<SpendTransactionItem[]>([]);
  const [anomalies, setAnomalies] = useState<TransactionAnomalyItem[]>([]);
  const [period, setPeriod] = useState<AccountingPeriodItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [budgetName, setBudgetName] = useState("");
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [budgetDepartment, setBudgetDepartment] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [committedAmount, setCommittedAmount] = useState("");
  const [forecastAmount, setForecastAmount] = useState("");

  const [externalId, setExternalId] = useState("");
  const [transactionDate, setTransactionDate] = useState("");
  const [merchantName, setMerchantName] = useState("");
  const [transactionDescription, setTransactionDescription] = useState("");
  const [transactionAmount, setTransactionAmount] = useState("");
  const [transactionDepartment, setTransactionDepartment] = useState("");

  const [editingTransactionId, setEditingTransactionId] = useState<string | null>(null);
  const [splitDrafts, setSplitDrafts] = useState<[SplitDraft, SplitDraft]>([
    emptySplit(),
    emptySplit(),
  ]);

  const [periodName, setPeriodName] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");

  const activeBudget = budgets[0] ?? null;
  const openAnomalies = anomalies.filter(item => item.status === "open");
  const editingTransaction = useMemo(
    () => transactions.find(item => item.id === editingTransactionId) ?? null,
    [editingTransactionId, transactions],
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      listBudgets(organizationId),
      listSpendTransactions(organizationId),
      listTransactionAnomalies(organizationId),
      listAccountingPeriods(organizationId),
    ])
      .then(
        async ([
          budgetResponse,
          transactionResponse,
          anomalyResponse,
          periodResponse,
        ]) => {
        const firstBudget = budgetResponse.items[0];
        const budgetSummary = firstBudget
          ? await getBudgetSummary(organizationId, firstBudget.id)
          : null;
        if (!active) return;
        setBudgets(budgetResponse.items);
        setTransactions(transactionResponse.items);
        setAnomalies(anomalyResponse.items);
        setPeriod(periodResponse.items[0] ?? null);
        setSummary(budgetSummary);
        setError(null);
        },
      )
      .catch(caught => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "预算与交易加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  async function refreshBudgetSummary(budgetId: string) {
    const nextSummary = await getBudgetSummary(organizationId, budgetId);
    setSummary(nextSummary);
  }

  async function refreshAnomalies() {
    const response = await listTransactionAnomalies(organizationId);
    setAnomalies(response.items);
  }

  async function handleCreateBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const year = Number(fiscalYear);
    if (
      !budgetName.trim() ||
      !budgetDepartment.trim() ||
      !budgetAmount ||
      !Number.isInteger(year)
    ) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const budget = await createBudget(organizationId, {
        name: budgetName.trim(),
        fiscal_year: year,
        department: budgetDepartment.trim(),
        amount: budgetAmount,
        currency: "USD",
      });
      const commitments: Array<Promise<unknown>> = [];
      if (Number(committedAmount) > 0) {
        commitments.push(
          createBudgetCommitment(organizationId, budget.id, {
            commitment_type: "committed",
            amount: committedAmount,
            description: "已签署合同与采购承诺",
          }),
        );
      }
      if (Number(forecastAmount) > 0) {
        commitments.push(
          createBudgetCommitment(organizationId, budget.id, {
            commitment_type: "forecast",
            amount: forecastAmount,
            description: "预计发生的软件支出",
          }),
        );
      }
      await Promise.all(commitments);
      setBudgets(current => [budget, ...current.filter(item => item.id !== budget.id)]);
      await refreshBudgetSummary(budget.id);
      setBudgetName("");
      setBudgetDepartment("");
      setBudgetAmount("");
      setCommittedAmount("");
      setForecastAmount("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "预算保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleImportTransaction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !externalId.trim() ||
      !transactionDate ||
      !merchantName.trim() ||
      !transactionDescription.trim() ||
      !transactionAmount ||
      !transactionDepartment.trim()
    ) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const result = await importSpendTransactions(organizationId, {
        source_provider: "manual",
        source_account_id: "workspace-entry",
        rows: [
          {
            external_id: externalId.trim(),
            transaction_date: transactionDate,
            merchant_name: merchantName.trim(),
            description: transactionDescription.trim(),
            amount: transactionAmount,
            currency: "USD",
            department: transactionDepartment.trim(),
          },
        ],
      });
      setTransactions(current => [
        ...result.items,
        ...current.filter(
          item => !result.items.some(imported => imported.id === item.id),
        ),
      ]);
      if (activeBudget) await refreshBudgetSummary(activeBudget.id);
      await refreshAnomalies();
      setExternalId("");
      setTransactionDate("");
      setMerchantName("");
      setTransactionDescription("");
      setTransactionAmount("");
      setTransactionDepartment("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "交易导入失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleClassify(transaction: SpendTransactionItem) {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateSpendTransaction(organizationId, transaction.id, {
        category: "软件",
      });
      setTransactions(current =>
        current.map(item => (item.id === updated.id ? updated : item)),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "交易归类失败");
    } finally {
      setSaving(false);
    }
  }

  function beginSplit(transaction: SpendTransactionItem) {
    setEditingTransactionId(transaction.id);
    if (transaction.splits.length >= 2) {
      setSplitDrafts([
        {
          amount: transaction.splits[0].amount,
          department: transaction.splits[0].department,
        },
        {
          amount: transaction.splits[1].amount,
          department: transaction.splits[1].department,
        },
      ]);
      return;
    }
    setSplitDrafts([emptySplit(), emptySplit()]);
  }

  async function handleSaveSplits(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !editingTransaction ||
      splitDrafts.some(item => !item.amount || !item.department.trim())
    ) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await setSpendTransactionSplits(
        organizationId,
        editingTransaction.id,
        splitDrafts.map(item => ({
          amount: item.amount,
          department: item.department.trim(),
          category: editingTransaction.category ?? "软件",
        })),
      );
      setTransactions(current =>
        current.map(item => (item.id === updated.id ? updated : item)),
      );
      if (activeBudget) await refreshBudgetSummary(activeBudget.id);
      await refreshAnomalies();
      setEditingTransactionId(null);
      setSplitDrafts([emptySplit(), emptySplit()]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "交易拆分保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreatePeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!periodName.trim() || !periodStart || !periodEnd) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createAccountingPeriod(organizationId, {
        name: periodName.trim(),
        start_date: periodStart,
        end_date: periodEnd,
      });
      setPeriod(created);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "会计期间创建失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleLockPeriod() {
    if (!period) return;
    setSaving(true);
    setError(null);
    try {
      setPeriod(await lockAccountingPeriod(organizationId, period.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "期间锁定失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workspace-panel workspace-spend">
      <div className="workspace-section-heading">
        <span>支出控制</span>
        <h2>预算与交易</h2>
        <p>
          用预算、承诺、预测和真实交易构成同一套支出口径。交易可以人工归类和精确拆分，超支规则保留版本与证据，会计期间锁定后不可再改写。
        </p>
      </div>

      {error && (
        <p aria-live="polite" className="workspace-inline-error">
          {error}
        </p>
      )}

      <section className="workspace-spend-band">
        <div className="workspace-spend-title">
          <Landmark className="h-5 w-5" />
          <div>
            <h3>年度预算</h3>
            <p>按财年、部门和币种设置唯一预算，并区分承诺与预测。</p>
          </div>
        </div>
        <form className="workspace-spend-form" onSubmit={handleCreateBudget}>
          <label>
            <span>预算名称</span>
            <input
              required
              value={budgetName}
              onChange={event => setBudgetName(event.target.value)}
            />
          </label>
          <label>
            <span>财年</span>
            <input
              min="2000"
              required
              type="number"
              value={fiscalYear}
              onChange={event => setFiscalYear(event.target.value)}
            />
          </label>
          <label>
            <span>预算部门</span>
            <input
              required
              value={budgetDepartment}
              onChange={event => setBudgetDepartment(event.target.value)}
            />
          </label>
          <label>
            <span>预算金额</span>
            <input
              min="0.0001"
              required
              step="0.0001"
              type="number"
              value={budgetAmount}
              onChange={event => setBudgetAmount(event.target.value)}
            />
          </label>
          <label>
            <span>承诺金额</span>
            <input
              min="0"
              step="0.0001"
              type="number"
              value={committedAmount}
              onChange={event => setCommittedAmount(event.target.value)}
            />
          </label>
          <label>
            <span>预测金额</span>
            <input
              min="0"
              step="0.0001"
              type="number"
              value={forecastAmount}
              onChange={event => setForecastAmount(event.target.value)}
            />
          </label>
          <button disabled={saving} type="submit">
            <BadgeDollarSign className="h-4 w-4" />
            保存预算
          </button>
        </form>

        {activeBudget ? (
          <div className="workspace-budget-summary">
            <div className="workspace-budget-identity">
              <strong>{activeBudget.name}</strong>
              <span>
                {activeBudget.fiscal_year} · {activeBudget.department} ·{" "}
                {activeBudget.currency}
              </span>
            </div>
            {summary ? (
              <div className="workspace-budget-metrics">
                <BudgetMetric label="预算" value={summary.allocated} currency={summary.currency} />
                <BudgetMetric label="实际" value={summary.actual} currency={summary.currency} />
                <BudgetMetric
                  label="已承诺"
                  value={summary.committed}
                  currency={summary.currency}
                />
                <BudgetMetric
                  label="预测"
                  value={summary.forecast}
                  currency={summary.currency}
                />
                <BudgetMetric
                  emphasis
                  label="剩余"
                  value={summary.remaining}
                  currency={summary.currency}
                />
              </div>
            ) : null}
          </div>
        ) : !loading ? (
          <div className="workspace-empty">
            <h3>还没有预算</h3>
            <p>先建立当前财年的部门预算，再导入交易观察实际消耗与异常。</p>
          </div>
        ) : null}
      </section>

      <section className="workspace-spend-band">
        <div className="workspace-spend-title">
          <Upload className="h-5 w-5" />
          <div>
            <h3>交易导入与归类</h3>
            <p>外部交易 ID 用于防重；低置信度交易保留为未归类，等待人工确认。</p>
          </div>
        </div>
        <form className="workspace-spend-form" onSubmit={handleImportTransaction}>
          <label>
            <span>外部交易 ID</span>
            <input
              required
              value={externalId}
              onChange={event => setExternalId(event.target.value)}
            />
          </label>
          <label>
            <span>交易日期</span>
            <input
              required
              type="date"
              value={transactionDate}
              onChange={event => setTransactionDate(event.target.value)}
            />
          </label>
          <label>
            <span>商户</span>
            <input
              required
              value={merchantName}
              onChange={event => setMerchantName(event.target.value)}
            />
          </label>
          <label>
            <span>交易说明</span>
            <input
              required
              value={transactionDescription}
              onChange={event => setTransactionDescription(event.target.value)}
            />
          </label>
          <label>
            <span>交易金额</span>
            <input
              min="0.0001"
              required
              step="0.0001"
              type="number"
              value={transactionAmount}
              onChange={event => setTransactionAmount(event.target.value)}
            />
          </label>
          <label>
            <span>交易部门</span>
            <input
              required
              value={transactionDepartment}
              onChange={event => setTransactionDepartment(event.target.value)}
            />
          </label>
          <button disabled={saving} type="submit">
            <Upload className="h-4 w-4" />
            导入交易
          </button>
        </form>

        <div className="workspace-spend-list">
          {loading ? <p className="workspace-muted">正在加载交易...</p> : null}
          {!loading && transactions.length === 0 ? (
            <div className="workspace-empty">
              <h3>还没有交易</h3>
              <p>录入第一笔交易后，可以补充分类、部门拆分并检查预算异常。</p>
            </div>
          ) : null}
          {transactions.map(transaction => (
            <article key={transaction.id}>
              <div className="workspace-spend-transaction">
                <div>
                  <strong>{transaction.merchant_name}</strong>
                  <span>
                    {transaction.transaction_date} · {transaction.description}
                  </span>
                  <small>
                    {transaction.department} · {transaction.category ?? "未归类"}
                  </small>
                  <small>
                    {transaction.splits.length > 0
                      ? `${transaction.splits.length} 条拆分`
                      : "未拆分"}
                  </small>
                </div>
                <b>{formatMoney(transaction.amount, transaction.currency)}</b>
              </div>
              <div className="workspace-spend-actions">
                {transaction.category ? (
                  <span className="workspace-status-success">
                    <Tags className="h-4 w-4" />
                    已归类
                  </span>
                ) : (
                  <button
                    disabled={saving}
                    onClick={() => handleClassify(transaction)}
                    type="button"
                  >
                    归类为软件
                  </button>
                )}
                <button
                  disabled={saving}
                  onClick={() => beginSplit(transaction)}
                  type="button"
                >
                  <GitBranch className="h-4 w-4" />
                  编辑拆分
                </button>
              </div>
            </article>
          ))}
        </div>

        {editingTransaction ? (
          <form className="workspace-split-form" onSubmit={handleSaveSplits}>
            <div>
              <strong>拆分 {editingTransaction.merchant_name}</strong>
              <span>
                两条拆分金额之和必须等于{" "}
                {formatMoney(editingTransaction.amount, editingTransaction.currency)}
              </span>
            </div>
            {splitDrafts.map((draft, index) => (
              <div className="workspace-split-row" key={index}>
                <label>
                  <span>拆分金额 {index + 1}</span>
                  <input
                    min="0.0001"
                    required
                    step="0.0001"
                    type="number"
                    value={draft.amount}
                    onChange={event =>
                      setSplitDrafts(current => {
                        const next = [...current] as [SplitDraft, SplitDraft];
                        next[index] = { ...next[index], amount: event.target.value };
                        return next;
                      })
                    }
                  />
                </label>
                <label>
                  <span>拆分部门 {index + 1}</span>
                  <input
                    required
                    value={draft.department}
                    onChange={event =>
                      setSplitDrafts(current => {
                        const next = [...current] as [SplitDraft, SplitDraft];
                        next[index] = {
                          ...next[index],
                          department: event.target.value,
                        };
                        return next;
                      })
                    }
                  />
                </label>
              </div>
            ))}
            <button disabled={saving} type="submit">
              保存拆分
            </button>
          </form>
        ) : null}
      </section>

      <div className="workspace-spend-columns">
        <section className="workspace-spend-band">
          <div className="workspace-spend-title">
            <AlertTriangle className="h-5 w-5" />
            <div>
              <h3>异常与证据</h3>
              <p>每条异常保留规则版本、基线和观察值。</p>
            </div>
          </div>
          {openAnomalies.length === 0 ? (
            <div className="workspace-empty">
              <h3>暂无交易异常</h3>
              <p>当实际支出超过预算等规则命中时，异常会显示在这里。</p>
            </div>
          ) : (
            <div className="workspace-anomaly-list">
              {openAnomalies.map(anomaly => (
                <article key={anomaly.id}>
                  <AlertTriangle className="h-5 w-5" />
                  <div>
                    <strong>{anomalyLabel(anomaly.code)}</strong>
                    <p>{anomalyEvidence(anomaly)}</p>
                    <small>
                      基线 {formatMoney(anomaly.baseline_amount, "USD")} · 观察值{" "}
                      {formatMoney(anomaly.observed_amount, "USD")} ·{" "}
                      {anomaly.rule_version}
                    </small>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="workspace-spend-band">
          <div className="workspace-spend-title">
            <CalendarCheck className="h-5 w-5" />
            <div>
              <h3>会计期间</h3>
              <p>期间锁定前必须完成所有交易分类，锁定后禁止改写。</p>
            </div>
          </div>
          <form className="workspace-period-form" onSubmit={handleCreatePeriod}>
            <label>
              <span>期间名称</span>
              <input
                required
                value={periodName}
                onChange={event => setPeriodName(event.target.value)}
              />
            </label>
            <label>
              <span>期间开始</span>
              <input
                required
                type="date"
                value={periodStart}
                onChange={event => setPeriodStart(event.target.value)}
              />
            </label>
            <label>
              <span>期间结束</span>
              <input
                required
                type="date"
                value={periodEnd}
                onChange={event => setPeriodEnd(event.target.value)}
              />
            </label>
            <button disabled={saving} type="submit">
              创建期间
            </button>
          </form>
          {period ? (
            <div className="workspace-period-status">
              <div>
                <strong>{period.name}</strong>
                <span>
                  {period.start_date} 至 {period.end_date}
                </span>
              </div>
              {period.status === "locked" ? (
                <span className="workspace-status-success">
                  <CalendarCheck className="h-4 w-4" />
                  期间已锁定
                </span>
              ) : (
                <button disabled={saving} onClick={handleLockPeriod} type="button">
                  锁定期间
                </button>
              )}
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}

function BudgetMetric({
  currency,
  emphasis = false,
  label,
  value,
}: {
  currency: string;
  emphasis?: boolean;
  label: string;
  value: string;
}) {
  const className =
    emphasis && Number(value) < 0
      ? "is-negative"
      : emphasis
        ? "is-emphasis"
        : undefined;
  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{formatMoney(value, currency)}</strong>
    </div>
  );
}

function formatMoney(value: string, currency: string): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(Number(value));
}

function anomalyLabel(code: string): string {
  const labels: Record<string, string> = {
    budget_exceeded: "预算已超支",
  };
  return labels[code] ?? "交易异常";
}

function anomalyEvidence(anomaly: TransactionAnomalyItem): string {
  if (anomaly.code === "budget_exceeded") {
    return `实际支出 ${formatMoney(anomaly.observed_amount, "USD")} 已超过预算 ${formatMoney(anomaly.baseline_amount, "USD")}。`;
  }
  return anomaly.evidence;
}
