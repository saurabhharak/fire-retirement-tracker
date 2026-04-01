import { describe, it, expect } from "vitest";
import { formatIndian, formatRupees } from "../formatIndian";

describe("formatIndian", () => {
  it("formats small numbers without commas", () => {
    expect(formatIndian(500)).toBe("500");
  });

  it("formats thousands", () => {
    expect(formatIndian(1250)).toBe("1,250");
  });

  it("formats lakhs", () => {
    expect(formatIndian(125000)).toBe("1,25,000");
  });

  it("formats crores", () => {
    expect(formatIndian(10844030)).toBe("1,08,44,030");
  });

  it("handles negative numbers", () => {
    expect(formatIndian(-50000)).toBe("-50,000");
  });

  it("handles zero", () => {
    expect(formatIndian(0)).toBe("0");
  });

  it("rounds floats", () => {
    expect(formatIndian(1234.56)).toBe("1,235");
  });

  it("formats large crore values", () => {
    expect(formatIndian(108440302)).toBe("10,84,40,302");
  });
});

describe("formatRupees", () => {
  it("prepends rupee symbol", () => {
    expect(formatRupees(125000)).toBe("₹1,25,000");
  });

  it("handles negative with rupee symbol", () => {
    expect(formatRupees(-50000)).toBe("₹-50,000");
  });
});
