export function toMonthlyAmount(amount: number, frequency: string): number {
  switch (frequency) {
    case "quarterly":
      return amount / 3;
    case "yearly":
      return amount / 12;
    case "one-time":
      return 0;
    default:
      return amount; // monthly
  }
}

export function isExpenseInMonth(
  expense: { frequency: string; expense_month?: number; expense_year?: number },
  month: number,
  year: number,
): boolean {
  if (expense.frequency !== "one-time") return true;
  return expense.expense_month === month && expense.expense_year === year;
}

export function getExpenseAmountForMonth(
  amount: number,
  frequency: string,
): number {
  switch (frequency) {
    case "quarterly":
      return amount / 3;
    case "yearly":
      return amount / 12;
    case "one-time":
      return amount;
    default:
      return amount;
  }
}
