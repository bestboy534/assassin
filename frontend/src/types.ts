export type BillingCycle = "monthly" | "yearly" | "weekly" | "quarterly" | "unknown";
export type SourceHint = "csv" | "apple_mail" | "stripe_mail" | "paypal_mail" | "google_play" | "unknown";
export type SubscriptionStatus = "need_confirm" | "apple_unresolved" | "flagged" | "cancel_in_progress" | "cancelled" | "verified_saved" | "cancellation_failed" | "active" | "ignored";
export type SubscriptionItem = {
  id: string; software_name: string; merchant_name?: string | null; amount: number; currency: string;
  billing_cycle: BillingCycle; transaction_date?: string | null; normalized_amount_usd: number; monthly_cost_usd: number;
  status: SubscriptionStatus; risk_type: string; confidence: number; evidence: string; needs_user_confirmation: boolean;
  cancel_url?: string | null; fallback_search_url?: string | null; support_email?: string | null; guide_steps: string[]; risk_note?: string | null;
};
export type AnalyzeResponse = { items: SubscriptionItem[]; run_id?: string | null };
