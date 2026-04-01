import type { FixedExpense } from "../../hooks/useExpenses";
import { formatRupees } from "../../lib/formatIndian";
import { effectiveMonthlyAmount, isExpenseInMonth } from "../../lib/expenseUtils";

interface OwnerTotalsBarProps {
  expenses: FixedExpense[];
  month: number;
  year: number;
}

function calcOwnerTotal(expenses: FixedExpense[], owner: string, month: number, year: number): number {
  return expenses
    .filter((e) => (e.owner ?? "household") === owner)
    .filter((e) => isExpenseInMonth(e, month, year))
    .reduce((sum, e) => sum + effectiveMonthlyAmount(e.amount, e.frequency), 0);
}

export function OwnerTotalsBar({ expenses, month, year }: OwnerTotalsBarProps) {
  const youTotal = calcOwnerTotal(expenses, "you", month, year);
  const wifeTotal = calcOwnerTotal(expenses, "wife", month, year);
  const householdTotal = calcOwnerTotal(expenses, "household", month, year);
  const grandTotal = youTotal + wifeTotal + householdTotal;

  const items = [
    { label: "You", value: youTotal, color: "text-[#D4A843]", bg: "bg-[#D4A843]/10" },
    { label: "Wife", value: wifeTotal, color: "text-[#E07A5F]", bg: "bg-[#E07A5F]/10" },
    { label: "Household", value: householdTotal, color: "text-[#6B7280]", bg: "bg-[#6B7280]/10" },
    { label: "Total", value: grandTotal, color: "text-[#00895E]", bg: "bg-[#00895E]/10" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
      {items.map((item) => (
        <div key={item.label} className={`${item.bg} rounded-lg px-3 py-2 border border-[#1A3A5C]/20`}>
          <p className="text-xs text-[#E8ECF1]/50">{item.label}</p>
          <p className={`text-sm font-semibold ${item.color}`} style={{ fontVariantNumeric: "tabular-nums" }}>
            {formatRupees(Math.round(item.value))}
          </p>
        </div>
      ))}
    </div>
  );
}
