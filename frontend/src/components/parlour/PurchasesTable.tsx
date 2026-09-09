import { useMemo, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Pencil, Trash2, X } from "lucide-react";
import { formatRupees } from "../../lib/formatIndian";
import type { AmulDailyPurchase } from "../../hooks/useAmulPurchases";

const editInputClass =
  "w-28 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1 text-sm text-[#E8ECF1]";

interface PurchasesTableProps {
  purchases: AmulDailyPurchase[];
  onRemove: (id: string) => Promise<unknown>;
  onUpdate?: (id: string, data: Partial<AmulDailyPurchase>) => Promise<unknown>;
}

function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleString("en-IN", {
    month: "long",
    year: "numeric",
  });
}

export function PurchasesTable({ purchases, onRemove, onUpdate }: PurchasesTableProps) {
  const months = useMemo(
    () =>
      Array.from(new Set(purchases.map((p) => p.purchase_date.slice(0, 7))))
        .sort()
        .reverse(),
    [purchases]
  );
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editAmount, setEditAmount] = useState("");
  const [editNote, setEditNote] = useState("");

  if (purchases.length === 0) return null;

  // Snap to the most recent month with data unless the user picked one explicitly
  const activeMonth =
    selectedMonth && months.includes(selectedMonth) ? selectedMonth : months[0];
  const monthIdx = months.indexOf(activeMonth);
  const monthRows = purchases.filter((p) => p.purchase_date.startsWith(activeMonth));
  const monthTotal = monthRows.reduce((sum, p) => sum + p.amount, 0);
  const since = purchases.reduce(
    (min, p) => (p.purchase_date < min ? p.purchase_date : min),
    purchases[0].purchase_date
  );

  const startEdit = (p: AmulDailyPurchase) => {
    setEditingId(p.id);
    setEditAmount(String(p.amount));
    setEditNote(p.note ?? "");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditAmount("");
    setEditNote("");
  };

  const saveEdit = async (p: AmulDailyPurchase) => {
    if (!onUpdate) return cancelEdit();
    const amount = parseFloat(editAmount);
    if (isNaN(amount) || amount < 0) return;
    await onUpdate(p.id, { amount, note: editNote.trim() || null });
    cancelEdit();
  };

  const onEditKeyDown = (e: React.KeyboardEvent, p: AmulDailyPurchase) => {
    if (e.key === "Enter") saveEdit(p);
    if (e.key === "Escape") cancelEdit();
  };

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <h3 className="font-semibold text-[#E8ECF1]">Daily Purchases</h3>
          <p className="text-xs text-[#E8ECF1]/50">
            Tracking since {since} ({purchases.length} days recorded) — ₹0 days need
            manual entry
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-[#E8ECF1]">
          <button
            onClick={() =>
              setSelectedMonth(months[Math.min(monthIdx + 1, months.length - 1)])
            }
            disabled={monthIdx >= months.length - 1}
            aria-label="Previous month"
            className="p-1 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded disabled:opacity-40 hover:border-[#D4A843]/50 transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="min-w-[8.5rem] text-center font-medium">
            {monthLabel(activeMonth)}
          </span>
          <button
            onClick={() => setSelectedMonth(months[Math.max(monthIdx - 1, 0)])}
            disabled={monthIdx <= 0}
            aria-label="Next month"
            className="p-1 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded disabled:opacity-40 hover:border-[#D4A843]/50 transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-[#E8ECF1]">
          <thead>
            <tr className="text-left text-[#E8ECF1]/50 border-b border-[#1A3A5C]/30">
              <th className="py-2 pr-3 font-medium">Date</th>
              <th className="py-2 pr-3 font-medium">Amount (₹)</th>
              <th className="py-2 pr-3 font-medium">Note</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {monthRows.map((p) => (
              <tr key={p.id} className="border-b border-[#1A3A5C]/20">
                <td className="py-2 pr-3">{p.purchase_date}</td>
                {editingId === p.id ? (
                  <>
                    <td className="py-2 pr-3">
                      <input
                        type="number"
                        min="0"
                        value={editAmount}
                        onChange={(e) => setEditAmount(e.target.value)}
                        onKeyDown={(e) => onEditKeyDown(e, p)}
                        className={editInputClass}
                        aria-label="Purchase amount"
                      />
                    </td>
                    <td className="py-2 pr-3">
                      <input
                        type="text"
                        value={editNote}
                        onChange={(e) => setEditNote(e.target.value)}
                        onKeyDown={(e) => onEditKeyDown(e, p)}
                        className={editInputClass}
                        aria-label="Purchase note"
                      />
                    </td>
                    <td className="py-2">
                      <div className="flex gap-1">
                        <button
                          onClick={() => saveEdit(p)}
                          className="text-[#00895E] hover:text-[#00895E]/80 transition-colors"
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
                    <td className="py-2 pr-3 font-semibold text-[#00895E]">
                      {formatRupees(p.amount)}
                    </td>
                    <td className="py-2 pr-3 text-[#E8ECF1]/70">{p.note || "—"}</td>
                    <td className="py-2 text-right">
                      <div className="flex justify-end gap-2">
                        {onUpdate && (
                          <button
                            onClick={() => startEdit(p)}
                            className="text-[#D4A843]/70 hover:text-[#D4A843] transition-colors"
                            aria-label={`Edit purchase for ${p.purchase_date}`}
                          >
                            <Pencil size={16} />
                          </button>
                        )}
                        <button
                          onClick={() => onRemove(p.id)}
                          className="text-[#E5A100]/70 hover:text-[#E5A100] transition-colors"
                          aria-label={`Delete purchase for ${p.purchase_date}`}
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
              <td className="py-2 pr-3 font-semibold" colSpan={2}>
                Total — {monthLabel(activeMonth)}
              </td>
              <td className="py-2 pr-3 font-semibold text-[#00895E]">
                {formatRupees(monthTotal)}
              </td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
