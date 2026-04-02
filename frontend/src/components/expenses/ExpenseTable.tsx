import type { FixedExpense } from "../../hooks/useExpenses";
import { formatRupees } from "../../lib/formatIndian";
import { effectiveMonthlyAmount } from "../../lib/expenseUtils";
import { MONTH_NAMES } from "../../lib/constants";

interface ExpenseTableProps {
  expenses: FixedExpense[];
  showOneTime: boolean;
  onDeactivate: (id: string) => void;
}

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

export function ExpenseTable({ expenses, showOneTime, onDeactivate }: ExpenseTableProps) {
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
            <th className="text-right py-3 px-2">Amount</th>
            <th className="text-left py-3 px-2">Frequency</th>
            {showOneTime && <th className="text-left py-3 px-2">Month/Year</th>}
            <th className="text-right py-3 px-2">Monthly Equiv.</th>
            <th className="text-right py-3 px-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {expenses.map((expense) => (
            <tr
              key={expense.id ?? expense.name}
              className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10 transition-colors"
            >
              <td className="py-3 px-2 text-[#E8ECF1]">{expense.name}</td>
              <td className="py-3 px-2">{ownerBadge(expense.owner)}</td>
              <td className="py-3 px-2 text-right text-[#E8ECF1]">
                {formatRupees(expense.amount)}
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
                  onClick={() => expense.id && onDeactivate(expense.id)}
                  disabled={!expense.id}
                  className="text-[#E5A100] hover:text-[#E5A100]/80 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Deactivate
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
