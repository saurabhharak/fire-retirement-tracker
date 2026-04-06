import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface Project {
  id: string;
  name: string;
  status: "active" | "completed";
  budget: number | null;
  start_date: string;
  end_date: string | null;
  is_active?: boolean;
  created_at?: string;
}

export function useProjects(filters: { status?: string; active?: boolean } = {}) {
  const queryClient = useQueryClient();
  const active = filters.active ?? true;

  const params = new URLSearchParams();
  params.set("active", String(active));
  if (filters.status) params.set("status", filters.status);

  const query = useQuery({
    queryKey: ["projects", { active, status: filters.status }],
    queryFn: () =>
      api
        .get<{ data: Project[] }>(`/api/projects?${params.toString()}`)
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: Omit<Project, "id" | "is_active" | "created_at">) =>
      api.post("/api/projects", data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Project> }) =>
      api.patch(`/api/projects/${id}`, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/projects/${id}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  return {
    projects: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deactivate: deactivate.mutateAsync,
  };
}
