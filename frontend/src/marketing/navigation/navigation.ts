import {
  BarChart3,
  BookOpen,
  BriefcaseBusiness,
  Building2,
  Calculator,
  CreditCard,
  FileCheck2,
  Gauge,
  Globe2,
  LayoutDashboard,
  LockKeyhole,
  MonitorCheck,
  PieChart,
  PlugZap,
  ReceiptText,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Users,
  WalletCards,
  type LucideIcon,
} from "lucide-react";

export type NavigationItem = {
  label: string;
  description?: string;
  to: string;
  icon?: LucideIcon;
};

export type NavigationGroup = {
  label: string;
  menuTitle: string;
  items: readonly NavigationItem[];
  feature: NavigationItem;
};

export const navigationGroups: readonly NavigationGroup[] = [
  {
    label: "为什么选择我们",
    menuTitle: "按团队了解",
    items: [
      { label: "财务团队", description: "控制软件支出和付款", to: "/solutions/finance", icon: CreditCard },
      { label: "IT 团队", description: "管理访问权限和安全风险", to: "/solutions/it", icon: MonitorCheck },
      { label: "采购团队", description: "规范采购和续订流程", to: "/solutions/procurement", icon: BriefcaseBusiness },
      { label: "运营团队", description: "自动化软件日常运维", to: "/solutions/operations", icon: Gauge },
    ],
    feature: {
      label: "平台有何不同",
      description: "从财务视角连接软件管理与付款",
      to: "/how-cledara-is-different",
      icon: ShieldCheck,
    },
  },
  {
    label: "解决方案",
    menuTitle: "解决方案",
    items: [
      { label: "审批和采购", description: "建立战略性软件采购流程", to: "/solutions/software-approvals-and-purchasing", icon: FileCheck2 },
      { label: "支出优化", description: "找出浪费、重复订阅和低使用率", to: "/solutions/software-spend-optimization", icon: TrendingDown },
      { label: "软件支付", description: "每个供应商一张虚拟卡", to: "/solutions/software-payments", icon: WalletCards },
      { label: "企业支出", description: "差旅、报销与日常支出", to: "/solutions/spend-management", icon: CreditCard },
      { label: "应用目录", description: "集中查看所有工具和负责人", to: "/solutions/application-directory", icon: LayoutDashboard },
      { label: "分析报表", description: "预算、续订和使用率仪表盘", to: "/solutions/analytics-and-reporting", icon: PieChart },
      { label: "会计自动化", description: "发票、收据和账务导出", to: "/solutions/accounting-automation", icon: ReceiptText },
      { label: "集成", description: "连接财务、身份和协作系统", to: "/integrations", icon: PlugZap },
      { label: "员工参与", description: "让团队参与软件治理", to: "/solutions/cledara-engage", icon: Users },
      { label: "入职和离职", description: "同步工具访问和权限变更", to: "/solutions/onboarding", icon: Building2 },
      { label: "软件安全", description: "减少影子 IT 和访问风险", to: "/solutions/software-security", icon: LockKeyhole },
      { label: "合规", description: "审批、付款和审计留痕", to: "/solutions/saas-compliance", icon: ShieldCheck },
    ],
    feature: {
      label: "SaaS 管理",
      description: "把购买、支付、使用和续订放在同一处",
      to: "/saas-management",
      icon: Globe2,
    },
  },
  {
    label: "资源",
    menuTitle: "资源中心",
    items: [
      { label: "博客", description: "软件采购和财务运营文章", to: "/blog", icon: BookOpen },
      { label: "客户故事", description: "查看团队如何管控软件支出", to: "/customer-stories", icon: Users },
      { label: "常见问题", description: "平台、付款和安全问题", to: "/faq", icon: ShieldCheck },
      { label: "线上活动", description: "采购、IT 与财务协同分享", to: "/events-webinars", icon: MonitorCheck },
      { label: "指南与模板", description: "模板、清单和最佳实践", to: "/guides-templates", icon: FileCheck2 },
      { label: "节省计算器", description: "估算可节省的软件订阅支出", to: "/calculator", icon: Calculator },
      { label: "产品公告", description: "产品更新和平台能力", to: "/resources/announcements", icon: Sparkles },
      { label: "集成市场", description: "探索可连接的财务和 IT 工具", to: "/marketplace", icon: PlugZap },
      { label: "数据中心", description: "查看软件支出趋势和行业数据", to: "/resources/data-hub", icon: BarChart3 },
      { label: "AI 软件报告", description: "基于真实交易数据的采购洞察", to: "/resources/ai-report", icon: PieChart },
    ],
    feature: {
      label: "买家指南",
      description: "软件管理平台评估清单",
      to: "/resources/buyers-guide",
      icon: BookOpen,
    },
  },
] as const;

export const footerColumns = [
  {
    title: "为什么选择我们",
    links: [
      { label: "财务团队", to: "/solutions/finance" },
      { label: "采购团队", to: "/solutions/procurement" },
      { label: "IT 团队", to: "/solutions/it" },
      { label: "运营团队", to: "/solutions/operations" },
      { label: "平台差异", to: "/how-cledara-is-different" },
    ],
  },
  {
    title: "解决方案",
    links: [
      { label: "审批和采购", to: "/solutions/software-approvals-and-purchasing" },
      { label: "软件支付", to: "/solutions/software-payments" },
      { label: "分析报表", to: "/solutions/analytics-and-reporting" },
      { label: "会计自动化", to: "/solutions/accounting-automation" },
      { label: "安全与合规", to: "/solutions/software-security" },
    ],
  },
  {
    title: "资源",
    links: [
      { label: "博客", to: "/blog" },
      { label: "客户故事", to: "/customer-stories" },
      { label: "数据中心", to: "/resources/data-hub" },
      { label: "AI 软件报告", to: "/resources/ai-report" },
      { label: "帮助中心", to: "/help-center" },
    ],
  },
  {
    title: "公司",
    links: [
      { label: "关于我们", to: "/about" },
      { label: "招聘", to: "/careers" },
      { label: "播客", to: "/podcasts" },
      { label: "合作伙伴", to: "/become-a-partner" },
      { label: "安全中心", to: "/security" },
    ],
  },
  {
    title: "更多",
    links: [
      { label: "支持指标", to: "/support-metrics" },
      { label: "媒体中心", to: "/press" },
      { label: "联系我们", to: "/company/contact" },
      { label: "隐私政策", to: "/privacy-policy" },
      { label: "服务条款", to: "/terms" },
    ],
  },
] as const;
