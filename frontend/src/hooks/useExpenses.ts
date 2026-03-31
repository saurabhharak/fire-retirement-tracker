import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface FixedExpense {
  id?: string;
  name: string;
  amount: number;
  frequency: "monthly" | "quarterly" | "yearly" | "one-time";
  is_active?: boolean;
  owner?: string;
}

export interface FixedExpenseUpdate {
  name?: string;
  amount?: number;
  frequency?: "monthly" | "quarterly" | "yearly" | "one-time";
  is_active?: boolean;
  owner?: string;
}

export function useExpenses(active = true) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["expenses", active],
    queryFn: () =>
      api
        .get<{ data: FixedExpense[] }>(`/api/expenses?active=${active}`)
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: Omit<FixedExpense, "id" | "is_active">) =>
      api.post("/api/expenses", data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["expenses"] }),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: FixedExpenseUpdate }) =>
      api.patch(`/api/expenses/${id}`, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["expenses"] }),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/expenses/${id}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["expenses"] }),
  });

  return {
    entries: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deactivate: deactivate.mutateAsync,
  };
}
