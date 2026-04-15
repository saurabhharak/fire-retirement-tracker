import { MetricCard } from "../MetricCard";
import { formatRupees } from "../../lib/formatIndian";

interface FinancialSummaryProps {
  yourIncome: number;
  wifeIncome: number;
  totalIncome: number;
  fixedExpenseMonthly: number;
  totalSip: number;
  savings: number;
  savingsRate: number;
  noIncomeForMonth?: boolean;
}

export function FinancialSummary({
  yourIncome,
  wifeIncome,
  totalIncome,
  fixedExpenseMonthly,
  totalSip,
  savings,
  savingsRate,
  noIncomeForMonth,
}: FinancialSummaryProps) {
  return (
    <section>
      <h2 className="text-lg font-semibold text-[#E8ECF1] mb-4">
        Financial Summary
      </h2>
      {noIncomeForMonth && (
        <p className="text-sm text-[#E5A100] mb-3">
          No income recorded for this month. Showing zeros for income fields.
        </p>
      )}
      {/* Income row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <MetricCard label="Your Income" value={yourIncome} />
        <MetricCard label="Wife's Income" value={wifeIncome} />
        <MetricCard label="Total Income" value={totalIncome} color="gold" />
      </div>
      {/* Expense row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Fixed Expenses" value={Math.round(fixedExpenseMonthly)} />
        <MetricCard label="SIP Investment" value={totalSip} color="gold" />
        <MetricCard label="Cash Left" value={Math.round(Math.max(0, savings - totalSip))} />
        <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30">
          <p className="text-sm text-[#E8ECF1]/60 mb-1">Savings (Inc - Exp)</p>
          <p
            className={`text-2xl font-bold ${savings >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}
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
  );
}
