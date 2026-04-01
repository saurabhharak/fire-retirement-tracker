import { describe, it, expect } from "vitest";
import { toMonthlyAmount } from "../expenseUtils";

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
