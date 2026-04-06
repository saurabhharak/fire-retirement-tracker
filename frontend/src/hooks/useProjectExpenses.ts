import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface ProjectExpense {
  id: string;
  project_id: string;
  date: string;
  category: string;
  description: string;
  total_amount: number | null;
  paid_amount: number;
  paid_by: string;
  is_active?: boolean;
  created_at?: string;
}

export interface ProjectExpenseInput {
  project_id: string;
  date: string;
  category: string;
  description: string;
  total_amount?: number | null;
  paid_amount: number;
  paid_by?: string;
}

export interface ProjectSummary {
  total_paid: number;
  entry_count: number;
  category_totals: Record<string, number>;
  monthly_totals: Record<string, number>;
}

export function useProjectExpenses(
  filters: { projectId?: string; category?: string; active?: boolean } = {}
) {
  const queryClient = useQueryClient();
  const active = filters.active ?? true;

  const params = new URLSearchParams();
  params.set("active", String(active));
  if (filters.projectId) params.set("project_id", filters.projectId);
  if (filters.category) params.set("category", filters.category);

  const query = useQuery({
    queryKey: ["project-expenses", { projectId: filters.projectId, category: filters.category, active }],
    queryFn: () =>
      api
        .get<{ data: ProjectExpense[] }>(`/api/project-expenses?${params.toString()}`)
        .then((r) => r.data),
    enabled: !!filters.projectId,
  });

  const save = useMutation({
    mutationFn: (data: ProjectExpenseInput) =>
      api.post("/api/project-expenses", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["project-summary"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProjectExpense> }) =>
      api.patch(`/api/project-expenses/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["project-summary"] });
    },
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/project-expenses/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["project-summary"] });
    },
  });

  return {
    expenses: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deactivate: deactivate.mutateAsync,
  };
}

export function useProjectSummary(projectId?: string) {
  return useQuery({
    queryKey: ["project-summary", projectId],
    queryFn: () =>
      api
        .get<{ data: ProjectSummary }>(`/api/project-expenses/summary?project_id=${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}
