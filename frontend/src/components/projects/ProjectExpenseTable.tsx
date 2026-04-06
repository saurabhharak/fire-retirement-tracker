import { useState, useMemo } from "react";
import { Pencil, Check, X, Trash2 } from "lucide-react";
import { formatIndian } from "../../lib/formatIndian";
import type { ProjectExpense } from "../../hooks/useProjectExpenses";

interface Props {
  expenses: ProjectExpense[];
  categories: string[];
  onUpdate: (args: { id: string; data: Partial<ProjectExpense> }) => Promise<unknown>;
  onDeactivate: (id: string) => Promise<unknown>;
}

type SortKey = "date" | "category" | "paid_amount";

interface EditForm {
  date: string;
  category: string;
  description: string;
  total_amount: string;
  paid_amount: string;
  paid_by: string;
}

export function ProjectExpenseTable({ expenses, categories, onUpdate, onDeactivate }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDesc, setSortDesc] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [search, setSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState("");

  const sorted = useMemo(() => {
    let filtered = expenses;
    if (search) {
      const q = search.toLowerCase();
      filtered = filtered.filter(
        (e) =>
          e.description.toLowerCase().includes(q) ||
          e.category.toLowerCase().includes(q) ||
          e.paid_by.toLowerCase().includes(q)
      );
    }
    if (filterCategory) {
      filtered = filtered.filter((e) => e.category === filterCategory);
    }
    return [...filtered].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "date") cmp = a.date.localeCompare(b.date);
      else if (sortKey === "category") cmp = a.category.localeCompare(b.category);
      else cmp = a.paid_amount - b.paid_amount;
      return sortDesc ? -cmp : cmp;
    });
  }, [expenses, sortKey, sortDesc, search, filterCategory]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc(!sortDesc);
    else { setSortKey(key); setSortDesc(true); }
  };

  const startEdit = (e: ProjectExpense) => {
    setEditingId(e.id);
    setEditForm({
      date: e.date,
      category: e.category,
      description: e.description,
      total_amount: e.total_amount != null ? String(e.total_amount) : "",
      paid_amount: String(e.paid_amount),
      paid_by: e.paid_by,
    });
    setEditError("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm(null);
    setEditError("");
  };

  const saveEdit = async () => {
    if (!editForm || !editingId) return;
    setSaving(true);
    setEditError("");
    try {
      await onUpdate({
        id: editingId,
        data: {
          date: editForm.date,
          category: editForm.category,
          description: editForm.description,
          total_amount: editForm.total_amount ? parseFloat(editForm.total_amount) : null,
          paid_amount: parseFloat(editForm.paid_amount),
          paid_by: editForm.paid_by,
        },
      });
      cancelEdit();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const sortIcon = (key: SortKey) =>
    sortKey === key ? (sortDesc ? " \u2193" : " \u2191") : "";

  return (
    <div>
      {/* Filters */}
      <div className="flex gap-3 mb-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search expenses..."
          className="bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1] flex-1 max-w-xs"
        />
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="bg-[#0D1B2A] border border-[#1A3A5C]/50 rounded px-3 py-1.5 text-sm text-[#E8ECF1]"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-[#1A3A5C]/30">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#132E3D] text-[#E8ECF1]/60 text-left">
              <th className="px-3 py-2 cursor-pointer" onClick={() => handleSort("date")}>
                Date{sortIcon("date")}
              </th>
              <th className="px-3 py-2 cursor-pointer" onClick={() => handleSort("category")}>
                Category{sortIcon("category")}
              </th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2 text-right">Total</th>
              <th className="px-3 py-2 text-right cursor-pointer" onClick={() => handleSort("paid_amount")}>
                Paid{sortIcon("paid_amount")}
              </th>
              <th className="px-3 py-2">Paid By</th>
              <th className="px-3 py-2 w-20"></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((e) => {
              const isEditing = editingId === e.id;

              if (isEditing && editForm) {
                return (
                  <tr key={e.id} className="bg-[#0D1B2A] border-t border-[#1A3A5C]/20">
                    <td className="px-3 py-1.5">
                      <input type="date" value={editForm.date}
                        onChange={(ev) => setEditForm({ ...editForm, date: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-32" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input list="edit-categories" value={editForm.category}
                        onChange={(ev) => setEditForm({ ...editForm, category: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-full" />
                      <datalist id="edit-categories">
                        {categories.map((c) => <option key={c} value={c} />)}
                      </datalist>
                    </td>
                    <td className="px-3 py-1.5">
                      <input type="text" value={editForm.description} maxLength={200}
                        onChange={(ev) => setEditForm({ ...editForm, description: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-full" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input type="number" value={editForm.total_amount} min="0" step="0.01"
                        onChange={(ev) => setEditForm({ ...editForm, total_amount: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-24 text-right" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input type="number" value={editForm.paid_amount} min="0" step="0.01"
                        onChange={(ev) => setEditForm({ ...editForm, paid_amount: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-24 text-right" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input type="text" value={editForm.paid_by} maxLength={100}
                        onChange={(ev) => setEditForm({ ...editForm, paid_by: ev.target.value })}
                        className="bg-[#132E3D] border border-[#1A3A5C]/50 rounded px-1 py-0.5 text-sm text-[#E8ECF1] w-full" />
                    </td>
                    <td className="px-3 py-1.5">
                      <div className="flex gap-1">
                        <button onClick={saveEdit} disabled={saving}
                          className="p-1 text-[#00895E] hover:bg-[#00895E]/20 rounded">
                          <Check size={14} />
                        </button>
                        <button onClick={cancelEdit}
                          className="p-1 text-[#E8ECF1]/60 hover:bg-[#E8ECF1]/10 rounded">
                          <X size={14} />
                        </button>
                      </div>
                      {editError && <p className="text-[#E5A100] text-xs mt-1">{editError}</p>}
                    </td>
                  </tr>
                );
              }

              return (
                <tr key={e.id} className="border-t border-[#1A3A5C]/20 hover:bg-[#132E3D]/50 text-[#E8ECF1]">
                  <td className="px-3 py-2">{e.date}</td>
                  <td className="px-3 py-2">
                    <span className="bg-[#1A3A5C]/40 px-2 py-0.5 rounded text-xs">{e.category}</span>
                  </td>
                  <td className="px-3 py-2">{e.description}</td>
                  <td className="px-3 py-2 text-right text-[#E8ECF1]/60">
                    {e.total_amount != null ? `\u20B9${formatIndian(e.total_amount)}` : "\u2014"}
                  </td>
                  <td className="px-3 py-2 text-right font-medium">
                    {`\u20B9${formatIndian(e.paid_amount)}`}
                  </td>
                  <td className="px-3 py-2 text-[#E8ECF1]/60">{e.paid_by}</td>
                  <td className="px-3 py-2">
                    <div className="flex gap-1">
                      <button onClick={() => startEdit(e)}
                        className="p-1 text-[#E8ECF1]/40 hover:text-[#D4A843] rounded">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => onDeactivate(e.id)}
                        className="p-1 text-[#E8ECF1]/40 hover:text-[#E5A100] rounded">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <p className="text-center text-[#E8ECF1]/40 py-8">No expenses found</p>
        )}
      </div>
    </div>
  );
}
