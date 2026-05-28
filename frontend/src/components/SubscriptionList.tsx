import { useSubscriptionStore } from "../store";
import { SubscriptionCard } from "./SubscriptionCard";
export function SubscriptionList() {
  const items = useSubscriptionStore(s => s.items);
  if (items.length === 0) return <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">暂无分析结果。先粘贴一段账单文本并点击“开始分析”。</section>;
  return <section className="space-y-4">{items.map(item => <SubscriptionCard key={item.id} item={item} />)}</section>;
}
