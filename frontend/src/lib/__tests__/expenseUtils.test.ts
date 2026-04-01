import { describe, it, expect } from "vitest";
import { toMonthlyAmount, isExpenseInMonth, getExpenseAmountForMonth } from "../expenseUtils";

describe("toMonthlyAmount", () => {
  it("returns monthly amount as-is", () => {
    expect(toMonthlyAmount(3000, "monthly")).toBe(3000);
  });

  it("converts quarterly to monthly", () => {
    expect(toMonthlyAmount(9000, "quarterly")).toBe(3000);
  });

  it("converts yearly to monthly", () => {
    expect(toMonthlyAmount(12000, "yearly")).toBe(1000);
  });

  it("returns 0 for one-time expenses", () => {
    expect(toMonthlyAmount(50000, "one-time")).toBe(0);
  });

  it("handles unknown frequency as monthly", () => {
    expect(toMonthlyAmount(5000, "unknown")).toBe(5000);
  });
});

describe("isExpenseInMonth", () => {
  it("returns true for recurring expenses regardless of month", () => {
    expect(isExpenseInMonth({ frequency: "monthly" }, 3, 2026)).toBe(true);
    expect(isExpenseInMonth({ frequency: "quarterly" }, 6, 2026)).toBe(true);
    expect(isExpenseInMonth({ frequency: "yearly" }, 12, 2026)).toBe(true);
  });

  it("returns true for one-time expense matching month/year", () => {
    expect(
      isExpenseInMonth(
        { frequency: "one-time", expense_month: 4, expense_year: 2026 },
        4,
        2026,
      ),
    ).toBe(true);
  });

  it("returns false for one-time expense in different month", () => {
    expect(
      isExpenseInMonth(
        { frequency: "one-time", expense_month: 4, expense_year: 2026 },
        5,
        2026,
      ),
    ).toBe(false);
  });

  it("returns false for one-time expense in different year", () => {
    expect(
      isExpenseInMonth(
        { frequency: "one-time", expense_month: 4, expense_year: 2026 },
        4,
        2027,
      ),
    ).toBe(false);
  });

  it("returns false for one-time expense without month/year", () => {
    expect(isExpenseInMonth({ frequency: "one-time" }, 4, 2026)).toBe(false);
  });
});

describe("getExpenseAmountForMonth", () => {
  it("returns full amount for monthly", () => {
    expect(getExpenseAmountForMonth(3000, "monthly")).toBe(3000);
  });

  it("returns quarterly / 3", () => {
    expect(getExpenseAmountForMonth(9000, "quarterly")).toBe(3000);
  });

  it("returns yearly / 12", () => {
    expect(getExpenseAmountForMonth(12000, "yearly")).toBe(1000);
  });

  it("returns full amount for one-time", () => {
    expect(getExpenseAmountForMonth(50000, "one-time")).toBe(50000);
  });
});
