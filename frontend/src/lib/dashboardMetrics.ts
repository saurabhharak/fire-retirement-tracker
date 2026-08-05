import type { FireInputsData } from "../hooks/useFireInputs";
import { effectiveMonthlyAmount } from "./expenseUtils";

interface ExpenseLike {
  amount: number;
  frequency: string;
}

export interface DashboardMetrics {
  currentAge: number;
  yearsToRetirement: number;
  monthsRemaining: number;
  countdownYears: number;
  countdownMonths: number;
  progressPct: number;
  fixedExpenseTotal: number;
  totalSip: number;
  monthlySavings: number;
  totalNetWorth: number;
}

interface ComputeOptions {
  inputs: FireInputsData;
  today?: Date;
  expenses?: ExpenseLike[];
  sipTotalInvested?: number;
  metalsValue?: number;
}

/**
 * All dashboard derived calculations in one place.
 *
 * - Age uses fractional years so the countdown can show real months.
 * - One-time expenses are EXCLUDED from the monthly expense total
 *   (matching the backend retirement engine and the Income & Expenses page).
 * - Progress is measured from current age (no hardcoded 25 start).
 */
export function computeDashboardMetrics({
  inputs,
  today = new Date(),
  expenses = [],
  sipTotalInvested = 0,
  metalsValue = 0,
}: ComputeOptions): DashboardMetrics {
  const dob = new Date(inputs.dob);
  const fractionalAge = (today.getTime() - dob.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
  const currentAge = Math.floor(fractionalAge);

  const yearsToRetirement = Math.max(0, inputs.retirement_age - currentAge);

  // Fractional months remaining, floored, so the countdown shows real months.
  const monthsRemaining = Math.max(
    0,
    Math.floor((inputs.retirement_age - fractionalAge) * 12),
  );
  const countdownYears = Math.floor(monthsRemaining / 12);
  const countdownMonths = monthsRemaining % 12;

  // Progress toward retirement: fraction of the journey from birth to the
  // retirement age already completed. No hardcoded career-start age.
  const progressPct =
    inputs.retirement_age > 0
      ? Math.min(100, Math.max(0, Math.round((currentAge / inputs.retirement_age) * 100)))
      : 0;

  // Monthly expenses: recurring only (one-time expenses are NOT monthly).
  const fixedExpenseTotal = expenses.reduce((sum, e) => {
    if (e.frequency === "one-time") return sum;
    return sum + effectiveMonthlyAmount(e.amount, e.frequency);
  }, 0);

  const totalSip = (inputs.your_sip ?? 0) + (inputs.wife_sip ?? 0);
  const monthlySavings = 0 - fixedExpenseTotal; // income is not part of the inputs here

  const totalNetWorth = (inputs.existing_corpus ?? 0) + sipTotalInvested + metalsValue;

  return {
    currentAge,
    yearsToRetirement,
    monthsRemaining,
    countdownYears,
    countdownMonths,
    progressPct,
    fixedExpenseTotal,
    totalSip,
    monthlySavings,
    totalNetWorth,
  };
}

// Re-export so the Dashboard and tests share one implementation of "is this a
// monthly expense?".
export { effectiveMonthlyAmount };
