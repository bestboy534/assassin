import { CalendarDays, Clock3, Download } from "lucide-react";
import { Button } from "../../shared/components/Button";
import type { PublicPage } from "../content/pages";

export function ReportPage({ page }: { page: PublicPage }) {
  const isAi = page.id === "report";
  const facts = isAi
    ? [["AI 采用率", "持续上升"], ["预算变化", "从试用转向长期投入"], ["治理重点", "价值、风险与重复采购"]]
    : [["企业应用数", "仍在增长"], ["续订压力", "预算团队更早介入"], ["主要机会", "低使用率与重复工具"]];

  return (
    <article className="report-page">
      <header className="report-header">
        <div className="report-meta">
          <span><CalendarDays className="h-4 w-4" />2026 年中文摘要</span>
          <span><Clock3 className="h-4 w-4" />阅读 8 分钟</span>
        </div>
        <h1>{page.title}</h1>
        <span className="report-category">{page.category}</span>
        <p>{page.description}</p>
      </header>
      <div className="report-image-wrap"><img alt="" src={page.asset} /></div>
      <section className="report-body">
        <div>
          <p className="eyebrow">报告摘要</p>
          <h2>{isAi ? "从好奇试用，走向有预算、有责任人的长期采用" : "软件支出管理正在从记账，转向持续优化"}</h2>
          <p>{isAi ? "真正的问题已经不再是要不要用 AI，而是哪些工具创造了可衡量价值、谁负责治理，以及怎样避免同类产品重复采购。" : "当合同、付款、使用率和负责人被放在同一个上下文里，团队就能在续订之前做出判断。"}</p>
          <Button download href={page.cta.to} variant="dark">
            {page.cta.label} <Download className="h-4 w-4" />
          </Button>
        </div>
        <div className="report-facts">
          {facts.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
        </div>
      </section>
    </article>
  );
}
