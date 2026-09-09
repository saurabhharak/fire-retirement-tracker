import { useState } from "react";
import { ChevronDown, ChevronRight, Eye, Trash2 } from "lucide-react";
import { formatRupees } from "../../lib/formatIndian";
import type { AmulInvoice } from "../../hooks/useAmulInvoices";
import { InvoiceDetail } from "./InvoiceDetail";

interface InvoiceListProps {
  invoices: AmulInvoice[];
  parlourId: string;
  onRemove: (id: string) => Promise<unknown>;
}

export function InvoiceList({ invoices, parlourId, onRemove }: InvoiceListProps) {
  const [openId, setOpenId] = useState<string | null>(null);

  if (invoices.length === 0) {
    return (
      <p className="text-sm text-[#E8ECF1]/50">
        No purchase invoices yet — upload a distributor PDF above to extract line items.
      </p>
    );
  }
  const detail = invoices.find((i) => i.id === openId);

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
      {detail && (
        <InvoiceDetail
          invoice={detail}
          parlourId={parlourId}
          onClose={() => setOpenId(null)}
        />
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-[#E8ECF1]">
          <thead>
            <tr className="text-left text-[#E8ECF1]/50 border-b border-[#1A3A5C]/30">
              <th className="py-2 pr-3 font-medium">Date</th>
              <th className="py-2 pr-3 font-medium">Distributor</th>
              <th className="py-2 pr-3 font-medium">Bill No</th>
              <th className="py-2 pr-3 font-medium">Type</th>
              <th className="py-2 pr-3 font-medium">Total (₹)</th>
              <th className="py-2 pr-3 font-medium">Items</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id} className="border-b border-[#1A3A5C]/20">
                <td className="py-2 pr-3">{inv.bill_date}</td>
                <td className="py-2 pr-3">{inv.distributor}</td>
                <td className="py-2 pr-3">{inv.bill_no || "—"}</td>
                <td className="py-2 pr-3">
                  {inv.invoice_type === "tax_invoice" ? "Tax Invoice" : "Bill of Supply"}
                </td>
                <td className="py-2 pr-3 font-semibold text-[#E5A100]">
                  {formatRupees(inv.total_amount)}
                </td>
                <td className="py-2 pr-3">
                  <button
                    onClick={() => setOpenId(openId === inv.id ? null : inv.id)}
                    className="inline-flex items-center gap-1 text-[#D4A843]/80 hover:text-[#D4A843] transition-colors"
                    aria-label={`View items for invoice ${inv.bill_no ?? inv.id}`}
                  >
                    {openId === inv.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    <Eye size={15} />
                    View
                  </button>
                </td>
                <td className="py-2 text-right">
                  <button
                    onClick={() => onRemove(inv.id)}
                    className="text-[#E5A100]/70 hover:text-[#E5A100] transition-colors"
                    aria-label={`Delete invoice ${inv.bill_no ?? inv.id}`}
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}