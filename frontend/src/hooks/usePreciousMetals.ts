import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type MetalType = "gold" | "silver" | "platinum";
export type MetalOwner = "you" | "wife" | "household";

export interface PreciousMetalEntry {
  id?: string;
  metal_type: MetalType;
  purchase_date: string;
  weight_grams: number;
  price_per_gram: number;
  total_cost?: number;
  purity: string;
  owner: MetalOwner;
  notes?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface PreciousMetalCreate {
  metal_type: MetalType;
  purchase_date: string;
  weight_grams: number;
  price_per_gram: number;
  purity: string;
  owner: MetalOwner;
  notes?: string;
}

export interface PreciousMetalUpdate {
  metal_type?: MetalType;
  purchase_date?: string;
  weight_grams?: number;
  price_per_gram?: number;
  purity?: string;
  owner?: MetalOwner;
  notes?: string;
}

export function usePreciousMetals(filters: { active?: boolean; metal?: string } = {}) {
  const queryClient = useQueryClient();
  const active = filters.active ?? true;

  const params = new URLSearchParams();
  params.set("active", String(active));
  if (filters.metal) params.set("metal", filters.metal);
  const qs = params.toString();

  const query = useQuery({
    queryKey: ["precious-metals", filters],
    queryFn: () =>
      api
        .get<{ data: PreciousMetalEntry[] }>(`/api/precious-metals?${qs}`)
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: PreciousMetalCreate) =>
      api.post("/api/precious-metals", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["precious-metals"] });
      queryClient.invalidateQueries({ queryKey: ["metals-summary"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PreciousMetalUpdate }) =>
      api.patch(`/api/precious-metals/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["precious-metals"] });
      queryClient.invalidateQueries({ queryKey: ["metals-summary"] });
    },
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/precious-metals/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["precious-metals"] });
      queryClient.invalidateQueries({ queryKey: ["metals-summary"] });
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
