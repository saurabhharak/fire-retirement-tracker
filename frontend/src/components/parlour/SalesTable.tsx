import { useMemo, useState } from "react";
import { Check, Pencil, Trash2, X } from "lucide-react";
import { formatRupees } from "../../lib/formatIndian";
import { dailyTotal } from "../../lib/parlourCalculations";
import type { AmulDailySale } from "../../hooks/useAmulSales";

const PAGE_SIZE = 20;

interface SalesTableProps {
  sales: AmulDailySale[];
  onRemove: (id: string) => Promise<unknown>;
  onUpdate?: (id: string, data: Partial<AmulDailySale>) => Promise<unknown>;
}

export function SalesTable({ sales, onRemove, onUpdate }: SalesTableProps) {
  const [page, setPage] = useState(0);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCash, setEditCash] = useState("");
  const [editOnline, setEditOnline] = useState("");

  if (sales.length === 0) return null;

  const totalPages = Math.max(1, Math.ceil(sales.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageRows = sales.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const grandTotal = sales.reduce((sum, s) => sum + dailyTotal(s), 0);

  const totalCache = useMemo(
    () =>
      sales.reduce<Record<string, number>>((acc, s) => {
        acc[s.id] = dailyTotal(s);
        return acc;
      }, {}),
    [sales]
  );

  const startEdit = (s: AmulDailySale) => {
    setEditingId(s.id);
    setEditCash(String(s.cash_amount));
    setEditOnline(String(s.online_amount));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditCash("");
    setEditOnline("");
  };

  const saveEdit = async (s: AmulDailySale) => {
    if (!onUpdate) return cancelEdit();
    const cash = parseFloat(editCash);
    const online = parseFloat(editOnline);
    if (isNaN(cash) || isNaN(online) || cash < 0 || online < 0) return;
    if (cash + online <= 0) return;
    await onUpdate(s.id, { cash_amount: cash, online_amount: online });
    cancelEdit();
  };

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-[#E8ECF1]">
          <thead>
            <tr className="text-left text-[#E8ECF1]/50 border-b border-[#1A3A5C]/30">
              <th className="py-2 pr-3 font-medium">Date</th>
              <th className="py-2 pr-3 font-medium">Cash (₹)</th>
              <th className="py-2 pr-3 font-medium">Online (₹)</th>
              <th className="py-2 pr-3 font-medium">Total (₹)</th>
              <th className="py-2 pr-3 font-medium">Sender</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {pageRows.map((s) => (
              <tr key={s.id} className="border-b border-[#1A3A5C]/20">
                <td className="py-2 pr-3">{s.sale_date}</td>
                {editingId === s.id ? (
                  <>
                    <td className="py-2 pr-3">
                      <input
                        type="number"
                        min="0"
                        value={editCash}
                        onChange={(e) => setEditCash(e.target.value)}
                        className="w-20 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1 text-sm text-[#E8ECF1]"
                      />
                    </td>
                    <td className="py-2 pr-3">
                      <input
                        type="number"
                        min="0"
                        value={editOnline}
                        onChange={(e) => setEditOnline(e.target.value)}
                        className="w-20 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1 text-sm text-[#E8ECF1]"
                      />
                    </td>
                    <td className="py-2 pr-3 text-[#E8ECF1]/50">
                      {(parseFloat(editCash) || 0) + (parseFloat(editOnline) || 0)}
                    </td>
                    <td className="py-2 pr-3" colSpan={1}>
                      <div className="flex gap-1">
                        <button
                          onClick={() => saveEdit(s)}
                          className="text-[#00895E] hover:text-[#00895E]-80 transition-colors"
                          aria-label="Save edit"
                        >
                          <Check size={16} />
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="text-[#E5A100]/70 hover:text-[#E5A100] transition-colors"
                          aria-label="Cancel edit"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="py-2 pr-3">{formatRupees(s.cash_amount)}</td>
                    <td className="py-2 pr-3">{formatRupees(s.online_amount)}</td>
                    <td className="py-2 pr-3 font-semibold text-[#00895E]">
                      {formatRupees(totalCache[s.id])}
                    </td>
                    <td className="py-2 pr-3 text-[#E8ECF1]/70">{s.sender_name || "—"}</td>
                    <td className="py-2 text-right">
                      <div className="flex justify-end gap-2">
                        {onUpdate && (
                          <button
                            onClick={() => startEdit(s)}
                            className="text-[#D4A843]/70 hover:text-[#D4A843] transition-colors"
                            aria-label={`Edit sale for ${s.sale_date}`}
                          >
                            <Pencil size={16} />
                          </button>
                        )}
                        <button
                          onClick={() => onRemove(s.id)}
                          className="text-[#E5A100]/70 hover:text-[#E5A100] transition-colors"
                          aria-label={`Delete sale for ${s.sale_date}`}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td className="py-2 pr-3 font-semibold" colSpan={3}>
                Total
              </td>
              <td className="py-2 pr-3 font-semibold text-[#00895E]">
                {formatRupees(grandTotal)}
              </td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 text-sm text-[#E8ECF1]/60">
          <span>
            Page {safePage + 1} of {totalPages} ({sales.length} records)
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={safePage === 0}
              className="px-3 py-1 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded disabled:opacity-40"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={safePage === totalPages - 1}
              className="px-3 py-1 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}