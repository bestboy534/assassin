import { ArrowRight, LayoutDashboard, Star } from "lucide-react";
import { Button } from "../../shared/components/Button";

const directoryApps = [
  ["协作", "#5b5fc7"],
  ["财务", "#161b3d"],
  ["设计", "#ef5da8"],
  ["AI", "#111827"],
  ["销售", "#ff6b35"],
  ["创意", "#ed2224"],
  ["会议", "#2d8cff"],
  ["客户", "#00a1e0"],
  ["研发", "#24292f"],
] as const;

export function ApplicationDirectoryPage() {
  return (
    <>
      <section className="official-product-hero">
        <div className="official-product-inner">
          <div className="official-product-copy">
            <span className="detail-badge"><LayoutDashboard className="h-4 w-4" />应用目录</span>
            <h1>完整掌握每一款软件工具</h1>
            <p>在一个目录中查看成本、预算、使用者、使用率、合同和合规信息。每款应用由谁负责、何时续订、是否真正被使用，都清清楚楚。</p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Button href="/signup">开始建立目录 <ArrowRight className="h-4 w-4" /></Button>
              <div aria-label="客户评价" className="review-proof">
                <span>{[0, 1, 2, 3, 4].map(star => <Star className="h-4 w-4" fill="currentColor" key={star} />)}</span>
                <small>深受财务团队信赖</small>
              </div>
            </div>
          </div>
          <div aria-label="应用目录产品界面示意" className="directory-visual">
            <div className="directory-window-bar"><span /><span /><span /><strong>应用目录</strong></div>
            <div className="directory-app-grid">
              {directoryApps.map(([label, color], index) => (
                <div className="directory-app" key={`${label}-${index}`}>
                  <span style={{ background: color }}>{label.slice(0, 1)}</span>
                  <small>{label}</small>
                </div>
              ))}
            </div>
            <div className="directory-floating-stat stat-apps"><small>应用数量</small><strong>73</strong><span>较上月 +4</span></div>
            <div className="directory-floating-stat stat-spend"><small>软件支出</small><strong>¥304,728</strong><span>本月预算内</span></div>
          </div>
        </div>
      </section>
      <section className="official-intro-section">
        <div className="official-intro-copy">
          <p className="eyebrow">统一软件目录</p>
          <h2>所有软件，一处看清</h2>
          <p>不再依赖零散表格和聊天记录。应用、负责人、付款、续订与使用情况始终保持关联。</p>
        </div>
        <div className="official-feature-grid">
          {[
            ["发现全部应用", "汇总正在付款和团队正在使用的软件，减少遗漏与影子 IT。"],
            ["明确责任归属", "为每款应用设置业务负责人、部门和预算，问题出现时知道该找谁。"],
            ["提前处理续订", "把合同日期、使用率和支出放在一起，在扣款前决定续订、降级或取消。"],
          ].map(([title, body], index) => (
            <article className="official-feature" key={title}>
              <span>0{index + 1}</span><h3>{title}</h3><p>{body}</p>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
