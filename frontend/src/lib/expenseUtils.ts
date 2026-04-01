/**
 * Returns the effective monthly amount for an expense based on its frequency.
 * - monthly   -> amount
 * - quarterly -> amount / 3
 * - yearly    -> amount / 12
 * - one-time  -> amount (the full amount charged in its specific month)
 */
export function effectiveMonthlyAmount(amount: number, frequency: string): number {
  switch (frequency) {
    case "quarterly":
      return amount / 3;
    case "yearly":
      return amount / 12;
    case "one-time":
      return amount;
    default:
      return amount; // monthly
  }
}

/**
 * Backward-compatible wrapper: converts a recurring expense to monthly.
 * One-time expenses return 0 (excluded from recurring monthly totals).
 */
export function toMonthlyAmount(amount: number, frequency: string): number {
  if (frequency === "one-time") return 0;
  return effectiveMonthlyAmount(amount, frequency);
}

export function isExpenseInMonth(
  expense: { frequency: string; expense_month?: number; expense_year?: number },
  month: number,
  year: number,
): boolean {
  if (expense.frequency !== "one-time") return true;
  return expense.expense_month === month && expense.expense_year === year;
}

/**
 * @deprecated Use effectiveMonthlyAmount instead.
 */
export function getExpenseAmountForMonth(
  amount: number,
  frequency: string,
): number {
  return effectiveMonthlyAmount(amount, frequency);
}
