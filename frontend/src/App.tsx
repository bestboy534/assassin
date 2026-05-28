import { InputPanel } from "./components/InputPanel";
import { SummaryCards } from "./components/SummaryCards";
import { SubscriptionList } from "./components/SubscriptionList";
import { useSubscriptionStore } from "./store";
import { Trash2 } from "lucide-react";
export default function App() {
  const clearAll = useSubscriptionStore(s => s.clearAll);
  const items = useSubscriptionStore(s => s.items);
  const lastRunId = useSubscriptionStore(s => s.lastRunId);
  function exportReport() { const blob = new Blob([JSON.stringify(items, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "saas-assassin-report.json"; a.click(); URL.revokeObjectURL(url); }
  return <main className="min-h-screen px-4 py-8 text-slate-900"><div className="mx-auto max-w-6xl space-y-6"><header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="text-sm font-semibold text-slate-500">SaaS Assassin MVP</p><h1 className="mt-1 text-3xl font-bold tracking-tight md:text-4xl">上传账单，发现每月浪费在哪些 AI / SaaS 订阅上</h1><p className="mt-3 max-w-2xl text-slate-600">第一版只做账单识别、费用估算和退订指引。不托管账号、不抓 Cookie、不自动登录。</p></div><div className="flex gap-2"><button className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700" onClick={exportReport}>导出报告</button><button className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700" onClick={clearAll}><Trash2 className="h-4 w-4"/> 清空数据</button></div></header>{lastRunId && <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">后端 SQLite 已保存本次结构化结果，run_id：<code className="font-mono text-slate-900">{lastRunId}</code>。原始账单不会保存。</div>}<SummaryCards/><InputPanel/><SubscriptionList/></div></main>;
}
