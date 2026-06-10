import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  BriefcaseBusiness,
  Building2,
  Calculator,
  Check,
  ChevronDown,
  CreditCard,
  FileCheck2,
  Gauge,
  Globe2,
  LayoutDashboard,
  LockKeyhole,
  Menu,
  MonitorCheck,
  PieChart,
  PlugZap,
  ReceiptText,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Users,
  WalletCards,
  X,
  Zap,
  type LucideIcon,
} from "lucide-react";

type PageId =
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
  | "security"
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
  | "start"
  | "login"
  | "about"
  | "careers"
  | "partner"
  | "podcasts"
  | "cambridge"
  | "companySecurity"
  | "support"
  | "press"
  | "privacy"
  | "terms"
  | "contact";

type NavItem = {
  id: PageId;
  title: string;
  description: string;
  icon: LucideIcon;
};

type DetailPage = {
  id: PageId;
  category: string;
  title: string;
  description: string;
  badge: string;
  icon: LucideIcon;
  cta: string;
  stats: [string, string, string];
  bullets: string[];
  steps: string[];
  visualTitle: string;
  visualRows: [string, string, string][];
};

const brandWidth = 118;

const navGroups: Array<{
  label: string;
  menuTitle: string;
  items: NavItem[];
  feature: NavItem;
}> = [
  {
    label: "为什么选择我们",
    menuTitle: "功能",
    items: [
      { id: "finance", title: "财务团队", description: "控制软件支出和付款", icon: CreditCard },
      { id: "it", title: "IT 团队", description: "管理访问权限和安全风险", icon: MonitorCheck },
      { id: "procurement", title: "采购团队", description: "规范采购和续订流程", icon: BriefcaseBusiness },
      { id: "operations", title: "运营团队", description: "自动化软件日常运维", icon: Gauge },
    ],
    feature: {
      id: "difference",
      title: "有何不同之处",
      description: "唯一一款面向财务团队的软件管理平台",
      icon: ShieldCheck,
    },
  },
  {
    label: "解决方案",
    menuTitle: "解决方案",
    items: [
      { id: "approvals", title: "审批和采购", description: "建立战略性软件采购流程", icon: FileCheck2 },
      { id: "optimization", title: "支出优化", description: "找出浪费、重复订阅和低使用率", icon: TrendingDown },
      { id: "payments", title: "软件支付", description: "每个供应商一张虚拟卡", icon: WalletCards },
      { id: "spend", title: "企业支出", description: "差旅、报销与日常支出", icon: CreditCard },
      { id: "directory", title: "应用目录", description: "集中查看所有工具和负责人", icon: LayoutDashboard },
      { id: "analytics", title: "分析报表", description: "预算、续订和使用率仪表盘", icon: PieChart },
      { id: "accounting", title: "会计自动化", description: "发票、收据和账务导出", icon: ReceiptText },
      { id: "integrations", title: "集成", description: "连接财务、身份和协作系统", icon: PlugZap },
      { id: "engage", title: "员工参与", description: "让团队参与软件治理", icon: Users },
      { id: "onboarding", title: "入职和离职", description: "同步工具访问和权限变更", icon: Building2 },
      { id: "security", title: "软件安全", description: "减少影子 IT 和访问风险", icon: LockKeyhole },
      { id: "compliance", title: "合规", description: "审批、付款和审计留痕", icon: ShieldCheck },
    ],
    feature: {
      id: "management",
      title: "SaaS 管理",
      description: "把购买、支付、使用和续订放在同一处",
      icon: Globe2,
    },
  },
  {
    label: "资源",
    menuTitle: "资源中心",
    items: [
      { id: "blog", title: "博客", description: "软件采购和财务运营文章", icon: BookOpen },
      { id: "stories", title: "客户故事", description: "查看团队如何管控软件支出", icon: Users },
      { id: "faq", title: "常见问题", description: "平台、付款和安全问题", icon: ShieldCheck },
      { id: "webinars", title: "线上活动", description: "采购、IT 与财务协同分享", icon: MonitorCheck },
      { id: "guides", title: "指南", description: "模板、清单和最佳实践", icon: FileCheck2 },
      { id: "calculator", title: "节省计算器", description: "估算可节省的软件订阅支出", icon: Calculator },
      { id: "announcements", title: "公告", description: "产品更新和平台能力", icon: Sparkles },
      { id: "marketplace", title: "集成市场", description: "探索可连接的财务和 IT 工具", icon: PlugZap },
      { id: "datahub", title: "数据中心", description: "查看软件支出趋势和行业数据", icon: BarChart3 },
      { id: "report", title: "AI 软件报告", description: "基于真实交易数据的采购洞察", icon: PieChart },
    ],
    feature: {
      id: "buyers",
      title: "买家指南",
      description: "为财务团队准备的软件管理采购指南",
      icon: BookOpen,
    },
  },
];

const baseRows: [string, string, string][] = [
  ["需求提交", "业务负责人", "等待审批"],
  ["预算检查", "财务团队", "已通过"],
  ["虚拟卡创建", "系统自动", "已完成"],
  ["续订提醒", "30 天后", "待处理"],
];

const detailPages: Record<PageId, DetailPage> = {
  finance: {
    id: "finance",
    category: "面向财务",
    title: "减少 SaaS 浪费，为下一位员工腾出预算",
    description: "从采购申请到付款、发票、续订和会计归档，财务团队可以在一个工作台里看清成本、控制风险并释放预算。",
    badge: "支出控制",
    icon: CreditCard,
    cta: "查看财务工作台",
    stats: ["18%", "平均可节省支出", "42 小时/月"],
    bullets: ["按供应商设置预算上限", "自动收集收据和发票", "在续订前发现低使用率"],
    steps: ["发现软件", "归属负责人", "设置付款规则", "生成月末凭证"],
    visualTitle: "财务控制台",
    visualRows: baseRows,
  },
  procurement: {
    id: "procurement",
    category: "面向采购",
    title: "在团队需要时，及时买到真正需要的软件",
    description: "让团队按流程申请工具，采购、财务和 IT 一起审查预算、合同和安全要求，在速度和控制之间取得平衡。",
    badge: "采购流程",
    icon: BriefcaseBusiness,
    cta: "模拟采购流程",
    stats: ["4 步", "从申请到付款", "100% 留痕"],
    bullets: ["集中处理新工具申请", "把合同和业务理由放在同一处", "在付款前完成审批"],
    steps: ["业务申请", "财务预算", "IT 安全审查", "发卡付款"],
    visualTitle: "采购审批流",
    visualRows: [
      ["Figma 设计席位", "产品团队", "审批中"],
      ["OpenAI 企业版", "数据团队", "预算审查"],
      ["Notion", "运营团队", "已批准"],
      ["HubSpot", "市场团队", "等待资料"],
    ],
  },
  it: {
    id: "it",
    category: "面向 IT",
    title: "让软件栈保持安全，也始终处于控制之中",
    description: "集中查看应用、权限、负责人和使用状态，减少影子 IT，并让 IT 与财务共同处理访问风险。",
    badge: "访问管理",
    icon: MonitorCheck,
    cta: "查看应用目录",
    stats: ["54 个", "已发现应用", "9 个风险"],
    bullets: ["识别未登记应用", "跟踪负责人和部门", "在离职和权限变化时同步处理"],
    steps: ["同步身份目录", "发现应用", "标记风险", "通知负责人"],
    visualTitle: "应用风险面板",
    visualRows: [
      ["旧版 CRM", "无负责人", "高风险"],
      ["设计工具", "12 个成员", "正常"],
      ["AI 写作工具", "未登记付款", "待确认"],
      ["代码仓库", "SSO 开启", "安全"],
    ],
  },
  operations: {
    id: "operations",
    category: "面向运营",
    title: "让软件流程自动运行，并始终井然有序",
    description: "应用负责人、续订提醒、付款规则和发票归档自动串联，运营团队不再依赖零散表格和临时提醒。",
    badge: "运营自动化",
    icon: Gauge,
    cta: "查看运营看板",
    stats: ["13 小时", "每月节省", "0 遗漏"],
    bullets: ["续订日前自动提醒", "按部门维护预算", "记录每个工具的生命周期"],
    steps: ["创建应用", "分配负责人", "设置提醒", "归档结果"],
    visualTitle: "软件运维队列",
    visualRows: baseRows,
  },
  difference: {
    id: "difference",
    category: "有何不同",
    title: "从财务视角管理软件，而不只是记录软件清单",
    description: "把软件发现、审批、付款、发票和使用率连接起来，让每个决策都有业务和成本依据。",
    badge: "平台差异",
    icon: ShieldCheck,
    cta: "了解平台差异",
    stats: ["1 个", "统一工作台", "全流程"],
    bullets: ["管理付款而不只管理清单", "财务、IT、采购共用同一事实来源", "把节省机会放在续订前"],
    steps: ["发现", "审批", "支付", "优化"],
    visualTitle: "统一软件管理平台",
    visualRows: baseRows,
  },
  approvals: {
    id: "approvals",
    category: "解决方案",
    title: "建立一套战略性的软件采购流程",
    description: "业务团队快速提交软件需求，财务和 IT 在同一流程里完成价值、预算、安全和采购判断。",
    badge: "审批流",
    icon: FileCheck2,
    cta: "启动审批示例",
    stats: ["5 分钟", "提交申请", "3 方协作"],
    bullets: ["收集业务理由和预算", "按金额自动分派审批人", "审批通过后创建专用付款方式"],
    steps: ["填写需求", "上传报价", "审批预算", "创建付款"],
    visualTitle: "审批和采购",
    visualRows: baseRows,
  },
  optimization: {
    id: "optimization",
    category: "解决方案",
    title: "用数据洞察让软件支出始终不偏离计划",
    description: "低使用率、重复订阅和无人负责的应用都会被标记，帮助团队在续订扣款前及时采取行动。",
    badge: "节省机会",
    icon: TrendingDown,
    cta: "查看优化机会",
    stats: ["18%", "潜在节省", "12 个机会"],
    bullets: ["自动识别低使用率", "发现重复工具", "为续订谈判准备数据"],
    steps: ["分析使用率", "计算浪费", "通知负责人", "执行降本"],
    visualTitle: "节省机会列表",
    visualRows: [
      ["设计工具", "18% 使用率", "可降级"],
      ["会议录制", "重复订阅", "可合并"],
      ["自动化工具", "无人负责", "需确认"],
      ["AI 工具", "超出预算", "需审批"],
    ],
  },
  payments: {
    id: "payments",
    category: "解决方案",
    title: "把软件付款的控制权交回财务团队",
    description: "每个供应商使用独立虚拟卡，并设置预算、周期和审批规则，避免意外扣款和难以追踪的共享信用卡。",
    badge: "虚拟卡",
    icon: WalletCards,
    cta: "创建付款规则",
    stats: ["100%", "供应商隔离", "实时提醒"],
    bullets: ["设置单笔和周期限额", "续订前自动提醒", "扣款失败原因清晰可见"],
    steps: ["选择应用", "设置限额", "审批发卡", "同步凭证"],
    visualTitle: "付款卡片",
    visualRows: baseRows,
  },
  spend: {
    id: "spend",
    category: "解决方案",
    title: "一套完整的企业支出管理方案",
    description: "用同一套付款、审批和收据流程覆盖软件订阅、差旅和日常业务支出，减少月末整理工作。",
    badge: "企业支出",
    icon: CreditCard,
    cta: "查看支出页面",
    stats: ["76 张", "自动匹配收据", "1 次导出"],
    bullets: ["移动端上传收据", "按预算自动分类", "同步到会计系统"],
    steps: ["刷卡", "上传收据", "自动匹配", "导出账务"],
    visualTitle: "支出卡片",
    visualRows: [
      ["差旅", "¥3,420", "收据已匹配"],
      ["软件订阅", "¥8,260", "等待发票"],
      ["办公采购", "¥940", "已归档"],
      ["员工报销", "¥520", "待审批"],
    ],
  },
  directory: {
    id: "directory",
    category: "解决方案",
    title: "建立完整的软件工具目录",
    description: "把付款记录、团队反馈和使用率统一成软件目录，不再靠散落表格维护。",
    badge: "应用清单",
    icon: LayoutDashboard,
    cta: "查看应用目录",
    stats: ["54 个", "应用已收录", "7 个待处理"],
    bullets: ["按部门和负责人筛选", "记录合同和续订日期", "标记风险和使用状态"],
    steps: ["导入交易", "识别供应商", "绑定负责人", "维护状态"],
    visualTitle: "应用目录",
    visualRows: baseRows,
  },
  analytics: {
    id: "analytics",
    category: "解决方案",
    title: "看懂每一笔软件支出去向",
    description: "用统一仪表盘查看部门预算、续订日历、使用率和节省机会，让每一笔支出都有依据。",
    badge: "数据分析",
    icon: PieChart,
    cta: "查看分析报表",
    stats: ["8 张", "关键报表", "实时"],
    bullets: ["按部门追踪支出", "查看月度趋势", "导出管理层摘要"],
    steps: ["汇总数据", "生成指标", "标记异常", "输出报告"],
    visualTitle: "管理报表",
    visualRows: [
      ["本月支出", "¥83,420", "较上月 -8%"],
      ["续订风险", "9 个", "需处理"],
      ["低使用率", "12 个", "可优化"],
      ["未归档发票", "6 张", "待补齐"],
    ],
  },
  accounting: {
    id: "accounting",
    category: "解决方案",
    title: "让软件会计工作自动运行",
    description: "自动收集收据、匹配付款、补齐供应商信息，并为会计系统准备干净数据。",
    badge: "月末自动化",
    icon: ReceiptText,
    cta: "查看会计流程",
    stats: ["76 张", "发票自动匹配", "0 手动表格"],
    bullets: ["付款后提醒上传发票", "按供应商自动归类", "导出到会计工具"],
    steps: ["付款发生", "收据匹配", "补齐科目", "导出凭证"],
    visualTitle: "发票收集",
    visualRows: baseRows,
  },
  integrations: {
    id: "integrations",
    category: "解决方案",
    title: "把平台连接到团队使用的每一个工具",
    description: "通过集成同步用户、交易、审批和会计信息，让数据不用在工具之间来回搬。",
    badge: "集成市场",
    icon: PlugZap,
    cta: "探索集成",
    stats: ["40+", "可连接工具", "双向同步"],
    bullets: ["连接身份目录", "同步会计凭证", "把提醒推送到协作工具"],
    steps: ["选择系统", "授权连接", "映射字段", "自动同步"],
    visualTitle: "集成状态",
    visualRows: baseRows,
  },
  engage: {
    id: "engage",
    category: "解决方案",
    title: "随时掌握真实的软件使用数据",
    description: "让最了解工具的员工参与申请、反馈、使用确认和续订判断，同时保留财务控制。",
    badge: "团队协作",
    icon: Users,
    cta: "查看协作流程",
    stats: ["24 人", "参与确认", "高响应"],
    bullets: ["自动询问应用负责人", "收集团队反馈", "把反馈转成续订决策"],
    steps: ["通知负责人", "收集反馈", "确认使用", "生成建议"],
    visualTitle: "团队反馈",
    visualRows: baseRows,
  },
  onboarding: {
    id: "onboarding",
    category: "解决方案",
    title: "在一个地方管理所有软件访问权限",
    description: "新员工需要的工具、离职员工的访问和付款负责人变化，都能进入同一套标准流程。",
    badge: "人员变更",
    icon: Building2,
    cta: "查看入职流程",
    stats: ["1 天", "完成访问检查", "0 遗漏"],
    bullets: ["按角色推荐工具", "离职时提醒移除访问", "同步负责人变更"],
    steps: ["人员变动", "检查工具", "分配访问", "关闭风险"],
    visualTitle: "人员访问",
    visualRows: baseRows,
  },
  security: {
    id: "security",
    category: "解决方案",
    title: "在安全问题演变成事故之前发现它",
    description: "看清未登记应用、共享账号、无负责人供应商和可疑付款，把风险转成可分派、可关闭的任务。",
    badge: "安全治理",
    icon: LockKeyhole,
    cta: "查看安全面板",
    stats: ["9 个", "风险待处理", "SSO"],
    bullets: ["发现未授权工具", "标记无负责人应用", "记录安全审查结论"],
    steps: ["发现风险", "分派负责人", "补齐审查", "关闭任务"],
    visualTitle: "安全任务",
    visualRows: baseRows,
  },
  compliance: {
    id: "compliance",
    category: "解决方案",
    title: "从软件使用第一天到最后一天都保持合规",
    description: "每次申请、审批、付款、访问变更和发票归档都有记录，方便审计、预算复盘和供应商管理。",
    badge: "审计留痕",
    icon: ShieldCheck,
    cta: "查看合规记录",
    stats: ["100%", "流程留痕", "随时导出"],
    bullets: ["保存审批记录", "绑定付款和发票", "为审计准备证据包"],
    steps: ["申请", "审批", "付款", "归档"],
    visualTitle: "审计记录",
    visualRows: baseRows,
  },
  management: {
    id: "management",
    category: "核心平台",
    title: "SaaS 管理：管理软件生命周期的每一个节点",
    description: "从发现新工具，到审批、付款、使用反馈、续订和取消，形成一个完整闭环。",
    badge: "SaaS 管理",
    icon: Globe2,
    cta: "查看平台能力",
    stats: ["1 个", "统一平台", "全生命周期"],
    bullets: ["统一软件事实来源", "连接财务和 IT 工作流", "在续订前做出决策"],
    steps: ["发现", "购买", "支付", "优化"],
    visualTitle: "SaaS 生命周期",
    visualRows: baseRows,
  },
  blog: {
    id: "blog",
    category: "资源",
    title: "博客：软件采购、财务运营和 AI 支出洞察",
    description: "用文章沉淀软件管理方法，帮助团队建立更清晰的采购和支出规则。",
    badge: "内容中心",
    icon: BookOpen,
    cta: "阅读最新文章",
    stats: ["42 篇", "精选文章", "每周更新"],
    bullets: ["AI 软件采购策略", "续订谈判方法", "财务和 IT 协作模板"],
    steps: ["选择主题", "阅读指南", "下载模板", "应用到流程"],
    visualTitle: "最新文章",
    visualRows: [
      ["AI 工具预算", "8 分钟阅读", "热门"],
      ["续订谈判清单", "模板", "可下载"],
      ["影子 IT 治理", "指南", "推荐"],
      ["月末发票整理", "案例", "新发布"],
    ],
  },
  stories: {
    id: "stories",
    category: "资源",
    title: "客户故事：看看团队如何把软件支出管起来",
    description: "从发现工具到减少浪费，真实团队的工作流可以帮助你判断适合自己的落地方式。",
    badge: "客户案例",
    icon: Users,
    cta: "查看客户故事",
    stats: ["200+", "用户反馈", "4.8/5"],
    bullets: ["财务团队如何节省时间", "IT 如何发现风险", "采购如何标准化流程"],
    steps: ["选择行业", "查看挑战", "学习流程", "复用模板"],
    visualTitle: "案例库",
    visualRows: baseRows,
  },
  faq: {
    id: "faq",
    category: "资源",
    title: "常见问题：上线前你可能想确认的事",
    description: "覆盖软件发现、付款方式、审批规则、安全、发票和数据同步等关键问题。",
    badge: "FAQ",
    icon: ShieldCheck,
    cta: "查看问题列表",
    stats: ["24 个", "常见问题", "按主题分类"],
    bullets: ["如何发现现有订阅", "如何设置付款限额", "如何导出会计数据"],
    steps: ["选择主题", "查看答案", "联系团队", "配置流程"],
    visualTitle: "问题中心",
    visualRows: baseRows,
  },
  webinars: {
    id: "webinars",
    category: "资源",
    title: "线上活动：和财务、IT、采购团队一起学习",
    description: "围绕软件采购、AI 支出治理和续订管理定期举办直播和回放。",
    badge: "线上活动",
    icon: MonitorCheck,
    cta: "报名活动",
    stats: ["3 场", "近期活动", "可回放"],
    bullets: ["AI 软件治理", "续订谈判", "财务自动化"],
    steps: ["选择主题", "报名", "参加直播", "下载资料"],
    visualTitle: "活动日历",
    visualRows: baseRows,
  },
  guides: {
    id: "guides",
    category: "资源",
    title: "指南：把软件管理流程落到表单、规则和模板里",
    description: "为采购申请、续订复盘、供应商审查和预算管理准备可复用资料。",
    badge: "指南库",
    icon: FileCheck2,
    cta: "下载指南",
    stats: ["15 份", "模板指南", "可复用"],
    bullets: ["采购申请模板", "续订复盘清单", "供应商安全问卷"],
    steps: ["选择模板", "下载", "调整字段", "导入流程"],
    visualTitle: "模板库",
    visualRows: baseRows,
  },
  calculator: {
    id: "calculator",
    category: "资源",
    title: "节省计算器：估算你能从软件订阅中省下多少",
    description: "输入团队规模、工具数量和月度支出，快速估算可优化空间。",
    badge: "计算器",
    icon: Calculator,
    cta: "开始计算",
    stats: ["18%", "参考节省率", "3 分钟"],
    bullets: ["估算低使用率浪费", "识别重复工具", "生成节省建议"],
    steps: ["输入支出", "填写工具数量", "选择团队规模", "得到建议"],
    visualTitle: "节省估算",
    visualRows: baseRows,
  },
  announcements: {
    id: "announcements",
    category: "资源",
    title: "公告：查看产品更新和新能力",
    description: "按时间线查看平台能力、集成、报表和安全相关更新。",
    badge: "更新日志",
    icon: Sparkles,
    cta: "查看公告",
    stats: ["每月", "产品更新", "可订阅"],
    bullets: ["新集成", "报表改进", "安全增强"],
    steps: ["查看更新", "了解影响", "启用能力", "通知团队"],
    visualTitle: "更新列表",
    visualRows: baseRows,
  },
  marketplace: {
    id: "marketplace",
    category: "资源",
    title: "集成市场：发现可连接的系统",
    description: "探索身份、会计、协作和数据工具，把软件管理融入现有流程。",
    badge: "市场",
    icon: PlugZap,
    cta: "浏览集成",
    stats: ["40+", "集成工具", "快速连接"],
    bullets: ["会计系统", "身份目录", "协作通知"],
    steps: ["选择集成", "授权", "映射数据", "启用同步"],
    visualTitle: "集成市场",
    visualRows: baseRows,
  },
  datahub: {
    id: "datahub",
    category: "数据中心",
    title: "用真实软件支出数据看清市场变化",
    description: "按行业、公司规模和软件类别查看支出趋势，为预算、谈判和采购决策提供参考。",
    badge: "行业数据",
    icon: BarChart3,
    cta: "查看数据中心",
    stats: ["1000+", "软件供应商", "持续更新"],
    bullets: ["查看热门软件类别", "比较行业支出趋势", "了解 AI 工具增长"],
    steps: ["选择行业", "筛选规模", "比较趋势", "导出洞察"],
    visualTitle: "软件支出数据",
    visualRows: [
      ["AI 与自动化", "同比增长 42%", "快速增长"],
      ["协作工具", "平均 12 款", "保持稳定"],
      ["设计软件", "席位利用率 68%", "可优化"],
      ["财务工具", "续订率 91%", "高粘性"],
    ],
  },
  report: {
    id: "report",
    category: "研究报告",
    title: "AI 正在重塑软件采购，预算规则也需要升级",
    description: "基于真实软件交易数据，分析 AI 工具的增长、重复采购风险和财务团队需要建立的新控制方式。",
    badge: "AI 软件报告",
    icon: PieChart,
    cta: "阅读完整报告",
    stats: ["42%", "AI 支出增长", "真实数据"],
    bullets: ["AI 工具增长趋势", "重复采购和影子 IT", "新的预算与审批策略"],
    steps: ["查看数据", "识别风险", "调整规则", "制定策略"],
    visualTitle: "报告摘要",
    visualRows: [
      ["AI 工具数量", "同比 +42%", "上升"],
      ["重复订阅", "平均 3.2 个", "需治理"],
      ["无负责人应用", "占比 14%", "有风险"],
      ["审批覆盖率", "目标 100%", "建议"],
    ],
  },
  buyers: {
    id: "buyers",
    category: "资源",
    title: "买家指南：评估软件管理平台时该看什么",
    description: "从采购、财务、IT、安全和落地成本五个角度，判断什么方案适合你的团队。",
    badge: "买家指南",
    icon: BookOpen,
    cta: "打开指南",
    stats: ["5 个", "评估维度", "清单"],
    bullets: ["付款控制能力", "审批和审计留痕", "是否支持团队协作"],
    steps: ["定义目标", "比较能力", "估算 ROI", "启动试点"],
    visualTitle: "评估清单",
    visualRows: baseRows,
  },
  pricing: {
    id: "pricing",
    category: "定价",
    title: "按团队规模和使用场景选择合适方案",
    description: "用清晰套餐覆盖软件管理、审批、付款、分析和会计自动化能力。",
    badge: "定价",
    icon: Calculator,
    cta: "查看方案",
    stats: ["3 档", "团队方案", "可定制"],
    bullets: ["基础软件目录", "审批和付款控制", "高级分析和集成"],
    steps: ["选择规模", "确认功能", "预约演示", "开始配置"],
    visualTitle: "方案对比",
    visualRows: [
      ["Starter", "软件目录", "适合小团队"],
      ["Growth", "审批与付款", "推荐"],
      ["Scale", "分析和集成", "可定制"],
      ["Enterprise", "安全和合规", "联系销售"],
    ],
  },
  demo: {
    id: "demo",
    category: "预约演示",
    title: "预约一次产品演示",
    description: "填写你的团队规模、当前工具数量和最想解决的问题，我们会用一条完整流程演示平台。",
    badge: "演示",
    icon: FileCheck2,
    cta: "提交预约",
    stats: ["30 分钟", "完整演示", "定制流程"],
    bullets: ["演示审批采购", "演示虚拟卡付款", "演示月末发票整理"],
    steps: ["填写信息", "选择时间", "确认需求", "进入演示"],
    visualTitle: "预约信息",
    visualRows: baseRows,
  },
  start: {
    id: "start",
    category: "开始使用",
    title: "从导入第一批软件支出开始",
    description: "连接交易、识别供应商、分配负责人，再逐步启用审批和付款控制。",
    badge: "启动",
    icon: Zap,
    cta: "创建工作区",
    stats: ["15 分钟", "完成初始化", "可试用"],
    bullets: ["导入交易记录", "确认软件列表", "邀请团队成员"],
    steps: ["创建工作区", "导入数据", "确认应用", "启用规则"],
    visualTitle: "启动清单",
    visualRows: baseRows,
  },
  login: {
    id: "login",
    category: "登录",
    title: "登录你的软件管理工作区",
    description: "这里是登录页面占位。后续接入账户系统后，可替换为真实登录流程。",
    badge: "登录",
    icon: LockKeyhole,
    cta: "继续登录",
    stats: ["SSO", "安全登录", "双因素"],
    bullets: ["邮箱登录", "企业 SSO", "双因素验证"],
    steps: ["输入邮箱", "验证身份", "选择工作区", "进入控制台"],
    visualTitle: "登录面板",
    visualRows: baseRows,
  },
  about: {
    id: "about",
    category: "公司",
    title: "我们希望让软件采购和付款变得更透明",
    description: "团队围绕一个简单目标工作：让现代公司能够更快采用好软件，同时保持财务控制和运营秩序。",
    badge: "关于我们",
    icon: Building2,
    cta: "了解公司",
    stats: ["全球", "服务团队", "持续成长"],
    bullets: ["财务优先的产品理念", "跨部门协作", "透明的软件支出"],
    steps: ["理解问题", "连接数据", "设计流程", "持续优化"],
    visualTitle: "公司概览",
    visualRows: baseRows,
  },
  careers: {
    id: "careers",
    category: "公司",
    title: "加入我们，一起改善企业购买软件的方式",
    description: "我们寻找愿意解决真实运营问题、重视用户体验并喜欢跨团队协作的人。",
    badge: "招聘",
    icon: Users,
    cta: "查看开放职位",
    stats: ["多地", "灵活协作", "开放岗位"],
    bullets: ["产品与工程", "客户与运营", "市场与销售"],
    steps: ["查看职位", "提交申请", "团队交流", "加入我们"],
    visualTitle: "招聘流程",
    visualRows: baseRows,
  },
  partner: {
    id: "partner",
    category: "合作伙伴",
    title: "与会计、咨询和技术伙伴共同服务客户",
    description: "合作伙伴可以把软件支出管理加入自己的服务组合，为客户提供更完整的财务运营能力。",
    badge: "伙伴计划",
    icon: PlugZap,
    cta: "申请成为伙伴",
    stats: ["多类型", "伙伴模式", "联合服务"],
    bullets: ["会计与财务顾问", "技术集成伙伴", "联合市场活动"],
    steps: ["提交申请", "确认模式", "完成培训", "共同服务"],
    visualTitle: "伙伴计划",
    visualRows: baseRows,
  },
  podcasts: {
    id: "podcasts",
    category: "播客",
    title: "听财务和运营负责人分享真实经验",
    description: "围绕创业、财务运营、软件采购和团队管理展开对话，提供可直接复用的经验。",
    badge: "财务播客",
    icon: MonitorCheck,
    cta: "收听节目",
    stats: ["多期", "真实访谈", "持续更新"],
    bullets: ["财务负责人访谈", "创业团队经验", "运营方法分享"],
    steps: ["选择节目", "收听", "查看摘要", "订阅更新"],
    visualTitle: "最新节目",
    visualRows: baseRows,
  },
  cambridge: {
    id: "cambridge",
    category: "合作",
    title: "通过体育合作连接团队、社区和共同成长",
    description: "品牌合作不只是曝光，也可以围绕团队精神、长期投入和社区价值建立连接。",
    badge: "球队合作",
    icon: Users,
    cta: "了解合作故事",
    stats: ["长期", "合作关系", "社区"],
    bullets: ["共同价值", "社区参与", "品牌故事"],
    steps: ["建立连接", "共同策划", "参与活动", "分享成果"],
    visualTitle: "合作项目",
    visualRows: baseRows,
  },
  companySecurity: {
    id: "companySecurity",
    category: "安全",
    title: "用清晰的控制、权限和流程保护客户数据",
    description: "安全能力覆盖身份访问、数据处理、审计记录和运营流程，帮助团队放心管理软件支出。",
    badge: "安全中心",
    icon: LockKeyhole,
    cta: "查看安全说明",
    stats: ["持续", "安全监控", "严格权限"],
    bullets: ["访问权限控制", "数据传输与存储保护", "审计和事件响应"],
    steps: ["识别风险", "实施控制", "持续监控", "响应事件"],
    visualTitle: "安全控制",
    visualRows: baseRows,
  },
  support: {
    id: "support",
    category: "客户支持",
    title: "透明展示支持响应和服务质量",
    description: "用可量化指标呈现响应速度、解决效率和客户满意度，让服务体验更加透明。",
    badge: "支持指标",
    icon: Gauge,
    cta: "查看支持数据",
    stats: ["快速", "首次响应", "高满意度"],
    bullets: ["响应时间", "问题解决率", "客户满意度"],
    steps: ["提交问题", "确认优先级", "跟进解决", "反馈体验"],
    visualTitle: "支持表现",
    visualRows: baseRows,
  },
  press: {
    id: "press",
    category: "媒体中心",
    title: "新闻、品牌资料和公司动态",
    description: "集中查看媒体报道、新闻稿、品牌资源和公司重要动态。",
    badge: "媒体",
    icon: BookOpen,
    cta: "查看媒体资料",
    stats: ["新闻", "品牌资源", "公司动态"],
    bullets: ["新闻稿", "品牌素材", "媒体联系"],
    steps: ["选择资料", "查看内容", "下载资源", "联系团队"],
    visualTitle: "媒体资料",
    visualRows: baseRows,
  },
  privacy: {
    id: "privacy",
    category: "法律",
    title: "隐私政策",
    description: "说明我们如何收集、使用、保存和保护个人信息，以及用户可以如何行使自己的数据权利。",
    badge: "隐私",
    icon: ShieldCheck,
    cta: "阅读隐私政策",
    stats: ["透明", "数据处理", "用户权利"],
    bullets: ["收集哪些信息", "如何使用信息", "如何联系我们"],
    steps: ["阅读条款", "了解权利", "管理偏好", "提出请求"],
    visualTitle: "隐私说明",
    visualRows: baseRows,
  },
  terms: {
    id: "terms",
    category: "法律",
    title: "服务条款",
    description: "说明产品使用、账户责任、服务范围、付款和双方权利义务等基础约定。",
    badge: "条款",
    icon: FileCheck2,
    cta: "阅读服务条款",
    stats: ["清晰", "服务约定", "责任边界"],
    bullets: ["服务使用规则", "账户和付款责任", "知识产权与终止"],
    steps: ["阅读条款", "确认适用范围", "接受约定", "开始使用"],
    visualTitle: "条款摘要",
    visualRows: baseRows,
  },
  contact: {
    id: "contact",
    category: "联系我们",
    title: "告诉我们你想解决的软件管理问题",
    description: "无论是采购、支付、发票、续订还是安全治理，都可以留下信息与团队交流。",
    badge: "联系",
    icon: Users,
    cta: "提交联系信息",
    stats: ["快速", "团队回复", "按需沟通"],
    bullets: ["产品咨询", "合作伙伴", "媒体与其他问题"],
    steps: ["选择主题", "填写信息", "团队回复", "继续沟通"],
    visualTitle: "联系表单",
    visualRows: baseRows,
  },
  home: {} as DetailPage,
};

const pageFallback = detailPages.management;

const logoStrip = ["Sofar", "Countingup", "trivago", "havaianas", "fever", "Bond", "Jiminny"];

const appRows = [
  ["Slack", "林一", "虚拟卡", "¥28,000", "今天", "96%"],
  ["OpenAI", "数据团队", "虚拟卡", "¥175,000", "4 天后", "61%"],
  ["BambooHR", "人事", "虚拟卡", "¥7,200", "6 月 09 日", "88%"],
  ["Adobe CC", "创意团队", "虚拟卡", "¥21,400", "6 月 12 日", "18%"],
  ["Stripe", "财务", "虚拟卡", "¥106,000", "6 月 19 日", "74%"],
  ["Monday", "产品", "虚拟卡", "¥50,200", "7 月 02 日", "43%"],
];

const featureCards = [
  {
    icon: CreditCard,
    title: "用专用虚拟卡控制软件支出",
    body: "每个供应商独立限额、独立负责人，续订扣款前先确认，减少意外支出。",
    action: "管理付款",
    tint: "mint",
    target: "payments" as PageId,
  },
  {
    icon: FileCheck2,
    title: "把采购、续订和取消变成流程",
    body: "业务提交需求，财务看预算，IT 看安全，审批通过后再付款。",
    action: "控制采购",
    tint: "violet",
    target: "approvals" as PageId,
  },
  {
    icon: ReceiptText,
    title: "月末发票和凭证自动整理",
    body: "付款、收据、供应商和科目信息自动关联，减少手动追发票。",
    action: "自动化日常工作",
    tint: "amber",
    target: "accounting" as PageId,
  },
  {
    icon: TrendingDown,
    title: "在续订前发现节省机会",
    body: "低使用率、重复订阅和无人负责的应用会被提前标记出来。",
    action: "优化软件支出",
    tint: "coral",
    target: "optimization" as PageId,
  },
];

const platformTracks = [
  {
    label: "管理",
    icon: Gauge,
    items: ["采购申请", "审批流程", "预算规则", "使用率提醒"],
  },
  {
    label: "支付",
    icon: WalletCards,
    items: ["虚拟卡", "支出限额", "发票归档", "报销流程"],
  },
];

const testimonials = [
  {
    quote: "我们终于能在一个地方看清哪些软件还在用、什么时候续订、谁负责每张账单。",
    name: "刘静",
    role: "财务负责人",
  },
  {
    quote: "续订视图让谈判提前发生，而不是等扣款完成后才发现预算超了。",
    name: "何然",
    role: "财务经理",
  },
  {
    quote: "卡片、审批、收据和负责人都连起来之后，月末结账明显轻松了。",
    name: "陈曼",
    role: "控制经理",
  },
];

const savingsInputs = [
  { label: "发现应用", value: 54 },
  { label: "自动归档发票", value: 76 },
  { label: "每月节省小时", value: 13 },
];

function pageFromHash(): PageId {
  const raw = window.location.hash.replace("#/", "").replace("#", "");
  if (!raw) return "home";
  return (raw in detailPages ? raw : "home") as PageId;
}

function navigateTo(id: PageId) {
  window.location.hash = id === "home" ? "/" : `/${id}`;
}

function Mark({ compact = false, inverse = false }: { compact?: boolean; inverse?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-9 w-9 grid-cols-2 gap-1 rounded-[10px] bg-[#cbf8ff] p-1.5 shadow-sm">
        <span className="rounded-br-lg rounded-tl-md bg-[#2ecad3]" />
        <span className="rounded-bl-lg rounded-tr-md bg-[#72dde2]" />
        <span className="rounded-br-lg rounded-tl-md bg-[#b7edf0]" />
        <span className="rounded-bl-lg rounded-tr-md bg-[#42bec6]" />
      </span>
      {!compact && (
        <span
          aria-label="品牌名待定"
          className={`brand-slot ${inverse ? "brand-slot-inverse" : ""}`}
          style={{ width: brandWidth }}
        />
      )}
    </div>
  );
}

function Button({
  children,
  variant = "primary",
  className = "",
  onClick,
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "dark";
  className?: string;
  onClick?: () => void;
}) {
  const variants = {
    primary:
      "bg-[#cafbff] text-[#17204f] hover:bg-white focus-visible:outline-[#cafbff] shadow-[0_18px_36px_rgba(35,224,232,0.22)]",
    secondary:
      "border border-white/35 bg-white/5 text-white hover:bg-white/12 focus-visible:outline-white",
    ghost:
      "border border-slate-200 bg-white text-slate-900 hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-[#35c7ce]",
    dark:
      "bg-[#20245f] text-white hover:bg-[#171b4d] focus-visible:outline-[#35c7ce]",
  };

  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-5 py-3 text-sm font-bold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${variants[variant]} ${className}`}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function NavItemButton({ item, onNavigate }: { item: NavItem; onNavigate: (id: PageId) => void }) {
  const Icon = item.icon;

  return (
    <button className="mega-link" onClick={() => onNavigate(item.id)} type="button">
      <span className="mega-icon">
        <Icon className="h-5 w-5" />
      </span>
      <span>
        <strong>{item.title}</strong>
        <small>{item.description}</small>
      </span>
    </button>
  );
}

function Nav({ currentPage, onNavigate }: { currentPage: PageId; onNavigate: (id: PageId) => void }) {
  const [open, setOpen] = useState(false);
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const showGroup = (label: string) => {
    cancelClose();
    setOpenGroup(label);
  };

  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = setTimeout(() => {
      setOpenGroup(null);
      closeTimer.current = null;
    }, 2000);
  };

  useEffect(() => () => cancelClose(), []);

  const navigateAndClose = (id: PageId) => {
    cancelClose();
    setOpenGroup(null);
    onNavigate(id);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#3f469e]/95 text-white backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
        <button aria-label="返回首页" className="brand-button" onClick={() => onNavigate("home")} type="button">
          <Mark inverse />
        </button>

        <nav className="hidden items-center gap-1 lg:flex">
          {navGroups.map(group => (
            <div
              className="relative"
              key={group.label}
              onMouseEnter={() => showGroup(group.label)}
              onMouseLeave={scheduleClose}
            >
              <button
                aria-expanded={openGroup === group.label}
                className="inline-flex items-center gap-1 rounded-md px-4 py-2 text-sm font-semibold text-white/88 transition hover:bg-white/10"
                onClick={() => {
                  cancelClose();
                  setOpenGroup(value => value === group.label ? null : group.label);
                }}
                type="button"
              >
                {group.label}
                <ChevronDown className="h-4 w-4" />
              </button>
              <div
                className={`mega-menu absolute left-1/2 top-full w-[704px] -translate-x-1/2 rounded-xl border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl transition ${
                  openGroup === group.label
                    ? "pointer-events-auto translate-y-2 opacity-100"
                    : "pointer-events-none translate-y-3 opacity-0"
                }`}
                onMouseEnter={cancelClose}
                onMouseLeave={scheduleClose}
              >
                <div className="border-b border-slate-100 px-8 py-5 text-sm font-black text-[#20245f]">
                  {group.menuTitle}
                </div>
                <div className="grid grid-cols-2 gap-x-12 gap-y-8 px-8 py-7">
                  {group.items.map(item => (
                    <NavItemButton item={item} key={item.id} onNavigate={navigateAndClose} />
                  ))}
                </div>
                <button className="mega-feature" onClick={() => navigateAndClose(group.feature.id)} type="button">
                  <span className="mega-icon active">
                    <group.feature.icon className="h-5 w-5" />
                  </span>
                  <span>
                    <strong>{group.feature.title}</strong>
                    <small>{group.feature.description}</small>
                  </span>
                </button>
              </div>
            </div>
          ))}
          <button
            className={`rounded-md px-4 py-2 text-sm font-semibold transition hover:bg-white/10 ${currentPage === "buyers" ? "text-white" : "text-white/88"}`}
            onClick={() => onNavigate("buyers")}
            type="button"
          >
            买家指南
          </button>
          <button
            className={`rounded-md px-4 py-2 text-sm font-semibold transition hover:bg-white/10 ${currentPage === "pricing" ? "text-white" : "text-white/88"}`}
            onClick={() => onNavigate("pricing")}
            type="button"
          >
            定价
          </button>
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <button className="text-sm font-semibold text-white/78 transition hover:text-white" onClick={() => onNavigate("login")} type="button">
            登录
          </button>
          <Button variant="secondary" className="min-h-10 px-8 py-2" onClick={() => onNavigate("demo")}>
            预约演示
          </Button>
        </div>

        <button
          aria-label={open ? "关闭菜单" : "打开菜单"}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-white/25 lg:hidden"
          onClick={() => setOpen(value => !value)}
          type="button"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="mobile-nav border-t border-white/10 px-5 pb-5 lg:hidden">
          <div className="grid gap-2 pt-3">
            {navGroups.flatMap(group => [group.feature, ...group.items]).map(item => (
              <button className="rounded-md px-3 py-3 text-left text-sm font-semibold text-white/90 hover:bg-white/10" key={item.id} onClick={() => { onNavigate(item.id); setOpen(false); }} type="button">
                {item.title}
              </button>
            ))}
            <button className="rounded-md px-3 py-3 text-left text-sm font-semibold text-white/90 hover:bg-white/10" onClick={() => { onNavigate("pricing"); setOpen(false); }} type="button">
              定价
            </button>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <Button variant="secondary" className="w-full px-3" onClick={() => { onNavigate("demo"); setOpen(false); }}>
                演示
              </Button>
              <Button className="w-full px-3" onClick={() => { onNavigate("start"); setOpen(false); }}>
                开始
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

function Announcement({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  return (
    <div className="bg-[#12163e] px-5 py-3 text-center text-sm font-semibold text-white">
      <button className="inline-flex items-center justify-center gap-2 text-white/90 hover:text-white" onClick={() => onNavigate("buyers")} type="button">
        <Sparkles className="h-4 w-4 text-[#cafbff]" />
        新报告：为 AI 软件采购建立更聪明的预算和审批策略
        <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}

function HeroDashboard({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  return (
    <div className="hero-dashboard mx-auto mt-16 w-full max-w-6xl">
      <div className="dashboard-shell">
        <aside className="dashboard-sidebar" aria-hidden="true">
          <div className="mb-7 flex items-center gap-2">
            <Mark compact />
            <div className="h-2.5 w-20 rounded-full bg-slate-200" />
          </div>
          {["仪表盘", "应用", "我的任务", "交易", "报表", "合规"].map((item, index) => (
            <div className={`sidebar-item ${index === 1 ? "active" : ""}`} key={item}>
              <span />
              <strong>{item}</strong>
            </div>
          ))}
          <div className="low-usage">
            <div className="flex items-center justify-between">
              <strong>低使用率</strong>
              <X className="h-3.5 w-3.5" />
            </div>
            <p>Adobe CC 使用率降至 18%。请在续订前检查席位。</p>
          </div>
        </aside>

        <main className="dashboard-main">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="account-select">人民币账户</div>
              <h3>应用</h3>
            </div>
            <button className="add-app" onClick={() => onNavigate("directory")} type="button">
              添加新应用
            </button>
          </div>

          <div className="notice">
            <Zap className="h-4 w-4" />
            <span>还有更多应用等待纳入控制。</span>
            <strong>新</strong>
          </div>

          <div className="searchbar">
            <Search className="h-4 w-4" />
            <span>按名称或负责人搜索...</span>
            <button onClick={() => onNavigate("finance")} type="button">财务视图</button>
          </div>

          <div className="app-table">
            <div className="table-head">
              <span>名称</span>
              <span>负责人</span>
              <span>付款</span>
              <span>下次扣款</span>
              <span>使用率</span>
            </div>
            {appRows.map(([app, owner, method, amount, date, usage], index) => (
              <div className="table-row" key={app}>
                <span className="app-name">
                  <i className={`app-dot dot-${index}`} />
                  {app}
                </span>
                <span>{owner}</span>
                <span>{method}</span>
                <span>
                  <strong>{amount}</strong>
                  <small>{date}</small>
                </span>
                <span>
                  <em style={{ width: usage }} />
                  {usage}
                </span>
              </div>
            ))}
          </div>
        </main>

        <section className="spend-card">
          <div className="flex items-center justify-between">
            <strong>软件支出</strong>
            <BarChart3 className="h-4 w-4 text-[#2ecad3]" />
          </div>
          <p>54 个应用</p>
          <h4>¥98,540</h4>
          <span>本月已支出</span>
          <div className="mini-chart" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
            <i />
          </div>
        </section>
      </div>
    </div>
  );
}

function Hero({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  return (
    <section className="hero relative overflow-hidden bg-[#232765] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_15%,rgba(74,213,221,0.22),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0))]" />
      <div className="relative mx-auto max-w-7xl px-5 pb-24 pt-20 text-center lg:px-8 lg:pb-32">
        <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/18 bg-white/7 px-4 py-2 text-sm font-bold text-white/88">
          <span className="grid h-5 w-5 place-items-center rounded-full bg-[#ff6247] text-[10px] text-white">G2</span>
          4.8 分，来自 200+ 条评价
        </div>
        <h1 className="mx-auto mt-8 max-w-5xl text-balance text-5xl font-extrabold leading-[0.95] tracking-normal md:text-7xl lg:text-8xl">
          <span className="block sm:inline">AI 正在放大</span>{" "}
          <span className="block sm:inline">你的软件栈。</span>{" "}
          <span className="block sm:inline">我们帮你</span>{" "}
          <span className="block sm:inline">把它管住。</span>
        </h1>
        <p className="mx-auto mt-7 max-w-3xl text-balance text-lg font-medium leading-8 text-white/76 md:text-xl">
          看清每一个 SaaS 和 AI 工具，理解真实使用情况，并从一个财务优先的平台控制每一次付款。
        </p>
        <p className="mt-3 text-base font-bold text-[#cafbff]">
          面向财务团队的软件订阅管理。
        </p>
        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button onClick={() => onNavigate("start")}>
            开始使用 <ArrowRight className="h-4 w-4" />
          </Button>
          <Button variant="secondary" onClick={() => onNavigate("demo")}>
            预约演示
          </Button>
        </div>

        <div className="hero-logos mt-12 flex flex-wrap items-center justify-center gap-x-10 gap-y-4 text-white/58">
          {logoStrip.slice(0, 5).map(logo => (
            <span className="font-serif text-2xl font-bold italic tracking-normal" key={logo}>
              {logo}
            </span>
          ))}
        </div>

        <HeroDashboard onNavigate={onNavigate} />
      </div>
    </section>
  );
}

function LogoCloud() {
  return (
    <section className="border-b border-slate-100 bg-white py-10">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-x-12 gap-y-5 px-5 text-slate-400 lg:px-8">
        {logoStrip.map(logo => (
          <span className="text-lg font-black tracking-tight" key={logo}>
            {logo}
          </span>
        ))}
      </div>
    </section>
  );
}

function SubscriptionControl({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  const [active, setActive] = useState(0);
  const selected = featureCards[active];
  const Icon = selected.icon;

  return (
    <section className="bg-white py-24" id="platform">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[0.95fr_1.05fr] lg:items-center lg:px-8">
        <div>
          <p className="eyebrow">完整可见性</p>
          <h2 className="section-title">所有软件订阅都可见、可控、可追踪</h2>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
            把付款控制、审批、续订、使用率和供应商负责人放进同一个运营视图，让财务、IT、采购使用同一套事实。
          </p>
          <div className="mt-8 grid gap-3">
            {featureCards.map((feature, index) => {
              const FeatureIcon = feature.icon;
              return (
                <button
                  className={`feature-tab ${active === index ? "active" : ""}`}
                  key={feature.title}
                  onClick={() => setActive(index)}
                  type="button"
                >
                  <span className={`feature-icon ${feature.tint}`}>
                    <FeatureIcon className="h-5 w-5" />
                  </span>
                  <span>
                    <strong>{feature.title}</strong>
                    <small>{feature.action}</small>
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="product-stage">
          <div className={`stage-accent ${selected.tint}`} />
          <div className="feature-visual">
            <div className="flex items-center justify-between">
              <span className={`visual-icon ${selected.tint}`}>
                <Icon className="h-6 w-6" />
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">实时控制</span>
            </div>
            <h3>{selected.title}</h3>
            <p>{selected.body}</p>
            <div className="approval-flow">
              {["提交申请", "预算检查", "财务审批", "创建虚拟卡"].map((step, index) => (
                <div className="flow-step" key={step}>
                  <span>{index + 1}</span>
                  <strong>{step}</strong>
                  <Check className="h-4 w-4" />
                </div>
              ))}
            </div>
            <div className="renewal-strip">
              <div>
                <small>下次续订</small>
                <strong>Adobe Creative Cloud</strong>
              </div>
              <div>
                <small>潜在节省</small>
                <strong>¥28,000</strong>
              </div>
              <Button variant="dark" className="min-h-10 px-4 py-2" onClick={() => onNavigate(selected.target)}>
                查看页面
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function PlatformLoop() {
  return (
    <section className="bg-[#f6fafb] py-24">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <p className="eyebrow">管理加支付</p>
          <h2 className="section-title">把简单的软件管理和强大的付款控制结合起来</h2>
        </div>

        <div className="mt-16 grid gap-8 lg:grid-cols-[1fr_1.1fr_1fr] lg:items-center">
          {platformTracks.map(track => {
            const TrackIcon = track.icon;
            return (
              <div className="track-panel" key={track.label}>
                <div className="mb-5 flex items-center gap-3">
                  <span className="grid h-11 w-11 place-items-center rounded-md bg-[#20245f] text-[#cafbff]">
                    <TrackIcon className="h-5 w-5" />
                  </span>
                  <h3>{track.label}</h3>
                </div>
                <div className="grid gap-3">
                  {track.items.map(item => (
                    <div className="track-item" key={item}>
                      <Check className="h-4 w-4" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          <div className="platform-map lg:order-none">
            <div className="map-ring outer" />
            <div className="map-ring middle" />
            <div className="map-center">
              <Mark compact />
            </div>
            {["Slack", "Figma", "Xero", "QuickBooks", "Atlassian", "OpenAI"].map((app, index) => (
              <span className={`app-node node-${index}`} key={app}>
                {app.slice(0, 2)}
              </span>
            ))}
            <span className="map-pill pill-a">影子 IT</span>
            <span className="map-pill pill-b">软件支出</span>
            <span className="map-pill pill-c">入职流程</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function SpendSection({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  return (
    <section className="overflow-hidden bg-[#20245f] py-24 text-white">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[0.85fr_1.15fr] lg:items-center lg:px-8">
        <div>
          <p className="eyebrow text-[#cafbff]">企业支出</p>
          <h2 className="section-title text-white">把订阅、差旅和日常支出都放进同一套规则</h2>
          <p className="mt-6 text-lg leading-8 text-white/72">
            将软件订阅卡与日常企业支出、报销、收据上传和会计同步连接起来，让财务流程更干净。
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            {["实体卡", "收据扫描", "会计同步", "报销流程"].map(item => (
              <span className="rounded-full border border-white/16 bg-white/8 px-4 py-2 text-sm font-bold text-white/80" key={item}>
                {item}
              </span>
            ))}
          </div>
          <Button className="mt-9" onClick={() => onNavigate("spend")}>
            了解更多 <ArrowRight className="h-4 w-4" />
          </Button>
        </div>

        <div className="mobile-stack">
          <div className="phone phone-back">
            <div className="phone-notch" />
            <div className="card-preview">
              <span>Business</span>
              <strong>•••• 2859</strong>
            </div>
            <div className="receipt">
              <ReceiptText className="h-5 w-5" />
              <div>
                <strong>收据已匹配</strong>
                <small>会计数据已准备</small>
              </div>
            </div>
          </div>
          <div className="phone phone-front">
            <div className="phone-notch" />
            <h3>支出</h3>
            <div className="balance">¥58,420</div>
            <div className="phone-bars">
              <i style={{ height: "38%" }} />
              <i style={{ height: "62%" }} />
              <i style={{ height: "48%" }} />
              <i style={{ height: "78%" }} />
              <i style={{ height: "55%" }} />
            </div>
            <div className="transaction">
              <span>差旅</span>
              <strong>¥3,260</strong>
            </div>
            <div className="transaction">
              <span>软件</span>
              <strong>¥9,120</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stories({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  return (
    <section className="bg-white py-24" id="stories">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <p className="eyebrow">客户成功故事</p>
            <h2 className="section-title">看看现代财务团队如何评价这种工作方式</h2>
          </div>
          <button className="rating-pill" onClick={() => onNavigate("stories")} type="button">
            <span>G2</span>
            <strong>4.8/5</strong>
            <small>200+ 条评价</small>
          </button>
        </div>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {testimonials.map((story, index) => (
            <article className="testimonial" key={story.name}>
              <div className="stars">★★★★★</div>
              <p>“{story.quote}”</p>
              <div className="mt-8 flex items-center gap-3">
                <span className={`avatar avatar-${index}`}>{story.name[0]}</span>
                <div>
                  <strong>{story.name}</strong>
                  <small>{story.role}</small>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function CalculatorCta({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  const total = useMemo(
    () => savingsInputs.reduce((sum, item) => sum + item.value, 0),
    [],
  );

  return (
    <section className="bg-[#f6fafb] py-24" id="calculator">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[1fr_0.8fr] lg:items-center lg:px-8">
        <div>
          <p className="eyebrow">节省计算器</p>
          <h2 className="section-title">估算你的软件订阅能节省多少</h2>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
            回答几个关于团队规模、应用数量和支出的简单问题，把软件栈变成更清晰的财务计划。
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button variant="dark" onClick={() => onNavigate("calculator")}>
              现在计算 <ArrowRight className="h-4 w-4" />
            </Button>
            <Button variant="ghost" onClick={() => onNavigate("demo")}>
              预约演示
            </Button>
          </div>
        </div>

        <div className="calculator-card">
          <div className="flex items-center justify-between">
            <strong>预计影响</strong>
            <ShieldCheck className="h-5 w-5 text-[#2ecad3]" />
          </div>
          <div className="impact-number">{total}%</div>
          <span>模拟控制得分</span>
          <div className="mt-7 grid gap-4">
            {savingsInputs.map(item => (
              <div className="metric-row" key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function DetailVisual({ page }: { page: DetailPage }) {
  return (
    <div className="detail-visual">
      <div className="flex items-center justify-between">
        <div>
          <small>{page.badge}</small>
          <h3>{page.visualTitle}</h3>
        </div>
        <span className="rounded-full bg-[#dffbfc] px-3 py-1 text-xs font-black text-[#168890]">实时</span>
      </div>
      <div className="detail-row-head">
        <span>事项</span>
        <span>负责人</span>
        <span>状态</span>
      </div>
      {page.visualRows.map(([name, owner, status]) => (
        <div className="detail-row" key={`${name}-${owner}`}>
          <strong>{name}</strong>
          <span>{owner}</span>
          <em>{status}</em>
        </div>
      ))}
    </div>
  );
}

function DetailPageView({ page, onNavigate }: { page: DetailPage; onNavigate: (id: PageId) => void }) {
  const Icon = page.icon;

  return (
    <>
      <section className="detail-hero">
        <div className="mx-auto grid max-w-7xl gap-12 px-5 py-20 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-8">
          <div>
            <span className="detail-badge">
              <Icon className="h-4 w-4" />
              {page.category}
            </span>
            <h1>{page.title}</h1>
            <p>{page.description}</p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Button onClick={() => onNavigate("demo")}>
                {page.cta} <ArrowRight className="h-4 w-4" />
              </Button>
              <Button variant="secondary" onClick={() => onNavigate("pricing")}>
                查看定价
              </Button>
            </div>
          </div>
          <DetailVisual page={page} />
        </div>
      </section>

      <section className="bg-white py-20">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 lg:grid-cols-3 lg:px-8">
          {page.bullets.map((item, index) => (
            <article className="detail-card" key={item}>
              <span>{index + 1}</span>
              <h3>{item}</h3>
              <p>把这个能力嵌入日常流程，团队可以在采购、付款和续订前做出更清晰的判断。</p>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-[#f6fafb] py-20">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-8">
          <div>
            <p className="eyebrow">工作流</p>
            <h2 className="section-title">像官网一样，每个入口都有完整页面和流程视图</h2>
          </div>
          <div className="detail-steps">
            {page.steps.map((step, index) => (
              <div className="detail-step" key={step}>
                <span>{index + 1}</span>
                <strong>{step}</strong>
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

function HomePage({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  return (
    <>
      <Hero onNavigate={onNavigate} />
      <LogoCloud />
      <SubscriptionControl onNavigate={onNavigate} />
      <PlatformLoop />
      <SpendSection onNavigate={onNavigate} />
      <Stories onNavigate={onNavigate} />
      <CalculatorCta onNavigate={onNavigate} />
    </>
  );
}

function Footer({ onNavigate }: { onNavigate: (id: PageId) => void }) {
  const columns = [
    {
      title: "为什么选择我们",
      links: [
        ["财务团队", "finance"],
        ["采购团队", "procurement"],
        ["IT 团队", "it"],
        ["运营团队", "operations"],
        ["有何不同", "difference"],
      ],
    },
    {
      title: "解决方案",
      links: [
        ["审批和采购", "approvals"],
        ["软件支付", "payments"],
        ["分析报表", "analytics"],
        ["会计自动化", "accounting"],
        ["安全与合规", "security"],
      ],
    },
    {
      title: "资源",
      links: [
        ["博客", "blog"],
        ["客户故事", "stories"],
        ["数据中心", "datahub"],
        ["AI 软件报告", "report"],
        ["节省计算器", "calculator"],
      ],
    },
    {
      title: "公司",
      links: [
        ["关于我们", "about"],
        ["招聘", "careers"],
        ["播客", "podcasts"],
        ["合作伙伴", "partner"],
        ["安全中心", "companySecurity"],
      ],
    },
    {
      title: "更多",
      links: [
        ["支持指标", "support"],
        ["媒体中心", "press"],
        ["联系我们", "contact"],
        ["隐私政策", "privacy"],
        ["服务条款", "terms"],
      ],
    },
  ] as Array<{ title: string; links: Array<[string, PageId]> }>;

  return (
    <footer className="bg-[#12163e] px-5 py-14 text-white lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-10 md:grid-cols-[1.2fr_2fr]">
        <div>
          <Mark inverse />
          <p className="mt-5 max-w-sm text-sm leading-7 text-white/58">
            一个面向财务团队的软件订阅管理网页原型。品牌名位置已留空，后续可以直接填入。
          </p>
        </div>
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-5">
          {columns.map(column => (
            <div key={column.title}>
              <h3 className="text-sm font-extrabold text-white">{column.title}</h3>
              <div className="mt-4 grid gap-3">
                {column.links.map(([label, link]) => (
                  <button className="text-left text-sm font-medium text-white/58 hover:text-white" key={link} onClick={() => onNavigate(link)} type="button">
                    {label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </footer>
  );
}

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageId>(() => pageFromHash());

  useEffect(() => {
    const onHashChange = () => {
      setCurrentPage(pageFromHash());
      window.scrollTo({ top: 0, behavior: "smooth" });
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const handleNavigate = (id: PageId) => {
    if (id === currentPage) {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    navigateTo(id);
  };

  const detailPage = currentPage === "home" ? null : detailPages[currentPage] || pageFallback;

  return (
    <main className="min-h-screen bg-white text-slate-950">
      <Announcement onNavigate={handleNavigate} />
      <Nav currentPage={currentPage} onNavigate={handleNavigate} />
      {detailPage ? <DetailPageView page={detailPage} onNavigate={handleNavigate} /> : <HomePage onNavigate={handleNavigate} />}
      <Footer onNavigate={handleNavigate} />
    </main>
  );
}
