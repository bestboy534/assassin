import { ArrowRight } from "lucide-react";
import { Button } from "../../shared/components/Button";

export function SupportMetricsPage() {
  return (
    <>
      <section className="support-hero">
        <span>透明服务承诺</span>
        <h1>本季度客户支持指标</h1>
        <p>我们通过快速、清晰且持续跟进的支持，帮助团队更顺利地管理软件，并公开呈现关键服务指标。</p>
        <div className="support-logos">{["财务团队", "采购团队", "IT 团队", "运营团队", "安全团队", "管理层"].map(item => <strong key={item}>{item}</strong>)}</div>
      </section>
      <section className="support-metrics-grid">
        {[
          ["98%", "客户满意度"],
          ["2 分钟", "工作时段首次响应中位数"],
          ["92%", "首次联系解决率"],
          ["全天候", "紧急安全问题支持"],
        ].map(([value, label]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}
        <Button href="/help-center" variant="dark">前往帮助中心 <ArrowRight className="h-4 w-4" /></Button>
      </section>
    </>
  );
}
