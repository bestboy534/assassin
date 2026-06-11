import { type FormEvent, useEffect, useState } from "react";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  ShieldCheck,
} from "lucide-react";
import {
  acceptRiskFinding,
  createVendor,
  createVendorAssessment,
  getLatestVendorAssessment,
  listRiskFindings,
  listVendors,
  type RiskFindingItem,
  type VendorAssessmentItem,
  type VendorItem,
} from "../app/api";

type FinancialStability = "strong" | "medium" | "weak";
type ServiceCriticality = "low" | "medium" | "high";

export function VendorRiskSection({ organizationId }: { organizationId: string }) {
  const [vendors, setVendors] = useState<VendorItem[]>([]);
  const [findings, setFindings] = useState<RiskFindingItem[]>([]);
  const [latestAssessment, setLatestAssessment] = useState<VendorAssessmentItem | null>(null);
  const [selectedVendorId, setSelectedVendorId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [category, setCategory] = useState("");
  const [businessOwner, setBusinessOwner] = useState("");
  const [riskOwner, setRiskOwner] = useState("");
  const [hasSoc2, setHasSoc2] = useState(false);
  const [hasIso27001, setHasIso27001] = useState(false);
  const [hasDpa, setHasDpa] = useState(false);
  const [supportsSso, setSupportsSso] = useState(false);
  const [hasIncidentResponse, setHasIncidentResponse] = useState(false);
  const [storesSensitiveData, setStoresSensitiveData] = useState(false);
  const [financialStability, setFinancialStability] =
    useState<FinancialStability>("weak");
  const [serviceCriticality, setServiceCriticality] =
    useState<ServiceCriticality>("high");
  const [acceptanceReason, setAcceptanceReason] = useState("");
  const [acceptanceExpiresAt, setAcceptanceExpiresAt] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([listVendors(organizationId), listRiskFindings(organizationId)])
      .then(async ([vendorResponse, findingResponse]) => {
        const firstVendor = vendorResponse.items[0];
        const latest = firstVendor
          ? await getLatestVendorAssessment(organizationId, firstVendor.id)
          : { item: null };
        if (!active) return;
        setVendors(vendorResponse.items);
        setFindings(findingResponse.items);
        setSelectedVendorId(firstVendor?.id ?? null);
        setLatestAssessment(latest.item?.assessment ?? null);
        setError(null);
      })
      .catch(caught => {
        if (active) setError(caught instanceof Error ? caught.message : "供应商风险加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [organizationId]);

  async function handleCreateVendor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !category.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const vendor = await createVendor(organizationId, {
        name: name.trim(),
        domain: domain.trim() || null,
        country_code: countryCode.trim() || null,
        category: category.trim(),
        business_owner: businessOwner.trim() || null,
        risk_owner: riskOwner.trim() || null,
      });
      setVendors(current => [vendor, ...current.filter(item => item.id !== vendor.id)]);
      setName("");
      setDomain("");
      setCountryCode("");
      setCategory("");
      setBusinessOwner("");
      setRiskOwner("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "供应商保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedVendorId) return;
    setSaving(true);
    setError(null);
    try {
      const bundle = await createVendorAssessment(organizationId, selectedVendorId, {
        questionnaire_version: 1,
        has_soc2: hasSoc2,
        has_iso27001: hasIso27001,
        has_dpa: hasDpa,
        supports_sso: supportsSso,
        has_incident_response: hasIncidentResponse,
        financial_stability: financialStability,
        service_criticality: serviceCriticality,
        stores_sensitive_data: storesSensitiveData,
      });
      setLatestAssessment(bundle.assessment);
      setFindings(current => [
        ...bundle.findings,
        ...current.filter(
          item => !bundle.findings.some(created => created.id === item.id),
        ),
      ]);
      setVendors(current =>
        current.map(item =>
          item.id === selectedVendorId
            ? {
                ...item,
                overall_risk_score: bundle.assessment.total_score,
                risk_level: riskLevel(bundle.assessment.total_score),
              }
            : item,
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "风险评估提交失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleSelectVendor(vendorId: string) {
    setSelectedVendorId(vendorId);
    setLatestAssessment(null);
    setError(null);
    try {
      const latest = await getLatestVendorAssessment(organizationId, vendorId);
      setLatestAssessment(latest.item?.assessment ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "最近评估加载失败");
    }
  }

  async function handleAcceptFinding(finding: RiskFindingItem) {
    if (!acceptanceReason.trim() || !acceptanceExpiresAt) return;
    setSaving(true);
    setError(null);
    try {
      const accepted = await acceptRiskFinding(organizationId, finding.id, {
        reason: acceptanceReason.trim(),
        expires_at: acceptanceExpiresAt,
        risk_owner: finding.owner_name,
      });
      setFindings(current =>
        current.map(item => (item.id === accepted.id ? accepted : item)),
      );
      setAcceptanceReason("");
      setAcceptanceExpiresAt("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "风险接受失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-section-heading">
        <span>第三方治理</span>
        <h2>供应商风险</h2>
        <p>统一维护供应商主档，以固定版本规则评估安全、隐私、财务、运营和合规风险，并记录有期限的风险接受。</p>
      </div>

      <form className="workspace-procurement-form" onSubmit={handleCreateVendor}>
        <label>
          <span>供应商名称</span>
          <input required value={name} onChange={event => setName(event.target.value)} />
        </label>
        <label>
          <span>官网域名</span>
          <input value={domain} onChange={event => setDomain(event.target.value)} />
        </label>
        <label>
          <span>注册地</span>
          <input value={countryCode} onChange={event => setCountryCode(event.target.value)} />
        </label>
        <label>
          <span>类别</span>
          <input required value={category} onChange={event => setCategory(event.target.value)} />
        </label>
        <label>
          <span>业务负责人</span>
          <input
            value={businessOwner}
            onChange={event => setBusinessOwner(event.target.value)}
          />
        </label>
        <label>
          <span>风险负责人</span>
          <input value={riskOwner} onChange={event => setRiskOwner(event.target.value)} />
        </label>
        <button disabled={saving} type="submit">
          <Building2 className="h-4 w-4" />
          保存供应商
        </button>
      </form>

      {error && (
        <p aria-live="polite" className="workspace-inline-error">
          {error}
        </p>
      )}

      <div className="workspace-audit-layout">
        <div className="workspace-run-list">
          <h3>供应商主档</h3>
          {loading ? <p className="workspace-muted">正在加载供应商...</p> : null}
          {!loading && vendors.length === 0 ? (
            <div className="workspace-empty">
              <h3>还没有供应商</h3>
              <p>先登记供应商，再发起风险评估。</p>
            </div>
          ) : null}
          {vendors.map(vendor => (
            <article className="workspace-procurement-card" key={vendor.id}>
              <div>
                <strong>{vendor.name}</strong>
                <span>
                  {vendor.category}
                  {vendor.domain ? ` · ${vendor.domain}` : ""}
                </span>
                <small>
                  {vendor.risk_owner ?? "风险负责人未分配"} ·{" "}
                  {vendor.overall_risk_score === null
                    ? "待评估"
                    : `风险分 ${vendor.overall_risk_score}`}
                </small>
              </div>
              <button
                disabled={saving}
                onClick={() => handleSelectVendor(vendor.id)}
                type="button"
              >
                发起风险评估
              </button>
            </article>
          ))}
        </div>

        <div className="workspace-audit-results">
          <h3>可解释评估</h3>
          {!selectedVendorId ? (
            <div className="workspace-empty">
              <h3>选择一个供应商</h3>
              <p>从左侧主档发起评估，系统会展示每个风险维度的原因。</p>
            </div>
          ) : (
            <form className="workspace-risk-assessment" onSubmit={handleAssessment}>
              <div className="workspace-risk-checks">
                <RiskCheckbox checked={hasSoc2} label="SOC 2" onChange={setHasSoc2} />
                <RiskCheckbox
                  checked={hasIso27001}
                  label="ISO 27001"
                  onChange={setHasIso27001}
                />
                <RiskCheckbox checked={hasDpa} label="数据处理协议" onChange={setHasDpa} />
                <RiskCheckbox
                  checked={supportsSso}
                  label="企业单点登录"
                  onChange={setSupportsSso}
                />
                <RiskCheckbox
                  checked={hasIncidentResponse}
                  label="事件响应机制"
                  onChange={setHasIncidentResponse}
                />
                <RiskCheckbox
                  checked={storesSensitiveData}
                  label="处理敏感数据"
                  onChange={setStoresSensitiveData}
                />
              </div>
              <label>
                <span>财务稳定性</span>
                <select
                  value={financialStability}
                  onChange={event =>
                    setFinancialStability(event.target.value as FinancialStability)
                  }
                >
                  <option value="strong">稳健</option>
                  <option value="medium">一般</option>
                  <option value="weak">较弱</option>
                </select>
              </label>
              <label>
                <span>服务关键性</span>
                <select
                  value={serviceCriticality}
                  onChange={event =>
                    setServiceCriticality(event.target.value as ServiceCriticality)
                  }
                >
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                </select>
              </label>
              <button disabled={saving} type="submit">
                <ClipboardCheck className="h-4 w-4" />
                提交评估
              </button>
            </form>
          )}

          {latestAssessment ? (
            <div className="workspace-risk-result">
              <div className="workspace-risk-score">
                <ShieldCheck className="h-5 w-5" />
                <strong>风险总分 {latestAssessment.total_score}</strong>
                <span>{latestAssessment.rule_version}</span>
              </div>
              <div className="workspace-risk-dimensions">
                {Object.entries(latestAssessment.dimensions).map(([dimension, result]) => (
                  <article key={dimension}>
                    <strong>{riskDimensionLabel(dimension)}</strong>
                    <b>{result.score}</b>
                    <p>{result.reasons.join("；") || "未发现显著风险"}</p>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="workspace-risk-findings">
        <div>
          <h3>风险发现</h3>
          <p>风险接受必须填写理由和到期日；到期后应重新评估。</p>
        </div>
        <div className="workspace-risk-acceptance">
          <label>
            <span>接受理由</span>
            <input
              value={acceptanceReason}
              onChange={event => setAcceptanceReason(event.target.value)}
            />
          </label>
          <label>
            <span>接受到期日</span>
            <input
              type="date"
              value={acceptanceExpiresAt}
              onChange={event => setAcceptanceExpiresAt(event.target.value)}
            />
          </label>
        </div>
        {findings.length === 0 ? (
          <div className="workspace-empty">
            <h3>暂无风险发现</h3>
            <p>完成供应商评估后，高风险维度会显示在这里。</p>
          </div>
        ) : null}
        {findings.map(finding => (
          <article className="workspace-risk-finding" key={finding.id}>
            <AlertTriangle className="h-5 w-5" />
            <div>
              <strong>{riskDimensionLabel(finding.dimension)}风险需要处理</strong>
              <p>{finding.description}</p>
              <small>
                {severityLabel(finding.severity)} · {finding.owner_name} · 截止{" "}
                {finding.due_date}
              </small>
            </div>
            {finding.status === "accepted" ? (
              <span className="workspace-status-success">
                <CheckCircle2 className="h-4 w-4" />
                已接受
              </span>
            ) : (
              <button
                disabled={saving || !acceptanceReason.trim() || !acceptanceExpiresAt}
                onClick={() => handleAcceptFinding(finding)}
                type="button"
              >
                接受风险
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function RiskCheckbox({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="workspace-toggle">
      <input
        checked={checked}
        type="checkbox"
        onChange={event => onChange(event.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}

function riskDimensionLabel(dimension: string): string {
  const labels: Record<string, string> = {
    security: "安全",
    privacy: "隐私",
    financial: "财务",
    operational: "运营",
    compliance: "合规",
  };
  return labels[dimension] ?? dimension;
}

function severityLabel(severity: string): string {
  const labels: Record<string, string> = {
    critical: "严重",
    high: "高风险",
    medium: "中风险",
    low: "低风险",
  };
  return labels[severity] ?? severity;
}

function riskLevel(score: number): string {
  if (score >= 75) return "high";
  if (score >= 45) return "medium";
  return "low";
}
