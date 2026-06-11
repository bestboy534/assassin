import { ArrowRight, Check, Sparkles } from "lucide-react";
import { Button } from "../../shared/components/Button";
import type { PublicPage } from "../content/pages";

const visualRows = [
  ["需求与业务理由", "业务负责人", "已提交"],
  ["预算与合同检查", "财务团队", "进行中"],
  ["权限与安全审查", "IT 团队", "待确认"],
  ["执行与结果归档", "流程负责人", "已安排"],
] as const;

export function GenericSolutionPage({ page }: { page: PublicPage }) {
  const isDownload = page.cta.to.startsWith("/documents/");
  const secondary = page.secondaryCta ?? {
    label: "查看客户故事",
    to: "/customer-stories",
  };

  return (
    <>
      <section className="detail-hero">
        <div className="mx-auto grid max-w-7xl gap-12 px-5 py-20 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-8">
          <div>
            <span className="detail-badge">
              <Sparkles className="h-4 w-4" />
              {page.category}
            </span>
            <h1>{page.title}</h1>
            <p>{page.description}</p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Button download={isDownload ? "" : undefined} href={page.cta.to}>
                {page.cta.label} <ArrowRight className="h-4 w-4" />
              </Button>
              <Button href={secondary.to} variant="secondary">
                {secondary.label}
              </Button>
            </div>
          </div>
          <div className="detail-visual">
            <div className="flex items-center justify-between">
              <div>
                <small>{page.badge}</small>
                <h3>统一工作视图</h3>
              </div>
              <span className="rounded-full bg-[#dffbfc] px-3 py-1 text-xs font-black text-[#168890]">
                实时
              </span>
            </div>
            <div className="detail-row-head">
              <span>事项</span>
              <span>负责人</span>
              <span>状态</span>
            </div>
            {visualRows.map(([name, owner, status]) => (
              <div className="detail-row" key={name}>
                <strong>{name}</strong>
                <span>{owner}</span>
                <em>{status}</em>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white py-20">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 lg:grid-cols-3 lg:px-8">
          {page.bullets.map((item, index) => (
            <article className="detail-card" key={item}>
              <span>{index + 1}</span>
              <h2>{item}</h2>
              <p>把这一能力放进日常工作后，团队可以在采购、付款、使用和续订前做出更清晰的判断。</p>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-[#f6fafb] py-20">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-8">
          <div>
            <p className="eyebrow">工作流</p>
            <h2 className="section-title">从信息收集到结果归档，步骤始终清晰</h2>
          </div>
          <div className="detail-steps">
            {page.steps.map((step, index) => (
              <div className="detail-step" key={step}>
                <span>{index + 1}</span>
                <strong>{step}</strong>
                <Check className="ml-auto h-4 w-4 text-[#1aa4ad]" />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white py-20">
        <div className="mx-auto grid max-w-7xl gap-6 px-5 md:grid-cols-3 lg:px-8">
          {page.stats.map((stat, index) => (
            <div className="detail-stat" key={`${stat}-${index}`}>
              <strong>{stat}</strong>
              <span>{index === 0 ? "关键指标" : index === 1 ? "核心收益" : "运营效果"}</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
