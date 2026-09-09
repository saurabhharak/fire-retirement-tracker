import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface AmulDailyPurchase {
  id: string;
  parlour_id: string;
  purchase_date: string;
  amount: number;
  note?: string | null;
  entered_by?: string;
}

export function useAmulPurchases(parlourId?: string) {
  const queryClient = useQueryClient();
  const enabled = !!parlourId;

  const query = useQuery({
    queryKey: ["amul-purchases", parlourId],
    queryFn: () =>
      api
        .get<{ data: AmulDailyPurchase[] }>(
          `/api/amul/purchases?parlour_id=${parlourId}`
        )
        .then((r) => r.data),
    enabled,
  });

  const save = useMutation({
    mutationFn: (
      data: Omit<AmulDailyPurchase, "id" | "parlour_id" | "entered_by">
    ) => api.post(`/api/amul/purchases?parlour_id=${parlourId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-purchases"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AmulDailyPurchase> }) =>
      api.patch(`/api/amul/purchases/${id}?parlour_id=${parlourId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-purchases"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/api/amul/purchases/${id}?parlour_id=${parlourId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-purchases"] });
    },
  });

  return {
    purchases: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    remove: remove.mutateAsync,
  };
}
