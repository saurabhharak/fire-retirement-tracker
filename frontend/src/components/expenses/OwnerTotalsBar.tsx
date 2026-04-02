import type { FixedExpense } from "../../hooks/useExpenses";
import type { OwnerOption } from "./OwnerFilter";
import { formatRupees } from "../../lib/formatIndian";
import { effectiveMonthlyAmount } from "../../lib/expenseUtils";

interface OwnerTotalsBarProps {
  /** Pre-filtered expenses (month + tab, no owner filter) */
  expenses: FixedExpense[];
  ownerFilter: OwnerOption;
}

function calcOwnerTotal(expenses: FixedExpense[], owner: string): number {
  return expenses
    .filter((e) => (e.owner ?? "household") === owner)
    .reduce((sum, e) => sum + effectiveMonthlyAmount(e.amount, e.frequency), 0);
}

const ownerCards = [
  { key: "you", label: "You", color: "text-[#D4A843]", bg: "bg-[#D4A843]/10" },
  { key: "wife", label: "Wife", color: "text-[#E07A5F]", bg: "bg-[#E07A5F]/10" },
  { key: "household", label: "Household", color: "text-[#6B7280]", bg: "bg-[#6B7280]/10" },
] as const;

export function OwnerTotalsBar({ expenses, ownerFilter }: OwnerTotalsBarProps) {
  const totals: Record<"you" | "wife" | "household", number> = {
    you: calcOwnerTotal(expenses, "you"),
    wife: calcOwnerTotal(expenses, "wife"),
    household: calcOwnerTotal(expenses, "household"),
  };
  const grandTotal = totals.you + totals.wife + totals.household;

  // When a specific owner is selected, show only that owner + total
  const visibleCards = ownerFilter === "all"
    ? ownerCards
    : ownerCards.filter((c) => c.key === ownerFilter);

  return (
    <div className={`grid gap-3 mb-4 ${visibleCards.length === 1 ? "grid-cols-2" : "grid-cols-2 md:grid-cols-4"}`}>
      {visibleCards.map((card) => (
        <div key={card.key} className={`${card.bg} rounded-lg px-3 py-2 border border-[#1A3A5C]/20`}>
          <p className="text-xs text-[#E8ECF1]/50">{card.label}</p>
          <p className={`text-sm font-semibold ${card.color}`} style={{ fontVariantNumeric: "tabular-nums" }}>
            {formatRupees(Math.round(totals[card.key]))}
          </p>
        </div>
      ))}
      <div className="bg-[#00895E]/10 rounded-lg px-3 py-2 border border-[#1A3A5C]/20">
        <p className="text-xs text-[#E8ECF1]/50">Total</p>
        <p className="text-sm font-semibold text-[#00895E]" style={{ fontVariantNumeric: "tabular-nums" }}>
          {formatRupees(Math.round(ownerFilter === "all" ? grandTotal : totals[ownerFilter]))}
        </p>
      </div>
    </div>
  );
}
