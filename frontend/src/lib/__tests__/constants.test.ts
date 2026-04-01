import { describe, it, expect } from "vitest";
import { COLORS, NAV_ITEMS } from "../constants";

describe("COLORS", () => {
  it("has all required theme colors", () => {
    expect(COLORS.primary).toBe("#00895E");
    expect(COLORS.secondary).toBe("#D4A843");
    expect(COLORS.background).toBe("#0D1B2A");
    expect(COLORS.error).toBe("#C45B5B");
  });

  it("does not contain red (#FF0000)", () => {
    const values = Object.values(COLORS);
    expect(values).not.toContain("#FF0000");
    expect(values).not.toContain("#ff0000");
  });
});

describe("NAV_ITEMS", () => {
  it("has 8 navigation items", () => {
    expect(NAV_ITEMS).toHaveLength(8);
  });

  it("first item is Dashboard at root path", () => {
    expect(NAV_ITEMS[0].path).toBe("/");
    expect(NAV_ITEMS[0].label).toBe("Dashboard");
  });
});
