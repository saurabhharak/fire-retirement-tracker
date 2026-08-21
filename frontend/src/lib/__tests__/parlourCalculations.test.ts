import { describe, it, expect } from "vitest";
import {
  dailyTotal,
  trendChartData,
  periodLabel,
  formatPeriodValue,
  type TrendData,
} from "../parlourCalculations";

describe("dailyTotal", () => {
  it("sums cash + online", () => {
    expect(dailyTotal({ cash_amount: 2750, online_amount: 5769 })).toBe(8519);
  });

  it("handles missing amounts as zero", () => {
    expect(dailyTotal({ cash_amount: 100 })).toBe(100);
    expect(dailyTotal({})).toBe(0);
  });

  it("handles string amounts from the API", () => {
    expect(dailyTotal({ cash_amount: "2750", online_amount: "5769" })).toBe(8519);
  });
});

describe("trendChartData", () => {
  it("aligns and sorts by month", () => {
    const trends: TrendData = {
      labels: ["2026-08", "2026-07"],
      sales: [5000, 3000],
      purchases: [2000, 1000],
      expenses: [500, 300],
      profit: [2500, 1700],
    };
    const data = trendChartData(trends);
    expect(data.map((d) => d.month)).toEqual(["2026-07", "2026-08"]);
    expect(data[0].sales).toBe(3000);
    expect(data[0].purchases).toBe(1000);
    expect(data[0].expenses).toBe(300);
    expect(data[0].profit).toBe(1700);
  });

  it("returns empty array for empty trends", () => {
    expect(
      trendChartData({ labels: [], sales: [], purchases: [], expenses: [], profit: [] })
    ).toEqual([]);
  });

  it("handles missing arrays defensively", () => {
    expect(trendChartData({ labels: ["2026-07"], sales: [1] } as TrendData)).toHaveLength(0);
  });
});

describe("periodLabel", () => {
  it("maps period to label", () => {
    expect(periodLabel("day")).toBe("Daily");
    expect(periodLabel("month")).toBe("Monthly");
    expect(periodLabel("quarter")).toBe("Quarterly");
    expect(periodLabel("year")).toBe("Annual");
  });

  it("defaults to Monthly for unknown", () => {
    expect(periodLabel("decade" as "month")).toBe("Monthly");
  });
});

describe("formatPeriodValue", () => {
  it("formats a day", () => {
    expect(formatPeriodValue("2026-08-15")).toBe("15 August 2026");
  });

  it("formats a month", () => {
    expect(formatPeriodValue("2026-07")).toBe("July 2026");
  });

  it("formats a quarter", () => {
    expect(formatPeriodValue("2026-Q3")).toBe("Q3 2026");
  });

  it("formats a year", () => {
    expect(formatPeriodValue("2026")).toBe("2026");
  });

  it("returns empty for missing", () => {
    expect(formatPeriodValue()).toBe("");
  });
});
