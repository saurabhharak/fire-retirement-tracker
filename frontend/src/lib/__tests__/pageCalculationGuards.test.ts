import { describe, it, expect } from "vitest";

// Shared pure helpers extracted for testability. Each mirrors the corresponding
// bug the test guards against.

// ---- RetirementAnalysis: bucket tooltip double-multiply ----
export function bucketTooltipPct(pct: number): number {
  // Buggy version returned pct * 100 * 100 = 800% for a Safety bucket (8%).
  return pct * 100;
}

// ---- SipTracker: planned SIP for a given month index ----
export function plannedSipForIndex(sips: number[], monthIndex: number): number {
  return sips[monthIndex] ?? 0;
}

// ---- PreciousMetals: sign rendering ----
export function formatPnl(totalPnl: number, totalPnlPct: number): string {
  const sign = totalPnl >= 0 ? "+" : "-";
  return `${sign}₹${Math.round(Math.abs(totalPnl)).toLocaleString("en-IN")} (${totalPnlPct.toFixed(2)}%)`;
}

// ---- FundAllocation: category color key ----
export function badgeColorKey(category: string): string {
  // Backend sends lowercase "precious_metals"; the old color map keyed "Gold".
  const map: Record<string, string> = {
    equity: "Equity",
    debt: "Debt",
    precious_metals: "Gold",
    cash: "Cash",
  };
  return map[category] ?? "Other";
}

describe("RetirementAnalysis bucket tooltip pct", () => {
  it("shows 8% for a Safety bucket, not 800%", () => {
    expect(bucketTooltipPct(0.08)).toBe(8);
  });
  it("shows 27% for Income, not 2700%", () => {
    expect(bucketTooltipPct(0.27)).toBe(27);
  });
});

describe("SipTracker planned SIP by index", () => {
  it("returns the planned SIP at the logged month index", () => {
    const sips = [50000, 55000, 60500];
    expect(plannedSipForIndex(sips, 0)).toBe(50000);
    expect(plannedSipForIndex(sips, 2)).toBe(60500);
  });
});

describe("PreciousMetals P&L formatting", () => {
  it("renders a negative P&L with a minus sign", () => {
    const out = formatPnl(-5000, -2.5);
    expect(out).toContain("-₹5,000");
    expect(out).toContain("(-2.50%)");
  });
  it("renders a positive P&L with a plus sign", () => {
    const out = formatPnl(1234, 0.6);
    expect(out).toContain("+₹1,234");
  });
});

describe("FundAllocation badge color keys", () => {
  it("maps precious_metals to the Gold color key", () => {
    expect(badgeColorKey("precious_metals")).toBe("Gold");
  });
  it("maps lowercase equity/debt/cash correctly", () => {
    expect(badgeColorKey("equity")).toBe("Equity");
    expect(badgeColorKey("debt")).toBe("Debt");
    expect(badgeColorKey("cash")).toBe("Cash");
  });
});
