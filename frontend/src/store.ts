import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { SubscriptionItem, SubscriptionStatus } from "./types";
type State = { items: SubscriptionItem[]; lastRunId: string | null; setRunId: (runId: string | null) => void; setItems: (items: SubscriptionItem[]) => void; appendItems: (items: SubscriptionItem[]) => void; updateStatus: (id: string, status: SubscriptionStatus) => void; clearAll: () => void; };
export const useSubscriptionStore = create<State>()(persist((set) => ({
  items: [],
  lastRunId: null,
  setRunId: (runId) => set({ lastRunId: runId }),
  setItems: (items) => set({ items }),
  appendItems: (items) => set((state) => { const map = new Map(state.items.map(i => [i.id, i])); for (const item of items) map.set(item.id, { ...map.get(item.id), ...item }); return { items: Array.from(map.values()) }; }),
  updateStatus: (id, status) => set((state) => ({ items: state.items.map(i => i.id === id ? { ...i, status } : i) })),
  clearAll: () => set({ items: [], lastRunId: null })
}), { name: "saas-assassin-subscriptions" }));
