import { useState, useEffect } from "react";
import type { FixedExpense } from "../../hooks/useExpenses";
import { MONTH_NAMES } from "../../lib/constants";
import { inputCls, btnPrimary } from "../../lib/styles";

interface ExpenseFormState {
  name: string;
  owner: "you" | "wife" | "household";
  amount: number | "";
  frequency: "monthly" | "quarterly" | "yearly" | "one-time";
  expense_month: number;
  expense_year: number;
}

interface ExpenseQuickAddProps {
  selectedMonth: number;
  selectedYear: number;
  onSave: (data: Omit<FixedExpense, "id" | "is_active" | "created_at">) => Promise<unknown>;
}

export function ExpenseQuickAdd({ selectedMonth, selectedYear, onSave }: ExpenseQuickAddProps) {
  const [form, setForm] = useState<ExpenseFormState>({
    name: "",
    owner: "you",
    amount: "",
    frequency: "monthly",
    expense_month: selectedMonth,
    expense_year: selectedYear,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // M9: Sync expense_month/expense_year when parent navigation changes
  useEffect(() => {
    setForm((prev) => ({
      ...prev,
      expense_month: selectedMonth,
      expense_year: selectedYear,
    }));
  }, [selectedMonth, selectedYear]);

  const isOneTime = form.frequency === "one-time";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // M6: Validate amount > 0
    const numAmount = Number(form.amount);
    if (!numAmount || numAmount <= 0) {
      setError("Amount must be greater than 0");
      return;
    }

    setSaving(true);
    try {
      const payload: Omit<FixedExpense, "id" | "is_active" | "created_at"> = {
        name: form.name,
        owner: form.owner,
        amount: numAmount,
        frequency: form.frequency,
      };
      if (isOneTime) {
        payload.expense_month = form.expense_month;
        payload.expense_year = form.expense_year;
      }
      await onSave(payload);
      setForm({
        name: "",
        owner: "you",
        amount: "",
        frequency: "monthly",
        expense_month: selectedMonth,
        expense_year: selectedYear,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save expense");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#1A3A5C]/30"
    >
      <h3 className="text-sm font-medium text-[#E8ECF1]/80 mb-3">Quick Add Expense</h3>
      {error && (
        <div className="mb-3 px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}
      <div className={`grid grid-cols-1 gap-3 items-end ${isOneTime ? "md:grid-cols-7" : "md:grid-cols-5"}`}>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Name</label>
          <input
            type="text"
            placeholder="Expense name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            maxLength={100}
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Owner</label>
          <select
            value={form.owner}
            onChange={(e) => setForm({ ...form, owner: e.target.value as ExpenseFormState["owner"] })}
            className={inputCls}
          >
            <option value="you">You</option>
            <option value="wife">Wife</option>
            <option value="household">Household</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Amount</label>
          <input
            type="number"
            placeholder="0"
            value={form.amount}
            onChange={(e) =>
              setForm({ ...form, amount: e.target.value === "" ? "" : Number(e.target.value) })
            }
            required
            min={1}
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Frequency</label>
          <select
            value={form.frequency}
            onChange={(e) =>
              setForm({ ...form, frequency: e.target.value as ExpenseFormState["frequency"] })
            }
            className={inputCls}
          >
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="yearly">Yearly</option>
            <option value="one-time">One-time</option>
          </select>
        </div>
        {isOneTime && (
          <>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">Month</label>
              <select
                value={form.expense_month}
                onChange={(e) => setForm({ ...form, expense_month: Number(e.target.value) })}
                className={inputCls}
              >
                {MONTH_NAMES.map((m, i) => (
                  <option key={i} value={i + 1}>{m}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">Year</label>
              <input
                type="number"
                value={form.expense_year}
                onChange={(e) => setForm({ ...form, expense_year: Number(e.target.value) })}
                className={inputCls}
              />
            </div>
          </>
        )}
        <button type="submit" disabled={saving} className={btnPrimary}>
          {saving ? "Saving..." : "Add"}
        </button>
      </div>
    </form>
  );
}
