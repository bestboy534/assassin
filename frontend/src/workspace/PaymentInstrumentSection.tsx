import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  Ban,
  CreditCard,
  LockOpen,
  LockKeyhole,
  ShieldCheck,
  SlidersHorizontal,
  Snowflake,
} from "lucide-react";
import {
  closePaymentInstrument,
  createPaymentInstrument,
  freezePaymentInstrument,
  listPaymentInstruments,
  listPurchaseRequests,
  updatePaymentInstrumentLimits,
  unfreezePaymentInstrument,
  type PaymentInstrumentBundle,
  type PurchaseRequestItem,
} from "../app/api";

type LimitDraft = {
  single: string;
  daily: string;
  monthly: string;
  total: string;
};

function money(value: string) {
  return `$${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    active: "可用",
    close_pending: "等待关闭确认",
    closed: "已关闭",
    freeze_pending: "等待冻结确认",
    frozen: "已冻结",
    unfreeze_pending: "等待解冻确认",
  };
  return labels[status] ?? status;
}

export function PaymentInstrumentSection({
  organizationId,
}: {
  organizationId: string;
}) {
  const [purchases, setPurchases] = useState<PurchaseRequestItem[]>([]);
  const [cards, setCards] = useState<PaymentInstrumentBundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmFreezeId, setConfirmFreezeId] = useState<string | null>(null);
  const [confirmCloseId, setConfirmCloseId] = useState<string | null>(null);
  const [limitDrafts, setLimitDrafts] = useState<Record<string, LimitDraft>>({});

  const [purchaseId, setPurchaseId] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [merchantLock, setMerchantLock] = useState("");
  const [singleLimit, setSingleLimit] = useState("");
  const [dailyLimit, setDailyLimit] = useState("");
  const [monthlyLimit, setMonthlyLimit] = useState("");
  const [totalLimit, setTotalLimit] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      listPurchaseRequests(organizationId),
      listPaymentInstruments(organizationId),
    ])
      .then(([purchaseResponse, cardResponse]) => {
        if (!active) return;
        setPurchases(purchaseResponse.items);
        setCards(cardResponse.items);
        setError(null);
      })
      .catch(caught => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "支付工具加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  const availablePurchases = useMemo(
    () =>
      purchases.filter(
        purchase =>
          purchase.status === "approved" &&
          !cards.some(card => card.instrument.purchase_request_id === purchase.id),
      ),
    [cards, purchases],
  );

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("create");
    setError(null);
    try {
      const created = await createPaymentInstrument(
        organizationId,
        {
          purchase_request_id: purchaseId,
          owner_name: ownerName,
          merchant_lock: merchantLock,
          currency: "USD",
          limits: {
            single: singleLimit,
            daily: dailyLimit,
            monthly: monthlyLimit,
            total: totalLimit,
          },
        },
        `card-${purchaseId}`,
      );
      setCards(current => [
        created,
        ...current.filter(item => item.instrument.id !== created.instrument.id),
      ]);
      setPurchaseId("");
      setOwnerName("");
      setMerchantLock("");
      setSingleLimit("");
      setDailyLimit("");
      setMonthlyLimit("");
      setTotalLimit("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建虚拟卡失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleUpdateLimits(card: PaymentInstrumentBundle) {
    const draft = limitDrafts[card.instrument.id] ?? card.limits;
    setBusyKey(`limits-${card.instrument.id}`);
    setError(null);
    try {
      const updated = await updatePaymentInstrumentLimits(
        organizationId,
        card.instrument.id,
        draft,
      );
      setCards(current =>
        current.map(item =>
          item.instrument.id === updated.instrument.id ? updated : item,
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "更新限额失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleFreeze(card: PaymentInstrumentBundle) {
    setBusyKey(`freeze-${card.instrument.id}`);
    setError(null);
    try {
      const updated = await freezePaymentInstrument(
        organizationId,
        card.instrument.id,
      );
      setCards(current =>
        current.map(item =>
          item.instrument.id === updated.instrument.id ? updated : item,
        ),
      );
      setConfirmFreezeId(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "冻结卡片失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleUnfreeze(card: PaymentInstrumentBundle) {
    setBusyKey(`unfreeze-${card.instrument.id}`);
    setError(null);
    try {
      const updated = await unfreezePaymentInstrument(
        organizationId,
        card.instrument.id,
      );
      setCards(current =>
        current.map(item =>
          item.instrument.id === updated.instrument.id ? updated : item,
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "解冻卡片失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleClose(card: PaymentInstrumentBundle) {
    setBusyKey(`close-${card.instrument.id}`);
    setError(null);
    try {
      const updated = await closePaymentInstrument(
        organizationId,
        card.instrument.id,
      );
      setCards(current =>
        current.map(item =>
          item.instrument.id === updated.instrument.id ? updated : item,
        ),
      );
      setConfirmCloseId(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "关闭卡片失败");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="workspace-panel workspace-payments">
      <div className="workspace-section-heading">
        <span>审批后支付，供应商最终确认</span>
        <h2>支付与虚拟卡</h2>
        <p>
          从已批准采购创建受控支付工具，只展示品牌与末四位。限额、商户锁定和冻结动作都会记录，最终卡状态以支付供应商回执为准。
        </p>
      </div>

      <div className="workspace-payment-notice">
        <ShieldCheck />
        <div>
          <strong>安全显示边界</strong>
          <span>系统不保存、不返回完整卡号或 CVV。本地环境使用明确标记的 Sandbox Provider。</span>
        </div>
      </div>

      <section className="workspace-payment-band">
        <div className="workspace-spend-title">
          <CreditCard />
          <div>
            <h3>创建受控虚拟卡</h3>
            <p>只有完成财务审批的采购可创建，一笔采购只对应一张支付工具。</p>
          </div>
        </div>
        <form className="workspace-payment-form" onSubmit={handleCreate}>
          <label>
            <span>已批准采购</span>
            <select
              required
              value={purchaseId}
              onChange={event => setPurchaseId(event.target.value)}
            >
              <option value="">选择采购申请</option>
              {availablePurchases.map(purchase => (
                <option key={purchase.id} value={purchase.id}>
                  {purchase.software_name} · {money(String(purchase.estimated_monthly_cost_usd))}/月
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>持卡负责人</span>
            <input
              required
              value={ownerName}
              onChange={event => setOwnerName(event.target.value)}
            />
          </label>
          <label>
            <span>限定商户</span>
            <input
              required
              value={merchantLock}
              onChange={event => setMerchantLock(event.target.value)}
            />
          </label>
          <label>
            <span>初始单笔限额</span>
            <input
              min="0.01"
              required
              step="0.01"
              type="number"
              value={singleLimit}
              onChange={event => setSingleLimit(event.target.value)}
            />
          </label>
          <label>
            <span>初始日限额</span>
            <input
              min="0.01"
              required
              step="0.01"
              type="number"
              value={dailyLimit}
              onChange={event => setDailyLimit(event.target.value)}
            />
          </label>
          <label>
            <span>初始月度限额</span>
            <input
              min="0.01"
              required
              step="0.01"
              type="number"
              value={monthlyLimit}
              onChange={event => setMonthlyLimit(event.target.value)}
            />
          </label>
          <label>
            <span>初始总限额</span>
            <input
              min="0.01"
              required
              step="0.01"
              type="number"
              value={totalLimit}
              onChange={event => setTotalLimit(event.target.value)}
            />
          </label>
          <button disabled={busyKey === "create"} type="submit">
            创建虚拟卡
          </button>
        </form>
        {!loading && availablePurchases.length === 0 && cards.length === 0 ? (
          <p className="workspace-muted">暂无可创建卡片的已批准采购，请先完成采购审批。</p>
        ) : null}
      </section>

      {error ? <p className="workspace-inline-error">{error}</p> : null}

      <section className="workspace-payment-band">
        <div className="workspace-spend-title">
          <LockKeyhole />
          <div>
            <h3>卡片与限额</h3>
            <p>冻结和关闭属于高风险操作，提交后先进入待确认状态。</p>
          </div>
        </div>
        {loading ? <p className="workspace-muted">正在加载支付工具...</p> : null}
        {!loading && cards.length === 0 ? (
          <div className="workspace-empty">
            <h3>还没有虚拟卡</h3>
            <p>完成采购审批后，可以在上方创建第一张 Sandbox 卡。</p>
          </div>
        ) : null}
        <div className="workspace-payment-list">
          {cards.map(card => {
            const draft = limitDrafts[card.instrument.id] ?? card.limits;
            return (
              <article key={card.instrument.id}>
                <header>
                  <div className="workspace-card-identity">
                    <CreditCard />
                    <div>
                      <span>{card.instrument.sandbox ? "Sandbox" : "Live"}</span>
                      <h4>{card.instrument.brand} •••• {card.instrument.last4}</h4>
                      <p>{card.instrument.owner_name} · {card.instrument.department}</p>
                    </div>
                  </div>
                  <div className={`workspace-payment-status is-${card.instrument.status}`}>
                    {statusLabel(card.instrument.status)}
                  </div>
                </header>

                <div className="workspace-payment-guardrails">
                  <div>
                    <span>限定商户</span>
                    <strong>{card.instrument.merchant_lock}</strong>
                  </div>
                  <div>
                    <span>单笔</span>
                    <strong>{money(card.limits.single)}</strong>
                  </div>
                  <div>
                    <span>日限额</span>
                    <strong>{money(card.limits.daily)}</strong>
                  </div>
                  <div>
                    <span>月度</span>
                    <strong>{money(card.limits.monthly)}/月</strong>
                  </div>
                  <div>
                    <span>总限额</span>
                    <strong>{money(card.limits.total)}</strong>
                  </div>
                </div>

                {["active", "frozen"].includes(card.instrument.status) ? (
                  <div className="workspace-payment-limits">
                    <div className="workspace-payment-limits-title">
                      <SlidersHorizontal />
                      <strong>修改限额</strong>
                    </div>
                    <label>
                      <span>单笔限额</span>
                      <input
                        type="number"
                        value={draft.single}
                        onChange={event =>
                          setLimitDrafts(current => ({
                            ...current,
                            [card.instrument.id]: {
                              ...draft,
                              single: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <label>
                      <span>日限额</span>
                      <input
                        type="number"
                        value={draft.daily}
                        onChange={event =>
                          setLimitDrafts(current => ({
                            ...current,
                            [card.instrument.id]: {
                              ...draft,
                              daily: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <label>
                      <span>月度限额</span>
                      <input
                        type="number"
                        value={draft.monthly}
                        onChange={event =>
                          setLimitDrafts(current => ({
                            ...current,
                            [card.instrument.id]: {
                              ...draft,
                              monthly: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <label>
                      <span>总限额</span>
                      <input
                        type="number"
                        value={draft.total}
                        onChange={event =>
                          setLimitDrafts(current => ({
                            ...current,
                            [card.instrument.id]: {
                              ...draft,
                              total: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <button
                      disabled={busyKey === `limits-${card.instrument.id}`}
                      onClick={() => handleUpdateLimits(card)}
                      type="button"
                    >
                      更新限额
                    </button>
                  </div>
                ) : null}

                {["active", "frozen"].includes(card.instrument.status) ? (
                  <div className="workspace-payment-risk-action">
                    {card.instrument.status === "active" ? (
                      confirmFreezeId === card.instrument.id ? (
                        <div>
                          <span>冻结后交易将被阻止，需等待供应商确认。</span>
                          <button
                            disabled={busyKey === `freeze-${card.instrument.id}`}
                            onClick={() => handleFreeze(card)}
                            type="button"
                          >
                            <Snowflake />
                            确认冻结
                          </button>
                          <button
                            onClick={() => setConfirmFreezeId(null)}
                            type="button"
                          >
                            取消
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmFreezeId(card.instrument.id)}
                          type="button"
                        >
                          <Snowflake />
                          冻结卡片
                        </button>
                      )
                    ) : (
                      <button
                        disabled={busyKey === `unfreeze-${card.instrument.id}`}
                        onClick={() => handleUnfreeze(card)}
                        type="button"
                      >
                        <LockOpen />
                        解冻卡片
                      </button>
                    )}
                    {confirmCloseId === card.instrument.id ? (
                      <div>
                        <span>关闭后无法恢复，且后续交易将被拒绝。</span>
                        <button
                          disabled={busyKey === `close-${card.instrument.id}`}
                          onClick={() => handleClose(card)}
                          type="button"
                        >
                          <Ban />
                          确认关闭
                        </button>
                        <button
                          onClick={() => setConfirmCloseId(null)}
                          type="button"
                        >
                          取消
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmCloseId(card.instrument.id)}
                        type="button"
                      >
                        <Ban />
                        关闭卡片
                      </button>
                    )}
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
