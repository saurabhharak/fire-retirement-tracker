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
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
  });

  return {
    rate: query.data ?? null,
    isLoading: query.isLoading,
    isStale: query.data?.is_stale ?? false,
  };
}
