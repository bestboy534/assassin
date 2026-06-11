import { useState } from "react";
import { Check, Send } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { Button } from "../../shared/components/Button";

const topicLabels: Record<string, string> = {
  demo: "预约产品演示",
  partner: "合作伙伴咨询",
  press: "媒体联系",
  security: "安全问题",
  career: "职位申请",
};

export function ContactPage() {
  const [params] = useSearchParams();
  const [submitted, setSubmitted] = useState(false);
  const topic = params.get("topic") ?? "product";
  const role = params.get("role");

  return (
    <section className="content-index-page">
      <div className="mx-auto grid max-w-5xl gap-12 lg:grid-cols-[0.8fr_1.2fr]">
        <div>
          <p className="eyebrow">联系我们</p>
          <h1 className="mt-4 text-5xl font-black leading-tight text-[#171b46]">告诉我们你想解决的软件管理问题</h1>
          <p className="mt-6 text-lg leading-8 text-slate-600">
            当前主题：{topicLabels[topic] ?? "产品咨询"}{role ? `，职位编号：${role}` : ""}。
          </p>
        </div>
        {submitted ? (
          <div className="detail-card self-start" role="status">
            <span><Check className="h-5 w-5" /></span>
            <h2 className="mt-5 text-2xl font-black text-[#171b46]">需求已在本页确认</h2>
            <p>正式线索提交将在 CMS 与公开表单计划中接入。你可以继续浏览帮助中心或预约页面了解下一步信息。</p>
            <Button className="mt-6" href="/help-center" variant="dark">前往帮助中心</Button>
          </div>
        ) : (
          <form
            className="grid gap-5 rounded-lg border border-slate-200 bg-white p-7 shadow-sm"
            onSubmit={event => {
              event.preventDefault();
              setSubmitted(true);
            }}
          >
            <label className="grid gap-2 font-bold text-[#171b46]">姓名<input className="rounded-md border border-slate-300 px-4 py-3 font-normal" name="name" required /></label>
            <label className="grid gap-2 font-bold text-[#171b46]">工作邮箱<input className="rounded-md border border-slate-300 px-4 py-3 font-normal" name="email" required type="email" /></label>
            <label className="grid gap-2 font-bold text-[#171b46]">团队与需求<textarea className="min-h-36 rounded-md border border-slate-300 px-4 py-3 font-normal" name="message" required /></label>
            <Button type="submit" variant="dark">确认需求 <Send className="h-4 w-4" /></Button>
          </form>
        )}
      </div>
    </section>
  );
}
