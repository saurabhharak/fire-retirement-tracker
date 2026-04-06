import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { MetalRates } from "./useMetalRates";

export interface MetalBreakdown {
  metal: string;
  weight_grams: number;
  cost: number;
  value: number;
  pnl: number;
}

export interface MetalsSummary {
  total_weight_grams: number;
  total_cost: number;
  current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  by_metal: MetalBreakdown[];
  by_owner: { owner: string; weight_grams: number; cost: number; value: number; pnl: number }[];
  rate_used: MetalRates;
}

export function useMetalsSummary(metal?: string) {
  const qs = metal ? `?metal=${metal}` : "";

  return useQuery({
    queryKey: ["metals-summary", metal],
    queryFn: () =>
      api
        .get<{ data: MetalsSummary }>(`/api/precious-metals/summary${qs}`)
        .then((r) => r.data),
    staleTime: 15 * 60 * 1000,
  });
}
