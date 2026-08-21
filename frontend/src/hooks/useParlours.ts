import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface Parlour {
  id: string;
  name: string;
  role: "owner" | "data_entry";
  sarvam_starting_credits?: number;
  is_active?: boolean;
}

export function useParlours() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["parlours"],
    queryFn: () => api.get<{ data: Parlour[] }>("/api/parlours").then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: { name: string; sarvam_starting_credits?: number }) =>
      api.post("/api/parlours", data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["parlours"] }),
  });

  return {
    parlours: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
  };
}
