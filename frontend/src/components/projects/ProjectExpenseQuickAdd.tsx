import { useState } from "react";
import { Plus } from "lucide-react";
import type { ProjectExpenseInput } from "../../hooks/useProjectExpenses";

interface Props {
  projectId: string;
  categories: string[];
  onSave: (data: ProjectExpenseInput) => Promise<unknown>;
}

const EMPTY_FORM = {
  date: new Date().toISOString().slice(0, 10),
  category: "",
  description: "",
  total_amount: "",
  paid_amount: "",
  paid_by: "Saurabh Harak",
};

export function ProjectExpenseQuickAdd({ projectId, categories, onSave }: Props) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!form.category || !form.description || !form.paid_amount) {
      setError("Category, description, and paid amount are required");
      return;
    }

    setSaving(true);
    try {
      await onSave({
        project_id: projectId,
        date: form.date,
        category: form.category,
        description: form.description,
        total_amount: form.total_amount ? parseFloat(form.total_amount) : null,
        paid_amount: parseFloat(form.paid_amount),
        paid_by: form.paid_by || "Saurabh Harak",
      });
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 items-end">
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Date</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Category</label>
            <input
              list="project-categories"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="Select or type"
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
            <datalist id="project-categories">
              {categories.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>
          <div className="md:col-span-2 lg:col-span-1">
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Description</label>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What was this for?"
              maxLength={200}
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Total Amt</label>
            <input
              type="number"
              value={form.total_amount}
              onChange={(e) => setForm({ ...form, total_amount: e.target.value })}
              placeholder="Optional"
              min="0"
              step="0.01"
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#E8ECF1]/60 mb-1">Paid Amt</label>
            <input
              type="number"
              value={form.paid_amount}
              onChange={(e) => setForm({ ...form, paid_amount: e.target.value })}
              placeholder="Amount paid"
              min="0"
              step="0.01"
              required
              className="w-full bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-2 py-1.5 text-sm text-[#E8ECF1]"
            />
          </div>
          <div>
            <button
              type="submit"
              disabled={saving}
              className="w-full flex items-center justify-center gap-1 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded px-3 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              <Plus size={16} />
              {saving ? "Adding..." : "Add"}
            </button>
          </div>
        </div>
        {error && (
          <p className="text-[#E5A100] text-sm mt-2">{error}</p>
        )}
      </div>
    </form>
  );
}
