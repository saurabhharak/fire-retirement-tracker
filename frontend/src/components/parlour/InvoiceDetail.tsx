import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api } from "../../lib/api";
import { formatRupees } from "../../lib/formatIndian";
import type {
  AmulInvoice,
  AmulInvoiceItem,
} from "../../hooks/useAmulInvoices";

interface InvoiceDetailProps {
  invoice: AmulInvoice;
  parlourId: string;
  onClose: () => void;
}

export function InvoiceDetail({ invoice, parlourId, onClose }: InvoiceDetailProps) {
  const [items, setItems] = useState<AmulInvoiceItem[]>([...(invoice as unknown as { items?: AmulInvoiceItem[] }).items ?? []]);
  const [loading, setLoading] = useState(items.length === 0);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    if (items.length > 0) return;
    (async () => {
      try {
        const res = await api.get<{ data: { invoice: AmulInvoice; items: AmulInvoiceItem[] } }>(
          `/api/amul/invoices/${invoice.id}?parlour_id=${parlourId}`
        );
        if (alive) {
          setItems(res.data.items);
          setLoading(false);
        }
      } catch (e) {
        if (alive) {
          setError(e instanceof Error ? e.message : "Failed to load invoice");
          setLoading(false);
        }
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoice.id]);

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#E8ECF1]">
          Invoice — {invoice.bill_no || invoice.id.slice(0, 8)}
          <span className="ml-2 text-[#E8ECF1]/50">{invoice.bill_date}</span>
          <span className="ml-2 text-[#D4A843]">{formatRupees(invoice.total_amount)}</span>
        </h3>
        <button onClick={onClose} className="text-[#E8ECF1]/60 hover:text-[#E8ECF1]" aria-label="Close invoice detail">
          <X size={18} />
        </button>
      </div>

      {error && <p className="text-sm text-[#E5A100] mb-3">{error}</p>}

      {loading ? (
        <p className="text-[#E8ECF1]/60 text-sm">Loading items...</p>
      ) : items.length === 0 ? (
        <p className="text-[#E8ECF1]/60 text-sm">No line items.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-[#E8ECF1]">
            <thead>
              <tr className="text-left text-[#E8ECF1]/50 border-b border-[#1A3A5C]/30">
                <th className="py-2 pr-3 font-medium">#</th>
                <th className="py-2 pr-3 font-medium">Description</th>
                <th className="py-2 pr-3 font-medium">HSN</th>
                <th className="py-2 pr-3 font-medium">Rate</th>
                <th className="py-2 pr-3 font-medium">Box</th>
                <th className="py-2 pr-3 font-medium">Pcs</th>
                <th className="py-2 pr-3 font-medium">GST%</th>
                <th className="py-2 pr-3 font-medium">Net (₹)</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} className="border-b border-[#1A3A5C]/20">
                  <td className="py-2 pr-3">{it.sr_no}</td>
                  <td className="py-2 pr-3">{it.description}</td>
                  <td className="py-2 pr-3">{it.hsn || "—"}</td>
                  <td className="py-2 pr-3">{it.rate ?? "—"}</td>
                  <td className="py-2 pr-3">{it.box_qty ?? 0}</td>
                  <td className="py-2 pr-3">{it.pcs_qty ?? 0}</td>
                  <td className="py-2 pr-3">{it.gst_pct ?? 0}</td>
                  <td className="py-2 pr-3 font-semibold text-[#D4A843]">
                    {formatRupees(it.net_amount)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td className="py-2 pr-3 font-semibold" colSpan={7}>
                  Total
                </td>
                <td className="py-2 pr-3 font-semibold text-[#D4A843]">
                  {formatRupees(
                    items.reduce((s, it) => s + (Number(it.net_amount) || 0), 0)
                  )}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}