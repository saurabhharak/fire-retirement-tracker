import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type GoldPurity = "24K" | "22K" | "18K";
export type GoldOwner = "you" | "wife" | "household";

export interface GoldPurchaseEntry {
  id?: string;
  purchase_date: string;
  weight_grams: number;
  price_per_gram: number;
  total_cost: number;
  purity: GoldPurity;
  owner: GoldOwner;
  notes?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface GoldPurchaseCreate {
  purchase_date: string;
  weight_grams: number;
  price_per_gram: number;
  purity: GoldPurity;
  owner: GoldOwner;
  notes?: string;
}

export interface GoldPurchaseUpdate {
  purchase_date?: string;
  weight_grams?: number;
  price_per_gram?: number;
  purity?: GoldPurity;
  owner?: GoldOwner;
  notes?: string;
}

export function useGoldPurchases(filters: { active?: boolean } = {}) {
  const queryClient = useQueryClient();
  const active = filters.active ?? true;

  const query = useQuery({
    queryKey: ["gold-purchases", { active }],
    queryFn: () =>
      api
        .get<{ data: GoldPurchaseEntry[] }>(`/api/gold-purchases?active=${active}`)
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: GoldPurchaseCreate) =>
      api.post("/api/gold-purchases", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gold-purchases"] });
      queryClient.invalidateQueries({ queryKey: ["gold-portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["gold-rate"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoldPurchaseUpdate }) =>
      api.patch(`/api/gold-purchases/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gold-purchases"] });
      queryClient.invalidateQueries({ queryKey: ["gold-portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["gold-rate"] });
    },
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/gold-purchases/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gold-purchases"] });
      queryClient.invalidateQueries({ queryKey: ["gold-portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["gold-rate"] });
    },
  });

  return {
    entries: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deactivate: deactivate.mutateAsync,
  };
}
