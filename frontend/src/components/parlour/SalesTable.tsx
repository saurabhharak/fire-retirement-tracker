import { useMemo, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Pencil, Trash2, X } from "lucide-react";
import { formatRupees } from "../../lib/formatIndian";
import { dailyTotal } from "../../lib/parlourCalculations";
import type { AmulDailySale } from "../../hooks/useAmulSales";

const editInputClass =
  "w-24 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1 text-sm text-[#E8ECF1]";

interface SalesTableProps {
  sales: AmulDailySale[];
  onRemove: (id: string) => Promise<unknown>;
  onUpdate?: (id: string, data: Partial<AmulDailySale>) => Promise<unknown>;
}

function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleString("en-IN", {
    month: "long",
    year: "numeric",
  });
}

export function SalesTable({ sales, onRemove, onUpdate }: SalesTableProps) {
  const months = useMemo(
    () =>
      Array.from(new Set(sales.map((s) => s.sale_date.slice(0, 7)))).sort().reverse(),
    [sales]
  );
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCash, setEditCash] = useState("");
  const [editOnline, setEditOnline] = useState("");
  const [editSender, setEditSender] = useState("");

  if (sales.length === 0) return null;

  // Snap to the most recent month with data unless the user picked one explicitly
  const activeMonth =
    selectedMonth && months.includes(selectedMonth) ? selectedMonth : months[0];
  const monthIdx = months.indexOf(activeMonth);
  const monthRows = sales.filter((s) => s.sale_date.startsWith(activeMonth));
  const monthTotal = monthRows.reduce((sum, s) => sum + dailyTotal(s), 0);
  const since = sales.reduce(
    (min, s) => (s.sale_date < min ? s.sale_date : min),
    sales[0].sale_date
  );

  const startEdit = (s: AmulDailySale) => {
    setEditingId(s.id);
    setEditCash(String(s.cash_amount));
    setEditOnline(String(s.online_amount));
    setEditSender(s.sender_name ?? "");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditCash("");
    setEditOnline("");
    setEditSender("");
  };

  const saveEdit = async (s: AmulDailySale) => {
    if (!onUpdate) return cancelEdit();
    const cash = parseFloat(editCash);
    const online = parseFloat(editOnline);
    if (isNaN(cash) || isNaN(online) || cash < 0 || online < 0) return;
    if (cash + online <= 0) return;
    await onUpdate(s.id, {
      cash_amount: cash,
      online_amount: online,
      sender_name: editSender.trim() || null,
    });
    cancelEdit();
  };

  const onEditKeyDown = (e: React.KeyboardEvent, s: AmulDailySale) => {
    if (e.key === "Enter") saveEdit(s);
    if (e.key === "Escape") cancelEdit();
  };

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <h3 className="font-semibold text-[#E8ECF1]">Daily Sales</h3>
          <p className="text-xs text-[#E8ECF1]/50">
            Tracking since {since} ({sales.length} days recorded)
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-[#E8ECF1]">
          <button
            onClick={() => setSelectedMonth(months[Math.min(monthIdx + 1, months.length - 1)])}
            disabled={monthIdx >= months.length - 1}
            aria-label="Previous month"
            className="p-1 bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded disabled:opacity-40 hover:border-[#D4A843]/50 transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="min-w-[8.5rem] text-center font-medium">{monthLabel(activeMonth)}</span>
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
              <th className="py-2 pr-3 font-medium">Cash (₹)</th>
              <th className="py-2 pr-3 font-medium">Online (₹)</th>
              <th className="py-2 pr-3 font-medium">Total (₹)</th>
              <th className="py-2 pr-3 font-medium">Sender</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {monthRows.map((s) => (
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
                        onKeyDown={(e) => onEditKeyDown(e, s)}
                        className={editInputClass}
                        aria-label="Cash amount"
                      />
                    </td>
                    <td className="py-2 pr-3">
                      <input
                        type="number"
                        min="0"
                        value={editOnline}
                        onChange={(e) => setEditOnline(e.target.value)}
                        onKeyDown={(e) => onEditKeyDown(e, s)}
                        className={editInputClass}
                        aria-label="Online amount"
                      />
                    </td>
                    <td className="py-2 pr-3 text-[#E8ECF1]/50">
                      {(parseFloat(editCash) || 0) + (parseFloat(editOnline) || 0)}
                    </td>
                    <td className="py-2 pr-3">
                      <input
                        type="text"
                        value={editSender}
                        onChange={(e) => setEditSender(e.target.value)}
                        onKeyDown={(e) => onEditKeyDown(e, s)}
                        className={editInputClass}
                        aria-label="Sender name"
                      />
                    </td>
                    <td className="py-2">
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
                      {formatRupees(dailyTotal(s))}
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
                Total — {monthLabel(activeMonth)}
              </td>
              <td className="py-2 pr-3 font-semibold text-[#00895E]">
                {formatRupees(monthTotal)}
              </td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
