import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface LedgerContact {
  id: string;
  name: string;
  phone: string | null;
  total_gave: number;
  total_received: number;
  balance: number;
  balance_label: "owes you" | "you owe" | "settled";
  is_active: boolean;
  created_at: string;
}

export interface LedgerSummary {
  total_gave: number;
  total_received: number;
  net_balance: number;
  people_count: number;
}

export interface LedgerContactInput {
  name: string;
  phone?: string | null;
}

function invalidateLedger(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["ledger-contacts"] });
  queryClient.invalidateQueries({ queryKey: ["ledger-summary"] });
}

export function useLedgerContacts() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["ledger-contacts"],
    queryFn: () =>
      api
        .get<{ data: LedgerContact[] }>("/api/ledger-contacts")
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: LedgerContactInput) =>
      api.post("/api/ledger-contacts", data),
    onSuccess: () => invalidateLedger(queryClient),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<LedgerContactInput> }) =>
      api.patch(`/api/ledger-contacts/${id}`, data),
    onSuccess: () => invalidateLedger(queryClient),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/ledger-contacts/${id}`),
    onSuccess: () => invalidateLedger(queryClient),
  });

  return {
    contacts: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deactivate: deactivate.mutateAsync,
  };
}

export function useLedgerSummary() {
  return useQuery({
    queryKey: ["ledger-summary"],
    queryFn: () =>
      api
        .get<{ data: LedgerSummary }>("/api/ledger-contacts/summary")
        .then((r) => r.data),
  });
}
