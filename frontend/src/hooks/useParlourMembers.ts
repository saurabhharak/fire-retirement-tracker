import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface ParlourMember {
  id: string;
  member_id: string;
  role: "owner" | "data_entry";
  created_at?: string;
}

export function useParlourMembers(parlourId?: string) {
  const queryClient = useQueryClient();
  const enabled = !!parlourId;

  const query = useQuery({
    queryKey: ["parlour-members", parlourId],
    queryFn: () =>
      api
        .get<{ data: ParlourMember[] }>(`/api/parlours/${parlourId}/members`)
        .then((r) => r.data),
    enabled,
  });

  const addMember = useMutation({
    mutationFn: ({ email, role }: { email: string; role: "owner" | "data_entry" }) =>
      api.post(`/api/parlours/${parlourId}/members`, { member_email: email, role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["parlour-members"] });
      queryClient.invalidateQueries({ queryKey: ["parlours"] });
    },
  });

  const removeMember = useMutation({
    mutationFn: (memberId: string) =>
      api.delete(`/api/parlours/${parlourId}/members/${memberId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["parlour-members"] });
      queryClient.invalidateQueries({ queryKey: ["parlours"] });
    },
  });

  return {
    members: query.data || [],
    isLoading: query.isLoading,
    addMember: addMember.mutateAsync,
    removeMember: removeMember.mutateAsync,
  };
}