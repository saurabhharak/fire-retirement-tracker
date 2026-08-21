import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface AmulDailySale {
  id: string;
  parlour_id: string;
  sale_date: string;
  cash_amount: number;
  online_amount: number;
  sender_name?: string;
  entered_by?: string;
}

export function useAmulSales(parlourId?: string) {
  const queryClient = useQueryClient();
  const enabled = !!parlourId;

  const query = useQuery({
    queryKey: ["amul-sales", parlourId],
    queryFn: () =>
      api
        .get<{ data: AmulDailySale[] }>(`/api/amul/sales?parlour_id=${parlourId}`)
        .then((r) => r.data),
    enabled,
  });

  const save = useMutation({
    mutationFn: (data: Omit<AmulDailySale, "id" | "parlour_id" | "entered_by">) =>
      api.post(`/api/amul/sales?parlour_id=${parlourId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-sales"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AmulDailySale> }) =>
      api.patch(`/api/amul/sales/${id}?parlour_id=${parlourId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-sales"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/api/amul/sales/${id}?parlour_id=${parlourId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-sales"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  const importWhatsApp = useMutation({
    mutationFn: async (text: string) => {
      const form = new FormData();
      form.append("parlour_id", parlourId ?? "");
      form.append("text", text);
      const { apiFetch } = await import("../lib/api");
      return apiFetch<{ count: number; skipped: number }>(
        "/api/amul/sales/import-whatsapp",
        { method: "POST", body: form }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-sales"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  return {
    sales: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    remove: remove.mutateAsync,
    importWhatsApp: importWhatsApp.mutateAsync,
  };
}
