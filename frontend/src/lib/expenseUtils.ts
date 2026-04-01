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
