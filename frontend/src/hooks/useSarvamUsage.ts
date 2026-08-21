import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface SarvamSpend {
  starting: number;
  used: number;
  remaining: number;
  call_count: number;
  cost_inr: number;
}

export function useSarvamUsage(parlourId?: string) {
  return useQuery({
    queryKey: ["amul-sarvam-usage", parlourId],
    queryFn: () =>
      api
        .get<{ data: SarvamSpend }>(`/api/amul/sarvam-usage?parlour_id=${parlourId}`)
        .then((r) => r.data),
    enabled: !!parlourId,
  });
}
