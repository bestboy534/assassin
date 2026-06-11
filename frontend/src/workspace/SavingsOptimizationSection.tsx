import { type FormEvent, useEffect, useState } from "react";
import {
  BadgeCheck,
  CircleDollarSign,
  ClipboardCheck,
  Lightbulb,
  Target,
} from "lucide-react";
import {
  confirmSavingsOpportunity,
  createOptimizationProject,
  createSavingsOpportunity,
  getSavingsSummary,
  listOptimizationProjects,
  listSavingsOpportunities,
  realizeSavings,
  verifySavings,
  type OptimizationProjectBundle,
  type SavingsOpportunityItem,
  type SavingsSummaryItem,
} from "../app/api";

type ProjectDraft = {
  owner: string;
  dueDate: string;
};

type RealizationDraft = {
  newMonthlyCost: string;
  effectiveDate: string;
  evidence: string;
};

const emptySummary: SavingsSummaryItem = {
  currency: "USD",
  estimated: "0.0000",
  realized: "0.0000",
  verified: "0.0000",
  cost_avoidance: "0.0000",
};

function money(value: string, currency = "USD") {
  const amount = Number(value).toFixed(2);
  return currency === "USD" ? `$${amount}` : `${currency} ${amount}`;
}

function categoryLabel(category: string) {
  const labels: Record<string, string> = {
    cancellation: "取消订阅",
    cost_avoidance: "成本规避",
    downgrade: "降级方案",
    negotiation: "议价优化",
    seat_recovery: "席位回收",
  };
  return labels[category] ?? category;
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    confirmed: "已确认",
    in_progress: "执行中",
    new: "待确认",
    realized: "已实现",
    verified: "已验证",
  };
  return labels[status] ?? status;
}

export function SavingsOptimizationSection({
  organizationId,
}: {
  organizationId: string;
}) {
  const [opportunities, setOpportunities] = useState<SavingsOpportunityItem[]>([]);
  const [projects, setProjects] = useState<OptimizationProjectBundle[]>([]);
  const [summary, setSummary] = useState<SavingsSummaryItem>(emptySummary);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [category, setCategory] =
    useState<"cancellation" | "downgrade" | "negotiation" | "seat_recovery" | "cost_avoidance">(
      "cancellation",
    );
  const [monthlyBaseline, setMonthlyBaseline] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [contractEnd, setContractEnd] = useState("");
  const [evidence, setEvidence] = useState("");
  const [projectDrafts, setProjectDrafts] = useState<Record<string, ProjectDraft>>({});
  const [realizationDrafts, setRealizationDrafts] = useState<
    Record<string, RealizationDraft>
  >({});
  const [verificationDrafts, setVerificationDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      listSavingsOpportunities(organizationId),
      listOptimizationProjects(organizationId),
      getSavingsSummary(organizationId),
    ])
      .then(([opportunityResponse, projectResponse, summaryResponse]) => {
        if (!active) return;
        setOpportunities(opportunityResponse.items);
        setProjects(projectResponse.items);
        setSummary(summaryResponse);
        setError(null);
      })
      .catch(caught => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "节省优化加载失败");
        }
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
    setBusyKey("create");
    setError(null);
    try {
      const created = await createSavingsOpportunity(organizationId, {
        source_type: "manual",
        source_id: `manual-${Date.now()}`,
        rule_version: "manual-v1",
        period_key: effectiveDate.slice(0, 7),
        title,
        department,
        category,
        monthly_baseline: monthlyBaseline,
        currency: "USD",
        effective_date: effectiveDate,
        contract_end: contractEnd || null,
        evidence,
      });
      setOpportunities(current => [
        created,
        ...current.filter(item => item.id !== created.id),
      ]);
      setTitle("");
      setDepartment("");
      setMonthlyBaseline("");
      setEffectiveDate("");
      setContractEnd("");
      setEvidence("");
      setSummary(await getSavingsSummary(organizationId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建节省机会失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleConfirm(opportunityId: string) {
    setBusyKey(`confirm-${opportunityId}`);
    try {
      const confirmed = await confirmSavingsOpportunity(organizationId, opportunityId);
      setOpportunities(current =>
        current.map(item => (item.id === confirmed.id ? confirmed : item)),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "确认机会失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleCreateProject(opportunityId: string) {
    const draft = projectDrafts[opportunityId];
    if (!draft?.owner || !draft.dueDate) return;
    setBusyKey(`project-${opportunityId}`);
    try {
      const bundle = await createOptimizationProject(organizationId, opportunityId, {
        owner_name: draft.owner,
        due_date: draft.dueDate,
      });
      setProjects(current => [
        bundle,
        ...current.filter(item => item.project.id !== bundle.project.id),
      ]);
      setOpportunities(current =>
        current.map(item =>
          item.id === opportunityId ? { ...item, status: "in_progress" } : item,
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建优化项目失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRealize(project: OptimizationProjectBundle) {
    const draft = realizationDrafts[project.project.id];
    if (!draft?.effectiveDate || !draft.evidence || draft.newMonthlyCost === "") return;
    setBusyKey(`realize-${project.project.id}`);
    try {
      const updated = await realizeSavings(organizationId, project.project.id, {
        action: "cancelled",
        effective_date: draft.effectiveDate,
        new_monthly_cost: draft.newMonthlyCost,
        evidence: draft.evidence,
      });
      setProjects(current =>
        current.map(item => (item.project.id === updated.project.id ? updated : item)),
      );
      setSummary(await getSavingsSummary(organizationId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "记录实际节省失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleVerify(project: OptimizationProjectBundle) {
    const evidenceReference = verificationDrafts[project.project.id]?.trim();
    if (!evidenceReference) return;
    setBusyKey(`verify-${project.project.id}`);
    try {
      const updated = await verifySavings(
        organizationId,
        project.project.id,
        evidenceReference
          .split(",")
          .map(item => item.trim())
          .filter(Boolean),
      );
      setProjects(current =>
        current.map(item => (item.project.id === updated.project.id ? updated : item)),
      );
      setSummary(await getSavingsSummary(organizationId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "验证正式节省失败");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="workspace-panel workspace-savings">
      <div className="workspace-section-heading">
        <span>从机会到正式入账</span>
        <h2>节省优化</h2>
        <p>
          将账单、合同和使用数据中的优化线索转成可执行项目。预计、已实现和已验证金额分别核算，只有附带后续证据的金额才计入正式节省。
        </p>
      </div>

      <div className="workspace-savings-metrics">
        <article>
          <Lightbulb />
          <span>预计节省</span>
          <strong>{money(summary.estimated, summary.currency)}</strong>
        </article>
        <article>
          <Target />
          <span>已实现</span>
          <strong>{money(summary.realized, summary.currency)}</strong>
        </article>
        <article className="is-verified">
          <BadgeCheck />
          <span>正式节省</span>
          <strong>{money(summary.verified, summary.currency)}</strong>
        </article>
        <article>
          <CircleDollarSign />
          <span>成本规避</span>
          <strong>{money(summary.cost_avoidance, summary.currency)}</strong>
        </article>
      </div>

      <section className="workspace-savings-band">
        <div className="workspace-spend-title">
          <Lightbulb />
          <div>
            <h3>登记节省机会</h3>
            <p>固定期限合同按剩余月份估算，最长采用 12 个月基线。</p>
          </div>
        </div>
        <form className="workspace-savings-form" onSubmit={handleCreate}>
          <label>
            <span>机会标题</span>
            <input required value={title} onChange={event => setTitle(event.target.value)} />
          </label>
          <label>
            <span>负责部门</span>
            <input
              required
              value={department}
              onChange={event => setDepartment(event.target.value)}
            />
          </label>
          <label>
            <span>机会类型</span>
            <select
              value={category}
              onChange={event => setCategory(event.target.value as typeof category)}
            >
              <option value="cancellation">取消订阅</option>
              <option value="downgrade">降级方案</option>
              <option value="negotiation">议价优化</option>
              <option value="seat_recovery">席位回收</option>
              <option value="cost_avoidance">成本规避</option>
            </select>
          </label>
          <label>
            <span>月度基线</span>
            <input
              min="0"
              required
              step="0.01"
              type="number"
              value={monthlyBaseline}
              onChange={event => setMonthlyBaseline(event.target.value)}
            />
          </label>
          <label>
            <span>生效日期</span>
            <input
              required
              type="date"
              value={effectiveDate}
              onChange={event => setEffectiveDate(event.target.value)}
            />
          </label>
          <label>
            <span>合同结束</span>
            <input
              type="date"
              value={contractEnd}
              onChange={event => setContractEnd(event.target.value)}
            />
          </label>
          <label className="is-wide">
            <span>发现证据</span>
            <textarea
              required
              value={evidence}
              onChange={event => setEvidence(event.target.value)}
            />
          </label>
          <button disabled={busyKey === "create"} type="submit">
            创建节省机会
          </button>
        </form>
      </section>

      {error ? <p className="workspace-inline-error">{error}</p> : null}

      <section className="workspace-savings-band">
        <div className="workspace-spend-title">
          <ClipboardCheck />
          <div>
            <h3>机会与执行项目</h3>
            <p>确认基线后分配负责人，完成动作并以交易、账单或合同证据验证结果。</p>
          </div>
        </div>
        {loading ? <p className="workspace-muted">正在加载节省机会...</p> : null}
        {!loading && opportunities.length === 0 ? (
          <div className="workspace-empty">
            <h3>还没有节省机会</h3>
            <p>可以手动登记，也可以从账单审计结果一键创建。</p>
          </div>
        ) : null}
        <div className="workspace-savings-list">
          {opportunities.map(opportunity => {
            const project = projects.find(
              item => item.project.opportunity_id === opportunity.id,
            );
            const projectDraft = projectDrafts[opportunity.id] ?? {
              owner: "",
              dueDate: "",
            };
            const realizationDraft = project
              ? realizationDrafts[project.project.id] ?? {
                  newMonthlyCost: "",
                  effectiveDate: "",
                  evidence: "",
                }
              : null;
            return (
              <article key={opportunity.id}>
                <header>
                  <div>
                    <span>{categoryLabel(opportunity.category)}</span>
                    <h4>{opportunity.title}</h4>
                    <p>{opportunity.department} · {opportunity.evidence}</p>
                  </div>
                  <div>
                    <strong>预计 {money(opportunity.estimated_amount, opportunity.currency)}</strong>
                    <span>{statusLabel(project?.project.status ?? opportunity.status)}</span>
                  </div>
                </header>

                {opportunity.status === "new" ? (
                  <button
                    disabled={busyKey === `confirm-${opportunity.id}`}
                    onClick={() => handleConfirm(opportunity.id)}
                    type="button"
                  >
                    确认机会
                  </button>
                ) : null}

                {opportunity.status === "confirmed" && !project ? (
                  <div className="workspace-savings-action">
                    <label>
                      <span>项目负责人</span>
                      <input
                        value={projectDraft.owner}
                        onChange={event =>
                          setProjectDrafts(current => ({
                            ...current,
                            [opportunity.id]: {
                              ...projectDraft,
                              owner: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <label>
                      <span>完成期限</span>
                      <input
                        type="date"
                        value={projectDraft.dueDate}
                        onChange={event =>
                          setProjectDrafts(current => ({
                            ...current,
                            [opportunity.id]: {
                              ...projectDraft,
                              dueDate: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <button
                      disabled={busyKey === `project-${opportunity.id}`}
                      onClick={() => handleCreateProject(opportunity.id)}
                      type="button"
                    >
                      创建优化项目
                    </button>
                  </div>
                ) : null}

                {project ? (
                  <div className="workspace-savings-project">
                    <div>
                      <strong>{project.project.owner_name}</strong>
                      <span>完成期限 {project.project.due_date}</span>
                    </div>
                    {project.tasks.map(task => (
                      <p key={task.id}>{task.title}</p>
                    ))}
                  </div>
                ) : null}

                {project && !project.result && realizationDraft ? (
                  <div className="workspace-savings-action">
                    <label>
                      <span>调整后月费</span>
                      <input
                        min="0"
                        step="0.01"
                        type="number"
                        value={realizationDraft.newMonthlyCost}
                        onChange={event =>
                          setRealizationDrafts(current => ({
                            ...current,
                            [project.project.id]: {
                              ...realizationDraft,
                              newMonthlyCost: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <label>
                      <span>执行日期</span>
                      <input
                        type="date"
                        value={realizationDraft.effectiveDate}
                        onChange={event =>
                          setRealizationDrafts(current => ({
                            ...current,
                            [project.project.id]: {
                              ...realizationDraft,
                              effectiveDate: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <label className="is-wide">
                      <span>执行证据</span>
                      <input
                        value={realizationDraft.evidence}
                        onChange={event =>
                          setRealizationDrafts(current => ({
                            ...current,
                            [project.project.id]: {
                              ...realizationDraft,
                              evidence: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <button
                      disabled={busyKey === `realize-${project.project.id}`}
                      onClick={() => handleRealize(project)}
                      type="button"
                    >
                      记录实际节省
                    </button>
                  </div>
                ) : null}

                {project?.result ? (
                  <div className="workspace-savings-result">
                    <strong>
                      已实现 {money(project.result.realized_amount, project.project.currency)}
                    </strong>
                    <span>{project.result.realization_evidence}</span>
                  </div>
                ) : null}

                {project?.result?.status === "realized" ? (
                  <div className="workspace-savings-action">
                    <label className="is-wide">
                      <span>验证证据</span>
                      <input
                        placeholder="例如 transaction:交易编号"
                        value={verificationDrafts[project.project.id] ?? ""}
                        onChange={event =>
                          setVerificationDrafts(current => ({
                            ...current,
                            [project.project.id]: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <button
                      disabled={busyKey === `verify-${project.project.id}`}
                      onClick={() => handleVerify(project)}
                      type="button"
                    >
                      验证正式节省
                    </button>
                  </div>
                ) : null}

                {project?.result?.status === "verified" ? (
                  <div className="workspace-savings-verified">
                    <BadgeCheck />
                    <strong>
                      正式节省 {money(project.result.verified_amount, project.project.currency)}
                    </strong>
                    <span>{project.result.evidence_references.join("，")}</span>
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
