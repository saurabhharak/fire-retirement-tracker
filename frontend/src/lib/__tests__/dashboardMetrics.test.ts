import { describe, it, expect } from "vitest";
import { computeDashboardMetrics } from "../dashboardMetrics";

const BASE_INPUTS = {
  dob: "1997-07-11",
  retirement_age: 50,
  life_expectancy: 90,
  your_sip: 200000,
  wife_sip: 50000,
  step_up_pct: 0.1,
  existing_corpus: 0,
  equity_return: 0.11,
  debt_return: 0.07,
  precious_metals_return: 0.09,
  cash_return: 0.035,
  inflation: 0.06,
  swr: 0.03,
  equity_pct: 0.8,
  precious_metals_pct: 0.05,
  cash_pct: 0.02,
  monthly_expense: 125000,
};

const RECURRING = { frequency: "monthly" as const, amount: 10000 };
const QUARTERLY = { frequency: "quarterly" as const, amount: 9000 };
const YEARLY = { frequency: "yearly" as const, amount: 120000 };
const ONE_TIME = { frequency: "one-time" as const, amount: 200000 };

describe("computeDashboardMetrics countdown", () => {
  it("computes fractional months remaining instead of always 0", () => {
    // dob 1997-07-11 -> ~29.06y today (2026-08-05), retire at 50 => 20.94y => ~251 months
    const m = computeDashboardMetrics({ inputs: BASE_INPUTS, today: new Date(2026, 7, 5) });
    expect(m.yearsToRetirement).toBeGreaterThan(20);
    expect(m.monthsRemaining).toBeGreaterThan(240);
    // The buggy version computed monthsRemaining = floor(years)*12 => countdownMonths always 0.
    expect(m.countdownMonths).toBeGreaterThan(0);
  });

  it("reports 0 years / 0 months when already retired", () => {
    const m = computeDashboardMetrics({
      inputs: { ...BASE_INPUTS, dob: "1950-01-01" },
      today: new Date(2026, 7, 5),
    });
    expect(m.yearsToRetirement).toBe(0);
    expect(m.countdownMonths).toBe(0);
  });
});

describe("computeDashboardMetrics fixed expenses", () => {
  it("excludes one-time expenses from the monthly total", () => {
    const m = computeDashboardMetrics({
      inputs: BASE_INPUTS,
      expenses: [RECURRING, QUARTERLY, YEARLY, ONE_TIME],
      today: new Date(2026, 7, 5),
    });
    // 10000 + 3000 + 10000 = 23000; one-time 200000 excluded
    expect(m.fixedExpenseTotal).toBe(23000);
  });
});

describe("computeDashboardMetrics progress", () => {
  it("measures progress from birth to retirement age (no hardcoded 25 start)", () => {
    const m = computeDashboardMetrics({
      inputs: { ...BASE_INPUTS, dob: "1986-07-11" }, // ~40y today
      today: new Date(2026, 7, 5),
    });
    // 40 / 50 = 80% of the journey to retirement age 50.
    expect(m.progressPct).toBe(80);
  });

  it("reports 100% when at retirement age", () => {
    const m = computeDashboardMetrics({
      inputs: { ...BASE_INPUTS, dob: "1976-07-11" }, // ~50y today
      today: new Date(2026, 7, 5),
    });
    expect(m.yearsToRetirement).toBe(0);
    expect(m.progressPct).toBe(100);
  });
});

describe("computeDashboardMetrics net worth", () => {
  it("adds existing corpus, SIP invested, and metals without double counting", () => {
    const m = computeDashboardMetrics({
      inputs: { ...BASE_INPUTS, existing_corpus: 1000000 },
      sipTotalInvested: 200000,
      metalsValue: 300000,
      today: new Date(2026, 7, 5),
    });
    expect(m.totalNetWorth).toBe(1500000);
  });
});
