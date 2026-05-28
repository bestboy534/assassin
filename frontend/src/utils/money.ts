import type { SubscriptionItem } from "../types";
export function formatUsd(value: number): string { return `$${value.toFixed(2)}`; }
export function sumByStatus(items: SubscriptionItem[], statuses: string[]): number { return items.filter(i => statuses.includes(i.status)).reduce((s, i) => s + i.monthly_cost_usd, 0); }
export function totalMonthlySpend(items: SubscriptionItem[]): number { return items.filter(i => i.status !== "ignored").reduce((s, i) => s + i.monthly_cost_usd, 0); }
