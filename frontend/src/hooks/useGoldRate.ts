import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface GoldRate {
  rate_24k: number;
  rate_22k: number;
  rate_18k: number;
  currency: string;
  source: string;
  fetched_at: string;
  is_stale: boolean;
}

export function useGoldRate() {
  const query = useQuery({
    queryKey: ["gold-rate"],
    queryFn: () =>
      api
        .get<{ data: GoldRate | null }>("/api/gold-rate")
        .then((r) => r.data),
    staleTime: 6 * 60 * 60 * 1000,      // 6 hours (free tier: 100 req/month)
    refetchInterval: 6 * 60 * 60 * 1000, // 6 hours
  });

  return {
    rate: query.data ?? null,
    isLoading: query.isLoading,
    isStale: query.data?.is_stale ?? false,
  };
}
