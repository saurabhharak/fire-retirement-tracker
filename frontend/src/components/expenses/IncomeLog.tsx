import { useState } from "react";
import type { IncomeEntry } from "../../hooks/useIncome";
import { formatRupees } from "../../lib/formatIndian";
import { MONTH_NAMES } from "../../lib/constants";
import { inputCls, btnPrimary } from "../../lib/styles";
import { EmptyState } from "../EmptyState";

interface IncomeFormState {
  month: number;
  year: number;
  your_income: number | "";
  wife_income: number | "";
  notes: string;
}

const emptyIncomeForm = (): IncomeFormState => ({
  month: new Date().getMonth() + 1,
  year: new Date().getFullYear(),
  your_income: "",
  wife_income: "",
  notes: "",
});

interface IncomeLogProps {
  entries: IncomeEntry[];
  onSave: (data: IncomeEntry) => Promise<unknown>;
  onRemove: (params: { month: number; year: number }) => Promise<unknown>;
}

export function IncomeLog({ entries, onSave, onRemove }: IncomeLogProps) {
  const [showForm, setShowForm] = useState(false);
  const [incomeForm, setIncomeForm] = useState<IncomeFormState>(emptyIncomeForm());
  const [editingIncome, setEditingIncome] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<IncomeFormState>(emptyIncomeForm());
  const [savingAdd, setSavingAdd] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-populate add form when month/year matches an existing entry
  function syncFormWithExisting(month: number, year: number, base: Partial<IncomeFormState> = {}) {
    const existing = entries.find((e) => e.month === month && e.year === year);
    setIncomeForm({
      month,
      year,
      your_income: existing?.your_income ?? "",
      wife_income: existing?.wife_income ?? "",
      notes: existing?.notes ?? "",
      ...base,
    });
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSavingAdd(true);
    try {
      await onSave({
        month: incomeForm.month,
        year: incomeForm.year,
        your_income: Number(incomeForm.your_income) || 0,
        wife_income: Number(incomeForm.wife_income) || 0,
        notes: incomeForm.notes,
      });
      setIncomeForm(emptyIncomeForm());
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save income entry");
    } finally {
      setSavingAdd(false);
    }
  }

  async function handleEdit() {
    setError(null);
    setSavingEdit(true);
    try {
      await onSave({
        month: editForm.month,
        year: editForm.year,
        your_income: Number(editForm.your_income) || 0,
        wife_income: Number(editForm.wife_income) || 0,
        notes: editForm.notes,
      });
      setEditingIncome(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update income entry");
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleDelete(entry: IncomeEntry) {
    if (!window.confirm("Delete this income entry?")) return;
    await onRemove({ month: entry.month, year: entry.year });
  }

  function startEdit(entry: IncomeEntry) {
    setEditingIncome(`${entry.month}-${entry.year}`);
    setEditForm({
      month: entry.month,
      year: entry.year,
      your_income: entry.your_income,
      wife_income: entry.wife_income,
      notes: entry.notes,
    });
  }

  return (
    <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-[#E8ECF1]">Income Log</h2>
        <button onClick={() => {
          if (!showForm) {
            const f = emptyIncomeForm();
            const existing = entries.find((e) => e.month === f.month && e.year === f.year);
            if (existing) {
              setIncomeForm({ month: f.month, year: f.year, your_income: existing.your_income, wife_income: existing.wife_income, notes: existing.notes });
            } else {
              setIncomeForm(f);
            }
          }
          setShowForm(!showForm);
        }} className={btnPrimary}>
          {showForm ? "Cancel" : "+ Add Income"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSave}
          className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#1A3A5C]/30 grid grid-cols-1 md:grid-cols-6 gap-3 items-end"
        >
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Month</label>
            <select
              value={incomeForm.month}
              onChange={(e) => syncFormWithExisting(Number(e.target.value), incomeForm.year)}
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
              value={incomeForm.year}
              onChange={(e) => syncFormWithExisting(incomeForm.month, Number(e.target.value))}
              className={inputCls}
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Your Income</label>
            <input
              type="number"
              placeholder="0"
              value={incomeForm.your_income}
              onChange={(e) =>
                setIncomeForm({ ...incomeForm, your_income: e.target.value === "" ? "" : Number(e.target.value) })
              }
              className={inputCls}
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Wife's Income</label>
            <input
              type="number"
              placeholder="0"
              value={incomeForm.wife_income}
              onChange={(e) =>
                setIncomeForm({ ...incomeForm, wife_income: e.target.value === "" ? "" : Number(e.target.value) })
              }
              className={inputCls}
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Notes</label>
            <input
              type="text"
              placeholder="Optional"
              value={incomeForm.notes}
              onChange={(e) => setIncomeForm({ ...incomeForm, notes: e.target.value })}
              maxLength={500}
              className={inputCls}
            />
          </div>
          <button type="submit" disabled={savingAdd} className={btnPrimary}>
            {savingAdd ? "Saving..." : "Save"}
          </button>
        </form>
      )}

      {error && (
        <div className="mb-4 px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {entries.length === 0 ? (
        <EmptyState
          message="No income records yet. Add your first entry above."
          actionLabel="Add Income"
          onAction={() => setShowForm(true)}
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[#E8ECF1]/40 text-xs uppercase tracking-wider border-b border-[#1A3A5C]/30">
                <th className="text-left py-3 px-2">Month</th>
                <th className="text-right py-3 px-2">Your Income</th>
                <th className="text-right py-3 px-2">Wife's Income</th>
                <th className="text-right py-3 px-2">Total</th>
                <th className="text-left py-3 px-2">Notes</th>
                <th className="text-right py-3 px-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry: IncomeEntry) => {
                const key = `${entry.month}-${entry.year}`;
                const isEditing = editingIncome === key;

                if (isEditing) {
                  return (
                    <tr key={key} className="border-b border-[#1A3A5C]/20">
                      <td className="py-2 px-2 text-[#E8ECF1]">
                        {MONTH_NAMES[entry.month - 1]} {entry.year}
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          value={editForm.your_income}
                          onChange={(e) =>
                            setEditForm({ ...editForm, your_income: e.target.value === "" ? "" : Number(e.target.value) })
                          }
                          className={`${inputCls} w-28 text-right`}
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          value={editForm.wife_income}
                          onChange={(e) =>
                            setEditForm({ ...editForm, wife_income: e.target.value === "" ? "" : Number(e.target.value) })
                          }
                          className={`${inputCls} w-28 text-right`}
                        />
                      </td>
                      <td className="py-2 px-2 text-right text-[#E8ECF1]/40">--</td>
                      <td className="py-2 px-2">
                        <input
                          type="text"
                          value={editForm.notes}
                          onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                          maxLength={500}
                          className={`${inputCls} w-32`}
                        />
                      </td>
                      <td className="py-2 px-2 text-right space-x-2">
                        <button
                          onClick={handleEdit}
                          disabled={savingEdit}
                          className="text-[#00895E] hover:text-[#00895E]/80 text-xs font-medium"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingIncome(null)}
                          className="text-[#E8ECF1]/40 hover:text-[#E8ECF1]/60 text-xs font-medium"
                        >
                          Cancel
                        </button>
                      </td>
                    </tr>
                  );
                }

                return (
                  <tr
                    key={key}
                    className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10 transition-colors"
                  >
                    <td className="py-3 px-2 text-[#E8ECF1]">
                      {MONTH_NAMES[entry.month - 1]} {entry.year}
                    </td>
                    <td className="py-3 px-2 text-right text-[#E8ECF1]">
                      {formatRupees(entry.your_income)}
                    </td>
                    <td className="py-3 px-2 text-right text-[#E8ECF1]">
                      {formatRupees(entry.wife_income)}
                    </td>
                    <td className="py-3 px-2 text-right font-medium text-[#D4A843]">
                      {formatRupees(entry.your_income + entry.wife_income)}
                    </td>
                    <td className="py-3 px-2 text-[#E8ECF1]/60">{entry.notes || "--"}</td>
                    <td className="py-3 px-2 text-right space-x-2">
                      <button
                        onClick={() => startEdit(entry)}
                        className="text-[#3B82F6] hover:text-[#3B82F6]/80 text-xs font-medium"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(entry)}
                        className="text-[#E5A100] hover:text-[#E5A100]/80 text-xs font-medium"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
