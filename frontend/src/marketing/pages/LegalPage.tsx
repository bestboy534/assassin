import { Download, Printer, ShieldCheck } from "lucide-react";
import { Button } from "../../shared/components/Button";
import type { PublicPage } from "../content/pages";

const privacySections = [
  ["适用范围", "本政策适用于公开网站、演示预约、客户沟通和未来工作台中与个人信息有关的处理活动。企业客户上传的业务数据按照合同、数据处理协议和组织配置处理。"],
  ["我们收集的信息", "我们可能收集联系信息、账户与身份信息、设备和安全日志、表单提交内容、服务使用记录以及客户主动提供的支持材料。我们不会保存完整卡号或 CVV。"],
  ["使用目的与法律依据", "信息用于提供和改进服务、保障账号和平台安全、响应请求、履行合同、遵守法律义务，以及在获得适当同意时发送产品沟通。"],
  ["共享与跨境传输", "仅向提供托管、邮件、分析、安全和客户支持所必需的受托供应商共享最少信息。跨境传输会使用适用的数据保护机制并限制访问。"],
  ["保留与安全", "信息只在实现目的、履行合同或满足法律要求所需的时间内保留。我们使用访问控制、加密、日志、备份和定期测试保护数据。"],
  ["你的权利", "你可以根据适用法律请求访问、更正、删除、限制处理、反对处理或获取可携带副本。我们会验证请求者身份并在法定期限内回复。"],
  ["联系我们", "隐私请求可通过联系我们页面提交。请求会被记录、分派并提供处理状态，不要求用户在公开渠道提交敏感材料。"],
] as const;

const termsSections = [
  ["服务与账户", "用户应提供准确账户信息并妥善保护登录凭据。组织管理员负责成员邀请、角色分配和组织内配置。"],
  ["允许的使用", "不得利用服务进行违法活动、绕过安全控制、干扰平台运行、未经授权访问其他组织数据，或上传不具备处理权利的内容。"],
  ["客户数据", "客户保留其业务数据权利，并授权平台在提供服务、保障安全和履行支持义务所需范围内处理这些数据。"],
  ["费用与付款", "适用费用、账期、税费和续订安排以订单或订阅页面为准。发生付款问题时，平台会提供合理通知和恢复方式。"],
  ["第三方服务", "集成、支付和外部数据能力可能由第三方提供。平台会清楚标识相关边界，但不控制第三方服务自身的可用性和条款。"],
  ["保密与安全", "双方应保护在合作中获得的保密信息。平台采用合理的技术和组织措施，并对关键安全事件提供适当通知。"],
  ["期限与终止", "任一方可按订单和适用法律终止服务。终止后，客户可在约定窗口内导出数据，随后进入安全删除流程。"],
  ["责任与争议", "责任范围、适用法律和争议处理以客户订单、地区附录及强制法律规定为准。本中文页面用于清晰阅读，不替代已签署合同。"],
] as const;

export function LegalPage({ page }: { page: PublicPage }) {
  const isPrivacy = page.id === "privacy";
  const sections = isPrivacy ? privacySections : termsSections;

  return (
    <article className="legal-page">
      <header>
        <span><ShieldCheck className="h-4 w-4" />{isPrivacy ? "隐私" : "法律"}</span>
        <h1>{page.title}</h1>
        <p>{page.description}</p>
        <div className="mt-8 flex flex-wrap gap-3 print:hidden">
          <Button download href={page.cta.to} variant="dark">
            <Download className="h-4 w-4" />{page.cta.label}
          </Button>
          <Button onClick={() => window.print()} variant="ghost">
            <Printer className="h-4 w-4" />打印本文
          </Button>
        </div>
      </header>
      <div className="mx-auto max-w-[820px] py-12">
        <p className="mb-10 text-sm font-bold text-slate-500">生效日期：2026 年 6 月 11 日</p>
        {sections.map(([title, body], index) => (
          <section className="mb-10" key={title}>
            <h2 className="text-2xl font-black text-[#171b46]">{index + 1}. {title}</h2>
            <p className="mt-4 text-base leading-8 text-slate-600">{body}</p>
          </section>
        ))}
      </div>
    </article>
  );
}
