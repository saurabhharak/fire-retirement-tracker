import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

// e.g. { "gold": {"24K": 8000, "22K": 7333}, "silver": {"999": 95}, ... }
export type MetalRates = Record<string, Record<string, number>>;

export function useMetalRates() {
  return useQuery({
    queryKey: ["metal-rates"],
    queryFn: () =>
      api
        .get<{ data: MetalRates }>("/api/precious-metals/rates")
        .then((r) => r.data),
    staleTime: 6 * 60 * 60 * 1000,       // 6 hours (free tier: 100 req/month)
    refetchInterval: 6 * 60 * 60 * 1000, // 6 hours
  });
}
