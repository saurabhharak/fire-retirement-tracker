import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface AmulOtherExpense {
  id: string;
  parlour_id: string;
  expense_date: string;
  category: string;
  description: string;
  amount: number;
}

export const EXPENSE_CATEGORIES = [
  "rent",
  "electricity",
  "wages",
  "transport",
  "packing",
  "maintenance",
  "internet",
  "misc",
] as const;

export function useAmulOtherExpenses(parlourId?: string) {
  const queryClient = useQueryClient();
  const enabled = !!parlourId;

  const query = useQuery({
    queryKey: ["amul-expenses", parlourId],
    queryFn: () =>
      api
        .get<{ data: AmulOtherExpense[] }>(`/api/amul/expenses?parlour_id=${parlourId}`)
        .then((r) => r.data),
    enabled,
  });

  const save = useMutation({
    mutationFn: (data: Omit<AmulOtherExpense, "id" | "parlour_id">) =>
      api.post(`/api/amul/expenses?parlour_id=${parlourId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AmulOtherExpense> }) =>
      api.patch(`/api/amul/expenses/${id}?parlour_id=${parlourId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/api/amul/expenses/${id}?parlour_id=${parlourId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  return {
    expenses: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    remove: remove.mutateAsync,
  };
}
