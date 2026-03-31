import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface SipFund {
  fund_name: string;
  amount: number;
}

export interface SipLogEntry {
  month: number;
  year: number;
  planned_sip: number;
  actual_invested: number;
  notes: string;
  funds: SipFund[];
}

export function useSipLog(limit = 60) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["sip-log", limit],
    queryFn: () =>
      api
        .get<{ data: SipLogEntry[] }>(`/api/sip-log?limit=${limit}`)
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: SipLogEntry) => api.post("/api/sip-log", data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["sip-log"] }),
  });

  return {
    entries: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
  };
}
