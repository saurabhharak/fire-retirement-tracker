import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type LedgerDirection = "gave" | "received";
export type LedgerCategory = "loan" | "borrowed" | "payment" | "advance" | "other";
export type LedgerPaymentMethod = "cash" | "upi" | "bank_transfer" | "other";

export interface LedgerTxn {
  id: string;
  contact_id: string;
  direction: LedgerDirection;
  amount: number;
  date: string;
  category: LedgerCategory;
  payment_method: LedgerPaymentMethod;
  note: string | null;
  created_at: string;
}

export interface LedgerTxnInput {
  contact_id: string;
  direction: LedgerDirection;
  amount: number;
  date: string;
  category: LedgerCategory;
  payment_method: LedgerPaymentMethod;
  note?: string | null;
}

function invalidateAll(
  queryClient: ReturnType<typeof useQueryClient>,
  contactId: string
) {
  queryClient.invalidateQueries({ queryKey: ["ledger-txns", contactId] });
  queryClient.invalidateQueries({ queryKey: ["ledger-contacts"] });
  queryClient.invalidateQueries({ queryKey: ["ledger-summary"] });
}

export function useLedgerTxns(contactId: string) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["ledger-txns", contactId],
    queryFn: () =>
      api
        .get<{ data: LedgerTxn[] }>(`/api/ledger-txns?contact_id=${contactId}`)
        .then((r) => r.data),
    enabled: !!contactId,
  });

  const save = useMutation({
    mutationFn: (data: LedgerTxnInput) =>
      api.post("/api/ledger-txns", data),
    onSuccess: () => invalidateAll(queryClient, contactId),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<LedgerTxnInput> }) =>
      api.patch(`/api/ledger-txns/${id}`, data),
    onSuccess: () => invalidateAll(queryClient, contactId),
  });

  const deleteTxn = useMutation({
    mutationFn: (id: string) => api.delete(`/api/ledger-txns/${id}`),
    onSuccess: () => invalidateAll(queryClient, contactId),
  });

  return {
    txns: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deleteTxn: deleteTxn.mutateAsync,
  };
}
