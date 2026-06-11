import { ArrowRight, Building2, Globe2, HeartHandshake, Users } from "lucide-react";
import { Button } from "../../shared/components/Button";

const values = [
  ["客户第一", "从财务与运营团队每天面对的真实问题出发，做清楚、可靠、能落地的产品。"],
  ["保持好奇", "不满足于“行业一直这样做”，持续追问有没有更简单、更透明的方法。"],
  ["共同负责", "跨团队共享信息、明确负责人，让每一个决定都有上下文和后续。"],
] as const;

export function CompanyStoryPage() {
  return (
    <>
      <section className="story-hero" style={{ backgroundImage: "url(/assets/about-hero.jpg)" }}>
        <div className="story-overlay" />
        <div className="story-content">
          <span>关于我们</span>
          <h1>我们的使命，是让企业与软件建立更好的关系</h1>
          <p>软件本应帮助团队前进，而不是制造混乱。我们让采购、付款、使用和治理回到清晰、可控的状态。</p>
        </div>
      </section>
      <section className="company-values-section">
        <div className="company-values-heading">
          <p className="eyebrow">我们为什么做这件事</p>
          <h2>让好软件更容易被采用，也更容易被负责地管理</h2>
          <p>我们连接财务、采购、IT 和业务团队，让速度与控制不再互相冲突。</p>
        </div>
        <div className="company-values-grid">
          {values.map(([title, body], index) => (
            <article key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{body}</p></article>
          ))}
        </div>
        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {[
            [Users, "跨职能团队", "产品、工程、客户和运营团队围绕同一客户结果协作。"],
            [Globe2, "全球视角", "理解不同市场的财务、隐私和采购要求。"],
            [HeartHandshake, "长期关系", "把透明沟通和可持续价值放在短期承诺之前。"],
          ].map(([Icon, title, body]) => (
            <article className="detail-card" key={String(title)}>
              <span><Icon className="h-5 w-5" /></span><h3>{String(title)}</h3><p>{String(body)}</p>
            </article>
          ))}
        </div>
        <Button className="mt-10" href="/careers" variant="dark">
          认识团队与开放职位 <ArrowRight className="h-4 w-4" />
        </Button>
      </section>
    </>
  );
}

export function CambridgePage() {
  return (
    <>
      <section className="detail-hero">
        <div className="mx-auto max-w-5xl px-5 py-24 text-center lg:px-8">
          <span className="detail-badge"><Building2 className="h-4 w-4" />社区合作</span>
          <h1 className="mx-auto">通过体育合作连接团队、社区和共同成长</h1>
          <p className="mx-auto">长期合作不只关乎曝光。它把团队精神、社区参与和持续投入连接成可以共同建设的关系。</p>
          <Button className="mt-9" href="/become-a-partner">
            了解合作方式 <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </section>
      <section className="bg-white py-20">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 md:grid-cols-3 lg:px-8">
          {[
            ["共同价值", "围绕团队协作、长期投入和社区责任设计合作内容。"],
            ["真实参与", "通过活动、内容和员工参与，让合作进入真实场景。"],
            ["持续成长", "用长期节奏复盘成果，不把合作变成一次性传播。"],
          ].map(([title, body], index) => (
            <article className="detail-card" key={title}><span>{index + 1}</span><h2>{title}</h2><p>{body}</p></article>
          ))}
        </div>
      </section>
    </>
  );
}
