import { useState } from "react";
import type { FixedExpense, FixedExpenseUpdate, PaymentMethod, ExpenseCategory } from "../../hooks/useExpenses";
import { formatRupees } from "../../lib/formatIndian";
import { effectiveMonthlyAmount } from "../../lib/expenseUtils";
import { MONTH_NAMES, EXPENSE_CATEGORIES } from "../../lib/constants";
import { inputCls } from "../../lib/styles";

interface ExpenseTableProps {
  expenses: FixedExpense[];
  showOneTime: boolean;
  onDeactivate: (id: string) => void;
  onEdit: (id: string, data: FixedExpenseUpdate) => Promise<unknown>;
}

interface EditForm {
  name: string;
  owner: "you" | "wife" | "household";
  category: ExpenseCategory;
  amount: number | "";
  frequency: "monthly" | "quarterly" | "yearly" | "one-time";
  payment_method: PaymentMethod;
  expense_month: number;
  expense_year: number;
}

const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  upi: "UPI",
  credit_card: "Credit Card",
  cash: "Cash",
};

function ownerBadge(owner?: string) {
  const cls =
    owner === "you"
      ? "bg-[#D4A843]/20 text-[#D4A843]"
      : owner === "wife"
        ? "bg-[#E07A5F]/20 text-[#E07A5F]"
        : "bg-[#6B7280]/20 text-[#6B7280]";
  const label =
    owner === "you" ? "You" : owner === "wife" ? "Wife" : "Household";
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {label}
    </span>
  );
}

function categoryBadge(category?: string) {
  const cat =
    EXPENSE_CATEGORIES.find((c) => c.value === (category ?? "other")) ??
    EXPENSE_CATEGORIES[EXPENSE_CATEGORIES.length - 1];
  return (
    <span
      className="text-xs font-medium px-2 py-0.5 rounded-full"
      style={{ backgroundColor: `${cat.color}20`, color: cat.color }}
    >
      {cat.label}
    </span>
  );
}

export function ExpenseTable({ expenses, showOneTime, onDeactivate, onEdit }: ExpenseTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);

  function startEdit(expense: FixedExpense) {
    if (!expense.id) return;
    setEditingId(expense.id);
    setEditForm({
      name: expense.name,
      owner: expense.owner ?? "household",
      category: expense.category ?? "other",
      amount: expense.amount,
      frequency: expense.frequency,
      payment_method: expense.payment_method ?? "cash",
      expense_month: expense.expense_month ?? new Date().getMonth() + 1,
      expense_year: expense.expense_year ?? new Date().getFullYear(),
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm(null);
  }

  async function saveEdit() {
    if (!editingId || !editForm) return;
    const numAmount = Number(editForm.amount);
    if (!numAmount || numAmount <= 0) return;
    setSaving(true);
    try {
      const data: FixedExpenseUpdate = {
        name: editForm.name,
        owner: editForm.owner,
        category: editForm.category,
        amount: numAmount,
        frequency: editForm.frequency,
        payment_method: editForm.payment_method,
      };
      if (editForm.frequency === "one-time") {
        data.expense_month = editForm.expense_month;
        data.expense_year = editForm.expense_year;
      }
      await onEdit(editingId, data);
      setEditingId(null);
      setEditForm(null);
    } finally {
      setSaving(false);
    }
  }

  if (expenses.length === 0) {
    return (
      <div className="text-center py-8 text-[#E8ECF1]/40 text-sm">
        No expenses match the current filters.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[#E8ECF1]/40 text-xs uppercase tracking-wider border-b border-[#1A3A5C]/30">
            <th className="text-left py-3 px-2">Name</th>
            <th className="text-left py-3 px-2">Owner</th>
            <th className="text-left py-3 px-2">Category</th>
            <th className="text-right py-3 px-2">Amount</th>
            <th className="text-left py-3 px-2">Paid via</th>
            <th className="text-left py-3 px-2">Frequency</th>
            {showOneTime && <th className="text-left py-3 px-2">Month/Year</th>}
            <th className="text-right py-3 px-2">Monthly Equiv.</th>
            <th className="text-right py-3 px-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {expenses.map((expense) => {
            const isEditing = editingId === expense.id;

            if (isEditing && editForm) {
              return (
                <tr
                  key={expense.id ?? expense.name}
                  className="border-b border-[#1A3A5C]/20 bg-[#1A3A5C]/10"
                >
                  <td className="py-2 px-2">
                    <input
                      type="text"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      maxLength={100}
                      className={`${inputCls} w-32`}
                    />
                  </td>
                  <td className="py-2 px-2">
                    <select
                      value={editForm.owner}
                      onChange={(e) => setEditForm({ ...editForm, owner: e.target.value as EditForm["owner"] })}
                      className={`${inputCls} w-24`}
                    >
                      <option value="you">You</option>
                      <option value="wife">Wife</option>
                      <option value="household">Household</option>
                    </select>
                  </td>
                  <td className="py-2 px-2">
                    <select
                      value={editForm.category}
                      onChange={(e) => setEditForm({ ...editForm, category: e.target.value as ExpenseCategory })}
                      className={`${inputCls} w-28`}
                    >
                      {EXPENSE_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>{c.label}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 px-2">
                    <input
                      type="number"
                      value={editForm.amount}
                      onChange={(e) =>
                        setEditForm({ ...editForm, amount: e.target.value === "" ? "" : Number(e.target.value) })
                      }
                      min={1}
                      className={`${inputCls} w-24 text-right`}
                    />
                  </td>
                  <td className="py-2 px-2">
                    <select
                      value={editForm.payment_method}
                      onChange={(e) => setEditForm({ ...editForm, payment_method: e.target.value as PaymentMethod })}
                      className={`${inputCls} w-28`}
                    >
                      <option value="upi">UPI</option>
                      <option value="credit_card">Credit Card</option>
                      <option value="cash">Cash</option>
                    </select>
                  </td>
                  <td className="py-2 px-2">
                    <select
                      value={editForm.frequency}
                      onChange={(e) => setEditForm({ ...editForm, frequency: e.target.value as EditForm["frequency"] })}
                      className={`${inputCls} w-28`}
                    >
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="yearly">Yearly</option>
                      <option value="one-time">One-time</option>
                    </select>
                  </td>
                  {showOneTime && (
                    <td className="py-2 px-2">
                      {editForm.frequency === "one-time" ? (
                        <div className="flex gap-1">
                          <select
                            value={editForm.expense_month}
                            onChange={(e) => setEditForm({ ...editForm, expense_month: Number(e.target.value) })}
                            className={`${inputCls} w-20`}
                          >
                            {MONTH_NAMES.map((m, i) => (
                              <option key={i} value={i + 1}>{m}</option>
                            ))}
                          </select>
                          <input
                            type="number"
                            value={editForm.expense_year}
                            onChange={(e) => setEditForm({ ...editForm, expense_year: Number(e.target.value) })}
                            className={`${inputCls} w-16`}
                          />
                        </div>
                      ) : (
                        <span className="text-[#E8ECF1]/40">--</span>
                      )}
                    </td>
                  )}
                  <td className="py-2 px-2 text-right text-[#E8ECF1]/40">--</td>
                  <td className="py-2 px-2 text-right space-x-2">
                    <button
                      onClick={saveEdit}
                      disabled={saving}
                      className="text-[#00895E] hover:text-[#00895E]/80 text-xs font-medium disabled:opacity-50"
                    >
                      Save
                    </button>
                    <button
                      onClick={cancelEdit}
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
                key={expense.id ?? expense.name}
                className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10 transition-colors"
              >
                <td className="py-3 px-2 text-[#E8ECF1]">{expense.name}</td>
                <td className="py-3 px-2">{ownerBadge(expense.owner)}</td>
                <td className="py-3 px-2">{categoryBadge(expense.category)}</td>
                <td className="py-3 px-2 text-right text-[#E8ECF1]">
                  {formatRupees(expense.amount)}
                </td>
                <td className="py-3 px-2 text-[#E8ECF1]/60">
                  {PAYMENT_LABELS[expense.payment_method ?? "cash"]}
                </td>
                <td className="py-3 px-2 text-[#E8ECF1]/60 capitalize">
                  {expense.frequency}
                </td>
                {showOneTime && (
                  <td className="py-3 px-2 text-[#E8ECF1]/60">
                    {expense.frequency === "one-time" && expense.expense_month
                      ? `${MONTH_NAMES[expense.expense_month - 1]} ${expense.expense_year}`
                      : "--"}
                  </td>
                )}
                <td className="py-3 px-2 text-right text-[#E8ECF1]/60">
                  {formatRupees(Math.round(effectiveMonthlyAmount(expense.amount, expense.frequency)))}
                </td>
                <td className="py-3 px-2 text-right space-x-2">
                  <button
                    onClick={() => startEdit(expense)}
                    disabled={!expense.id}
                    className="text-[#3B82F6] hover:text-[#3B82F6]/80 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => expense.id && onDeactivate(expense.id)}
                    disabled={!expense.id}
                    className="text-[#E5A100] hover:text-[#E5A100]/80 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Deactivate
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
