import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { formatRupees } from "../../lib/formatIndian";
import type { AmulOtherExpense } from "../../hooks/useAmulOtherExpenses";

interface OtherExpensesProps {
  expenses: AmulOtherExpense[];
  onSave: (data: {
    expense_date: string;
    category: string;
    description: string;
    amount: number;
  }) => Promise<unknown>;
  onRemove: (id: string) => Promise<unknown>;
}

const CATEGORIES = [
  "rent",
  "electricity",
  "wages",
  "transport",
  "packing",
  "maintenance",
  "internet",
  "misc",
];

export function OtherExpenses({ expenses, onSave, onRemove }: OtherExpensesProps) {
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10));
  const [category, setCategory] = useState("rent");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) {
      setError("Enter a valid amount");
      return;
    }
    if (!expenseDate) {
      setError("Select a date");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await onSave({
        expense_date: expenseDate,
        category,
        description: description.trim(),
        amount: amt,
      });
      setDescription("");
      setAmount("");
    } finally {
      setSaving(false);
    }
  };

  const total = expenses.reduce((s, e) => s + e.amount, 0);

  return (
    <div className="mb-6">
      {/* Quick add */}
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-4">
        <h3 className="text-sm font-semibold text-[#E8ECF1] mb-3">
          Add Other Expense (rent, electricity, wages...)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 items-end">
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Date</label>
            <input
              type="date"
              value={expenseDate}
              onChange={(e) => setExpenseDate(e.target.value)}
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c.charAt(0).toUpperCase() + c.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Amount (₹)</label>
            <input
              type="number"
              min="1"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Note (optional)</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={200}
              placeholder="e.g. July rent"
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="flex items-center justify-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 transition-colors"
          >
            <Plus size={16} />
            {saving ? "Saving..." : "Add"}
          </button>
        </div>
        {error && <p className="text-sm text-[#E5A100] mt-2">{error}</p>}
      </div>

      {/* Table */}
      {expenses.length > 0 && (
        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-[#E8ECF1]">
              <thead>
                <tr className="text-left text-[#E8ECF1]/50 border-b border-[#1A3A5C]/30">
                  <th className="py-2 pr-3 font-medium">Date</th>
                  <th className="py-2 pr-3 font-medium">Category</th>
                  <th className="py-2 pr-3 font-medium">Note</th>
                  <th className="py-2 pr-3 font-medium">Amount (₹)</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {expenses.map((e) => (
                  <tr key={e.id} className="border-b border-[#1A3A5C]/20">
                    <td className="py-2 pr-3">{e.expense_date}</td>
                    <td className="py-2 pr-3 capitalize">{e.category}</td>
                    <td className="py-2 pr-3 text-[#E8ECF1]/70">{e.description || "—"}</td>
                    <td className="py-2 pr-3 font-semibold text-[#E5A100]">
                      {formatRupees(e.amount)}
                    </td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => onRemove(e.id)}
                        className="text-[#E5A100]/70 hover:text-[#E5A100] transition-colors"
                        aria-label={`Delete expense ${e.description || e.id}`}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td className="py-2 pr-3 font-semibold" colSpan={3}>
                    Total Other Expenses
                  </td>
                  <td className="py-2 pr-3 font-semibold text-[#E5A100]">
                    {formatRupees(total)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
