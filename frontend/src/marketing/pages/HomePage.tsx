import {
  ArrowRight,
  BarChart3,
  Check,
  CreditCard,
  FileCheck2,
  ReceiptText,
  ShieldCheck,
  TrendingDown,
} from "lucide-react";
import { Button } from "../../shared/components/Button";

const apps = [
  ["协作工具", "产品团队", "¥28,000", "96%"],
  ["AI 平台", "数据团队", "¥175,000", "61%"],
  ["人事系统", "人事团队", "¥7,200", "88%"],
  ["设计套件", "创意团队", "¥21,400", "18%"],
] as const;

const capabilities = [
  {
    icon: FileCheck2,
    title: "审批与采购",
    body: "让业务、财务、IT 和安全团队在同一流程里做出采购决定。",
    to: "/solutions/software-approvals-and-purchasing",
  },
  {
    icon: CreditCard,
    title: "软件支付",
    body: "为每个供应商设置独立付款方式、预算和扣款规则。",
    to: "/solutions/software-payments",
  },
  {
    icon: ReceiptText,
    title: "会计自动化",
    body: "把付款、收据、发票和会计字段自动关联起来。",
    to: "/solutions/accounting-automation",
  },
  {
    icon: TrendingDown,
    title: "支出优化",
    body: "在续订之前发现低使用率、重复工具和无人负责的应用。",
    to: "/solutions/software-spend-optimization",
  },
] as const;

export function HomePage() {
  return (
    <>
      <section className="hero relative overflow-hidden bg-[#232765] text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_15%,rgba(74,213,221,0.22),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0))]" />
        <div className="relative mx-auto max-w-7xl px-5 pb-24 pt-20 text-center lg:px-8 lg:pb-32">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/18 bg-white/7 px-4 py-2 text-sm font-bold text-white/88">
            <ShieldCheck className="h-4 w-4 text-[#cafbff]" />
            面向财务、采购与 IT 团队
          </div>
          <h1 className="mx-auto mt-8 max-w-5xl text-balance text-5xl font-extrabold leading-[0.98] tracking-normal md:text-7xl lg:text-8xl">
            建立战略性软件采购流程
          </h1>
          <p className="mx-auto mt-7 max-w-3xl text-balance text-lg font-medium leading-8 text-white/76 md:text-xl">
            看清每一款 SaaS 和 AI 工具，连接申请、付款、发票、使用率与续订，在一个财务优先的平台控制软件全生命周期。
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button href="/signup">
              开始使用 <ArrowRight className="h-4 w-4" />
            </Button>
            <Button href="/book-a-demo" variant="secondary">
              预约演示
            </Button>
          </div>

          <div className="hero-dashboard mx-auto mt-16 w-full max-w-6xl">
            <div className="dashboard-shell">
              <aside aria-hidden="true" className="dashboard-sidebar">
                {["总览", "应用目录", "采购", "支出", "报表", "合规"].map((item, index) => (
                  <div className={`sidebar-item ${index === 1 ? "active" : ""}`} key={item}>
                    <span />
                    <strong>{item}</strong>
                  </div>
                ))}
                <div className="low-usage">
                  <strong>低使用率提醒</strong>
                  <p>设计套件使用率降至 18%，请在续订前检查席位。</p>
                </div>
              </aside>
              <div className="dashboard-main">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="account-select">人民币账户</div>
                    <h3>应用目录</h3>
                  </div>
                  <a className="add-app" href="/solutions/application-directory">查看全部应用</a>
                </div>
                <div className="notice">
                  <ShieldCheck className="h-4 w-4" />
                  <span>所有应用都已关联负责人、预算和续订日期。</span>
                </div>
                <div className="app-table">
                  <div className="table-head">
                    <span>名称</span>
                    <span>负责人</span>
                    <span>本月支出</span>
                    <span>使用率</span>
                    <span>状态</span>
                  </div>
                  {apps.map(([app, owner, amount, usage], index) => (
                    <div className="table-row" key={app}>
                      <span className="app-name"><i className={`app-dot dot-${index}`} />{app}</span>
                      <span>{owner}</span>
                      <span><strong>{amount}</strong></span>
                      <span><em style={{ width: usage }} />{usage}</span>
                      <span>{index === 3 ? "待优化" : "正常"}</span>
                    </div>
                  ))}
                </div>
              </div>
              <section className="spend-card">
                <div className="flex items-center justify-between">
                  <strong>软件支出</strong>
                  <BarChart3 className="h-4 w-4 text-[#2ecad3]" />
                </div>
                <p>54 个应用</p>
                <h4>¥98,540</h4>
                <span>本月已支出</span>
                <div aria-hidden="true" className="mini-chart"><i /><i /><i /><i /><i /></div>
              </section>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white py-24">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <div className="max-w-3xl">
            <p className="eyebrow">完整可见性</p>
            <h2 className="section-title">所有软件订阅都可见、可控、可追踪</h2>
            <p className="mt-6 text-lg leading-8 text-slate-600">
              财务、采购和 IT 使用同一套事实，不再依赖零散表格、共享信用卡和临时提醒。
            </p>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-2">
            {capabilities.map(item => (
              <article className="detail-card" key={item.title}>
                <span><item.icon className="h-5 w-5" /></span>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
                <a className="mt-5 inline-flex items-center gap-2 text-sm font-black text-[#20245f]" href={item.to}>
                  查看方案 <ArrowRight className="h-4 w-4" />
                </a>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#f6fafb] py-24">
        <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-2 lg:items-center lg:px-8">
          <div>
            <p className="eyebrow">统一工作流</p>
            <h2 className="section-title">把购买、支付、使用和续订连接起来</h2>
            <p className="mt-6 text-lg leading-8 text-slate-600">
              每一步都有负责人、截止时间和可追溯记录，团队能更早发现风险，也能更快推进真正需要的软件。
            </p>
            <Button className="mt-8" href="/saas-management" variant="dark">
              查看 SaaS 管理能力 <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="detail-steps">
            {["发现全部软件", "完成采购与安全审批", "控制付款和发票", "在续订前优化成本"].map((step, index) => (
              <div className="detail-step" key={step}>
                <span>{index + 1}</span>
                <strong>{step}</strong>
                <Check className="ml-auto h-5 w-5 text-[#1aa4ad]" />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#20245f] py-24 text-white">
        <div className="mx-auto max-w-4xl px-5 text-center lg:px-8">
          <p className="eyebrow text-[#cafbff]">从第一批数据开始</p>
          <h2 className="section-title mx-auto text-white">先看清软件，再决定下一步行动</h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-white/72">
            从应用目录或一份账单开始，逐步建立采购、支付、续订和合规工作流。
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button href="/solutions/application-directory">查看应用目录</Button>
            <Button href="/calculator" variant="secondary">估算节省空间</Button>
          </div>
        </div>
      </section>
    </>
  );
}
