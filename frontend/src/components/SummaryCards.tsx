import { useSubscriptionStore } from "../store";
import { formatUsd, sumByStatus, totalMonthlySpend } from "../utils/money";
export function SummaryCards() {
  const items = useSubscriptionStore(s => s.items);
  const cards = [
    { label: "本月总订阅支出", value: totalMonthlySpend(items), hint: "所有非忽略项月化合计" },
    { label: "疑似可优化金额", value: sumByStatus(items, ["need_confirm", "flagged", "apple_unresolved"]), hint: "待确认 + 已闲置 + Apple 未解析" },
    { label: "确认浪费金额", value: sumByStatus(items, ["flagged"]), hint: "用户已标记闲置" },
    { label: "已取消金额", value: sumByStatus(items, ["cancelled"]), hint: "用户手动标记已取消" },
    { label: "已验证节省", value: sumByStatus(items, ["verified_saved"]), hint: "下月账单复查确认" }
  ];
  return <section className="grid gap-4 md:grid-cols-5">{cards.map(c => <div key={c.label} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200"><div className="text-sm text-slate-500">{c.label}</div><div className="mt-2 text-2xl font-bold text-slate-900">{formatUsd(c.value)}</div><div className="mt-1 text-xs text-slate-400">{c.hint}</div></div>)}</section>;
}
