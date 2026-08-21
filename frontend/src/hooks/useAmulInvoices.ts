import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface AmulInvoiceItem {
  id: string;
  invoice_id: string;
  sr_no: number;
  hsn?: string;
  description: string;
  mrp?: number;
  rate?: number;
  box_qty?: number;
  pcs_qty?: number;
  free_qty?: number;
  scheme?: string;
  discount?: number;
  gst_pct?: number;
  gst_amount?: number;
  net_amount: number;
}

export interface AmulInvoice {
  id: string;
  parlour_id: string;
  distributor: string;
  bill_no: string | null;
  bill_date: string;
  invoice_type: "tax_invoice" | "bill_of_supply";
  total_amount: number;
  tax_amount?: number;
  taxable_amount?: number;
  status?: "draft" | "confirmed";
  sarvam_credits_used?: number;
}

export interface UploadResult {
  data?: AmulInvoice[];
  credits_used?: number;
  status?: string;
  source?: string;
}

export function useAmulInvoices(parlourId?: string) {
  const queryClient = useQueryClient();
  const enabled = !!parlourId;

  const query = useQuery({
    queryKey: ["amul-invoices", parlourId],
    queryFn: () =>
      api
        .get<{ data: AmulInvoice[] }>(`/api/amul/invoices?parlour_id=${parlourId}`)
        .then((r) => r.data),
    enabled,
  });

  const upload = useMutation({
    mutationFn: async ({
      file,
      useDocling,
    }: {
      file: File;
      useDocling: boolean;
    }): Promise<UploadResult> => {
      const form = new FormData();
      form.append("parlour_id", parlourId ?? "");
      form.append("use_docling", String(useDocling));
      form.append("file", file);
      // Use apiFetch with a FormData body (no JSON content-type)
      const { apiFetch } = await import("../lib/api");
      return apiFetch<UploadResult>("/api/amul/invoices/upload", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
      queryClient.invalidateQueries({ queryKey: ["amul-sarvam-usage"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AmulInvoice> }) =>
      api.patch(`/api/amul/invoices/${id}?parlour_id=${parlourId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  const updateItem = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AmulInvoiceItem> }) =>
      api.patch(`/api/amul/invoice-items/${id}?parlour_id=${parlourId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/api/amul/invoices/${id}?parlour_id=${parlourId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["amul-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["amul-analytics"] });
    },
  });

  return {
    invoices: query.data || [],
    isLoading: query.isLoading,
    upload: upload.mutateAsync,
    update: update.mutateAsync,
    updateItem: updateItem.mutateAsync,
    remove: remove.mutateAsync,
  };
}
