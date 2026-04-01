import { useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { useIncome } from "../hooks/useIncome";
import type { IncomeEntry } from "../hooks/useIncome";
import { useExpenses } from "../hooks/useExpenses";
import type { FixedExpense } from "../hooks/useExpenses";
import { useFireInputs } from "../hooks/useFireInputs";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { formatRupees, formatIndian } from "../lib/formatIndian";
import { toMonthlyAmount } from "../lib/expenseUtils";

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const PIE_COLORS = {
  sip: "#00895E",
  your: "#D4A843",
  wife: "#E07A5F",
  household: "#6B7280",
  savings: "#3B82F6",
};

/* ---------- Income Form ---------- */
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

/* ---------- Expense Form ---------- */
interface ExpenseFormState {
  name: string;
  owner: string;
  amount: number | "";
  frequency: "monthly" | "quarterly" | "yearly" | "one-time";
}

const emptyExpenseForm = (): ExpenseFormState => ({
  name: "",
  owner: "you",
  amount: "",
  frequency: "monthly",
});

/* ========== Main Component ========== */
export default function IncomeExpenses() {
  const income = useIncome(24);
  const expenses = useExpenses(true);
  const fireInputs = useFireInputs();

  /* Income form state */
  const [incomeForm, setIncomeForm] = useState<IncomeFormState>(emptyIncomeForm());
  const [editingIncome, setEditingIncome] = useState<string | null>(null); // "month-year"
  const [editForm, setEditForm] = useState<IncomeFormState>(emptyIncomeForm());
  const [incomeSaving, setIncomeSaving] = useState(false);

  /* Expense form state */
  const [expenseForm, setExpenseForm] = useState<ExpenseFormState>(emptyExpenseForm());
  const [expenseSaving, setExpenseSaving] = useState(false);

  /* Show/hide add forms */
  const [showIncomeForm, setShowIncomeForm] = useState(false);
  const [showExpenseForm, setShowExpenseForm] = useState(false);

  /* Loading */
  if (income.isLoading || expenses.isLoading || fireInputs.isLoading) {
    return <LoadingState message="Loading income & expenses..." />;
  }

  /* ---------- Derived Calculations ---------- */
  const latestIncome = income.entries.length > 0 ? income.entries[0] : null;
  const yourIncome = latestIncome?.your_income ?? 0;
  const wifeIncome = latestIncome?.wife_income ?? 0;
  const totalIncome = yourIncome + wifeIncome;

  const inputs = fireInputs.data;
  const totalSip = (inputs?.your_sip ?? 0) + (inputs?.wife_sip ?? 0);

  const fixedExpenseMonthly = expenses.entries.reduce(
    (sum: number, e: FixedExpense) => sum + toMonthlyAmount(e.amount, e.frequency),
    0
  );

  const totalOutflow = fixedExpenseMonthly + totalSip;
  const savings = totalIncome - totalOutflow;
  const savingsRate = totalIncome > 0 ? Math.round((savings / totalIncome) * 1000) / 10 : 0;

  /* Expense breakdown by owner */
  const yourExpenses = expenses.entries
    .filter((e: FixedExpense) => e.owner === "you")
    .reduce((sum: number, e: FixedExpense) => sum + toMonthlyAmount(e.amount, e.frequency), 0);
  const wifeExpenses = expenses.entries
    .filter((e: FixedExpense) => e.owner === "wife")
    .reduce((sum: number, e: FixedExpense) => sum + toMonthlyAmount(e.amount, e.frequency), 0);
  const householdExpenses = expenses.entries
    .filter((e: FixedExpense) => e.owner === "household" || (!e.owner))
    .reduce((sum: number, e: FixedExpense) => sum + toMonthlyAmount(e.amount, e.frequency), 0);

  /* Pie chart data */
  const pieData = [
    { name: "SIP", value: Math.round(totalSip), color: PIE_COLORS.sip },
    { name: "Your Expenses", value: Math.round(yourExpenses), color: PIE_COLORS.your },
    { name: "Wife Expenses", value: Math.round(wifeExpenses), color: PIE_COLORS.wife },
    { name: "Household", value: Math.round(householdExpenses), color: PIE_COLORS.household },
    { name: "Savings", value: Math.round(Math.max(0, savings - totalSip)), color: PIE_COLORS.savings },
  ].filter((d) => d.value > 0);

  /* ---------- Handlers ---------- */
  async function handleIncomeSave(e: React.FormEvent) {
    e.preventDefault();
    setIncomeSaving(true);
    try {
      await income.save({
        month: incomeForm.month,
        year: incomeForm.year,
        your_income: Number(incomeForm.your_income) || 0,
        wife_income: Number(incomeForm.wife_income) || 0,
        notes: incomeForm.notes,
      });
      setIncomeForm(emptyIncomeForm());
      setShowIncomeForm(false);
    } finally {
      setIncomeSaving(false);
    }
  }

  async function handleIncomeEdit(e: React.FormEvent) {
    e.preventDefault();
    setIncomeSaving(true);
    try {
      await income.save({
        month: editForm.month,
        year: editForm.year,
        your_income: Number(editForm.your_income) || 0,
        wife_income: Number(editForm.wife_income) || 0,
        notes: editForm.notes,
      });
      setEditingIncome(null);
    } finally {
      setIncomeSaving(false);
    }
  }

  async function handleIncomeDelete(entry: IncomeEntry) {
    if (!window.confirm("Delete this income entry?")) return;
    await income.remove({ month: entry.month, year: entry.year });
  }

  function startEditIncome(entry: IncomeEntry) {
    setEditingIncome(`${entry.month}-${entry.year}`);
    setEditForm({
      month: entry.month,
      year: entry.year,
      your_income: entry.your_income,
      wife_income: entry.wife_income,
      notes: entry.notes,
    });
  }

  async function handleExpenseSave(e: React.FormEvent) {
    e.preventDefault();
    setExpenseSaving(true);
    try {
      await expenses.save({
        name: expenseForm.name,
        owner: expenseForm.owner,
        amount: Number(expenseForm.amount) || 0,
        frequency: expenseForm.frequency,
      });
      setExpenseForm(emptyExpenseForm());
      setShowExpenseForm(false);
    } finally {
      setExpenseSaving(false);
    }
  }

  async function handleExpenseDeactivate(id: string) {
    if (!window.confirm("Deactivate this expense?")) return;
    await expenses.deactivate(id);
  }

  /* Shared input classes */
  const inputCls =
    "w-full bg-[#0D1B2A] border border-[#1A3A5C] rounded-lg px-3 py-2 text-[#E8ECF1] text-sm focus:outline-none focus:border-[#00895E] transition-colors";
  const btnPrimary =
    "px-4 py-2 bg-[#00895E] text-white text-sm font-medium rounded-lg hover:bg-[#00895E]/80 transition-colors disabled:opacity-50";
  const btnSecondary =
    "px-4 py-2 bg-[#1A3A5C]/40 text-[#E8ECF1]/80 text-sm font-medium rounded-lg hover:bg-[#1A3A5C]/60 transition-colors";

  return (
    <div className="space-y-8">
      <PageHeader
        title="Income & Expenses"
        subtitle="Track your monthly income and fixed expenses"
      />

      {/* ====== Financial Summary ====== */}
      <section>
        <h2 className="text-lg font-semibold text-[#E8ECF1] mb-4">
          Financial Summary
        </h2>
        {/* Income row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <MetricCard label="Your Income" value={yourIncome} />
          <MetricCard label="Wife's Income" value={wifeIncome} />
          <MetricCard label="Total Income" value={totalIncome} color="gold" />
        </div>
        {/* Expense row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="Fixed Expenses" value={Math.round(fixedExpenseMonthly)} />
          <MetricCard label="Total SIP" value={totalSip} color="success" />
          <MetricCard label="Total Outflow" value={Math.round(totalOutflow)} color="warning" />
          <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
            <p className="text-sm text-[#E8ECF1]/60 mb-1">Savings</p>
            <p
              className={`text-2xl font-bold ${savings >= 0 ? "text-[#00895E]" : "text-[#C45B5B]"}`}
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {formatRupees(Math.round(savings))}
            </p>
            <p className="text-xs text-[#E8ECF1]/40 mt-1">
              {savingsRate}% savings rate
            </p>
          </div>
        </div>
      </section>

      {/* ====== Where Your Money Goes ====== */}
      {pieData.length > 0 && (
        <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
          <h2 className="text-lg font-semibold text-[#E8ECF1] mb-6">
            Where Your Money Goes
          </h2>
          <div className="flex flex-col lg:flex-row items-center gap-8">
            <div className="w-64 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#132E3D",
                      border: "1px solid #1A3A5C",
                      borderRadius: "8px",
                      color: "#E8ECF1",
                    }}
                    formatter={(value: number) => [formatRupees(value), ""]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-3">
              {pieData.map((item) => (
                <div key={item.name} className="flex items-center gap-3">
                  <span
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm text-[#E8ECF1]/80 w-32">
                    {item.name}
                  </span>
                  <span className="text-sm font-medium text-[#E8ECF1]">
                    {formatRupees(item.value)}
                  </span>
                  <span className="text-xs text-[#E8ECF1]/40">
                    {totalIncome > 0
                      ? `${Math.round((item.value / totalIncome) * 100)}%`
                      : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ====== Income Log ====== */}
      <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-[#E8ECF1]">
            Income Log
          </h2>
          <button
            onClick={() => setShowIncomeForm(!showIncomeForm)}
            className={btnPrimary}
          >
            {showIncomeForm ? "Cancel" : "+ Add Income"}
          </button>
        </div>

        {/* Add Income Form */}
        {showIncomeForm && (
          <form
            onSubmit={handleIncomeSave}
            className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#1A3A5C]/30 grid grid-cols-1 md:grid-cols-6 gap-3 items-end"
          >
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Month
              </label>
              <select
                value={incomeForm.month}
                onChange={(e) =>
                  setIncomeForm({ ...incomeForm, month: Number(e.target.value) })
                }
                className={inputCls}
              >
                {MONTH_NAMES.map((m, i) => (
                  <option key={i} value={i + 1}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Year
              </label>
              <input
                type="number"
                value={incomeForm.year}
                onChange={(e) =>
                  setIncomeForm({ ...incomeForm, year: Number(e.target.value) })
                }
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Your Income
              </label>
              <input
                type="number"
                placeholder="0"
                value={incomeForm.your_income}
                onChange={(e) =>
                  setIncomeForm({
                    ...incomeForm,
                    your_income: e.target.value === "" ? "" : Number(e.target.value),
                  })
                }
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Wife's Income
              </label>
              <input
                type="number"
                placeholder="0"
                value={incomeForm.wife_income}
                onChange={(e) =>
                  setIncomeForm({
                    ...incomeForm,
                    wife_income: e.target.value === "" ? "" : Number(e.target.value),
                  })
                }
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Notes
              </label>
              <input
                type="text"
                placeholder="Optional"
                value={incomeForm.notes}
                onChange={(e) =>
                  setIncomeForm({ ...incomeForm, notes: e.target.value })
                }
                className={inputCls}
              />
            </div>
            <button type="submit" disabled={incomeSaving} className={btnPrimary}>
              {incomeSaving ? "Saving..." : "Save"}
            </button>
          </form>
        )}

        {/* Income Table */}
        {income.entries.length === 0 ? (
          <EmptyState
            message="No income records yet. Add your first entry above."
            actionLabel="Add Income"
            onAction={() => setShowIncomeForm(true)}
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
                {income.entries.map((entry: IncomeEntry) => {
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
                              setEditForm({
                                ...editForm,
                                your_income:
                                  e.target.value === ""
                                    ? ""
                                    : Number(e.target.value),
                              })
                            }
                            className={`${inputCls} w-28 text-right`}
                          />
                        </td>
                        <td className="py-2 px-2">
                          <input
                            type="number"
                            value={editForm.wife_income}
                            onChange={(e) =>
                              setEditForm({
                                ...editForm,
                                wife_income:
                                  e.target.value === ""
                                    ? ""
                                    : Number(e.target.value),
                              })
                            }
                            className={`${inputCls} w-28 text-right`}
                          />
                        </td>
                        <td className="py-2 px-2 text-right text-[#E8ECF1]/40">
                          --
                        </td>
                        <td className="py-2 px-2">
                          <input
                            type="text"
                            value={editForm.notes}
                            onChange={(e) =>
                              setEditForm({ ...editForm, notes: e.target.value })
                            }
                            className={`${inputCls} w-32`}
                          />
                        </td>
                        <td className="py-2 px-2 text-right space-x-2">
                          <button
                            onClick={handleIncomeEdit}
                            disabled={incomeSaving}
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
                      <td className="py-3 px-2 text-[#E8ECF1]/60">
                        {entry.notes || "--"}
                      </td>
                      <td className="py-3 px-2 text-right space-x-2">
                        <button
                          onClick={() => startEditIncome(entry)}
                          className="text-[#3B82F6] hover:text-[#3B82F6]/80 text-xs font-medium"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleIncomeDelete(entry)}
                          className="text-[#C45B5B] hover:text-[#C45B5B]/80 text-xs font-medium"
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

      {/* ====== Fixed Expenses ====== */}
      <section className="bg-[#1A3A5C]/20 backdrop-blur-sm rounded-2xl p-6 border border-white/5">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-lg font-semibold text-[#E8ECF1]">
              Fixed Expenses
            </h2>
            <p className="text-xs text-[#E8ECF1]/40 mt-1">
              Monthly recurring total:{" "}
              <span className="text-[#D4A843] font-medium">
                {formatRupees(Math.round(fixedExpenseMonthly))}
              </span>
            </p>
          </div>
          <button
            onClick={() => setShowExpenseForm(!showExpenseForm)}
            className={btnPrimary}
          >
            {showExpenseForm ? "Cancel" : "+ Add Expense"}
          </button>
        </div>

        {/* Add Expense Form */}
        {showExpenseForm && (
          <form
            onSubmit={handleExpenseSave}
            className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#1A3A5C]/30 grid grid-cols-1 md:grid-cols-5 gap-3 items-end"
          >
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Name
              </label>
              <input
                type="text"
                placeholder="Expense name"
                value={expenseForm.name}
                onChange={(e) =>
                  setExpenseForm({ ...expenseForm, name: e.target.value })
                }
                required
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Owner
              </label>
              <select
                value={expenseForm.owner}
                onChange={(e) =>
                  setExpenseForm({ ...expenseForm, owner: e.target.value })
                }
                className={inputCls}
              >
                <option value="you">You</option>
                <option value="wife">Wife</option>
                <option value="household">Household</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Amount
              </label>
              <input
                type="number"
                placeholder="0"
                value={expenseForm.amount}
                onChange={(e) =>
                  setExpenseForm({
                    ...expenseForm,
                    amount: e.target.value === "" ? "" : Number(e.target.value),
                  })
                }
                required
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-[#E8ECF1]/60 mb-1">
                Frequency
              </label>
              <select
                value={expenseForm.frequency}
                onChange={(e) =>
                  setExpenseForm({
                    ...expenseForm,
                    frequency: e.target.value as ExpenseFormState["frequency"],
                  })
                }
                className={inputCls}
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
                <option value="one-time">One-time</option>
              </select>
            </div>
            <button type="submit" disabled={expenseSaving} className={btnPrimary}>
              {expenseSaving ? "Saving..." : "Save"}
            </button>
          </form>
        )}

        {/* Expenses Table */}
        {expenses.entries.length === 0 ? (
          <EmptyState
            message="No fixed expenses yet. Add your first expense above."
            actionLabel="Add Expense"
            onAction={() => setShowExpenseForm(true)}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#E8ECF1]/40 text-xs uppercase tracking-wider border-b border-[#1A3A5C]/30">
                  <th className="text-left py-3 px-2">Name</th>
                  <th className="text-left py-3 px-2">Owner</th>
                  <th className="text-right py-3 px-2">Amount</th>
                  <th className="text-left py-3 px-2">Frequency</th>
                  <th className="text-right py-3 px-2">Monthly Equiv.</th>
                  <th className="text-right py-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {expenses.entries.map((expense: FixedExpense) => (
                  <tr
                    key={expense.id ?? expense.name}
                    className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10 transition-colors"
                  >
                    <td className="py-3 px-2 text-[#E8ECF1]">{expense.name}</td>
                    <td className="py-3 px-2">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          expense.owner === "you"
                            ? "bg-[#D4A843]/20 text-[#D4A843]"
                            : expense.owner === "wife"
                            ? "bg-[#E07A5F]/20 text-[#E07A5F]"
                            : "bg-[#6B7280]/20 text-[#6B7280]"
                        }`}
                      >
                        {expense.owner === "you"
                          ? "You"
                          : expense.owner === "wife"
                          ? "Wife"
                          : "Household"}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-right text-[#E8ECF1]">
                      {formatRupees(expense.amount)}
                    </td>
                    <td className="py-3 px-2 text-[#E8ECF1]/60 capitalize">
                      {expense.frequency}
                    </td>
                    <td className="py-3 px-2 text-right text-[#E8ECF1]/60">
                      {formatRupees(Math.round(toMonthlyAmount(expense.amount, expense.frequency)))}
                    </td>
                    <td className="py-3 px-2 text-right">
                      <button
                        onClick={() =>
                          expense.id && handleExpenseDeactivate(expense.id)
                        }
                        className="text-[#C45B5B] hover:text-[#C45B5B]/80 text-xs font-medium"
                      >
                        Deactivate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
