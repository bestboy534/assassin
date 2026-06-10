import { type ReactNode, useMemo, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  Check,
  ChevronDown,
  CreditCard,
  FileCheck2,
  Gauge,
  Menu,
  ReceiptText,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  WalletCards,
  X,
  Zap,
} from "lucide-react";

const navGroups = [
  {
    label: "Why Cledara",
    columns: [
      ["Finance", "Control every recurring payment"],
      ["Procurement", "Approve buying and renewals"],
      ["IT", "Track access, usage, and risk"],
      ["Operations", "Automate software admin"],
    ],
  },
  {
    label: "Solutions",
    columns: [
      ["Approvals", "Strategic software purchasing"],
      ["Spend optimization", "Find waste and duplicates"],
      ["Software payments", "Cards built for SaaS"],
      ["Accounting automation", "Invoices without the chase"],
    ],
  },
  {
    label: "Resources",
    columns: [
      ["Blog", "Guides for finance teams"],
      ["Customer stories", "Real results and workflows"],
      ["Data hub", "Live SaaS spend benchmarks"],
      ["Calculator", "Estimate subscription savings"],
    ],
  },
];

const logoStrip = ["Sofar", "Countingup", "trivago", "havaianas", "fever", "Bond", "Jiminny"];

const appRows = [
  ["Slack", "Nikhesh", "Card", "$4,000", "Today", "96%"],
  ["OpenAI", "Nikhesh", "Card", "$25,000", "4 days", "61%"],
  ["BambooHR", "People", "Card", "$1,000", "Jun 09", "88%"],
  ["Adobe CC", "Creative", "Card", "$3,020", "Jun 12", "18%"],
  ["Stripe", "Finance", "Card", "$15,000", "Jun 19", "74%"],
  ["Monday", "Product", "Card", "$7,069", "Jul 02", "43%"],
];

const featureCards = [
  {
    icon: CreditCard,
    title: "Control spend with cards built for software",
    body: "Issue one virtual card per vendor, cap renewals, and stop surprise charges before they land.",
    action: "Manage payments",
    tint: "mint",
  },
  {
    icon: FileCheck2,
    title: "Buy, renew, and cancel with less friction",
    body: "Give teams a clean approval flow for new tools, renewals, owner changes, and budget checks.",
    action: "Control purchasing",
    tint: "violet",
  },
  {
    icon: ReceiptText,
    title: "Put month-end admin on autopilot",
    body: "Collect receipts, route invoices, and keep accounting exports ready without spreadsheet chasing.",
    action: "Automate day to day",
    tint: "amber",
  },
  {
    icon: TrendingDown,
    title: "Spot opportunities to spend smarter",
    body: "Catch low usage, duplicate tools, and risky renewals while there is still time to act.",
    action: "Save on software spend",
    tint: "coral",
  },
];

const platformTracks = [
  {
    label: "Management",
    items: ["Purchase requests", "Approvals", "Budgets", "Usage alerts"],
  },
  {
    label: "Payments",
    items: ["Virtual cards", "Spend limits", "Invoices", "Reimbursements"],
  },
];

const testimonials = [
  {
    quote: "We finally have one place to see which software is active, what renews next, and who owns every bill.",
    name: "Jenny Liu",
    role: "Head of Finance",
  },
  {
    quote: "The renewal view changed how we negotiate. We see contracts early enough to act, not after the charge.",
    name: "Nathan H.",
    role: "Finance Manager",
  },
  {
    quote: "Cards, approvals, receipts, and owners are connected now. Month-end feels much calmer.",
    name: "Marta V.",
    role: "Controller",
  },
];

const savingsInputs = [
  { label: "Apps discovered", value: 54 },
  { label: "Invoices captured", value: 76 },
  { label: "Hours saved", value: 13 },
];

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
        <span className={`text-xl font-extrabold tracking-tight ${inverse ? "text-white" : "text-slate-950"}`}>
          Cledara
        </span>
      )}
    </div>
  );
}

function Button({
  children,
  variant = "primary",
  className = "",
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "dark";
  className?: string;
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
      type="button"
    >
      {children}
    </button>
  );
}

function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#232765]/95 text-white backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
        <a aria-label="Cledara home" className="flex items-center gap-3" href="#">
          <Mark inverse />
        </a>

        <nav className="hidden items-center gap-1 lg:flex">
          {navGroups.map(group => (
            <div className="group relative" key={group.label}>
              <button className="inline-flex items-center gap-1 rounded-md px-4 py-2 text-sm font-semibold text-white/88 transition hover:bg-white/10">
                {group.label}
                <ChevronDown className="h-4 w-4" />
              </button>
              <div className="pointer-events-none absolute left-0 top-full w-[520px] translate-y-3 rounded-xl border border-slate-200 bg-white p-4 text-slate-900 opacity-0 shadow-2xl transition group-hover:pointer-events-auto group-hover:translate-y-2 group-hover:opacity-100">
                <div className="grid grid-cols-2 gap-2">
                  {group.columns.map(([title, body]) => (
                    <a
                      className="rounded-lg p-3 transition hover:bg-[#f3fbfb]"
                      href="#platform"
                      key={title}
                    >
                      <div className="font-bold text-[#1e2764]">{title}</div>
                      <div className="mt-1 text-sm text-slate-500">{body}</div>
                    </a>
                  ))}
                </div>
              </div>
            </div>
          ))}
          <a className="rounded-md px-4 py-2 text-sm font-semibold text-white/88 transition hover:bg-white/10" href="#stories">
            Customers
          </a>
          <a className="rounded-md px-4 py-2 text-sm font-semibold text-white/88 transition hover:bg-white/10" href="#calculator">
            Pricing
          </a>
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <a className="text-sm font-semibold text-white/78 transition hover:text-white" href="#">
            Log in
          </a>
          <Button variant="secondary" className="min-h-10 px-4 py-2">
            Book a Demo
          </Button>
          <Button className="min-h-10 px-4 py-2">
            Get Started <ArrowRight className="h-4 w-4" />
          </Button>
        </div>

        <button
          aria-label={open ? "Close menu" : "Open menu"}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-white/25 lg:hidden"
          onClick={() => setOpen(value => !value)}
          type="button"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-white/10 px-5 pb-5 lg:hidden">
          <div className="grid gap-2 pt-3">
            {[...navGroups.map(group => group.label), "Customers", "Pricing"].map(item => (
              <a className="rounded-md px-3 py-3 text-sm font-semibold text-white/90 hover:bg-white/10" href="#" key={item}>
                {item}
              </a>
            ))}
            <div className="mt-2 grid grid-cols-2 gap-3">
              <Button variant="secondary" className="w-full px-3">
                Demo
              </Button>
              <Button className="w-full px-3">
                Start
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

function Announcement() {
  return (
    <div className="bg-[#12163e] px-5 py-3 text-center text-sm font-semibold text-white">
      <a className="inline-flex items-center justify-center gap-2 text-white/90 hover:text-white" href="#calculator">
        <Sparkles className="h-4 w-4 text-[#cafbff]" />
        New report: design a smarter AI buying strategy from real SaaS spend patterns
        <ArrowRight className="h-4 w-4" />
      </a>
    </div>
  );
}

function HeroDashboard() {
  return (
    <div className="hero-dashboard mx-auto mt-16 w-full max-w-6xl">
      <div className="dashboard-shell">
        <aside className="dashboard-sidebar" aria-hidden="true">
          <div className="mb-7 flex items-center gap-2">
            <Mark compact />
            <div className="h-2.5 w-20 rounded-full bg-slate-200" />
          </div>
          {["Dashboard", "Applications", "My tasks", "Transactions", "Reports", "Compliance"].map((item, index) => (
            <div className={`sidebar-item ${index === 1 ? "active" : ""}`} key={item}>
              <span />
              <strong>{item}</strong>
            </div>
          ))}
          <div className="low-usage">
            <div className="flex items-center justify-between">
              <strong>Low Usage</strong>
              <X className="h-3.5 w-3.5" />
            </div>
            <p>Adobe CC usage is down 18%. Review licenses before renewal.</p>
          </div>
        </aside>

        <main className="dashboard-main">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="account-select">GBP Account</div>
              <h3>Applications</h3>
            </div>
            <button className="add-app" type="button">
              Add new application
            </button>
          </div>

          <div className="notice">
            <Zap className="h-4 w-4" />
            <span>More applications are waiting to be controlled.</span>
            <strong>New</strong>
          </div>

          <div className="searchbar">
            <Search className="h-4 w-4" />
            <span>Search by name or owner...</span>
            <button type="button">Finance view</button>
          </div>

          <div className="app-table">
            <div className="table-head">
              <span>Name</span>
              <span>Owner</span>
              <span>Payment</span>
              <span>Next pay</span>
              <span>Usage</span>
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
            <strong>Software Spend</strong>
            <BarChart3 className="h-4 w-4 text-[#2ecad3]" />
          </div>
          <p>54 applications</p>
          <h4>$13,854.98</h4>
          <span>Spent this month</span>
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

function Hero() {
  return (
    <section className="hero relative overflow-hidden bg-[#232765] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_15%,rgba(74,213,221,0.22),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0))]" />
      <div className="relative mx-auto max-w-7xl px-5 pb-24 pt-20 text-center lg:px-8 lg:pb-32">
        <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/18 bg-white/7 px-4 py-2 text-sm font-bold text-white/88">
          <span className="grid h-5 w-5 place-items-center rounded-full bg-[#ff6247] text-[10px] text-white">G2</span>
          4.8 stars from 200+ reviews
        </div>
        <h1 className="mx-auto mt-8 max-w-5xl text-balance text-5xl font-extrabold leading-[0.95] tracking-normal md:text-7xl lg:text-8xl">
          <span className="block sm:inline">AI is multiplying</span>{" "}
          <span className="block sm:inline">your software</span>{" "}
          <span className="block sm:inline">stack. Cledara</span>{" "}
          <span className="block sm:inline">keeps it in check.</span>
        </h1>
        <p className="mx-auto mt-7 max-w-3xl text-balance text-lg font-medium leading-8 text-white/76 md:text-xl">
          See every SaaS and AI tool, understand real usage, and control each payment from one finance-first platform.
        </p>
        <p className="mt-3 text-base font-bold text-[#cafbff]">
          Subscription management for Finance.
        </p>
        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button>
            Get Started <ArrowRight className="h-4 w-4" />
          </Button>
          <Button variant="secondary">Book a Demo</Button>
        </div>

        <div className="hero-logos mt-12 flex flex-wrap items-center justify-center gap-x-10 gap-y-4 text-white/58">
          {logoStrip.slice(0, 5).map(logo => (
            <span className="font-serif text-2xl font-bold italic tracking-normal" key={logo}>
              {logo}
            </span>
          ))}
        </div>

        <HeroDashboard />
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

function SubscriptionControl() {
  const [active, setActive] = useState(0);
  const selected = featureCards[active];
  const Icon = selected.icon;

  return (
    <section className="bg-white py-24" id="platform">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[0.95fr_1.05fr] lg:items-center lg:px-8">
        <div>
          <p className="eyebrow">Complete visibility</p>
          <h2 className="section-title">All of your software subscriptions, visible and under control</h2>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
            Cledara-style software management brings payment control, approvals, renewals, usage, and vendor ownership into one operational view.
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
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">Live control</span>
            </div>
            <h3>{selected.title}</h3>
            <p>{selected.body}</p>
            <div className="approval-flow">
              {["Request", "Budget check", "Finance approval", "Virtual card"].map((step, index) => (
                <div className="flow-step" key={step}>
                  <span>{index + 1}</span>
                  <strong>{step}</strong>
                  <Check className="h-4 w-4" />
                </div>
              ))}
            </div>
            <div className="renewal-strip">
              <div>
                <small>Next renewal</small>
                <strong>Adobe Creative Cloud</strong>
              </div>
              <div>
                <small>Potential saving</small>
                <strong>$4,000</strong>
              </div>
              <Button variant="dark" className="min-h-10 px-4 py-2">
                Review
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
          <p className="eyebrow">Management plus payments</p>
          <h2 className="section-title">Combining simple management and powerful payments for more control</h2>
        </div>

        <div className="mt-16 grid gap-8 lg:grid-cols-[1fr_1.1fr_1fr] lg:items-center">
          {platformTracks.map(track => (
            <div className="track-panel" key={track.label}>
              <div className="mb-5 flex items-center gap-3">
                <span className="grid h-11 w-11 place-items-center rounded-md bg-[#20245f] text-[#cafbff]">
                  {track.label === "Management" ? <Gauge className="h-5 w-5" /> : <WalletCards className="h-5 w-5" />}
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
          ))}

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
            <span className="map-pill pill-a">Shadow IT</span>
            <span className="map-pill pill-b">SaaS Spend</span>
            <span className="map-pill pill-c">Onboarding</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function SpendSection() {
  return (
    <section className="overflow-hidden bg-[#20245f] py-24 text-white">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[0.85fr_1.15fr] lg:items-center lg:px-8">
        <div>
          <p className="eyebrow text-[#cafbff]">Cledara Spend</p>
          <h2 className="section-title text-white">Business and travel spend on the go</h2>
          <p className="mt-6 text-lg leading-8 text-white/72">
            Pair subscription cards with everyday spend, reimbursements, mobile wallets, and receipt capture for a cleaner finance workflow.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            {["Physical cards", "Receipt scan", "Accounting sync", "Reimbursements"].map(item => (
              <span className="rounded-full border border-white/16 bg-white/8 px-4 py-2 text-sm font-bold text-white/80" key={item}>
                {item}
              </span>
            ))}
          </div>
          <Button className="mt-9">
            Learn more <ArrowRight className="h-4 w-4" />
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
                <strong>Receipt matched</strong>
                <small>Accounting ready</small>
              </div>
            </div>
          </div>
          <div className="phone phone-front">
            <div className="phone-notch" />
            <h3>Spend</h3>
            <div className="balance">$8,420</div>
            <div className="phone-bars">
              <i style={{ height: "38%" }} />
              <i style={{ height: "62%" }} />
              <i style={{ height: "48%" }} />
              <i style={{ height: "78%" }} />
              <i style={{ height: "55%" }} />
            </div>
            <div className="transaction">
              <span>Travel</span>
              <strong>$460</strong>
            </div>
            <div className="transaction">
              <span>Software</span>
              <strong>$1,280</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stories() {
  return (
    <section className="bg-white py-24" id="stories">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <p className="eyebrow">Customer success stories</p>
            <h2 className="section-title">Read what modern finance teams have to say</h2>
          </div>
          <div className="rating-pill">
            <span>G2</span>
            <strong>4.8/5</strong>
            <small>200+ reviews</small>
          </div>
        </div>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {testimonials.map((story, index) => (
            <article className="testimonial" key={story.name}>
              <div className="stars">★★★★★</div>
              <p>"{story.quote}"</p>
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

function CalculatorCta() {
  const total = useMemo(
    () => savingsInputs.reduce((sum, item) => sum + item.value, 0),
    [],
  );

  return (
    <section className="bg-[#f6fafb] py-24" id="calculator">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[1fr_0.8fr] lg:items-center lg:px-8">
        <div>
          <p className="eyebrow">Savings calculator</p>
          <h2 className="section-title">Discover how much you could save on subscriptions</h2>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
            Answer a few company questions and turn your software stack into a sharper finance plan.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button variant="dark">
              Calculate now <ArrowRight className="h-4 w-4" />
            </Button>
            <Button variant="ghost">Book a Demo</Button>
          </div>
        </div>

        <div className="calculator-card">
          <div className="flex items-center justify-between">
            <strong>Projected impact</strong>
            <ShieldCheck className="h-5 w-5 text-[#2ecad3]" />
          </div>
          <div className="impact-number">{total}%</div>
          <span>Modeled control score</span>
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

function Footer() {
  return (
    <footer className="bg-[#12163e] px-5 py-14 text-white lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-10 md:grid-cols-[1.2fr_2fr]">
        <div>
          <Mark inverse />
          <p className="mt-5 max-w-sm text-sm leading-7 text-white/58">
            A faithful local prototype inspired by the Cledara SaaS management homepage structure and visual language.
          </p>
        </div>
        <div className="grid gap-8 sm:grid-cols-4">
          {[
            ["Why Cledara", "Finance", "Procurement", "IT", "Operations"],
            ["Solutions", "Approvals", "Payments", "Analytics", "Integrations"],
            ["Resources", "Blog", "Stories", "Guides", "Calculator"],
            ["Company", "About", "Careers", "Partners", "FAQs"],
          ].map(([title, ...links]) => (
            <div key={title}>
              <h3 className="text-sm font-extrabold text-white">{title}</h3>
              <div className="mt-4 grid gap-3">
                {links.map(link => (
                  <a className="text-sm font-medium text-white/58 hover:text-white" href="#" key={link}>
                    {link}
                  </a>
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
  return (
    <main className="min-h-screen bg-white text-slate-950">
      <Announcement />
      <Nav />
      <Hero />
      <LogoCloud />
      <SubscriptionControl />
      <PlatformLoop />
      <SpendSection />
      <Stories />
      <CalculatorCta />
      <Footer />
    </main>
  );
}
