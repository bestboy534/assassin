import { ArrowRight, Check, Globe2, Heart, MapPin, Users } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../../shared/components/Button";
import { careerRoles } from "../content/pages";

const benefits = [
  "灵活的混合办公方式",
  "有竞争力的薪酬与长期激励",
  "学习与专业发展预算",
  "身心健康与家庭支持",
  "跨办公室协作与团队活动",
  "清晰、透明的成长反馈",
] as const;

const faqs = [
  ["招聘流程有几轮？", "通常包括初步交流、能力讨论、与未来协作伙伴交流，以及最终双向确认。"],
  ["可以远程工作吗？", "职位页面会标明办公地点和混合方式，部分岗位可在特定时区远程协作。"],
  ["如何准备申请？", "请说明你解决过的真实问题、承担的责任，以及你希望在下一份工作中继续学习什么。"],
] as const;

export function CareersPage() {
  return (
    <>
      <section className="story-hero careers-story" style={{ backgroundImage: "url(/assets/careers-hero.jpg)" }}>
        <div className="story-overlay" />
        <div className="story-content">
          <span>加入团队</span>
          <h1>和我们一起，建设更好的未来</h1>
          <p>加入一支跨城市、跨职能的团队，用更透明、更高效的方式改变企业购买和管理软件的体验。</p>
          <Button className="mt-8" href="/careers#open-roles">查看开放职位 <ArrowRight className="h-4 w-4" /></Button>
        </div>
      </section>

      <section className="bg-white py-24">
        <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-2 lg:items-start lg:px-8">
          <div>
            <p className="eyebrow">我们做什么</p>
            <h2 className="section-title">让企业采用软件的速度和治理能力一起提升</h2>
          </div>
          <div className="grid gap-6 text-lg leading-8 text-slate-600">
            <p>我们解决的是财务、采购、IT 和业务团队每天都在面对的真实协作问题。</p>
            <p>这里的工作需要把复杂业务讲清楚，认真处理细节，并持续验证产品是否真的改善了用户的日常工作。</p>
          </div>
        </div>
      </section>

      <section className="bg-[#f6fafb] py-24">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <div className="max-w-3xl">
            <p className="eyebrow">团队与价值观</p>
            <h2 className="section-title">清晰沟通，主动负责，保持好奇</h2>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {[
              [Users, "共同负责", "重要信息不留在个人手中，决定有负责人，也有后续。"],
              [Heart, "真正关心用户", "从真实工作流出发，不用表面热闹代替实际价值。"],
              [Globe2, "多元视角", "跨地区、跨职能理解问题，让不同经验进入产品判断。"],
            ].map(([Icon, title, body]) => (
              <article className="detail-card" key={String(title)}>
                <span><Icon className="h-5 w-5" /></span><h3>{String(title)}</h3><p>{String(body)}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white py-24">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
          <div>
            <p className="eyebrow">员工故事</p>
            <h2 className="section-title">在不同岗位，共同把复杂问题做简单</h2>
          </div>
          <div className="grid gap-5">
            {[
              ["产品与设计", "我喜欢这里会认真追问用户为什么卡住，再一起把流程打磨到真正顺手。"],
              ["客户团队", "我们不只回答问题，也把客户反馈带回产品决策，看到它变成实际改进。"],
              ["工程团队", "领域边界清楚，但讨论很开放。每个人都能理解自己工作的业务影响。"],
            ].map(([team, quote]) => (
              <blockquote className="detail-card" key={team}><p>“{quote}”</p><h3>{team}</h3></blockquote>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#20245f] py-24 text-white">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <p className="eyebrow text-[#cafbff]">全球办公室</p>
          <h2 className="section-title text-white">在多个城市协作，保持同一工作节奏</h2>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {["伦敦", "纽约", "巴塞罗那"].map(city => (
              <div className="rounded-lg border border-white/15 p-6" key={city}>
                <MapPin className="h-5 w-5 text-[#cafbff]" /><h3 className="mt-5 text-2xl font-black">{city}</h3><p className="mt-2 text-white/65">混合办公与跨时区协作</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white py-24">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <p className="eyebrow">福利与支持</p>
          <h2 className="section-title">为长期成长提供实际支持</h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {benefits.map(item => <div className="detail-step" key={item}><Check className="h-5 w-5 text-[#1aa4ad]" /><strong>{item}</strong></div>)}
          </div>
        </div>
      </section>

      <section className="open-roles-section" id="open-roles">
        <div className="open-roles-heading">
          <p className="eyebrow">开放职位</p>
          <h2>寻找下一位同行者</h2>
          <p>每个职位都有独立页面，包含职责、合作方式和申请入口。</p>
        </div>
        <div className="role-list">
          {careerRoles.map(role => (
            <Link className="role-row" key={role.slug} to={`/careers/${role.slug}`}>
              <div><strong>{role.title}</strong><span>{role.team}</span></div>
              <span>{role.location}</span><ArrowRight className="h-5 w-5" />
            </Link>
          ))}
        </div>
      </section>

      <section className="bg-[#f6fafb] py-24">
        <div className="mx-auto max-w-4xl px-5 lg:px-8">
          <p className="eyebrow">招聘 FAQ</p>
          <h2 className="section-title">申请前常见问题</h2>
          <div className="mt-10 grid gap-4">
            {faqs.map(([question, answer]) => (
              <article className="detail-card" key={question}><h3>{question}</h3><p>{answer}</p></article>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

export function CareerDetailPage() {
  const { roleSlug } = useParams();
  const role = careerRoles.find(item => item.slug === roleSlug);

  if (!role) {
    return (
      <section className="content-index-page text-center">
        <h1>没有找到这个职位</h1>
        <Button className="mt-8" href="/careers" variant="dark">返回开放职位</Button>
      </section>
    );
  }

  return (
    <article>
      <header className="detail-hero">
        <div className="mx-auto max-w-5xl px-5 py-24 lg:px-8">
          <span className="detail-badge">{role.team}</span>
          <h1>{role.title}</h1>
          <p>{role.location}。你将与跨职能团队合作，把复杂的软件采购和财务运营问题转化为清晰体验。</p>
          <Button className="mt-9" href={`/company/contact?topic=career&role=${role.slug}`}>
            申请这个职位 <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </header>
      <section className="mx-auto grid max-w-5xl gap-10 px-5 py-20 lg:grid-cols-2 lg:px-8">
        <div><p className="eyebrow">你会负责</p><h2 className="mt-3 text-3xl font-black text-[#171b46]">把重要问题推进到结果</h2></div>
        <div className="detail-steps">
          {["理解用户和业务上下文", "与跨职能伙伴设计方案", "交付并验证真实效果", "分享判断并持续改进"].map((item, index) => (
            <div className="detail-step" key={item}><span>{index + 1}</span><strong>{item}</strong></div>
          ))}
        </div>
      </section>
    </article>
  );
}
