import { useState } from "react";
import { analyzeBillingText } from "../api";
import { useSubscriptionStore } from "../store";
import type { SourceHint } from "../types";
import { Loader2, ShieldCheck } from "lucide-react";
const sample = `Transaction Date,Post Date,Description,Amount,Currency,Category,Status
2026-05-01,2026-05-02,OPENAI *CHATGPT SUBSCRIP,20.00,USD,Software,Cleared
2026-05-03,2026-05-04,ANTHROPIC PBC,20.00,USD,Technology,Cleared
2026-05-08,2026-05-09,MIDJOURNEY INC,30.00,USD,Software,Cleared
2026-05-12,2026-05-13,OPENAI *API,14.52,USD,Software,Cleared
2026-05-15,2026-05-16,APPLE.COM/BILL,680,TWD,Software,Cleared`;
export function InputPanel() {
  const appendItems = useSubscriptionStore(s => s.appendItems);
  const [rawText, setRawText] = useState("");
  const [sourceHint, setSourceHint] = useState<SourceHint>("csv");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function handleAnalyze() {
    if (!rawText.trim()) { setError("请先粘贴账单文本或 CSV 内容。"); return; }
    setError(""); setLoading(true);
    try { const data = await analyzeBillingText(rawText, sourceHint); appendItems(data.items); }
    catch (err) { setError(err instanceof Error ? err.message : "解析失败"); }
    finally { setLoading(false); }
  }
  return <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
    <div className="mb-4 flex items-start gap-3 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800"><ShieldCheck className="mt-0.5 h-5 w-5 shrink-0"/><div><div className="font-semibold">隐私边界</div><p>不需要账号密码，不抓 Cookie，不自动登录。MVP 阶段不保存原始账单；建议先删除银行卡号、邮箱、地址等敏感信息。</p></div></div>
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold text-slate-900">粘贴账单 / 收据文本</h2><select className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" value={sourceHint} onChange={e => setSourceHint(e.target.value as SourceHint)}><option value="csv">信用卡 CSV</option><option value="apple_mail">Apple 收据</option><option value="stripe_mail">Stripe 收据</option><option value="paypal_mail">PayPal 收据</option><option value="google_play">Google Play</option><option value="unknown">未知</option></select></div>
    <textarea className="min-h-56 w-full rounded-xl border border-slate-300 p-4 font-mono text-sm outline-none focus:border-slate-500" placeholder="粘贴 CSV、Apple 收据、Stripe 邮件或 PayPal 文本..." value={rawText} onChange={e => setRawText(e.target.value)} />
    {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
    <div className="mt-4 flex flex-wrap gap-3"><button className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60" onClick={handleAnalyze} disabled={loading}>{loading ? <span className="inline-flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin"/> 解析中</span> : "开始分析"}</button><button className="rounded-xl border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700" onClick={() => setRawText(sample)}>填入示例数据</button></div>
  </section>;
}
