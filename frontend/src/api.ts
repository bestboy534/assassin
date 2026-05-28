import type { AnalyzeResponse, SourceHint } from "./types";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export async function analyzeBillingText(rawText: string, sourceHint: SourceHint): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE_URL}/api/analyze`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ raw_text: rawText, source_hint: sourceHint }) });
  if (!res.ok) throw new Error(await res.text() || `Analyze failed: ${res.status}`);
  return res.json();
}
