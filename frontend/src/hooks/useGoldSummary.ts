import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { GoldRate } from "./useGoldRate";

export interface GoldOwnerBreakdown {
  owner: "you" | "wife" | "household";
  weight_grams: number;
  cost: number;
  value: number;
  pnl: number;
}

export interface GoldPurityBreakdown {
  purity: "24K" | "22K" | "18K";
  weight_grams: number;
  cost: number;
  value: number;
}

export interface GoldPortfolioSummary {
  total_weight_grams: number;
  total_cost: number;
  current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  by_owner: GoldOwnerBreakdown[];
  by_purity: GoldPurityBreakdown[];
  rate_used: GoldRate | null;
}

export function useGoldSummary() {
  const query = useQuery({
    queryKey: ["gold-portfolio-summary"],
    queryFn: () =>
      api
        .get<{ data: GoldPortfolioSummary }>("/api/gold-portfolio/summary")
        .then((r) => r.data),
    staleTime: 15 * 60 * 1000,
  });

  return {
    summary: query.data ?? null,
    isLoading: query.isLoading,
  };
}
