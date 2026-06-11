import { ArrowRight, Check, CreditCard, Database, LockKeyhole, Server, ShieldCheck, TestTube2 } from "lucide-react";
import { Button } from "../../shared/components/Button";

const controls = [
  {
    icon: CreditCard,
    title: "虚拟卡与令牌化",
    body: "支付能力通过合规供应商提供，平台只展示掩码信息，不保存完整卡号或 CVV。",
  },
  {
    icon: Database,
    title: "数据隐私与最小化",
    body: "只处理提供服务所需的数据，敏感字段限制访问，并支持保留和删除策略。",
  },
  {
    icon: ShieldCheck,
    title: "SOC 2 控制框架",
    body: "围绕访问、安全、变更、监控和供应商管理建立可验证的控制与证据。",
  },
  {
    icon: Server,
    title: "基础设施保护",
    body: "传输和静态数据加密，生产访问最小化，关键服务具备备份、恢复和监控。",
  },
  {
    icon: TestTube2,
    title: "定期安全测试",
    body: "持续进行依赖扫描、配置检查、漏洞评估和受控渗透测试。",
  },
  {
    icon: LockKeyhole,
    title: "身份与访问",
    body: "支持基于角色的权限、多因素认证和企业单点登录规划，关键操作全程审计。",
  },
] as const;

export function SecurityPage() {
  return (
    <>
      <section className="official-product-hero security-hero">
        <div className="official-product-inner">
          <div className="official-product-copy">
            <span className="detail-badge"><ShieldCheck className="h-4 w-4" />安全承诺</span>
            <h1>始终认真守护你的安全</h1>
            <p>安全不是附加功能。平台从支付边界、数据访问、身份验证到审计流程，都按照企业级要求设计并持续验证。</p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Button href="/company/contact?topic=security">联系安全团队 <ArrowRight className="h-4 w-4" /></Button>
              <Button href="/privacy-policy" variant="secondary">查看隐私政策</Button>
            </div>
          </div>
          <div aria-label="安全中心界面示意" className="security-console">
            <div className="security-rings"><span><ShieldCheck className="h-14 w-14" /></span></div>
            <div className="security-panel">
              <small>安全状态</small><h3>核心控制运行正常</h3>
              {["多因素认证与访问控制", "传输与静态数据加密", "持续监控与审计日志"].map(item => (
                <div className="security-check" key={item}><Check className="h-4 w-4" /><span>{item}</span><strong>运行中</strong></div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="security-standards">
        <div>
          <p className="eyebrow">安全与合规</p>
          <h2>覆盖数据、支付、基础设施与人员访问</h2>
          <p className="mt-6 leading-8 text-slate-600">每项承诺都对应可执行控制、负责人和定期复核，不用模糊口号代替安全边界。</p>
        </div>
        <div className="security-standard-list">
          {["最小权限与职责分离", "数据加密和密钥管理", "供应商风险评估", "事件响应与恢复演练"].map(item => (
            <div key={item}><ShieldCheck className="h-5 w-5" /><strong>{item}</strong></div>
          ))}
        </div>
      </section>

      <section className="bg-[#f6fafb] py-24">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <p className="eyebrow">控制措施</p>
          <h2 className="section-title">安全能力进入产品和运营的每一层</h2>
          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {controls.map(item => (
              <article className="detail-card" key={item.title}>
                <span><item.icon className="h-5 w-5" /></span><h3>{item.title}</h3><p>{item.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
