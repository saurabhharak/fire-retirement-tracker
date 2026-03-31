import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface IncomeEntry {
  month: number;
  year: number;
  your_income: number;
  wife_income: number;
  notes: string;
}

export function useIncome(limit = 12) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["income", limit],
    queryFn: () =>
      api
        .get<{ data: IncomeEntry[] }>(`/api/income?limit=${limit}`)
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: IncomeEntry) => api.post("/api/income", data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["income"] }),
  });

  const remove = useMutation({
    mutationFn: ({ month, year }: { month: number; year: number }) =>
      api.delete(`/api/income/${month}/${year}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["income"] }),
  });

  return {
    entries: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    remove: remove.mutateAsync,
  };
}
