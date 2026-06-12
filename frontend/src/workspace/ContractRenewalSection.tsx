import { type FormEvent, useEffect, useState } from "react";
import { CalendarClock, CheckCircle2, FileSignature } from "lucide-react";
import {
  createContract,
  listContracts,
  listRenewals,
  markContractVersionSigned,
  type ContractItem,
  type RenewalItem,
} from "../app/api";

export function ContractRenewalSection({ organizationId }: { organizationId: string }) {
  const [contracts, setContracts] = useState<ContractItem[]>([]);
  const [renewals, setRenewals] = useState<RenewalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [applicationName, setApplicationName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [amount, setAmount] = useState("");
  const [autoRenew, setAutoRenew] = useState(false);
  const [noticePeriodDays, setNoticePeriodDays] = useState("30");

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([listContracts(organizationId), listRenewals(organizationId)])
      .then(([contractResponse, renewalResponse]) => {
        if (!active) return;
        setContracts(contractResponse.items);
        setRenewals(renewalResponse.items);
        setError(null);
      })
      .catch(caught => {
        if (active) setError(caught instanceof Error ? caught.message : "合同与续订加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedAmount = Number(amount);
    const parsedNoticePeriod = Number(noticePeriodDays);
    if (
      !name.trim() ||
      !vendorName.trim() ||
      !ownerName.trim() ||
      !startDate ||
      !endDate ||
      Number.isNaN(parsedAmount) ||
      Number.isNaN(parsedNoticePeriod)
    ) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const bundle = await createContract(organizationId, {
        name: name.trim(),
        vendor_name: vendorName.trim(),
        application_name: applicationName.trim() || null,
        owner_name: ownerName.trim(),
        start_date: startDate,
        end_date: endDate,
        amount: parsedAmount,
        currency: "USD",
        billing_frequency: "yearly",
        auto_renew: autoRenew,
        notice_period_days: parsedNoticePeriod,
      });
      setContracts(current => [
        bundle.contract,
        ...current.filter(item => item.id !== bundle.contract.id),
      ]);
      setName("");
      setVendorName("");
      setApplicationName("");
      setOwnerName("");
      setStartDate("");
      setEndDate("");
      setAmount("");
      setAutoRenew(false);
      setNoticePeriodDays("30");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "合同保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleMarkSigned(contract: ContractItem) {
    if (!contract.current_version_id) return;
    setSaving(true);
    setError(null);
    try {
      const bundle = await markContractVersionSigned(
        organizationId,
        contract.id,
        contract.current_version_id,
      );
      setContracts(current =>
        current.map(item => (item.id === bundle.contract.id ? bundle.contract : item)),
      );
      const renewal = bundle.renewal;
      if (renewal) {
        setRenewals(current => [
          renewal,
          ...current.filter(item => item.id !== renewal.id),
        ]);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "合同签署状态更新失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-section-heading">
        <span>合同生命周期</span>
        <h2>合同续订</h2>
        <p>登记合同关键条款并锁定签署版本，系统会按合同结束日和通知期自动生成续订决策截止日。</p>
      </div>

      <form className="workspace-procurement-form" onSubmit={handleCreate}>
        <label>
          <span>合同名称</span>
          <input required value={name} onChange={event => setName(event.target.value)} />
        </label>
        <label>
          <span>供应商</span>
          <input
            required
            value={vendorName}
            onChange={event => setVendorName(event.target.value)}
          />
        </label>
        <label>
          <span>关联应用</span>
          <input
            value={applicationName}
            onChange={event => setApplicationName(event.target.value)}
          />
        </label>
        <label>
          <span>负责人</span>
          <input required value={ownerName} onChange={event => setOwnerName(event.target.value)} />
        </label>
        <label>
          <span>开始日期</span>
          <input
            required
            type="date"
            value={startDate}
            onChange={event => setStartDate(event.target.value)}
          />
        </label>
        <label>
          <span>结束日期</span>
          <input
            required
            type="date"
            value={endDate}
            onChange={event => setEndDate(event.target.value)}
          />
        </label>
        <label>
          <span>合同金额</span>
          <input
            min="0"
            required
            step="0.01"
            type="number"
            value={amount}
            onChange={event => setAmount(event.target.value)}
          />
        </label>
        <label>
          <span>通知期（天）</span>
          <input
            min="0"
            required
            type="number"
            value={noticePeriodDays}
            onChange={event => setNoticePeriodDays(event.target.value)}
          />
        </label>
        <label className="workspace-toggle">
          <input
            checked={autoRenew}
            type="checkbox"
            onChange={event => setAutoRenew(event.target.checked)}
          />
          <span>自动续订</span>
        </label>
        <button disabled={saving} type="submit">
          <FileSignature className="h-4 w-4" />
          保存合同
        </button>
      </form>

      {error && (
        <p aria-live="polite" className="workspace-inline-error">
          {error}
        </p>
      )}

      <div className="workspace-audit-layout">
        <div className="workspace-run-list">
          <h3>合同清单</h3>
          {loading ? <p className="workspace-muted">正在加载合同...</p> : null}
          {!loading && contracts.length === 0 ? (
            <div className="workspace-empty">
              <h3>还没有合同</h3>
              <p>先登记第一份合同，签署后即可自动进入续订日历。</p>
            </div>
          ) : null}
          {contracts.map(contract => (
            <article className="workspace-procurement-card" key={contract.id}>
              <div>
                <strong>{contract.name}</strong>
                <span>
                  {contract.vendor_name}
                  {contract.application_name ? ` · ${contract.application_name}` : ""}
                </span>
                <small>
                  {contract.owner_name} · {contractStatusLabel(contract.status)}
                </small>
              </div>
              {contract.status === "draft" ? (
                <button
                  disabled={saving || !contract.current_version_id}
                  onClick={() => handleMarkSigned(contract)}
                  type="button"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  标记已签署
                </button>
              ) : null}
            </article>
          ))}
        </div>

        <div className="workspace-audit-results">
          <h3>续订日历</h3>
          {loading ? <p className="workspace-muted">正在加载续订计划...</p> : null}
          {!loading && renewals.length === 0 ? (
            <div className="workspace-empty">
              <h3>暂无续订事项</h3>
              <p>合同标记为已签署后，续订日期和决策截止日会显示在这里。</p>
            </div>
          ) : null}
          {renewals.map(renewal => (
            <article key={renewal.id}>
              <CalendarClock className="h-5 w-5" />
              <div>
                <strong>续订决策截止</strong>
                <p>{renewal.decision_deadline}</p>
                <span>续订日期</span>
                <small>{renewal.renewal_date}</small>
                <small>
                  {renewal.owner_name} · {formatMoney(renewal.current_amount, renewal.currency)}
                </small>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function contractStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: "履约中",
    draft: "草稿",
    expired: "已到期",
    terminated: "已终止",
  };
  return labels[status] ?? status;
}

function formatMoney(value: number, currency: string): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}
