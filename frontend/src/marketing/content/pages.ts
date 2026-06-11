export type PageKind =
  | "generic"
  | "directory"
  | "story"
  | "careers"
  | "content-index"
  | "report"
  | "legal"
  | "security"
  | "support";

export type PageId =
  | "home"
  | "finance"
  | "procurement"
  | "it"
  | "operations"
  | "difference"
  | "approvals"
  | "optimization"
  | "payments"
  | "spend"
  | "directory"
  | "analytics"
  | "accounting"
  | "integrations"
  | "engage"
  | "onboarding"
  | "softwareSecurity"
  | "compliance"
  | "management"
  | "blog"
  | "stories"
  | "faq"
  | "webinars"
  | "guides"
  | "calculator"
  | "announcements"
  | "marketplace"
  | "datahub"
  | "report"
  | "buyers"
  | "pricing"
  | "demo"
  | "signup"
  | "login"
  | "about"
  | "careers"
  | "partner"
  | "podcasts"
  | "cambridge"
  | "security"
  | "support"
  | "press"
  | "privacy"
  | "terms"
  | "contact"
  | "help";

export type PublicPage = {
  id: PageId;
  path: string;
  aliases: readonly string[];
  category: string;
  title: string;
  description: string;
  badge: string;
  cta: { label: string; to: string };
  secondaryCta?: { label: string; to: string };
  bullets: readonly string[];
  steps: readonly string[];
  stats: readonly [string, string, string];
  kind: PageKind;
  asset?: string;
};

type PageOptions = Partial<
  Pick<
    PublicPage,
    "aliases" | "badge" | "bullets" | "steps" | "stats" | "kind" | "asset" | "secondaryCta"
  >
>;

function page(
  id: PageId,
  path: string,
  category: string,
  title: string,
  description: string,
  cta: PublicPage["cta"],
  options: PageOptions = {},
): PublicPage {
  return {
    id,
    path,
    aliases: options.aliases ?? [],
    category,
    title,
    description,
    badge: options.badge ?? category,
    cta,
    secondaryCta: options.secondaryCta,
    bullets: options.bullets ?? [
      "把关键信息集中到统一工作流",
      "让负责人、预算和进度始终清晰",
      "在行动前保留完整依据和记录",
    ],
    steps: options.steps ?? ["收集信息", "明确责任", "协同处理", "复盘结果"],
    stats: options.stats ?? ["实时", "统一视图", "全程留痕"],
    kind: options.kind ?? "generic",
    asset: options.asset,
  };
}

export const publicPages = [
  page(
    "finance",
    "/why/finance",
    "面向财务",
    "减少软件浪费，为下一位员工腾出预算",
    "从采购申请到付款、发票、续订和会计归档，财务团队可以在一个工作台里看清成本、控制风险并释放预算。",
    { label: "查看支出优化方案", to: "/solutions/software-spend-optimization" },
    {
      aliases: ["/solutions/finance"],
      bullets: ["按供应商设置预算上限", "自动收集收据和发票", "在续订前发现低使用率"],
      steps: ["发现软件", "归属负责人", "设置付款规则", "生成月末凭证"],
      stats: ["18%", "平均可节省支出", "42 小时/月"],
    },
  ),
  page(
    "procurement",
    "/why/procurement",
    "面向采购",
    "在团队需要时，及时买到真正需要的软件",
    "让团队按流程申请工具，采购、财务和 IT 一起审查预算、合同和安全要求，在速度和控制之间取得平衡。",
    { label: "查看审批采购流程", to: "/solutions/software-approvals-and-purchasing" },
    { aliases: ["/solutions/procurement"], steps: ["业务申请", "财务预算", "IT 安全审查", "采购执行"] },
  ),
  page(
    "it",
    "/why/it",
    "面向 IT",
    "让软件栈保持安全，也始终处于控制之中",
    "集中查看应用、权限、负责人和使用状态，减少影子 IT，并让 IT 与财务共同处理访问风险。",
    { label: "查看软件安全方案", to: "/solutions/software-security" },
    { aliases: ["/solutions/it"], bullets: ["识别未登记应用", "跟踪负责人和部门", "同步入职与离职权限"] },
  ),
  page(
    "operations",
    "/why/operations",
    "面向运营",
    "让软件流程自动运行，并始终井然有序",
    "应用负责人、续订提醒、付款规则和发票归档自动串联，运营团队不再依赖零散表格和临时提醒。",
    { label: "查看 SaaS 管理能力", to: "/saas-management" },
    { aliases: ["/solutions/operations"] },
  ),
  page(
    "difference",
    "/why/difference",
    "平台差异",
    "从财务视角管理软件，而不只是记录软件清单",
    "把软件发现、审批、付款、发票和使用率连接起来，让每个决策都有业务和成本依据。",
    { label: "了解统一管理方式", to: "/saas-management" },
    { aliases: ["/how-cledara-is-different"] },
  ),
  page(
    "approvals",
    "/solutions/approvals",
    "解决方案",
    "建立战略性软件采购流程",
    "业务团队快速提交软件需求，财务和 IT 在同一流程里完成价值、预算、安全和采购判断。",
    { label: "预约采购流程演示", to: "/book-a-demo" },
    {
      aliases: ["/solutions/software-approvals-and-purchasing"],
      bullets: ["收集业务理由和预算", "按金额自动分派审批人", "审批完成后连接付款与合同"],
      steps: ["填写需求", "上传报价", "审批预算", "执行采购"],
    },
  ),
  page(
    "optimization",
    "/solutions/optimization",
    "解决方案",
    "用数据洞察让软件支出始终不偏离计划",
    "低使用率、重复订阅和无人负责的应用都会被标记，帮助团队在续订扣款前及时采取行动。",
    { label: "估算节省空间", to: "/calculator" },
    { aliases: ["/solutions/software-spend-optimization"], stats: ["18%", "潜在节省", "12 个机会"] },
  ),
  page(
    "payments",
    "/solutions/payments",
    "解决方案",
    "把软件付款的控制权交回财务团队",
    "每个供应商使用独立虚拟卡，并设置预算、周期和审批规则，避免意外扣款和难以追踪的共享信用卡。",
    { label: "了解虚拟卡安全", to: "/security" },
    { aliases: ["/solutions/software-payments"] },
  ),
  page(
    "spend",
    "/solutions/spend",
    "解决方案",
    "一套完整的企业支出管理方案",
    "用同一套付款、审批和收据流程覆盖软件订阅、差旅和日常业务支出，减少月末整理工作。",
    { label: "查看会计自动化", to: "/solutions/accounting-automation" },
    { aliases: ["/solutions/spend-management"] },
  ),
  page(
    "directory",
    "/solutions/application-directory",
    "解决方案",
    "完整掌握每一款软件工具",
    "在一个目录中查看成本、预算、使用者、使用率、合同和合规信息。",
    { label: "开始建立应用目录", to: "/signup" },
    { kind: "directory", aliases: ["/application-directory"] },
  ),
  page(
    "analytics",
    "/solutions/analytics",
    "解决方案",
    "看懂每一笔软件支出去向",
    "用统一仪表盘查看部门预算、续订日历、使用率和节省机会，让每一笔支出都有依据。",
    { label: "查看软件支出报告", to: "/resources/data-hub" },
    { aliases: ["/solutions/analytics-and-reporting"] },
  ),
  page(
    "accounting",
    "/solutions/accounting",
    "解决方案",
    "让软件会计工作自动运行",
    "自动收集收据、匹配付款、补齐供应商信息，并为会计系统准备干净数据。",
    { label: "查看可连接的会计工具", to: "/integrations" },
    { aliases: ["/solutions/accounting-automation"] },
  ),
  page(
    "integrations",
    "/solutions/integrations",
    "解决方案",
    "把平台连接到团队使用的每一个工具",
    "通过集成同步用户、交易、审批和会计信息，让数据不用在工具之间来回搬。",
    { label: "浏览集成市场", to: "/marketplace" },
    { aliases: ["/integrations"] },
  ),
  page(
    "engage",
    "/solutions/engage",
    "解决方案",
    "让真正使用软件的员工参与治理",
    "自动收集应用负责人的反馈、使用确认和续订建议，同时保留财务与 IT 的控制。",
    { label: "查看客户实践", to: "/customer-stories" },
    { aliases: ["/solutions/cledara-engage"] },
  ),
  page(
    "onboarding",
    "/solutions/onboarding",
    "解决方案",
    "在一个地方管理所有软件访问权限",
    "新员工需要的工具、离职员工的访问和付款负责人变化，都能进入同一套标准流程。",
    { label: "查看 IT 团队方案", to: "/solutions/it" },
    { aliases: ["/solutions/onboarding"] },
  ),
  page(
    "softwareSecurity",
    "/solutions/security",
    "解决方案",
    "在安全问题演变成事故之前发现它",
    "看清未登记应用、共享账号、无负责人供应商和可疑付款，把风险转成可分派、可关闭的任务。",
    { label: "查看安全承诺", to: "/security" },
    { aliases: ["/solutions/software-security"] },
  ),
  page(
    "compliance",
    "/solutions/compliance",
    "解决方案",
    "从软件使用第一天到最后一天都保持合规",
    "每次申请、审批、付款、访问变更和发票归档都有记录，方便审计、预算复盘和供应商管理。",
    { label: "阅读隐私政策", to: "/privacy-policy" },
    { aliases: ["/solutions/saas-compliance"] },
  ),
  page(
    "management",
    "/solutions/saas-management",
    "核心平台",
    "管理软件生命周期的每一个节点",
    "从发现新工具，到审批、付款、使用反馈、续订和取消，形成一个完整闭环。",
    { label: "查看应用目录", to: "/solutions/application-directory" },
    { aliases: ["/saas-management"] },
  ),
  page(
    "blog",
    "/resources/blog",
    "资源",
    "软件采购、财务运营和 AI 支出洞察",
    "用中文文章沉淀软件管理方法，帮助团队建立更清晰的采购和支出规则。",
    { label: "查看指南与模板", to: "/guides-templates" },
    { aliases: ["/blog"] },
  ),
  page(
    "stories",
    "/resources/customer-stories",
    "资源",
    "看看团队如何把软件支出管起来",
    "从发现工具到减少浪费，真实团队的工作流可以帮助你判断适合自己的落地方式。",
    { label: "了解财务团队方案", to: "/solutions/finance" },
    { aliases: ["/customer-stories"] },
  ),
  page(
    "faq",
    "/resources/faq",
    "资源",
    "上线前你可能想确认的事",
    "覆盖软件发现、付款方式、审批规则、安全、发票和数据同步等关键问题。",
    { label: "前往帮助中心", to: "/help-center" },
    { aliases: ["/faq"] },
  ),
  page(
    "webinars",
    "/resources/webinars",
    "资源",
    "和财务、IT、采购团队一起学习",
    "围绕软件采购、AI 支出治理和续订管理定期提供中文活动内容与回放摘要。",
    { label: "查看近期公告", to: "/resources/announcements" },
    { aliases: ["/events-webinars"] },
  ),
  page(
    "guides",
    "/resources/guides",
    "资源",
    "把软件管理流程落到表单、规则和模板里",
    "为采购申请、续订复盘、供应商审查和预算管理准备可复用资料。",
    { label: "打开买家指南", to: "/resources/buyers-guide" },
    { aliases: ["/guides-templates"] },
  ),
  page(
    "calculator",
    "/resources/savings-calculator",
    "资源",
    "估算你能从软件订阅中省下多少",
    "根据团队规模、工具数量和月度支出，快速估算低使用率和重复工具带来的优化空间。",
    { label: "查看支出优化方案", to: "/solutions/software-spend-optimization" },
    { aliases: ["/calculator"], stats: ["18%", "参考节省率", "3 分钟"] },
  ),
  page(
    "announcements",
    "/resources/announcements",
    "资源",
    "产品公告与能力更新",
    "在本地中文落地页查看集成、报表、安全和工作流更新，再决定是否访问外部发布渠道。",
    { label: "浏览集成市场", to: "/marketplace" },
  ),
  page(
    "marketplace",
    "/resources/integration-marketplace",
    "资源",
    "发现可连接的系统",
    "探索身份、会计、协作和数据工具，把软件管理融入现有流程。",
    { label: "查看集成方案", to: "/integrations" },
    { aliases: ["/marketplace"] },
  ),
  page(
    "datahub",
    "/resources/data-hub",
    "数据中心",
    "用真实软件支出数据看清市场变化",
    "按行业、公司规模和软件类别查看中文摘要，为预算、谈判和采购决策提供参考。",
    { label: "下载中文摘要", to: "/documents/software-spend-report-summary.txt" },
    { kind: "report", asset: "/assets/spend-report.webp" },
  ),
  page(
    "report",
    "/resources/ai-report",
    "研究报告",
    "AI 正在重塑软件采购，预算规则也需要升级",
    "基于真实软件交易数据，分析 AI 工具增长、重复采购风险和财务团队需要建立的新控制方式。",
    { label: "下载中文摘要", to: "/documents/ai-report-summary.txt" },
    { kind: "report", asset: "/assets/ai-report.webp" },
  ),
  page(
    "buyers",
    "/resources/buyers-guide",
    "资源",
    "评估软件管理平台时该看什么",
    "从采购、财务、IT、安全和落地成本五个角度，判断什么方案适合你的团队。",
    { label: "查看平台差异", to: "/why/difference" },
  ),
  page(
    "pricing",
    "/pricing",
    "定价",
    "按团队规模和使用场景选择合适方案",
    "用清晰套餐覆盖软件管理、审批、付款、分析和会计自动化能力。",
    { label: "预约方案沟通", to: "/book-a-demo" },
    { stats: ["3 档", "团队方案", "可定制"] },
  ),
  page(
    "demo",
    "/demo",
    "预约演示",
    "用一条完整业务流程了解平台",
    "告诉我们团队规模、当前工具数量和最想解决的问题，演示页会引导你进入明确的联系流程。",
    { label: "提交演示需求", to: "/company/contact?topic=demo" },
    { aliases: ["/book-a-demo"], steps: ["确认目标", "选择场景", "提交需求", "安排演示"] },
  ),
  page(
    "signup",
    "/signup",
    "开始使用",
    "从导入第一批软件支出开始",
    "创建工作区后，连接交易、识别供应商、分配负责人，再逐步启用审批和付款控制。",
    { label: "已有账号，前往登录", to: "/login" },
    { aliases: ["/start"], steps: ["创建工作区", "导入数据", "确认应用", "启用规则"] },
  ),
  page(
    "login",
    "/login",
    "登录",
    "登录你的软件管理工作区",
    "账号系统接入后，这里将承载邮箱、企业 SSO 和多因素验证入口。",
    { label: "还没有账号，开始使用", to: "/signup" },
  ),
  page(
    "about",
    "/about",
    "公司",
    "我们的使命，是让企业与软件建立更好的关系",
    "软件本应帮助团队前进，而不是制造混乱。我们让采购、付款、使用和治理回到清晰、可控的状态。",
    { label: "了解团队与职位", to: "/careers" },
    { kind: "story", asset: "/assets/about-hero.jpg" },
  ),
  page(
    "careers",
    "/company/careers",
    "公司",
    "和我们一起，建设更好的未来",
    "加入一支跨城市、跨职能的团队，用更透明、更高效的方式改变企业购买和管理软件的体验。",
    { label: "查看开放职位", to: "/careers#open-roles" },
    { kind: "careers", aliases: ["/careers"], asset: "/assets/careers-hero.jpg" },
  ),
  page(
    "partner",
    "/company/partners",
    "合作伙伴",
    "与会计、咨询和技术伙伴共同服务客户",
    "把软件支出管理加入服务组合，为客户提供更完整的财务运营能力。",
    { label: "提交合作意向", to: "/company/contact?topic=partner" },
    { aliases: ["/become-a-partner"] },
  ),
  page(
    "podcasts",
    "/company/podcasts",
    "播客",
    "财务与运营播客",
    "按主题筛选关于 SaaS、创业、财务运营与企业增长的中文节目摘要。",
    { label: "查看全部节目", to: "/podcasts" },
    { kind: "content-index", aliases: ["/podcasts"] },
  ),
  page(
    "cambridge",
    "/company/cambridge",
    "合作",
    "通过体育合作连接团队、社区和共同成长",
    "围绕团队精神、长期投入和社区价值建立真实合作关系。",
    { label: "了解合作方式", to: "/become-a-partner" },
    { aliases: ["/cambridge"] },
  ),
  page(
    "security",
    "/company/security",
    "安全",
    "始终认真守护你的安全",
    "安全能力覆盖虚拟卡令牌化、数据隐私、SOC 2 控制、基础设施隔离和定期测试。",
    { label: "联系安全团队", to: "/company/contact?topic=security" },
    { kind: "security", aliases: ["/security"] },
  ),
  page(
    "support",
    "/company/support",
    "客户支持",
    "本季度客户支持指标",
    "用可量化指标呈现响应速度、解决效率和客户满意度，让服务体验更加透明。",
    { label: "前往帮助中心", to: "/help-center" },
    { kind: "support", aliases: ["/support-metrics"] },
  ),
  page(
    "press",
    "/company/press",
    "媒体中心",
    "媒体报道与公司动态",
    "按类型筛选新闻稿、媒体报道、数据研究和品牌资料。",
    { label: "联系媒体团队", to: "/company/contact?topic=press" },
    { kind: "content-index", aliases: ["/press"] },
  ),
  page(
    "privacy",
    "/legal/privacy",
    "法律",
    "隐私政策",
    "阅读我们如何收集、使用、保存和保护个人信息，以及你可以如何行使数据权利。",
    { label: "下载隐私政策", to: "/documents/privacy-policy.txt" },
    { kind: "legal", aliases: ["/privacy-policy"] },
  ),
  page(
    "terms",
    "/legal/terms",
    "法律",
    "服务条款",
    "阅读产品使用、账户责任、服务范围、付款和双方权利义务等基础约定。",
    { label: "下载服务条款", to: "/documents/terms-of-service.txt" },
    { kind: "legal", aliases: ["/terms"] },
  ),
  page(
    "contact",
    "/company/contact",
    "联系我们",
    "告诉我们你想解决的软件管理问题",
    "无论是采购、支付、发票、续订、安全、合作还是媒体需求，都可以从这里进入对应沟通流程。",
    { label: "查看常见问题", to: "/faq" },
    { aliases: ["/contact"] },
  ),
  page(
    "help",
    "/help-center",
    "帮助中心",
    "快速找到软件管理问题的中文答案",
    "先在本地帮助中心查看采购、付款、权限、发票和续订指南，再按需要联系支持团队。",
    { label: "查看支持指标", to: "/support-metrics" },
    { aliases: ["/help"] },
  ),
] as const satisfies readonly PublicPage[];

export const pagesById = Object.fromEntries(
  publicPages.map(item => [item.id, item]),
) as Record<Exclude<PageId, "home">, PublicPage>;

export const routePathById: Record<PageId, string> = {
  home: "/",
  ...Object.fromEntries(publicPages.map(item => [item.id, item.path])),
} as Record<PageId, string>;

export const legacyHashPaths: Record<string, string> = {
  directory: routePathById.directory,
  datahub: routePathById.datahub,
  report: routePathById.report,
  start: routePathById.signup,
  companySecurity: routePathById.security,
  ...Object.fromEntries(publicPages.map(item => [item.id, item.path])),
};

export type ContentEntry = {
  slug: string;
  title: string;
  summary: string;
  image: string;
  tags: readonly string[];
  meta: string;
  kind: "podcasts" | "press";
};

export const contentEntries: readonly ContentEntry[] = [
  {
    slug: "saas-growth-discipline",
    title: "从增长到可持续经营",
    summary: "讨论增长效率、软件成本，以及企业进入下一阶段时真正需要的运营纪律。",
    image: "/assets/podcast-saas.jpeg",
    tags: ["SaaS", "创始人访谈"],
    meta: "播客",
    kind: "podcasts",
  },
  {
    slug: "finance-foundations",
    title: "如何建立高效的财务基础设施",
    summary: "高增长公司如何在保持速度的同时建立采购、预算和软件治理体系。",
    image: "/assets/podcast-unicorns.jpeg",
    tags: ["财务运营", "增长"],
    meta: "播客",
    kind: "podcasts",
  },
  {
    slug: "software-stack-at-scale",
    title: "规模化以后，软件栈会发生什么变化",
    summary: "判断哪些工具值得续订、哪些流程应该自动化，以及怎样避免影子 IT。",
    image: "/assets/podcast-saas.jpeg",
    tags: ["产品", "软件管理"],
    meta: "播客",
    kind: "podcasts",
  },
  {
    slug: "company-funding-update",
    title: "软件支出管理平台完成新一轮融资",
    summary: "继续深化产品能力，帮助更多企业把软件采购、付款和治理集中到同一平台。",
    image: "/assets/press-founder.jpeg",
    tags: ["公司新闻", "融资"],
    meta: "新闻稿",
    kind: "press",
  },
  {
    slug: "fintech-recognition",
    title: "入选欧洲金融科技代表企业榜单",
    summary: "以财务团队为中心的软件管理体验，以及对采购和支付流程的整合获得行业认可。",
    image: "/assets/press-fintech.jpeg",
    tags: ["媒体报道", "金融科技"],
    meta: "媒体",
    kind: "press",
  },
  {
    slug: "annual-software-spend-report",
    title: "年度软件支出报告：AI 工具支出持续增长",
    summary: "报告展示企业应用数量、续订压力和 AI 预算变化。",
    image: "/assets/spend-report.webp",
    tags: ["数据报告", "AI"],
    meta: "研究",
    kind: "press",
  },
] as const;

export const careerRoles = [
  {
    slug: "senior-product-designer",
    title: "高级产品设计师",
    location: "伦敦 / 混合办公",
    team: "产品与设计",
  },
  {
    slug: "customer-success-manager",
    title: "客户成功经理",
    location: "纽约 / 混合办公",
    team: "客户团队",
  },
  {
    slug: "senior-software-engineer",
    title: "高级软件工程师",
    location: "巴塞罗那 / 混合办公",
    team: "工程",
  },
] as const;
